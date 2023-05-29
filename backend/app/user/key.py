from dataclasses import dataclass, field
from typing import Optional, Literal


@dataclass
class UserKey:
    """
    Contains data that identifies a verified user, mod or admin.
    Holding an instance of the subclasses is intended to mean "I have authorization to
    access data for this user".
    Similarly, requiring this type as an argument is intended to mean "using this
    function requires authorization to access the user".

    Example:
    << user = UserKey(username="usuario", rut="12345678-9")
    >> UserKey(username='usuario', rut='12345678-9', is_admin=False, is_mod=False)
    """

    username: str
    rut: str
    is_admin: Optional[bool] = field(init=False, default=False)
    is_mod: Optional[bool] = field(init=False, default=False)


class ModKey(UserKey):
    """
    Example:
    << mod = ModKey(username="moderador", rut="12345678-9")
    >> ModKey(username='moderador', rut='12345678-9', is_admin=False, is_mod=True)
    """

    is_mod: Literal[True] = True

    def __post_init__(self):
        self.is_admin = False


class AdminKey(ModKey):
    """
    Example:
    << admin = AdminKey(username="administrador", rut="12345678-9")
    >> AdminKey(username='administrador', rut='12345678-9', is_admin=True, is_mod=True)
    """

    is_admin: Literal[True] = True
