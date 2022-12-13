"""
Implements a logical AST with simplification operations.
"""


from abc import abstractmethod
from pydantic import BaseModel, Field
from typing import Annotated, Callable, ClassVar, Literal, Optional, TypeVar
import typing


T = TypeVar("T")


class BaseExpr(BaseModel):
    """
    A logical expression.
    The requirements that a student must uphold in order to take a course is expressed
    through a combination of expressions.
    """

    hash_cache: Annotated[Optional[int], Field(repr=False)] = None

    @abstractmethod
    def __str__(self) -> str:
        pass

    @abstractmethod
    def calc_hash(self) -> int:
        pass

    def hash(self) -> int:
        if self.hash_cache is None:
            self.hash_cache = self.calc_hash()
        return self.hash_cache

    def simplify(self) -> "models.Expr":
        # Ideally, we would like to do this:
        # assert isinstance(self, models.Expr)

        # But support was removed in python 3.6, so we have to do this:
        assert isinstance(self, typing.get_args(models.Expr))
        return self  # pyright: reportGeneralTypeIssues = false


class Operator(BaseExpr):
    """
    A logical connector between expressions.
    May be AND or OR.
    """

    expr: Literal["op"] = "op"
    neutral: ClassVar[bool]
    children: tuple["models.Expr", ...]

    @staticmethod
    @abstractmethod
    def op(a: bool, b: bool) -> bool:
        pass

    def calc_hash(self) -> int:
        h = hash(("op", self.neutral))
        for child in self.children:
            h = hash((h, child.hash()))
        return h

    @staticmethod
    def create(neutral: bool, children: tuple["models.Expr", ...]) -> "Operator":
        """
        Build an AND node or an OR node in a generic way, using the neutral element to
        distinguish between them.
        In other words, if `neutral` is true, build an AND node, otherwise build an OR
        node.
        """
        if neutral:
            return And(children=children)
        else:
            return Or(children=children)

    def __str__(self):
        op = "y" if self.neutral else "o"
        s = ""
        for child in self.children:
            if s != "":
                s += f" {op} "
            if isinstance(child, Operator):
                s += f"({child})"
            else:
                s += str(child)
        return s

    def simplify(self) -> "models.Expr":
        """
        Attempt to simplify this logical expression through logical properties.
        """
        simplified: "models.Expr" = self
        while True:
            # Try to simplify using all available methods
            previous = simplified
            for method in simplification_methods:
                if not isinstance(simplified, Operator):
                    break
                simplified = method(simplified)
            # Finish simplifying if no progress is made
            if simplified is previous:
                break
        return simplified

    def apply_simplification(
        self,
        ctx: T,
        rule: Callable[[T, "Operator", list["models.Expr"], "models.Expr"], bool],
    ) -> "Operator":
        """
        Apply a simplification rule to this connector.
        The rule is evaluated for each child.
        If the rule returns false, it's assumed the rule does not affect this child,
        and the child is passed through to the `new` children list.
        If the rule returns true, it's assumed that the rule code added the child to
        the new children list.

        Rule parameters:
            rule(context, `self`, list of new children, child in consideration)
        """
        new_children: list["models.Expr"] = []
        changed = False
        for child in self.children:
            if rule(ctx, self, new_children, child):
                # Child was simplified, mark as changed
                changed = True
            else:
                # No change done, pass child through to new instance
                new_children.append(child)
        # Make sure that if no changes are made, the exact same object is returned
        if changed:
            return Operator.create(self.neutral, tuple(new_children))
        else:
            return self

    def simplify_children(self) -> "models.Expr":
        """
        Simplify the children expressions of this operator.
        """
        return self.apply_simplification(None, simplify_inner_rule)

    def degen(self) -> "models.Expr":
        """
        Convert a childless operator to a constant, and a 1-child operator to just its
        child.
        """
        if len(self.children) == 0:
            return Const(value=self.neutral)
        elif len(self.children) == 1:
            return self.children[0]
        else:
            return self

    def assoc(self) -> "models.Expr":
        """
        Apply associativity: (a & b) & c  <->  a & b & c
        In other words, peel redundant layers.
        """
        return self.apply_simplification(None, assoc_rule)

    def anihil(self) -> "models.Expr":
        """
        Apply anihilation: a & 0  <->  0
        """
        return self.apply_simplification([False], anihil_rule)

    def ident(self) -> "models.Expr":
        """
        Apply identity: a & 1  <->  a
        """
        return self.apply_simplification(None, ident_rule)

    def idem(self) -> "models.Expr":
        """
        Apply idempotence: a & a  <->  a
        In other words, remove duplicates.
        """
        seen: set[int] = set()
        return self.apply_simplification(seen, idem_rule)

    def absorp(self) -> "models.Expr":
        """
        Apply absorption: a & (a | b)  <->  a
        In other words, if a grandchild is duplicated with a child, remove the entire
        parent of the grandchild.
        """
        children: set[int] = set()
        for child in self.children:
            children.add(child.hash())
        return self.apply_simplification(children, absorp_rule)

    def factor(self) -> "models.Expr":
        """
        Factorize the expression: (a & b) | (a & c)  <->  a & (b | c)
        """
        # Count for every grandchild factor, how many times it appears
        count_factors: dict[int, int] = {}
        for child in self.children:
            if isinstance(child, Operator) and child.neutral != self.neutral:
                for grandchild in child.children:
                    h = grandchild.hash()
                    count_factors[h] = count_factors.get(h, 0) + 1

        # Find the most repeated factor
        occurences, factor_hash = 0, 0
        for h, count in count_factors.items():
            if count > occurences:
                occurences, factor_hash = count, h
        if occurences <= 1:
            # Will not gain anything by factorizing
            return self

        # Build "inner" and "outer" clause
        # Also, find factor expression
        # An example: factorizing `(a & b & c) | (a & d) | e` into `a & (b & c | d) | e`
        # Here, the inner clause is `(b & c) | d`
        # The outer clause is `e`
        # Then, the final expression is reconstructed as `factor & inner | outer`
        inner: list["models.Expr"] = []
        outer: list["models.Expr"] = []
        factor = None
        for child in self.children:
            # Current objective: if the child is a clause that contains the factor,
            # strip the factor and add it to the inner clause.
            # If the child is a clause without the factor, add it to the outer clause.
            has_factor = False
            if isinstance(child, Operator) and child.neutral != self.neutral:
                without_factor: list["models.Expr"] = []
                for grandchild in child.children:
                    if grandchild.hash() == factor_hash:
                        # The child clause contains a factor
                        has_factor = True
                        # Keep track of the factor for later reference
                        factor = grandchild
                    else:
                        # Build a copy of the clause but excluding the factor
                        without_factor.append(grandchild)
                if has_factor:
                    # Strip the factor and add the expression to the inner clause
                    inner.append(
                        Operator.create(child.neutral, tuple(without_factor)).degen()
                    )
            if not has_factor:
                # Add the expression as-is to the outer clause
                outer.append(child)
        assert isinstance(factor, BaseExpr)

        # Merge inner and outer clauses with the factor
        inner_clause = Operator.create(self.neutral, tuple(inner))
        with_factor = Operator.create(not self.neutral, (factor, inner_clause))
        outer.append(with_factor)
        outer_clause = Operator.create(self.neutral, tuple(outer)).degen()
        return outer_clause


def simplify_inner_rule(
    ctx: None, op: Operator, new: list["models.Expr"], child: "models.Expr"
) -> bool:
    new_child = child.simplify()
    if new_child is not child:
        # Child was simplified
        new.append(new_child)
        return True
    return False


def assoc_rule(
    ctx: None, op: Operator, new: list["models.Expr"], child: "models.Expr"
) -> bool:
    if isinstance(child, Operator) and child.neutral == op.neutral:
        # Nested operations of the same type
        # Peel this level off
        for grandchild in child.children:
            new.append(grandchild)
        return True
    return False


def anihil_rule(
    anihilate: list[bool], op: Operator, new: list["models.Expr"], child: "models.Expr"
) -> bool:
    if anihilate[0] or isinstance(child, Const) and child.value != op.neutral:
        # This constant value destroys the entire operator clause
        new.clear()
        anihilate[0] = True
        return True
    return False


def ident_rule(
    ctx: None, op: Operator, new: list["models.Expr"], child: "models.Expr"
) -> bool:
    if isinstance(child, Const) and child.value == op.neutral:
        # Skip this child, since it adds nothing to the expression
        return True
    return False


def idem_rule(
    seen: set[int], op: Operator, new: list["models.Expr"], child: "models.Expr"
) -> bool:
    h = child.hash()
    if h in seen:
        # Skip this duplicate term
        return True
    seen.add(h)
    return False


def absorp_rule(
    children: set[int], op: Operator, new: list["models.Expr"], child: "models.Expr"
) -> bool:
    if isinstance(child, Operator) and child.neutral != op.neutral:
        for grandchild in child.children:
            h = grandchild.hash()
            if h in children:
                # This entire subclause is unnecessary
                return True
    return False


# A list of techniques to try when simplifying
simplification_methods = [
    Operator.assoc,
    Operator.simplify_children,
    Operator.anihil,
    Operator.ident,
    Operator.idem,
    Operator.absorp,
    Operator.degen,
    Operator.factor,
]


class And(Operator):
    """
    Logical AND connector.
    Only satisfied if all of its children are satisfied.
    """

    expr: Literal["and"] = "and"
    neutral: ClassVar[bool] = True

    @staticmethod
    def op(a: bool, b: bool) -> bool:
        return a and b


class Or(Operator):
    """
    Logical OR connector.
    Only satisfied if at least one of its children is satisfied.
    """

    expr: Literal["or"] = "or"
    neutral: ClassVar[bool] = False

    @staticmethod
    def op(a: bool, b: bool) -> bool:
        return a or b


class Atom(BaseExpr):
    """
    A logical atom, a leaf in the expression tree.
    Might be true or false depending on the exact context.
    """


class Const(Atom):
    """
    A constant, fixed value of True or False.
    """

    expr: Literal["const"] = "const"
    value: bool

    def __str__(self):
        return str(self.value)

    def calc_hash(self) -> int:
        return hash(("const", self.value))


from . import models

And.update_forward_refs()
Or.update_forward_refs()
Const.update_forward_refs()
