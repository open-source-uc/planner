"""
Simplification algorithms for logical expressions.
Used to simplify requirements, both when synchronizing courses and when considering the
context of a particular student.

Example: IIC2523
Requirements: IIC2333 o (IIC1222 y IIC2342 y ING1011) o (IIC1222 y IIC2342 y IPP1000)
Simplified:   IIC2333 o (IIC1222 y IIC2342 y (ING1011 o IPP1000))

Example: MAT1203
Requirements: MAT1600 o MAT1207 o (Carrera=Ingenieria) o (Carrera=Lic en Fisica)
    o (Carrera=Lic en Astronomia) o (Carrera=Lic en Astronomia)
In the context of an engineering student: None
"""

from typing import TypeVar, Callable
from .logic import And, BaseOp, Const, Expr, Operator, Or


T = TypeVar("T")


def simplify(expr: Expr) -> Expr:
    """
    Attempt to simplify this logical expression through logical properties.
    """
    while True:
        # Try to simplify using all available methods
        previous = expr
        for method in simplification_methods:
            if not isinstance(expr, (And, Or)):
                break
            prev = expr
            expr = method(expr)
            if prev is not expr:
                print(f"simplified from {prev} to {expr}")
        # Finish simplifying if no progress is made
        if expr is previous:
            break
    return expr


def apply_simplification(
    expr: Operator,
    ctx: T,
    rule: Callable[[T, Operator, list[Expr], Expr], bool],
) -> Operator:
    """
    Apply a simplification rule to this connector.
    The rule is evaluated for each child.
    If the rule returns false, it's assumed the rule does not affect this child,
    and the child is passed through to the `new` children list.
    If the rule returns true, it's assumed that the rule code added the child to
    the new children list.

    Rule parameters:
        rule(context, expression, new list of children, child in consideration)
    """
    new_children: list[Expr] = []
    changed = False
    for child in expr.children:
        if rule(ctx, expr, new_children, child):
            # Child was simplified, mark as changed
            changed = True
        else:
            # No change done, pass child through to new instance
            new_children.append(child)
    # Make sure that if no changes are made, the exact same object is returned
    if changed:
        return BaseOp.create(expr.neutral, tuple(new_children))
    else:
        return expr


def simplify_children_rule(
    ctx: None, op: Operator, new: list[Expr], child: Expr
) -> bool:
    new_child = simplify(child)
    if new_child is not child:
        # Child was simplified
        new.append(new_child)
        return True
    return False


def simplify_children(expr: Operator) -> Expr:
    """
    Simplify the children expressions of this operator.
    """
    return apply_simplification(expr, None, simplify_children_rule)


def degen(expr: Operator) -> Expr:
    """
    Convert a childless operator to a constant, and a 1-child operator to just its
    child.
    """
    if len(expr.children) == 0:
        return Const(value=expr.neutral)
    elif len(expr.children) == 1:
        return expr.children[0]
    else:
        return expr


def assoc_rule(ctx: None, op: Operator, new: list[Expr], child: Expr) -> bool:
    if isinstance(child, Operator) and child.neutral == op.neutral:
        # Nested operations of the same type
        # Peel this level off
        for grandchild in child.children:
            new.append(grandchild)
        return True
    return False


def assoc(expr: Operator) -> Expr:
    """
    Apply associativity: (a & b) & c  <->  a & b & c
    In other words, peel redundant layers.
    """
    return apply_simplification(expr, None, assoc_rule)


def anihil_rule(
    anihilate: list[bool], op: Operator, new: list[Expr], child: Expr
) -> bool:
    if not anihilate[0] and isinstance(child, Const) and child.value != op.neutral:
        # This constant value destroys the entire operator clause
        new.clear()
        new.append(Const(value=not op.neutral))
        anihilate[0] = True
    if anihilate[0]:
        return True
    return False


def anihil(expr: Operator) -> Expr:
    """
    Apply anihilation: a & 0  <->  0
    """
    return apply_simplification(expr, [False], anihil_rule)


def ident_rule(ctx: None, op: Operator, new: list[Expr], child: Expr) -> bool:
    if isinstance(child, Const) and child.value == op.neutral:
        # Skip this child, since it adds nothing to the expression
        return True
    return False


def ident(expr: Operator) -> Expr:
    """
    Apply identity: a & 1  <->  a
    """
    return apply_simplification(expr, None, ident_rule)


def idem_rule(seen: set[bytes], op: Operator, new: list[Expr], child: Expr) -> bool:
    if child.hash in seen:
        # Skip this duplicate term
        return True
    seen.add(child.hash)
    return False


def idem(expr: Operator) -> Expr:
    """
    Apply idempotence: a & a  <->  a
    In other words, remove duplicates.
    """
    seen: set[bytes] = set()
    return apply_simplification(expr, seen, idem_rule)


def absorp_rule(
    children: set[bytes], op: Operator, new: list[Expr], child: Expr
) -> bool:
    if isinstance(child, Operator) and child.neutral != op.neutral:
        for grandchild in child.children:
            if grandchild.hash in children:
                # This entire subclause is unnecessary
                return True
    return False


def absorp(expr: Operator) -> Expr:
    """
    Apply absorption: a & (a | b)  <->  a
    In other words, if a grandchild is duplicated with a child, remove the entire
    parent of the grandchild.
    """
    children: set[bytes] = set()
    for child in expr.children:
        children.add(child.hash)
    return apply_simplification(expr, children, absorp_rule)


def factor(expr: Operator) -> Expr:
    """
    Factorize the expression: (a & b) | (a & c)  <->  a & (b | c)
    """
    # Count for every grandchild factor, how many times it appears
    count_factors: dict[bytes, int] = {}
    for child in expr.children:
        if isinstance(child, Operator) and child.neutral != expr.neutral:
            for grandchild in child.children:
                h = grandchild.hash
                count_factors[h] = count_factors.get(h, 0) + 1

    # Find the most repeated factor
    occurences, factor_hash = 0, 0
    for h, count in count_factors.items():
        if count > occurences:
            occurences, factor_hash = count, h
    if occurences <= 1:
        # Will not gain anything by factorizing
        return expr

    # Build "inner" and "outer" clause
    # Also, find factor expression
    # An example: factorizing `(a & b & c) | (a & d) | e` into `a & (b & c | d) | e`
    # Here, the inner clause is `(b & c) | d`
    # The outer clause is `e`
    # Then, the final expression is reconstructed as `factor & inner | outer`
    inner: list[Expr] = []
    outer: list[Expr] = []
    factor = None
    for child in expr.children:
        # Current objective: if the child is a clause that contains the factor,
        # strip the factor and add it to the inner clause.
        # If the child is a clause without the factor, add it to the outer clause.
        has_factor = False
        if isinstance(child, (And, Or)) and child.neutral != expr.neutral:
            without_factor: list[Expr] = []
            for grandchild in child.children:
                if grandchild.hash == factor_hash:
                    # The child clause contains a factor
                    has_factor = True
                    # Keep track of the factor for later reference
                    factor = grandchild
                else:
                    # Build a copy of the clause but excluding the factor
                    without_factor.append(grandchild)
            if has_factor:
                # Strip the factor and add the expression to the inner clause
                inner.append(degen(BaseOp.create(child.neutral, tuple(without_factor))))
        if not has_factor:
            # Add the expression as-is to the outer clause
            outer.append(child)
    assert factor is not None

    # Merge inner and outer clauses with the factor
    inner_clause = BaseOp.create(expr.neutral, tuple(inner))
    with_factor = BaseOp.create(not expr.neutral, (factor, inner_clause))
    outer.append(with_factor)
    outer_clause = degen(BaseOp.create(expr.neutral, tuple(outer)))
    return outer_clause


# A list of techniques to try when simplifying
simplification_methods = [
    assoc,
    simplify_children,
    anihil,
    ident,
    idem,
    absorp,
    degen,
    factor,
]
