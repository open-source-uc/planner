import re
from collections.abc import Callable, Generator
from dataclasses import dataclass
from itertools import cycle
from typing import Any, Self

from pydantic.fields import ModelField


class Rut(str):
    """
    A RUT, like 12345678-K. No dots, no leading zeroes, uppercase K.
    """

    _pattern = re.compile(r"^(\d{1,16})-([0-9K])$")

    def __new__(cls: type[Self], value: str) -> Self:
        return super().__new__(cls, cls.validate_str(value))

    @classmethod
    def __get_validators__(
        cls: type[Self],
    ) -> Generator[Callable[..., Self], None, None]:
        yield cls.validate

    @classmethod
    def validate(cls: type[Self], value: str, field: ModelField) -> Self:
        return cls(cls.validate_str(value))

    @classmethod
    def validate_str(cls: type[Self], value: str) -> str:
        if not isinstance(value, str):  # type: ignore
            raise TypeError("string required")
        value = value.replace(".", "").strip().lstrip("0").upper()
        m = cls._pattern.fullmatch(value)
        if m is None:
            raise ValueError(f"Invalid RUT {value}")
        return value

    @classmethod
    def __modify_schema__(cls: type[Self], field_schema: dict[str, Any]) -> None:
        field_schema.update(
            description=(
                "A RUT, like 12345678-K. No dots, no leading zeroes, uppercase K."
            ),
            pattern=cls._pattern.pattern,
            examples=["12345678-5", "10000111-K"],
        )

    def validate_dv(self) -> bool:
        """
        Verifica que el RUT sea un RUT chileno válido segun su digito verificador.
        """
        m = Rut._pattern.fullmatch(self)
        assert m is not None
        stem, dv = m.groups()
        revertido = map(int, reversed(stem))
        factors = cycle(range(2, 8))
        s = sum(d * f for d, f in zip(revertido, factors, strict=False))
        res = (-s) % 11
        dv_num = 10 if dv == "K" else int(dv)
        return res == dv_num


@dataclass
class UserKey:
    """
    Contains data that identifies a verified user, mod or admin.
    Holding an instance of the subclasses is intended to mean "I have authorization to
    access data for this user".
    Similarly, requiring this type as an argument is intended to mean "using this
    function requires authorization to access the user".

    Example:
    << user = UserKey(rut="12345678-9")
    >> UserKey(rut='12345678-9')
    """

    rut: Rut


class ModKey(UserKey):
    """
    This key should only be constructed from `require_mod_auth`, which does the
    necessary authorization.
    Because this key can only come from a call to `require_mod_auth`, holding an
    instance of this type is intended to mean "I have mod authorization".
    Therefore, any function requiring `ModKey` as an argument means "using this
    function requires mod authorization".

    Example:
    << mod = ModKey(rut="12345678-9")
    >> ModKey(rut='12345678-9')
    """

    def as_any_user(self, user_rut: Rut) -> UserKey:
        """
        Moderators can access the resources of any user.
        """
        return UserKey(user_rut)


class AdminKey(ModKey):
    """
    This key should only be constructed from `require_admin_auth`, which does the
    necessary authorization.
    Because this key can only come from a call to `require_admin_auth`, holding an
    instance of this type is intended to mean "I have admin authorization".
    Therefore, any function requiring `AdminKey` as an argument means "using this
    function requires admin authorization".

    Example:
    << admin = AdminKey(rut="12345678-9")
    >> AdminKey(rut='12345678-9')
    """
