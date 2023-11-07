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

from collections.abc import Callable
from typing import TypeVar

from app.plan.validation.courses.logic import (
    And,
    AndClause,
    Atom,
    Const,
    DnfExpr,
    Expr,
    Operator,
    Or,
    create_op,
    hash_expr,
)

T = TypeVar("T")


def simplify(expr: Expr) -> Expr:
    """
    Attempt to simplify this logical expression through logical properties.
    """
    while True:
        # Try to simplify using all available methods
        previous = expr
        for method in simplification_methods:
            if not isinstance(expr, Operator):
                break
            expr = method(expr)
        # Finish simplifying if no progress is made
        if expr is previous:
            break
    return expr


def as_dnf(expr: Expr) -> DnfExpr:
    """
    Convert an expression to Disjunctive-Normal-Form.
    Ie. make the expression be an `Or` clause of `And` clauses.
    Ie. make it so that no `And` contains `Or`s.
    Ie. make it so the expression has the form:
        (A & B) | (A & C) | (D)
    Useful because then we have several possible "scenarios", each of them being a set
    of assumptions.
    """
    # Start by simplifying the entire expression
    expr = simplify(expr)

    # Now go step by step expanding the expression
    while True:
        # Try to simplify using all available methods
        previous = expr
        for method in dnf_methods:
            if not isinstance(expr, Operator):
                break
            expr = method(expr)
        # Finish simplifying if no progress is made
        if expr is previous:
            break

    # Fit into the `DnfExpr` format
    conjunctions: list[AndClause] = []
    if not isinstance(expr, Or):
        expr = Or(children=(expr,))
    for subexpr in expr.children:
        if not isinstance(subexpr, Atom):
            if isinstance(subexpr, And):
                subsubatoms: list[Atom] = []
                for subsubatom in subexpr.children:
                    if not isinstance(subsubatom, Atom):
                        raise Exception(f"dnf simplification failed: {expr}")
                    subsubatoms.append(subsubatom)
                conjunctions.append(AndClause(children=tuple(subsubatoms)))
            else:
                # This can never happen, because it would be an Or within an Or and
                # there are simplification rules that take care of that
                raise Exception(f"dnf simplification failed: {expr}")
        else:
            conjunctions.append(AndClause(children=(subexpr,)))

    return DnfExpr(children=tuple(conjunctions))


def apply_simplification(
    expr: Operator,
    ctx: T,
    rule: Callable[[T, Operator, list[Expr], Expr], bool],
) -> Operator:
    """
    Apply a simplification rule to this operator.
    (Note that this function can only be called on operators!)

    The rule is evaluated once for each child.
    Rule parameters:
        rule(context, expression, new list of children, child in consideration)
    - `context` is an arbitrary type passed to every invocation of the rule
    - `expression` is the value of `expr`, the same parent expression always
    - `new_children` is a mutable list where the new list of children is built
    - `child` is the child being considered in this invocation

    If the rule returns `False`, the child is added as-is to `new_children`
    automatically.
    If the rule returns `True`, the child is *not* added automatically: the rule can
    decide whether to add it or not.
    If all invocations return `False`, the expression is left unchanged (!) no matter
    the contents of `new_children`.
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
    return create_op(expr.neutral, tuple(new_children)) if changed else expr


def _dnfize_chilren_rule(ctx: None, op: Operator, new: list[Expr], child: Expr) -> bool:
    if isinstance(child, And):
        new_child = defactor(child)
        if new_child is not child:
            # Child was defactores
            new.append(new_child)
            return True
    return False


def dnfize_children(expr: Operator) -> Expr:
    """
    Defactorize any children `And` operators.
    This makes it so that no `And` has an `Or` clause as a child.
    """
    return apply_simplification(expr, None, _dnfize_chilren_rule)


def _simplify_children_rule(
    ctx: None,
    op: Operator,
    new: list[Expr],
    child: Expr,
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
    return apply_simplification(expr, None, _simplify_children_rule)


def degen(expr: Operator) -> Expr:
    """
    Convert a childless operator to a constant, and a 1-child operator to just its
    child.
    """
    if len(expr.children) == 0:
        return Const(value=expr.neutral)
    if len(expr.children) == 1:
        return expr.children[0]
    return expr


def _assoc_rule(ctx: None, op: Operator, new: list[Expr], child: Expr) -> bool:
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
    return apply_simplification(expr, None, _assoc_rule)


def _anihil_rule(
    anihilate: list[bool],
    op: Operator,
    new: list[Expr],
    child: Expr,
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
    return apply_simplification(expr, [False], _anihil_rule)


def _ident_rule(ctx: None, op: Operator, new: list[Expr], child: Expr) -> bool:
    if isinstance(child, Const) and child.value == op.neutral:
        # Skip this child, since it adds nothing to the expression
        return True
    return False


def ident(expr: Operator) -> Expr:
    """
    Apply identity: a & 1  <->  a
    """
    return apply_simplification(expr, None, _ident_rule)


def _idem_rule(seen: set[bytes], op: Operator, new: list[Expr], child: Expr) -> bool:
    if hash_expr(child) in seen:
        # Skip this duplicate term
        return True
    seen.add(hash_expr(child))
    return False


def idem(expr: Operator) -> Expr:
    """
    Apply idempotence: a & a  <->  a
    In other words, remove duplicates.
    """
    seen: set[bytes] = set()
    return apply_simplification(expr, seen, _idem_rule)


def _absorp_rule(
    children: set[bytes],
    op: Operator,
    new: list[Expr],
    child: Expr,
) -> bool:
    if isinstance(child, Operator) and child.neutral != op.neutral:
        for grandchild in child.children:
            if hash_expr(grandchild) in children:
                # This entire subclause is unnecessary
                return True
    return False


def absorp(expr: Operator) -> Expr:
    """
    Apply absorption: a & (a | b)  <->  a
                      a | (a & b)  <->  a
    In other words, if a grandchild is duplicated with a child, remove the entire
    parent of the grandchild.
    """
    children: set[bytes] = set()
    for child in expr.children:
        children.add(hash_expr(child))
    return apply_simplification(expr, children, _absorp_rule)


def factor(expr: Operator) -> Expr:
    """
    Factorize the expression: (a & b) | (a & c)  <->  a & (b | c)
    """
    # Count for every grandchild factor, how many times it appears
    count_factors: dict[bytes, int] = {}
    for child in expr.children:
        if isinstance(child, Operator) and child.neutral != expr.neutral:
            for grandchild in child.children:
                h = hash_expr(grandchild)
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
        if isinstance(child, And | Or) and child.neutral != expr.neutral:
            without_factor: list[Expr] = []
            for grandchild in child.children:
                if hash_expr(grandchild) == factor_hash:
                    # The child clause contains a factor
                    has_factor = True
                    # Keep track of the factor for later reference
                    factor = grandchild
                else:
                    # Build a copy of the clause but excluding the factor
                    without_factor.append(grandchild)
            if has_factor:
                # Strip the factor and add the expression to the inner clause
                inner.append(degen(create_op(child.neutral, tuple(without_factor))))
        if not has_factor:
            # Add the expression as-is to the outer clause
            outer.append(child)
    assert factor is not None

    # Merge inner and outer clauses with the factor
    inner_clause = create_op(expr.neutral, tuple(inner))
    with_factor = create_op(not expr.neutral, (factor, inner_clause))
    outer.append(with_factor)
    return degen(create_op(expr.neutral, tuple(outer)))


def defactor(expr: Operator) -> Expr:
    """
    Defactorize the expression: a & (b | c) -> (a & b) | (a & c)
    In order to simplify towards DNF form, it only defactorizes AND operators, so the
    dual conversion is not done:
        a | (b & c) -/> (a | b) & (a | c)
    """

    # For each children, derive a list of the "options" we can choose
    # Eg.   a & (b | c) & (d | e)
    #    -> [a] & [b, c] & [d, e]
    options: list[tuple[Expr, ...]] = []
    for child in expr.children:
        if isinstance(child, Operator) and child.neutral != expr.neutral:
            options.append(child.children)
        else:
            options.append((child,))

    # If there is nothing meaningful to do, exit early
    for opt in options:
        if len(opt) > 1:
            break
        if len(opt) == 0:
            # This is a special case:
            #    a & () & c & d
            # -> a & 0 & c & d
            # -> 0
            return expr
    else:
        # There are no options to pick from
        # Exit early
        return expr

    # Now, we have to choose all combinations of options, and join them
    # Eg.   [a] & [b, c] & [d, e]
    #    -> (a & b & d) | (a & b & e) | (a & c & d) | (a & c & e)
    cur_choice = [0 for _opt in options]
    new_children: list[Expr] = []
    while True:
        # Add this combination
        new_children.append(
            create_op(
                expr.neutral,
                tuple(options[i][cur_choice[i]] for i in range(len(options))),
            ),
        )

        # Check the next choice combination
        for i, opt in enumerate(options):
            cur_choice[i] += 1
            if cur_choice[i] >= len(opt):
                cur_choice[i] = 0
            else:
                break
        else:
            # Remember that the `else` block runs when no `break` occurs
            # This means that all choices were reset back to zero
            # (and therefore we already tried all options)
            break

    return create_op(not expr.neutral, tuple(new_children))


def defactor_and(expr: Operator) -> Expr:
    """
    Defactorize, but only `And` operators.
    Leave `Or` operators as-is.
    """
    if isinstance(expr, Or):
        return expr
    return defactor(expr)


# TODO: Simplify using business logic, for example:
# IIC2233 y IIC2233(c) -> IIC2233


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

# A list of techniques to try when doing DNF
dnf_methods = [
    simplify_children,
    dnfize_children,
    assoc,
    anihil,
    ident,
    idem,
    absorp,
    degen,
    defactor_and,
]
