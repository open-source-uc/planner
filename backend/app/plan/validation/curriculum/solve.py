"""
Fill the slots of a curriculum with courses, making sure that there is no overlap
within a block and respecting exclusivity rules.

General program flow when solving a curriculum:
1. A curriculum tree is built from external sources such as SIDING (see
    `sync.siding.translate`).
2. Some hand-written transformations are applied on the tree (see
    `sync.siding.siding_rules`), and the result is a curriculum tree as defined in
    `plan.validation.curriculum.tree`.
    This tree is not yet a graph, but instead is a "blueprint" to build a graph later.
3. When a plan needs to be validated, `solve_curriculum` is called with the taken
    courses and the curriculum tree as arguments.
4. A flow network is built, with each unit of flow representing a single credit. Each
    unit of flow that reaches the flow sink represents a credit in the curriculum.
    Flow can be sourced from a taken course, or from a virtual filler course.
    Filler courses represent courses that have not yet been taken, but *could* be taken.
    While building the network graph, a table is kept that maps from course codes to
    edge IDs in the graph, so that later we can identify which edge represents which
    course.
5. Min-cost-max-flow is run on the flow network.
    Virtual filler courses are given a high cost so that concrete taken courses are
    always preferred.
6. Once `solve_curriculum` returns, other modules like
    `plan.validation.curriculum.diagnose` analyze which edges have flow in them.
    If an edge from a filler course has flow, it means that some block could not be
    satisfied only with taken courses, and the solver had to fall back to filler
    courses.
    In this case, we report an error to the user.
7. When a user's plan is missing a course, sometimes there are several filler courses
    that could plug the hole equally well (or at least similarly well).
    However, the flow algorithm has to choose 1 option, and chooses that option
    arbitrarily.
    In order to determine all of the options that could satisfy a course, we have to
    find cycles in the solved graph.
    The `EquivalentFillerFinder` class helps with this.


The solved network (which is different than the curriculum tree) looks like this:

         course       instance          block
          edge          edge            edge       curriculum-tree edges
infinite -----> course -----> instance -----> leaf ----->  tree   -----> curriculum
 source          node  ----->   nodes  -----> node        nodes...          root

Each edge and node fulfills a different role:
    - Infinite source: The global source of flow (supersource).
    - Course edge: Has the course multiplicity as its edge capacity. This edge limits
    the amount of times a particular course can be coursed and still count towards
    the curriculum.
    - Course node: Distributes available flow for a particular course code within the
    course instances.
    - Instance edge: Limits the amount of credits a single instance can provide, and
    has an associated cost that depends on the particular course instance.
    For example, taken courses have a low cost and filler courses have a high cost.
    - Instance node: Distribute the available flow of an instance across the different
    curriculum blocks that a course can provide.
    - Block edge: Carries the flow between a particular course instance and a
    particular curriculum block that is being fed.
    Note that the specific curriculum blocks that a course can provide does not
    depend only on its course code.
    In particular, concrete courses with an associated equivalence can only count
    towards blocks that accept the equivalence.
    However, the same course with the same code, but tagged with another
    equivalence, would count towards other blocks.
    - Leaf node: Accepts flow from a set of courses, defined by the leaf.
    Called a leaf node because leaves in the curriculum tree are nodes of this type.
    - Tree nodes: The rest of the nodes are part of the structure of the curriculum
    itself.
    These nodes form a tree that eventually ends up in the root node.
    - Root node: The root of the curriculum graph. All flow ends up here. This is
    usually also an infinite sink that accepts all flow.

Note that for optimization some nodes may not physically exist in the flow network.
For example, any node that has one input and one output is useless, and is usually
replaced by a single edge.
In general, any node with one output that has at least as much output capacity as it
has input capacity is useless.
Similarly, any node with one input that has at least as much input capacity as it
has output capacity is useless.
"""

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field

from ...course import ConcreteId, EquivalenceId, PseudoCourse
from ...courseinfo import CourseInfo
from .tree import SUPERBLOCK_PREFIX, Block, Curriculum, FillerCourse, Leaf

# Infinite placeholder.
# A huge value that still fits in a 64-bit integer.
INFINITY: int = 10**18
# Base cost of using a filler course. In contrast with a taken course, filler courses
# are virtual courses that are not actually taken by the user. Instead, filler courses
# serve as a "fallback" when a curriculum can't be filled with taken courses only.
FILLER_COST = 10**6
# Offset the cost of course-block edges by the order in which blocks are defined.
BLOCK_ORDER_COST = 10**3
# Offset the cost of course-block edges by the order in which courses appear in the
# plan.
COURSE_ORDER_COST = 10**0

# Up to what cost is still considered "small" when considering filler equivalents.
EQUIVALENT_FILLER_THRESHOLD = 10**3


@dataclass
class Edge:
    """
    Represents an edge in the curriculum graph.
    """

    debug_name: str
    id: int
    cap: int
    flow: int
    src: int
    dst: int
    rev: int
    cost: int = 0


@dataclass
class Node:
    """
    Represents a node in the curriculum graph.
    """

    debug_name: str
    outgoing: set[int] = field(default_factory=set)
    incoming: set[int] = field(default_factory=set)
    outgoing_active: set[int] = field(default_factory=set)

    def flow(self, g: "SolvedCurriculum") -> int:
        f = 0
        for edgeid in self.incoming:
            edge = g.edges[edgeid]
            if edge.flow >= 0:
                f += edge.flow
        return f

    def cap(self, g: "SolvedCurriculum") -> int:
        c = 0
        for edgeid in self.outgoing:
            edge = g.edges[edgeid]
            c += edge.cap
        return c

    def incoming_cap(self, g: "SolvedCurriculum") -> int:
        c = 0
        for edgeid in self.incoming:
            edge = g.edges[edgeid]
            c += edge.cap
        return c


@dataclass
class BlockEdgeInfo:
    """
    Represents an edge from a course instance to a block in the curriculum graph.

    If the edge has flow going through it, it means that the course was assigned to the
    blocks in `block_path`.

    - active_flow: The amount of flow in this course instance - leaf block association.
        If this amount is zero, the association is not made.
        If it is not zero, `flow` amount of credits are being assigned to the
        course-block pair.
    - block_path: The curriculum block that is connected to receive the flow through
        this edge.
        The first element is the root, the last element is the leaf and there is any
        number of elements in between.
    """

    active_flow: int
    block_path: tuple[Block, ...]

    edge_id: int


@dataclass
class LayerCourseInstance:
    """
    Represents an instance of a course associated to a layer.
    Therefore the name: layer-course-instance.

    References the edges and nodes in the graph associated to this course instance.
    In particular, it contains the amount of flow running through this course.

    - active_edge: The edge that is currently receiving flow from this course.
        There should only be zero or one edges, otherwise it's an error.
    - block_edges: All the blocks that are able to receive flow from this course.
        Only up to one course can actually receive flow, though.
    """

    active_edge: BlockEdgeInfo | None
    block_edges: list[BlockEdgeInfo]

    instance_node: int | None

    def instance_edge_id(self, g: "SolvedCurriculum") -> int:
        """
        Get the edge id unique to this layer-course-instance triple.
        If there is a dedicated instance node, returns the edge to this node.
        If there is no dedicated instance node, then there must be only one block edge.
        In this case, return the block edge id.
        """
        if self.instance_node is None:
            return self.block_edges[0].edge_id
        for edge_id in g.nodes[self.instance_node].incoming:
            edge = g.edges[edge_id]
            if edge.cap != 0:
                return edge_id
        raise Exception("instance node has no proper parent?")


@dataclass
class LayerCourse:
    """
    Represents a course within a layer.

    References the edges and nodes in the graph associated with this course.
    In particular, it allows access to the total amount of flow associated with this
    course code, and a list of the specific course instances and their flows.

    - instances: All of the course instances associated with this course.
        Keyed by the same instance index used in `g.usable`.
        Obtain this instance index from a normal instance index by calling `g.map_id()`.
        Note that some instances may not exist if they are not referenced in this layer!
    """

    instances: list[LayerCourseInstance | None]

    # The ID of the node that sources credit for instances of this course.
    # If the available amount of credits is lower than the multiplicity, this is the
    # global source.
    # If the available amount of credits is higher than the multiplicity, this is a node
    # specifically created to limit the amount of credits available to instances of this
    # course.
    credit_source_id: int


@dataclass
class Layer:
    """
    Links courses with graph edges (for a particular layer).
    Information about course matching can be extracted from here.
    """

    # Contains an entry for each course code.
    courses: dict[str, LayerCourse] = field(default_factory=dict)


@dataclass
class UsableInstance:
    """
    Represents an instance of a course within the plan.

    - code: The code associated with this course instance.
    - credits: How many credits does this course stand for.
    - filler: If this course is a filler course, this is the filler data.
    - instance_idx: The instance index of this course.
        Instance indices start from zero, and go up for each course with the same code.
        Instance indices for filler courses continue from the taken instance indices.
    - flat_order: The order of this course within the plan.
        Used for prioritization.
        The `flat_order` values of filler courses continues after taken courses.
    - original_pseudocourse: The original `PseudoCourse` instance that gave birth to
        this `UsableInstance`.
        Should not be used to identify the instance.
        In particular, do not use `original_pseudocourse.code`, since this would ignore
        all course equivalencies!
    """

    code: str
    credits: int
    filler: FillerCourse | None
    instance_idx: int
    flat_order: int
    original_pseudocourse: PseudoCourse


@dataclass
class UsableCourse:
    """
    Contains information about the instances of a particular course code that the user
    coursed or is able to course.
    """

    # The multiplicity of this course.
    # This is the maximum amount of credits that can flow through all instances.
    # If `None`, there is no limit on the amount of credits that can count.
    multiplicity: int | None
    # The total amount of credits in usable courses (taken + filler credits).
    total: int
    # Each course instance belonging to this course code.
    instances: list[UsableInstance]


class SolvedCurriculum:
    """
    Context necessary to solve a curriculum.
    Also holds the results of the solving process (hence the name).
    """

    # List of nodes.
    # The ID of each node is its index in this list.
    nodes: list[Node]
    # Flat list of edges.
    edges: list[Edge]
    # The id of the universal source
    source: int
    # The id of the universal sink
    sink: int
    # Maps courses to the graph structure that represents them.
    layers: defaultdict[str, Layer]
    # Taken courses (and filler courses).
    usable: dict[str, UsableCourse]
    # Indicates the main superblock that each course counts towards.
    superblocks: dict[str, list[str]]
    # Maps from original (code, repeat index) to curriculum (code, repeat index).
    mapping: dict[str, list[tuple[str, int]]]

    def __init__(self) -> None:
        self.nodes = [Node(debug_name="source"), Node(debug_name="sink")]
        self.edges = []
        self.source = 0
        self.sink = 1
        self.layers = defaultdict(Layer)
        self.usable = {}
        self.superblocks = {}
        self.mapping = {}

    def map_class_id(self, code: str, rep_idx: int) -> tuple[str, int] | None:
        """
        Given a class id in the original plan, get a class id in the internal plan.
        This does things like mapping courses to their equivalents.
        """
        if code not in self.mapping:
            return None
        if rep_idx >= len(self.mapping[code]) or rep_idx < 0:
            return None
        return self.mapping[code][rep_idx]

    def add(self, node: Node) -> int:
        """
        Add a node to the graph, returning its id.
        """

        id = len(self.nodes)
        self.nodes.append(node)
        return id

    def connect(
        self,
        debug_name: str,
        src_id: int,
        dst_id: int,
        cap: int,
        cost: int = 0,
    ) -> int:
        """
        Connect two nodes in the graph.
        Returns the edge id.
        """

        src = self.nodes[src_id]
        dst = self.nodes[dst_id]
        fw_id = len(self.edges)
        bk_id = len(self.edges) + 1
        edge_fw = Edge(
            debug_name=debug_name,
            id=fw_id,
            cap=cap,
            flow=0,
            src=src_id,
            dst=dst_id,
            rev=bk_id,
            cost=cost,
        )
        edge_rev = Edge(
            debug_name=f"-{debug_name}",
            id=bk_id,
            cap=0,
            flow=0,
            src=dst_id,
            dst=src_id,
            rev=fw_id,
            cost=-cost,
        )
        src.outgoing.add(fw_id)
        src.outgoing_active.add(fw_id)
        dst.incoming.add(fw_id)
        dst.outgoing.add(bk_id)
        src.incoming.add(bk_id)
        self.edges.append(edge_fw)
        self.edges.append(edge_rev)
        return fw_id

    def move_source(self, edgeid: int, new_src_id: int):
        """
        Change the source node of an edge.
        """
        edge = self.edges[edgeid]
        old_src = self.nodes[edge.src]
        new_src = self.nodes[new_src_id]
        rev_id = edge.rev

        edge.src = new_src_id
        old_src.outgoing.remove(edgeid)
        new_src.outgoing.add(edgeid)
        if edgeid in old_src.outgoing_active:
            old_src.outgoing_active.remove(edgeid)
            new_src.outgoing_active.add(edgeid)

        self.edges[rev_id].dst = new_src_id
        old_src.incoming.remove(rev_id)
        new_src.incoming.add(rev_id)

    def dump_graphviz_pretty(self, curr: Curriculum) -> str:
        """
        Dumps a graph resembling the original curriculum.
        """
        out = "digraph {\n"
        next_id = 1

        by_block: defaultdict[
            str,
            defaultdict[int, list[tuple[str, int, BlockEdgeInfo]]],
        ] = defaultdict(lambda: defaultdict(list))
        for layer_id, layer in self.layers.items():
            for code, layercourse in layer.courses.items():
                for inst_idx, inst in enumerate(layercourse.instances):
                    if inst is None:
                        continue
                    for block_edge in inst.block_edges:
                        bid = id(block_edge.block_path[-1])
                        by_block[layer_id][bid].append((code, inst_idx, block_edge))

        def attach_course(
            layer_id: str,
            code: str,
            attach_to: str,
            flow: int,
            cap: int,
            is_filler: bool,
        ) -> int:
            if cap == 0 or (is_filler and flow == 0):
                return 0

            nonlocal out, next_id
            vid = f"v{next_id}"
            next_id += 1

            style = " style=dotted" if flow == 0 else ""
            style += ' color="red"' if is_filler else ""

            label = code
            if layer_id != "":
                label += f"[{layer_id}]"
            label += "\\n(faltante)" if is_filler else ""
            out += f'{vid} [label="{label}"{style}]\n'

            label = f"{0 if is_filler else flow}/{cap}"
            out += f'{vid} -> {attach_to} [label="{label}"{style}]\n'

            return flow

        def visit(block: Block) -> tuple[str, int]:
            nonlocal out, next_id
            vid = f"v{next_id}"
            next_id += 1

            flow = 0
            if isinstance(block, Leaf):
                for layer_id, layer in by_block.items():
                    if id(block) not in layer:
                        continue
                    for code, inst_idx, edge in layer[id(block)]:
                        usable = self.usable[code]
                        usable_inst = usable.instances[inst_idx]
                        subflow = attach_course(
                            layer_id,
                            code,
                            vid,
                            edge.active_flow,
                            usable_inst.credits,
                            usable_inst.filler is not None,
                        )

                        flow += subflow
                        next_id += 1
            else:
                for child in block.children:
                    subid, subflow = visit(child)
                    flow += subflow
                    sublabel = f"{subflow}/{child.cap}"
                    out += f'{subid} -> {vid} [label="{sublabel}"]\n'
            label = block.debug_name
            out += f'{vid} [label="{label}"]\n'

            return vid, flow

        vid, flow = visit(curr.root)
        out += f'v{next_id} [label=""]\n'
        out += f'{vid} -> v{next_id} [label="{flow}/{curr.root.cap}"]'
        out += "}"
        return out

    def dump_graphviz_debug(self, curriculum: Curriculum) -> str:
        """
        Dump the graph representation as a Graphviz DOT file.
        """
        out = "digraph {\n"
        id_counter = 0

        def next_id():
            nonlocal id_counter
            id_counter += 1
            return f"v{id_counter}"

        def mknode(label: str, extra: str = "", id: str | None = None):
            nonlocal out
            if id is None:
                id = next_id()
            out += f'{id} [label="{label}" {extra}]\n'
            return id

        def mkedge(
            src: str,
            dst: str,
            label: str,
            extra: str = "",
            dotted_flow: int | None = None,
        ):
            nonlocal out
            if dotted_flow == 0:
                extra += " style=dotted"
            extra = extra.strip()
            if extra:
                extra = " " + extra
            out += f'{src} -> {dst} [label="{label}"{extra}]\n'

        by_block: defaultdict[
            str,
            defaultdict[
                int,
                list[tuple[UsableInstance, LayerCourseInstance, BlockEdgeInfo]],
            ],
        ] = defaultdict(lambda: defaultdict(list))
        for layer_id, layer in self.layers.items():
            for code, layercourse in layer.courses.items():
                for inst_idx, inst in enumerate(layercourse.instances):
                    if inst is None:
                        continue
                    usable_inst = self.usable[code].instances[inst_idx]
                    for block_edge in inst.block_edges:
                        bid = id(block_edge.block_path[-1])
                        by_block[layer_id][bid].append((usable_inst, inst, block_edge))

        def visit(block: Block) -> tuple[str, int]:
            vid = mknode(f"{block.debug_name}")

            flow = 0
            if isinstance(block, Leaf):
                for layer_id, layer in by_block.items():
                    if id(block) not in layer:
                        continue
                    courseids: dict[str, str] = {}
                    for usable_inst, layer_inst, edge in layer[id(block)]:
                        code = usable_inst.code
                        if code not in courseids:
                            usable = self.usable[code]
                            lname = f"[{layer_id}]" if layer_id else ""
                            mult = (
                                "inf"
                                if usable.multiplicity is None
                                else usable.multiplicity
                            )
                            courseids[code] = mknode(
                                f"{code}{lname} {usable.total}/{mult}",
                            )

                        total_inst_flow = 0
                        for block_edge in layer_inst.block_edges:
                            total_inst_flow += block_edge.active_flow

                        label = f"{code} #{usable_inst.instance_idx+1}"
                        style = ""
                        if usable_inst.filler is not None:
                            label += "\n(faltante)"
                            style = "color=red"
                        inst_id = mknode(label, style)
                        mkedge(
                            courseids[code],
                            inst_id,
                            f"{total_inst_flow}/{usable_inst.credits}",
                            dotted_flow=total_inst_flow,
                        )

                        mkedge(
                            inst_id,
                            vid,
                            f"{edge.active_flow}/{usable_inst.credits}",
                            dotted_flow=edge.active_flow,
                        )

                        flow += edge.active_flow
            else:
                for child in block.children:
                    subid, subflow = visit(child)
                    flow += subflow
                    mkedge(
                        subid,
                        vid,
                        f"{subflow}/{child.cap}",
                        dotted_flow=subflow,
                    )

            return vid, flow

        vid, flow = visit(curriculum.root)
        sink = mknode("")
        mkedge(vid, sink, f"{flow}/{curriculum.root.cap}", dotted_flow=flow)
        out += "}"
        return out

    def dump_graphviz_raw(self, curriculum: Curriculum | None = None) -> str:
        """
        Dump the raw graphviz representation using node and edge indices instead of
        names.
        """
        out = "digraph {\n"
        for id, node in enumerate(self.nodes):
            label = f"v{id}"
            if id == self.source:
                label += "(s)"
            elif id == self.sink:
                label += "(t)"
            label += f" {node.debug_name}"
            out += f'  v{id} [label="{label}"];\n'
        for id, edge in enumerate(self.edges):
            if edge.cap == 0:
                continue
            rev = self.edges[edge.rev]
            assert rev.flow == -edge.flow and rev.cap == 0 and rev.cost == -edge.cost
            label = f"e{id} {edge.flow}/{edge.cap}"
            if edge.cost != 0:
                label += f" ${edge.cost}"
            attrs = f'label="{label}"'
            if edge.flow == 0:
                attrs += " style=dotted"
            out += f"  v{edge.src} -> v{edge.dst} [{attrs}];\n"
        out += "}"
        return out


def _connect_course_instance(
    courseinfo: CourseInfo,
    g: SolvedCurriculum,
    layer_id: str,
    block_order: int,
    block_path: tuple[Block, ...],
    inst: UsableInstance,
    connect_to: int,
):
    """
    Connect the course instance `inst` to the graph node `connect_to`.
    Creates a minimal amount of nodes and edges to model the connection in the graph.
    """

    # Figure out cost
    cost = 0
    cost += inst.flat_order * COURSE_ORDER_COST
    cost += block_order * BLOCK_ORDER_COST
    if inst.filler is not None:
        cost += FILLER_COST

    usable = g.usable[inst.code]
    layer = g.layers[layer_id]
    layercourse = layer.courses.get(inst.code, None)
    if layercourse is None:
        # This is the first instance of this course (in this layer)
        credit_src = g.source
        if usable.multiplicity is not None and usable.total > usable.multiplicity:
            # We need to introduce a course node to limit the amount of credits
            # available to instances of this course
            credit_src = g.add(Node(debug_name=f"{inst.code}{layer_id[:1]}"))
            g.connect("", g.source, credit_src, usable.multiplicity)
        layercourse = LayerCourse(
            credit_source_id=credit_src,
            instances=[None for _i in usable.instances],
        )
        layer.courses[inst.code] = layercourse

    layer_inst = layercourse.instances[inst.instance_idx]
    if layer_inst is None:
        # Now we would have to create an instance node, connect the course node to the
        # instance node and then connect the instance node to the block node
        # However, we don't want to do unnecessary work, and with a single connection
        # the instance node is doing no useful work, so connect the course node to the
        # block node directly
        layer_inst = LayerCourseInstance(
            active_edge=None,
            block_edges=[],
            instance_node=None,
        )
        layercourse.instances[inst.instance_idx] = layer_inst
        inst_node = layercourse.credit_source_id
    elif layer_inst.instance_node is None:
        # This is the second block being connected to this instance
        # There is no instance node created, so we'll have to create one
        inst_node = g.add(Node(f"{inst.code} #{inst.instance_idx+1}"))
        g.connect("", layercourse.credit_source_id, inst_node, inst.credits)
        for block_edge in layer_inst.block_edges:
            g.move_source(block_edge.edge_id, inst_node)
        layer_inst.instance_node = inst_node
    else:
        inst_node = layer_inst.instance_node

    # Add the block edge connection between the instance node and the block node
    block_edge = BlockEdgeInfo(
        active_flow=0,
        block_path=block_path,
        edge_id=g.connect("", inst_node, connect_to, inst.credits, cost),
    )
    layer_inst.block_edges.append(block_edge)


def _taken_block_courses_iter(
    g: SolvedCurriculum,
    block: Leaf,
) -> Iterable[UsableInstance]:
    """
    Iterate over the course instances whose codes match the given block.
    The instances are given in an arbitrary order.
    """
    if len(block.codes) < len(g.usable):
        # This block has little codes, iterate over the block codes
        return (
            inst
            for code in block.codes
            if code in g.usable
            for inst in g.usable[code].instances
            if not (
                # Skips instances with mismatching tagged equivalence
                isinstance(inst.original_pseudocourse, ConcreteId)
                and inst.original_pseudocourse.equivalence is not None
                and inst.original_pseudocourse.equivalence.code not in block.codes
            )
        )
    # This block has too many codes.
    # Iterate over the taken courses instead
    return (
        inst
        for code, usable in g.usable.items()
        if code in block.codes
        for inst in usable.instances
        if not (
            # Skips instances with mismatching tagged equivalence
            isinstance(inst.original_pseudocourse, ConcreteId)
            and inst.original_pseudocourse.equivalence is not None
            and inst.original_pseudocourse.equivalence.code not in block.codes
        )
    )


@dataclass
class VisitState:
    stack: list[Block] = field(default_factory=list)
    flat_order: int = 0


def _build_visit(
    courseinfo: CourseInfo,
    g: SolvedCurriculum,
    visit_state: VisitState,
    block: Block,
    connect_to: int,
):
    """
    Recursively visit a block of the curriculum tree, building it as we go.
    Connect all of the children, and then connect this node to `connect_to`.
    """
    visit_state.stack.append(block)

    if isinstance(block, Leaf):
        # A list of courses
        visit_state.flat_order += 1

        # Count the maximum amount of credits that could flow into this block
        subcreds = sum(inst.credits for inst in _taken_block_courses_iter(g, block))

        # Check if we must add an intermediate node to model the effect of the block's
        # capacity
        # Ie. if there are less credits that come in than the capacity that can go out,
        # then the capacity has no effect
        if subcreds > block.cap:
            subnode = g.add(Node(block.block_code))
            g.connect("", subnode, connect_to, block.cap, cost=0)
            connect_to = subnode

        # Actually connect the courses
        block_path = tuple(visit_state.stack)
        for inst in _taken_block_courses_iter(g, block):
            _connect_course_instance(
                courseinfo,
                g,
                block.layer,
                visit_state.flat_order,
                block_path,
                inst,
                connect_to,
            )
    else:
        # If this block imposes capacity restrictions, add a node to model this
        children_cap = 0
        for c in block.children:
            children_cap += c.cap
        if children_cap > block.cap:
            subnode = g.add(Node(block.block_code))
            g.connect("", subnode, connect_to, block.cap, cost=0)
            connect_to = subnode

        # A combination of blocks
        for c in block.children:
            _build_visit(courseinfo, g, visit_state, c, connect_to)

    visit_state.stack.pop()


def _add_usable_course(
    courseinfo: CourseInfo,
    curriculum: Curriculum,
    g: SolvedCurriculum,
    flat_order: int,
    to_add: PseudoCourse | FillerCourse,
):
    """
    Add a course to the usable courses pool (after doing the appropiate conversions).
    """
    og_course = to_add.course if isinstance(to_add, FillerCourse) else to_add
    code = og_course.code

    # Map curriculum equivalencies
    if code in curriculum.equivalencies:
        code = curriculum.equivalencies[code]

    if code in g.usable:
        usable = g.usable[code]
    else:
        usable = UsableCourse(
            multiplicity=curriculum.multiplicity_of(courseinfo, code),
            total=0,
            instances=[],
        )
        g.usable[code] = usable

    # Assign 1 ghost credit to 0-credit courses
    # Kind of a hack, but works pretty well
    # The curriculum definition must correspondingly also consider
    # 0-credit courses to have 1 ghost credit
    info = courseinfo.try_course(code)
    if info is not None:
        credits = info.credits or 1
    elif isinstance(og_course, EquivalenceId):
        credits = og_course.credits
    else:
        return

    filler = to_add if isinstance(to_add, FillerCourse) else None
    inst_idx = len(usable.instances)
    usable.instances.append(
        UsableInstance(
            code=code,
            credits=credits,
            filler=filler,
            instance_idx=inst_idx,
            flat_order=flat_order,
            original_pseudocourse=og_course,
        ),
    )
    usable.total += credits

    g.mapping.setdefault(og_course.code, []).append((code, inst_idx))


def _build_graph(
    courseinfo: CourseInfo,
    curriculum: Curriculum,
    taken_semesters: list[list[PseudoCourse]],
) -> SolvedCurriculum:
    """
    Take a curriculum prototype and a specific set of taken courses, and build a
    solvable graph that represents this curriculum.
    """

    g = SolvedCurriculum()

    # Fill in credit pool from approved courses and filler credits
    flat_order = 0
    for sem in taken_semesters:
        for c in sorted(sem, key=lambda c: c.code):
            if courseinfo.try_any(c) is None:
                continue
            _add_usable_course(courseinfo, curriculum, g, flat_order, c)
            flat_order += 1
    for fillers in curriculum.fillers.values():
        for filler in fillers:
            _add_usable_course(courseinfo, curriculum, g, flat_order, filler)
            flat_order += 1

    # Build curriculum graph from the curriculum tree
    _build_visit(courseinfo, g, VisitState(), curriculum.root, g.sink)
    return g


def _max_flow_min_cost(g: SolvedCurriculum):
    # Check that there are no negative cycles in the residual graph
    # To simplify this check, we just check that there are no negative cost edges in
    # the residual graph
    for edge in g.edges:
        if edge.flow < edge.cap and edge.cost < 0:
            raise Exception(
                "curriculum residual flow graph has negative cost edges",
            )
    if len(g.edges) == 0:
        return

    # Iteratively improve flow
    queue: dict[int, None] = {}
    parent: list[Edge] = [g.edges[0] for _node in g.nodes]
    while True:
        # Find shortest path from source to sink using SPFA
        dists: list[int] = [INFINITY for _node in g.nodes]
        dists[g.source] = 0
        queue.clear()
        queue[g.source] = None
        while queue:
            id = next(iter(queue.keys()))
            del queue[id]
            for edgeid in g.nodes[id].outgoing_active:
                edge = g.edges[edgeid]
                dst = edge.dst
                newdist = dists[edge.src] + edge.cost
                if newdist < dists[dst]:
                    dists[dst] = newdist
                    parent[dst] = edge
                    queue[dst] = None

        # If no path from source to sink is found, the flow is maximal
        if dists[g.sink] == INFINITY:
            break

        # Find the maximum flow that can go through the path
        flow = INFINITY
        cur = g.sink
        while cur != g.source:
            edge = parent[cur]
            f = edge.cap - edge.flow
            if f < flow:
                flow = f
            cur = edge.src

        # Apply flow to the path
        cur = g.sink
        while cur != g.source:
            edge = parent[cur]
            rev = g.edges[edge.rev]
            edge.flow += flow
            if edge.flow == edge.cap:
                # This edge reached max capacity, so it is no longer in the residual
                # graph
                g.nodes[edge.src].outgoing_active.remove(edge.id)
            if rev.flow == rev.cap:
                # This edge is about to have some spare capacity, so it will go back
                # into the residual graph
                g.nodes[rev.src].outgoing_active.add(rev.id)
            rev.flow -= flow
            cur = edge.src


class InvalidSolutionError(Exception):
    """
    Currently, the solver does not verify that there is no split flow.
    In other words, a course could be split in half and satisfy two blocks at once.
    This error is raised when that happens.

    TODO: Do something about this edge case
        Solving this problem is NP-complete, but it is such an edge case that we can
        probably get away by trying all possible paths the split flow could take.
    """


def _tag_edge_flow(g: SolvedCurriculum):
    """
    Iterate over all block edges, updating the value of `active_flow` in each of them,
    and the value of `active_edge` in their respective instances.
    """
    for layer_id, layer in g.layers.items():
        for code, layercourse in layer.courses.items():
            for inst_idx, inst in enumerate(layercourse.instances):
                if inst is None:
                    continue
                for block_edge in inst.block_edges:
                    # Considering a single layer-course-instance-block combination
                    flow = g.edges[block_edge.edge_id].flow
                    block_edge.active_flow = flow
                    if flow > 0:
                        # This combination is active!
                        if inst.active_edge is not None:
                            block_name = ",".join(
                                block.block_code for block in block_edge.block_path
                            )
                            edge_name = f"{layer_id}.{code}.{inst_idx+1}.[{block_name}]"
                            edges = [
                                f"e{edge.edge_id}"
                                f", tagged flow = {edge.active_flow}"
                                f", edge = {g.edges[edge.edge_id]}"
                                for edge in inst.block_edges
                            ]
                            debug_data = (
                                f"instance_node = {inst.instance_node}, {edges}"
                            )
                            raise InvalidSolutionError(
                                f"split flow at {edge_name}: {debug_data}",
                            )
                        inst.active_edge = block_edge


def _get_superblock(
    g: SolvedCurriculum,
    layers_to_check: list[str],
    code: str,
    rep_idx: int,
) -> str:
    for layer_id in layers_to_check:
        layer = g.layers[layer_id]
        if code not in layer.courses:
            continue
        layercourse = layer.courses[code]

        inst = layercourse.instances[rep_idx]
        if inst is None or inst.active_edge is None:
            continue

        # This block edge is active!
        # Use the first superblock block in the path
        for block in inst.active_edge.block_path:
            if block.block_code.startswith(SUPERBLOCK_PREFIX):
                return block.block_code[len(SUPERBLOCK_PREFIX) :]

    # No superblock found
    return ""


def _tag_superblocks(g: SolvedCurriculum):
    # Sort layers to check them in order
    # In particular, check the default "" layer first
    layer_ids = sorted(g.layers)

    # Find superblocks for all codes
    g.superblocks = {}
    for code, usable in g.usable.items():
        # Find the superblock for all course instances with this code
        g.superblocks[code] = [
            _get_superblock(g, layer_ids, code, i) for i in range(len(usable.instances))
        ]


def solve_curriculum(
    courseinfo: CourseInfo,
    curriculum: Curriculum,
    taken: list[list[PseudoCourse]],
) -> SolvedCurriculum:
    # Take the curriculum blueprint, and produce a graph for this student
    g = _build_graph(courseinfo, curriculum, taken)
    # Solve the flow problem on the produced graph
    _max_flow_min_cost(g)
    # Ensure that demand is satisfied exactly
    # Recommended courses should always fill in missing demand
    # It's a bug if they cannot fill in the demand
    if g.nodes[g.sink].flow(g) != curriculum.root.cap:
        raise Exception(
            "maximizing flow does not satisfy the root demand exactly,"
            " even with filler recommendations"
            f":\n{g.dump_graphviz_raw(curriculum)}",
        )
    # Determine the amount of flow in each edge
    try:
        _tag_edge_flow(g)
    except InvalidSolutionError as e:
        raise InvalidSolutionError(
            "min cost max flow produced invalid split-flow"
            " (ie. there is some course feeding two or more blocks)"
            f":\n{g.dump_graphviz_raw(curriculum)}",
        ) from e
    # Determine course superblocks
    _tag_superblocks(g)
    return g


@dataclass
class FillerGroup:
    fillers: dict[int, FillerCourse]
    blocks: dict[int, tuple[Block, ...]]
    credits: int


@dataclass
class FillerGroupSet:
    # Mapping from `id(FillerGroup)` to `FillerGroup`.
    groups: dict[int, FillerGroup] = field(default_factory=dict)

    def add_active(
        self,
        filler: FillerCourse,
        block_path: tuple[Block, ...],
        credits: int,
    ):
        """
        Add an active filler as its own group, assuming it was in no group before.
        """
        self.groups[id(filler)] = FillerGroup(
            credits=credits,
            fillers={id(filler): filler},
            blocks={id(block_path): block_path},
        )

    def add_inactive(
        self,
        inactive: FillerCourse,
        block_path: tuple[Block, ...],
        attach_to_active: FillerCourse,
    ):
        """
        Add an inactive filler to the group of `attach_to_active`.
        If the inactive filler already belonged to a group, merge both groups.
        """
        if id(inactive) in self.groups:
            # `inactive` already had a group, merge that group with the active group
            self.merge(inactive, attach_to_active)
        else:
            # `inactive` had no group, add it to the active group
            group = self.groups[id(attach_to_active)]
            group.fillers[id(inactive)] = inactive
            group.blocks[id(block_path)] = block_path

    def merge(self, a: FillerCourse, b: FillerCourse):
        """
        Declare that these two filler courses are equivalent, and merge their groups.
        """

        # Find the small and the big group
        small = self.groups[id(a)]
        big = self.groups[id(b)]
        if len(big.fillers) < len(small.fillers):
            big, small = small, big

        # Update the filler-group of a small number of fillers
        for small_filler in small.fillers:
            self.groups[id(small_filler)] = big
        big.fillers.update(small.fillers)

        # Update the rest of the data
        big.credits += small.credits
        big.blocks.update(small.blocks)
        if len(big.blocks) < len(small.blocks):
            big.blocks, small.blocks = small.blocks, big.blocks

        # Note that "small" is now trash


def _unique_path_through(g: SolvedCurriculum, block_edge: BlockEdgeInfo) -> list[Edge]:
    """
    Find the unique path from source to sink through the given block edge.
    """
    main_edge = g.edges[block_edge.edge_id]
    path: list[Edge] = []

    # Go towards the source
    up = main_edge
    while True:
        path.append(up)
        for parent in g.nodes[up.src].incoming:
            up = g.edges[parent]
            if up.cap != 0:
                break
        else:
            # Found no parent, we are at the source
            break

    # Go towards the sink
    down = g.nodes[main_edge.dst]
    while True:
        for down_edge_id in down.outgoing:
            down_edge = g.edges[down_edge_id]
            if down_edge.cap != 0:
                path.append(down_edge)
                down = g.nodes[down_edge.dst]
                break
        else:
            # Found no child, we are at the sink
            break

    return path


def extract_filler_groups(g: SolvedCurriculum) -> Iterable[FillerGroup]:
    """
    Extract groups of fillers, such that if from each group we take a certain amount of
    credits then we can satisfy all blocks.
    """

    # Some course instances are actually fillers.
    # If we find a filler course instance with active flow, it indicates that some
    # curriculum block is unsatisfied and the "best" way to satisfy it is by using the
    # filler.
    # When this happens, the flow is actually going somewhere: it feeds into a block.
    # However, sometimes there are other filler courses that could have been fillers
    # just as well, but the solver decided arbitrarily on one option.

    # When the solver arbitrarily chose the currently active option, it possibly had
    # many paths from source to sink to choose from.
    # It then chose one particular path, the path with minimum cost, and sent a certain
    # amount of flow through it.
    # Now, we want to see what other options the solver could have chosen, possibly with
    # slightly higher cost, we don't care.
    # To do this, we will un-send the flow through this path, and then see what new
    # paths show up from source to sink.

    # This would involve checking which paths are currently open and then checking
    # against the new set of paths after undoing the flow, but we can do better.
    # Because the flow is currently maximal, there are actually no paths from source to
    # sink at all!

    # If after removing filler A a path through filler B shows up, we will say A and B
    # are equivalent.
    # We will treat this equivalence as an actual equivalence class, and determine
    # "groups" of fillers and blocks that are missing.

    # One last note: when we say "look for a path", it does not mean *any* path.
    # For example, paths with cycles are not special: the cycles do not contribute
    # anything meaningful, it's just changing some unrelated course for some other
    # unrelated course.
    # I'm fairly sure that paths that go downwards, then upwards and then down again are
    # equivalent to cycles (unproven), so they should also be avoided.

    # Extract a flat list of all active and inactive fillers
    active_fillers: list[tuple[BlockEdgeInfo, FillerCourse]] = []
    inactive_fillers: list[tuple[BlockEdgeInfo, FillerCourse]] = []
    for layer in g.layers.values():
        for code, layercourse in layer.courses.items():
            usable = g.usable[code]
            for inst_idx, inst in enumerate(layercourse.instances):
                usable_inst = usable.instances[inst_idx]
                if inst is None or usable_inst.filler is None:
                    continue
                for block_edge in inst.block_edges:
                    if block_edge.active_flow == 0:
                        inactive_fillers.append((block_edge, usable_inst.filler))
                    else:
                        active_fillers.append((block_edge, usable_inst.filler))

    # For each active filler, un-send flow through its path and check which paths were
    # opened
    groups = FillerGroupSet()
    for active_filler, active_filler_course in active_fillers:
        # Create a new group where this filler resides
        groups.add_active(
            active_filler_course,
            active_filler.block_path,
            active_filler.active_flow,
        )

        # `filler_edge` is a block edge
        # Every node towards the source from a block edge has only one parent
        # Every node towards the sink from a block edge has only one child
        # This means that we can determine exactly one path through the filler edge
        # Find it
        path = _unique_path_through(g, active_filler)

        # Remove the flow through this path
        for edge in path:
            edge.flow -= active_filler.active_flow
            g.edges[edge.rev].flow += active_filler.active_flow

        # Search for open paths from source to sink through inactive fillers
        for inactive_filler, inactive_filler_course in inactive_fillers:
            # Determine if there is a clear path through this filler
            inactive_path = _unique_path_through(g, inactive_filler)
            clear_path = True
            for edge in inactive_path:
                if edge.flow >= edge.cap:
                    clear_path = False
                    break
            if not clear_path:
                continue

            # Therefore, this inactive filler is equivalent to the current active filler
            groups.add_inactive(
                inactive_filler_course,
                inactive_filler.block_path,
                active_filler_course,
            )

        # Re-add the flow that we removed
        for edge in path:
            edge.flow += active_filler.active_flow
            g.edges[edge.rev].flow -= active_filler.active_flow

    return groups.groups.values()
