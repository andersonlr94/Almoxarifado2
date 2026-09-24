"""
Sessão global do usuário logado.
Mantém o usuário atual em memória para uso em toda a aplicação.
"""

_current_user = None


def set_current_user(user: dict | None):
    global _current_user
    _current_user = dict(user) if user else None


def get_current_user() -> dict | None:
    return dict(_current_user) if _current_user else None


def clear_current_user():
    global _current_user
    _current_user = None


def get_username() -> str:
    u = get_current_user()
    return u.get("username", "") if u else ""


def get_display_name() -> str:
    u = get_current_user()
    if not u:
        return ""
    return u.get("display_name") or u.get("username", "")


def get_role() -> str:
    u = get_current_user()
    return u.get("role", "user") if u else ""


def is_admin() -> bool:
    return get_role() == "admin"


def is_authenticated() -> bool:
    return _current_user is not None
