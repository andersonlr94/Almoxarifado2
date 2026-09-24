"""
core/auth.py - Gerenciamento de usuarios e autenticacao.

Storage:
  1) Se config.obter_caminho_jsons() apontar para pasta valida em S:,
     usa  S:/.../Almox/Usuarios/usuarios.json  (compartilhado entre PCs).
  2) Fallback: %LOCALAPPDATA%/Almoxarifado2/usuarios.json  (local por maquina).

Formato usuarios.json:
  [
    {
      "username": "admin",
      "display_name": "Administrador",
      "role": "admin",           # admin | user
      "password_hash": "salt$hash",  # PBKDF2-HMAC-SHA256, 200k iter
      "active": true,
      "created_at": "2026-09-24T10:00:00",
      "created_by": "system"
    }
  ]

Hash: PBKDF2-HMAC-SHA256 com salt 16 bytes (hex). Sem dependências externas.
"""

import base64
import hashlib
import hmac
import json
import os
import secrets
import sys
from datetime import datetime

# Para resolver caminho local
if sys.platform == "win32":
    _APP_DIR = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "Almoxarifado2")
else:
    _APP_DIR = os.path.join(os.path.expanduser("~"), ".almoxarifado2")

os.makedirs(_APP_DIR, exist_ok=True)

_USUARIOS_LOCAL = os.path.join(_APP_DIR, "usuarios.json")
_ITERATIONS = 200_000
_SALT_BYTES = 16

# ---------------------------------------------------------------------------
# Helpers de caminho
# ---------------------------------------------------------------------------

def _obter_caminho_compartilhado() -> str:
    """Retorna caminho compartilhado se configurado, senão ''."""
    try:
        import config
        base = config.obter_caminho_jsons()
        if base and os.path.isdir(base):
            return os.path.normpath(os.path.join(base, "Almox", "Usuarios", "usuarios.json"))
    except Exception:
        pass
    return ""


def obter_caminho_usuarios() -> str:
    """Caminho efetivo para o arquivo de usuários (compartilhado preferencial)."""
    compartilhado = _obter_caminho_compartilhado()
    if compartilhado:
        return compartilhado
    return _USUARIOS_LOCAL


def obter_caminho_usuarios_local() -> str:
    return _USUARIOS_LOCAL


def obter_caminho_usuarios_compartilhado() -> str:
    return _obter_caminho_compartilhado()


# ---------------------------------------------------------------------------
# Hash
# ---------------------------------------------------------------------------

def hash_password(password: str, salt_hex: str | None = None) -> str:
    """Gera 'salt$hash' com PBKDF2-HMAC-SHA256."""
    if salt_hex is None:
        salt = secrets.token_bytes(_SALT_BYTES)
        salt_hex = salt.hex()
    else:
        salt = bytes.fromhex(salt_hex)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _ITERATIONS)
    hash_hex = dk.hex()
    return f"{salt_hex}${hash_hex}"


def verify_password(stored: str, provided: str) -> bool:
    """Verifica senha contra 'salt$hash' armazenado."""
    try:
        salt_hex, hash_hex = stored.split("$", 1)
        expected = hash_password(provided, salt_hex)
        # constant-time compare
        return hmac.compare_digest(expected, stored)
    except Exception:
        return False


def is_hashed(value: str) -> bool:
    """Heurística: nosso hash tem formato hex$hex com tamanhos esperados."""
    if "$" not in value:
        return False
    try:
        salt_hex, hash_hex = value.split("$", 1)
        # salt 32 hex chars (16 bytes), hash 64 hex chars (32 bytes)
        if len(salt_hex) == 32 and len(hash_hex) == 64:
            bytes.fromhex(salt_hex)
            bytes.fromhex(hash_hex)
            return True
    except Exception:
        pass
    return False

# ---------------------------------------------------------------------------
# IO
# ---------------------------------------------------------------------------

def _load_from_path(path: str) -> list:
    if not path or not os.path.isfile(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        return []
    except (FileNotFoundError, json.JSONDecodeError):
        return []
    except OSError:
        return []


def load_users() -> list:
    """
    Carrega usuários.
    Prioridade: compartilhado se existir; se compartilhado vazio mas local tem dados, retorna local.
    Isso permite migração suave.
    """
    compartilhado = _obter_caminho_compartilhado()
    local = _USUARIOS_LOCAL

    users_shared = _load_from_path(compartilhado) if compartilhado else []
    users_local = _load_from_path(local)

    # Se compartilhado está configurado e tem conteúdo, ele é a fonte da verdade
    if compartilhado and users_shared:
        return users_shared
    # Se compartilhado configurado mas vazio e local tem dados, retorna local (migrar depois)
    if compartilhado and not users_shared and users_local:
        return users_local
    # Se não há compartilhado configurado, usa local
    if not compartilhado:
        return users_local
    # Caso ambos vazios
    return users_shared or users_local


def _atomic_write(path: str, data: list):
    """Escrita atômica: escreve em .tmp e faz replace."""
    if not path:
        raise RuntimeError("Caminho de usuários não definido")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    # os.replace é atômico no Windows se no mesmo volume
    os.replace(tmp, path)


def save_users(users: list, path: str | None = None):
    """Salva usuários no caminho efetivo (ou override)."""
    if path is None:
        path = obter_caminho_usuarios()
    _atomic_write(path, users)
    # Espelha para local como backup offline quando o destino é compartilhado
    try:
        compartilhado = _obter_caminho_compartilhado()
        if compartilhado and path == compartilhado:
            # sempre mantém cópia local atualizada (permite login offline)
            _atomic_write(_USUARIOS_LOCAL, users)
    except Exception:
        pass


def _normalize_username(username: str) -> str:
    return username.strip().lower()

# ---------------------------------------------------------------------------
# Operações de usuário
# ---------------------------------------------------------------------------

def find_user(username: str, users: list | None = None) -> dict | None:
    if users is None:
        users = load_users()
    alvo = _normalize_username(username)
    for u in users:
        if _normalize_username(u.get("username", "")) == alvo:
            return dict(u)
    return None


def authenticate(username: str, password: str) -> dict | None:
    """Retorna dict do usuário (sem password_hash) se ok e ativo, senão None."""
    if not username or not password:
        return None
    users = load_users()
    user = find_user(username, users)
    if not user:
        return None
    if not user.get("active", True):
        return None
    stored = user.get("password_hash", "")
    if not stored:
        return None
    # Se por algum motivo o hash ainda estiver em texto puro (migração legada), aceita comparação direta uma vez
    if not is_hashed(stored):
        if stored == password:
            # migra para hash
            user["password_hash"] = hash_password(password)
            # atualiza no arquivo
            for i, u in enumerate(users):
                if _normalize_username(u.get("username", "")) == _normalize_username(username):
                    users[i] = user
                    break
            try:
                save_users(users)
            except Exception:
                pass
            # retorna sem hash
            user.pop("password_hash", None)
            return user
        return None
    if verify_password(stored, password):
        # não expor hash
        sanitized = dict(user)
        sanitized.pop("password_hash", None)
        return sanitized
    return None


def create_user(username: str, password: str, display_name: str = "", role: str = "user", created_by: str = "system") -> dict:
    """
    Cria novo usuário. Lança ValueError se inválido ou já existe.
    Retorna dict salvo (sem hash exposto).
    """
    username = username.strip()
    if not username:
        raise ValueError("Nome de usuário não pode ser vazio.")
    if len(username) < 3:
        raise ValueError("Usuário deve ter ao menos 3 caracteres.")
    if " " in username:
        raise ValueError("Usuário não pode conter espaços. Use letras/números/._-")
    if not password or len(password) < 4:
        raise ValueError("Senha deve ter ao menos 4 caracteres.")
    if role not in ("admin", "user"):
        role = "user"

    users = load_users()
    if find_user(username, users):
        raise ValueError(f"Usuário '{username}' já existe.")

    now = datetime.now().isoformat(timespec="seconds")
    new_user = {
        "username": username,
        "username_lower": _normalize_username(username),
        "display_name": display_name.strip() or username,
        "role": role,
        "password_hash": hash_password(password),
        "active": True,
        "created_at": now,
        "created_by": created_by,
    }
    users.append(new_user)
    save_users(users)
    sanitized = dict(new_user)
    sanitized.pop("password_hash", None)
    return sanitized


def update_user(username: str, display_name: str | None = None, role: str | None = None, active: bool | None = None, new_password: str | None = None):
    """Atualiza campos de um usuário existente."""
    users = load_users()
    alvo = _normalize_username(username)
    found = False
    for u in users:
        if _normalize_username(u.get("username", "")) == alvo:
            found = True
            if display_name is not None:
                u["display_name"] = display_name.strip() or u["username"]
            if role is not None and role in ("admin", "user"):
                # não permite remover último admin
                if u.get("role") == "admin" and role == "user":
                    admins = [x for x in users if x.get("role") == "admin" and x.get("active", True) and _normalize_username(x.get("username","")) != alvo]
                    if not admins:
                        raise ValueError("Não é possível remover o último administrador.")
                u["role"] = role
            if active is not None:
                # também não pode desativar último admin ativo
                if u.get("role") == "admin" and not active:
                    admins = [x for x in users if x.get("role") == "admin" and x.get("active", True) and _normalize_username(x.get("username","")) != alvo]
                    if not admins:
                        raise ValueError("Não é possível desativar o último administrador ativo.")
                u["active"] = bool(active)
            if new_password is not None:
                if len(new_password) < 4:
                    raise ValueError("Senha deve ter ao menos 4 caracteres.")
                u["password_hash"] = hash_password(new_password)
            u["updated_at"] = datetime.now().isoformat(timespec="seconds")
            break
    if not found:
        raise ValueError(f"Usuário '{username}' não encontrado.")
    save_users(users)
    # Se alterou senha/ativo do usuário auto, atualiza ou limpa auto-login
    try:
        import config
        auto_user, _ = config.obter_auto_login()
        if auto_user and _normalize_username(auto_user) == alvo:
            if new_password is not None:
                # senha mudou -> atualiza token para manter auto válido
                full = find_user(username)
                if full:
                    config.definir_auto_login(full.get("username", username), full.get("password_hash", ""))
            if active is not None and not active:
                # desativou o usuário auto -> limpa auto
                config.limpar_auto_login()
    except Exception:
        pass


def delete_user(username: str):
    """Remove usuário. Não permite remover último admin."""
    users = load_users()
    alvo = _normalize_username(username)
    to_remove = None
    for u in users:
        if _normalize_username(u.get("username", "")) == alvo:
            to_remove = u
            break
    if not to_remove:
        raise ValueError(f"Usuário '{username}' não encontrado.")
    if to_remove.get("role") == "admin":
        admins = [x for x in users if x.get("role") == "admin" and _normalize_username(x.get("username","")) != alvo]
        if not admins:
            raise ValueError("Não é possível remover o último administrador.")
    users = [u for u in users if _normalize_username(u.get("username","")) != alvo]
    save_users(users)
    # Se removeu o usuário que tinha auto-login, limpa config
    try:
        import config
        auto_user, _ = config.obter_auto_login()
        if auto_user and _normalize_username(auto_user) == alvo:
            config.limpar_auto_login()
    except Exception:
        pass


def ensure_default_admin() -> bool:
    """
    Garante que exista ao menos um admin.
    Se não houver nenhum usuário, cria admin/admin.
    Retorna True se criou, False se já existia.
    """
    users = load_users()
    if users:
        # já tem usuários, verifica se tem admin ativo
        has_admin = any(u.get("role") == "admin" and u.get("active", True) for u in users)
        if has_admin:
            return False
        # tem usuários mas nenhum admin ativo -> promove o primeiro ativo
        for u in users:
            if u.get("active", True):
                u["role"] = "admin"
                save_users(users)
                return False
        return False
    # nenhum usuário -> cria admin padrão
    try:
        create_user("admin", "admin", display_name="Administrador", role="admin", created_by="system")
        return True
    except ValueError:
        return False


def list_users(sanitize: bool = True) -> list:
    users = load_users()
    if sanitize:
        out = []
        for u in users:
            s = dict(u)
            s.pop("password_hash", None)
            out.append(s)
        return out
    return users


def count_users() -> int:
    return len(load_users())


# ---------------------------------------------------------------------------
# Auto-login (Entrar diretamente)
# ---------------------------------------------------------------------------

def try_auto_login() -> dict | None:
    """
    Tenta login automático via config.auto_login.
    Retorna usuário sanitizado se token ainda válido e ativo, senão None
    (e limpa auto_login se inválido).
    Token armazenado é o password_hash no momento da ativação.
    """
    try:
        import config
        auto_user, auto_token = config.obter_auto_login()
        if not auto_user or not auto_token:
            return None
        # Garante admin padrão antes de tentar (evita arquivo vazio)
        ensure_default_admin()
        user_full = find_user(auto_user)
        if not user_full:
            # usuário não existe mais -> limpa auto
            try:
                config.limpar_auto_login()
            except Exception:
                pass
            return None
        if not user_full.get("active", True):
            try:
                config.limpar_auto_login()
            except Exception:
                pass
            return None
        stored = user_full.get("password_hash", "")
        # Token deve bater exatamente com hash atual (se senha mudou, invalida)
        if stored != auto_token:
            try:
                config.limpar_auto_login()
            except Exception:
                pass
            return None
        # OK -> retorna sanitizado
        sanitized = dict(user_full)
        sanitized.pop("password_hash", None)
        return sanitized
    except Exception:
        return None


def enable_auto_login(username: str):
    """Ativa auto-login para username capturando seu hash atual."""
    import config
    user_full = find_user(username)
    if not user_full:
        raise ValueError(f"Usuário '{username}' não encontrado para auto-login.")
    token = user_full.get("password_hash", "")
    if not token:
        raise ValueError("Usuário sem hash de senha.")
    config.definir_auto_login(user_full.get("username", username), token)


def disable_auto_login():
    try:
        import config
        config.limpar_auto_login()
    except Exception:
        pass


def is_auto_login_enabled() -> bool:
    try:
        import config
        return config.is_auto_login_enabled()
    except Exception:
        return False
