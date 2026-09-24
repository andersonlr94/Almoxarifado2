"""
core/eventos.py — Evento "Usuário A enviou itens para B" direcionado via pasta compartilhada.

Armazenamento (só via pasta, sem servidor):
  <base>/Almox/Eventos/inbox/<para_username_lower>/<uuid>.json
  cada arquivo = um evento; escrita atômica (.tmp -> replace) evita colisão SMB
  cooldown anti-spam: 30s por par (de -> para) verificado no filesystem

Payload:
  {
    "id": "uuid4",
    "de": "anderson",
    "de_display": "Anderson",
    "para": "joao",
    "para_display": "João",
    "botao": "btn_enviar_separando",
    "page": "programacao_agulhas",
    "status": "Separando",
    "ts": "2026-09-25T19:40:00",
    "lida": false,
    "extra": { "itens": [ { "pedido":..., "kardex":..., "codigo":..., "qtde":... }, ... ] }
  }
"""

import json
import os
import uuid
import time
from datetime import datetime, timedelta

COOLDOWN_SEG = 30  # não permite novo clique para o mesmo destinatário antes disso
TTL_SEG = 60 * 60 * 2  # auto-limpeza após 2h (caso destinatário nunca leia)
BOTAO_ID = "btn_enviar_separando"  # novo nome (mantém compat com btn_notificar_separando)
BOTAO_ID_LEGADO = "btn_notificar_separando"


def _base_eventos() -> str:
    """Retorna pasta base de eventos (compartilhada se houver, senão local)."""
    try:
        import config
        base = config.obter_caminho_jsons()
        if base and os.path.isdir(base):
            return os.path.normpath(os.path.join(base, "Almox", "Eventos"))
    except Exception:
        pass
    # fallback local (não cruza PCs, mas mantém funcional offline)
    try:
        import sys
        if sys.platform == "win32":
            app_dir = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "Almoxarifado2")
        else:
            app_dir = os.path.join(os.path.expanduser("~"), ".almoxarifado2")
        return os.path.normpath(os.path.join(app_dir, "Eventos"))
    except Exception:
        return ""


def _pasta_inbox(para_username: str) -> str:
    base = _base_eventos()
    if not base:
        return ""
    norm = (para_username or "").strip().lower()
    if not norm:
        return ""
    return os.path.normpath(os.path.join(base, "inbox", norm))


def _atomic_write_json(path: str, data: dict):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def _carregar_json(path: str):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _is_cooldown_ativo(de_username: str, para_username: str, cooldown: int = COOLDOWN_SEG) -> tuple[bool, int]:
    """
    Verifica se existe evento recente de 'de' para 'para' dentro do cooldown.
    Retorna (ativo, segundos_restantes).
    Varre inbox do destinatário (fonte da verdade).
    """
    inbox = _pasta_inbox(para_username)
    if not inbox or not os.path.isdir(inbox):
        return False, 0
    de_norm = (de_username or "").strip().lower()
    agora = datetime.now()
    mais_recente = None
    for nome in os.listdir(inbox):
        if not nome.endswith(".json"):
            continue
        caminho = os.path.join(inbox, nome)
        # ignora .tmp
        if nome.endswith(".tmp"):
            continue
        data = _carregar_json(caminho)
        if not isinstance(data, dict):
            continue
        if (data.get("de") or "").strip().lower() != de_norm:
            continue
        ts_str = data.get("ts", "")
        try:
            ts = datetime.fromisoformat(ts_str)
        except Exception:
            # fallback mtime
            try:
                ts = datetime.fromtimestamp(os.path.getmtime(caminho))
            except Exception:
                continue
        if mais_recente is None or ts > mais_recente:
            mais_recente = ts
    if mais_recente is None:
        return False, 0
    diff = (agora - mais_recente).total_seconds()
    if diff < cooldown:
        return True, int(cooldown - diff)
    return False, 0


def _limpar_antigos_para_para(para_username: str, ttl: int = TTL_SEG):
    """Remove eventos com mais de TTL segundos (opcional, chamado no poll)."""
    inbox = _pasta_inbox(para_username)
    if not inbox or not os.path.isdir(inbox):
        return
    agora = time.time()
    for nome in os.listdir(inbox):
        if not nome.endswith(".json"):
            continue
        caminho = os.path.join(inbox, nome)
        try:
            mtime = os.path.getmtime(caminho)
            if agora - mtime > ttl:
                os.remove(caminho)
        except Exception:
            pass


def enviar_para_usuario(para_username: str, botao_id: str = BOTAO_ID, page: str = "programacao_agulhas", extra: dict | None = None) -> dict:
    """
    Dispara evento direcionado. Lança ValueError se inválido ou em cooldown.
    Retorna o evento criado.
    """
    from core import session as session_core
    from core import auth as auth_core

    de_user = session_core.get_current_user()
    if not de_user:
        raise ValueError("Nenhum usuário logado. Faça login antes de enviar.")
    de_username = (de_user.get("username") or "").strip()
    de_display = (de_user.get("display_name") or de_username).strip()
    if not de_username:
        raise ValueError("Usuário logado sem username.")

    para_username = (para_username or "").strip()
    if not para_username:
        raise ValueError("Selecione o usuário de destino.")
    if para_username.strip().lower() == de_username.strip().lower():
        raise ValueError("Você não pode enviar para você mesmo.")

    # valida destino existe e ativo
    dest = auth_core.find_user(para_username)
    if not dest:
        raise ValueError(f"Usuário '{para_username}' não encontrado.")
    if not dest.get("active", True):
        raise ValueError(f"Usuário '{para_username}' está desativado.")

    # cooldown anti-spam
    ativo, resto = _is_cooldown_ativo(de_username, para_username, COOLDOWN_SEG)
    if ativo:
        raise ValueError(f"Aguarde {resto}s antes de enviar novamente para {dest.get('display_name') or para_username} (anti-spam).")

    # verifica base
    inbox = _pasta_inbox(para_username)
    if not inbox:
        raise ValueError("Pasta de eventos não configurada. Configure a pasta compartilhada em Configurações.")

    evento = {
        "id": str(uuid.uuid4()),
        "de": de_username,
        "de_display": de_display,
        "para": para_username,
        "para_display": dest.get("display_name") or para_username,
        "botao": botao_id,
        "page": page,
        "status": "Separando",
        "ts": datetime.now().isoformat(timespec="seconds"),
        "lida": False,
        "extra": extra or {},
    }
    # nome inclui timestamp para ordenação e evita colisão
    fname = f"{evento['ts'].replace(':','-')}__{de_username}__{evento['id'][:8]}.json"
    # sanitiza
    fname = "".join(c if c.isalnum() or c in "-_." else "_" for c in fname)
    caminho = os.path.join(inbox, fname)
    _atomic_write_json(caminho, evento)

    # limpeza oportunista
    try:
        _limpar_antigos_para_para(para_username)
    except Exception:
        pass

    return evento


def listar_para_usuario(para_username: str, apenas_nao_lidas: bool = False) -> list:
    inbox = _pasta_inbox(para_username)
    if not inbox or not os.path.isdir(inbox):
        return []
    eventos = []
    for nome in os.listdir(inbox):
        if not nome.endswith(".json"):
            continue
        caminho = os.path.join(inbox, nome)
        data = _carregar_json(caminho)
        if not isinstance(data, dict):
            continue
        if apenas_nao_lidas and data.get("lida"):
            continue
        # guarda caminho para exclusão/marcar lida
        data["_path"] = caminho
        data["_fname"] = nome
        eventos.append(data)
    # ordena por ts
    def _key(e):
        try:
            return datetime.fromisoformat(e.get("ts",""))
        except Exception:
            return datetime.min
    eventos.sort(key=_key)
    return eventos


def marcar_lida(caminho: str):
    data = _carregar_json(caminho)
    if not isinstance(data, dict):
        return
    data["lida"] = True
    data["lida_em"] = datetime.now().isoformat(timespec="seconds")
    _atomic_write_json(caminho, data)


def excluir_evento(caminho: str):
    try:
        if os.path.isfile(caminho):
            os.remove(caminho)
    except Exception:
        pass


def obter_pasta_base() -> str:
    return _base_eventos()


def cooldown_restante(de_username: str, para_username: str) -> int:
    ativo, resto = _is_cooldown_ativo(de_username, para_username, COOLDOWN_SEG)
    return resto if ativo else 0
