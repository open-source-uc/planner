"""
This type stub file was generated by pyright.
"""

import typing as t
from . import Markup

def escape(s: t.Any) -> Markup:
    """Replace the characters ``&``, ``<``, ``>``, ``'``, and ``"`` in
    the string with HTML-safe sequences. Use this if you need to display
    text that might contain such characters in HTML.

    If the object has an ``__html__`` method, it is called and the
    return value is assumed to already be safe for HTML.

    :param s: An object to be converted to a string and escaped.
    :return: A :class:`Markup` string with the escaped text.
    """
    ...

def escape_silent(s: t.Optional[t.Any]) -> Markup:
    """Like :func:`escape` but treats ``None`` as the empty string.
    Useful with optional values, as otherwise you get the string
    ``'None'`` when the value is ``None``.

    >>> escape(None)
    Markup('None')
    >>> escape_silent(None)
    Markup('')
    """
    ...

def soft_str(s: t.Any) -> str:
    """Convert an object to a string if it isn't already. This preserves
    a :class:`Markup` string rather than converting it back to a basic
    string, so it will still be marked as safe and won't be escaped
    again.

    >>> value = escape("<User 1>")
    >>> value
    Markup('&lt;User 1&gt;')
    >>> escape(str(value))
    Markup('&amp;lt;User 1&amp;gt;')
    >>> escape(soft_str(value))
    Markup('&lt;User 1&gt;')
    """
    ...
