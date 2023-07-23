from dataclasses import dataclass


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

    rut: str


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

    def as_any_user(self, user_rut: str) -> UserKey:
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
