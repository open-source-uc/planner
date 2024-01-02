from app.plan.validation.courses.logic import (
    And,
    AndClause,
    Atom,
    DnfExpr,
    Expr,
    Or,
    ReqCourse,
)
from app.plan.validation.courses.simplify import as_dnf


def test_dnf():
    def atom(code: str) -> ReqCourse:
        return ReqCourse(code=code, coreq=False)

    def atoms(num: int) -> list[ReqCourse]:
        return [atom(chr(ord("A") + i)) for i in range(num)]

    def o(*children: Expr) -> Or:
        return Or(children=tuple(children))

    def y(*children: Expr) -> And:
        return And(children=tuple(children))

    def dnf(*andclauses: list[Atom]):
        return DnfExpr(
            children=tuple(
                AndClause(children=tuple(andclause)) for andclause in andclauses
            ),
        )

    a, b, c, d = atoms(4)

    assert as_dnf(
        y(a, b, o(c, d)),
    ) == dnf([a, b, c], [a, b, d])
    assert as_dnf(o(y(), a)) == dnf([], [a])
    assert as_dnf(o(o(c, d), a, b)) == dnf([c], [d], [a], [b])
    assert as_dnf(o()) == dnf()
    assert as_dnf(y(b, c)) == dnf([b, c])
