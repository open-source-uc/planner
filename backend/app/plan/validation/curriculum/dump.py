"""
Dump the curriculum graph.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Literal

from app.plan.validation.curriculum.solve import (
    BlockEdgeInfo,
    InstanceEdges,
    SolvedCurriculum,
    UsableInstance,
)
from app.plan.validation.curriculum.tree import Block, Curriculum, Leaf


@dataclass
class LayerEdges:
    edges: list[tuple[UsableInstance, InstanceEdges, BlockEdgeInfo]] = field(
        default_factory=list,
    )


@dataclass
class BlockLayers:
    layers: defaultdict[str, LayerEdges] = field(
        default_factory=lambda: defaultdict(LayerEdges),
    )


DumpStyle = Literal["pretty"] | Literal["debug"]


class GraphDumper:
    g: SolvedCurriculum
    curriculum: Curriculum
    style: DumpStyle

    byblock: defaultdict[
        Block,
        BlockLayers,
    ]

    next_id: int
    out: str

    def __init__(
        self,
        g: SolvedCurriculum,
        curriculum: Curriculum,
        style: DumpStyle,
    ) -> None:
        self.style = style
        self.g = g
        self.curriculum = curriculum
        self.next_id = 0
        self.out = ""

        self.by_block: defaultdict[Block, BlockLayers] = defaultdict(BlockLayers)
        for usable in g.usable.values():
            for inst in usable.instances:
                for layer_id, layer in inst.layers.items():
                    for edge in layer.block_edges:
                        block = edge.block_path[-1]
                        self.by_block[block].layers[layer_id].edges.append(
                            (inst, layer, edge),
                        )

    def mkid(self) -> str:
        self.next_id += 1
        return f"v{self.next_id}"

    def mknode(self, label: str, extra: str = "", id: str | None = None):
        if id is None:
            id = self.mkid()
        self.out += f'{id} [label="{label}" {extra}]\n'
        return id

    def mkedge(
        self,
        src: str,
        dst: str,
        label: str,
        *,
        extra: str = "",
    ):
        extra = extra.strip()
        if extra:
            extra = " " + extra
        self.out += f'{src} -> {dst} [label="{label}"{extra}]\n'

    def mkflowedge(
        self,
        src: str,
        dst: str,
        flow: int,
        cap: int,
        *,
        prelabel: str = "",
        postlabel: str = "",
        extra: str = "",
    ):
        label = f"{prelabel}{flow}/{cap}{postlabel}"
        if flow == 0:
            extra += " style=dotted"
        return self.mkedge(src, dst, label, extra=extra)

    def visit(self, block: Block) -> tuple[str, int]:
        vid = self.mknode(f"{block.debug_name}")

        flow = 0
        if isinstance(block, Leaf):
            for layer_id, edges in self.by_block[block].layers.items():
                courseids: dict[str, str] = {}
                for inst, layer, edge in edges.edges:
                    # Create a node that represents the course instance
                    code = inst.code
                    has_many = len(self.g.usable[code].instances) > 1
                    label = code
                    if has_many or self.style != "pretty":
                        label = f"{label} #{inst.instance_idx+1}"
                    # label += f"\n{inst.original_pseudocourse}"
                    style = ""
                    subflow = edge.flow
                    if inst.filler is not None:
                        if self.style == "pretty":
                            if edge.flow == 0:
                                continue
                            subflow = 0
                        label += "\n(faltante)"
                        style = "color=red"
                    inst_id = self.mknode(label, style)

                    # Connect instance node to block node
                    self.mkflowedge(
                        inst_id,
                        vid,
                        subflow,
                        inst.credits,
                    )

                    if self.style == "debug":
                        # Create a node for the entire course, and connect the instance
                        # node to it
                        if code not in courseids:
                            usable = self.g.usable[code]
                            lname = f"[{layer_id}]" if layer_id else ""
                            mult = (
                                "inf"
                                if usable.multiplicity.credits is None
                                else usable.multiplicity.credits
                            )
                            courseids[code] = self.mknode(
                                f"{code}{lname} {usable.total}/{mult}",
                            )

                        # Connect the course node to the instance node
                        total_inst_flow = 0
                        for block_edge in layer.block_edges:
                            total_inst_flow += block_edge.flow
                        self.mkflowedge(
                            courseids[code],
                            inst_id,
                            total_inst_flow,
                            inst.credits,
                        )

                    flow += subflow
        else:
            for child in block.children:
                subid, subflow = self.visit(child)
                flow += subflow
                self.mkflowedge(
                    subid,
                    vid,
                    subflow,
                    child.cap,
                )

        if flow > block.cap:
            flow = block.cap

        return vid, flow

    def dump(self) -> str:
        """
        Dump the graph representation as a Graphviz DOT file.
        """

        self.out += "digraph {\n"

        vid, flow = self.visit(self.curriculum.root)
        sink = self.mknode("")
        self.mkflowedge(vid, sink, flow, self.curriculum.root.cap)

        self.out += "}"

        return self.out
