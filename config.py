import json
import os

ARQUIVO_CONFIG = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "settings.json"
)


def _carregar():
    try:
        with open(ARQUIVO_CONFIG, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _salvar(dados):
    with open(ARQUIVO_CONFIG, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)


def obter_caminho_jsons():
    dados = _carregar()
    caminho = dados.get("caminho_jsons", "")
    if caminho and os.path.isdir(caminho):
        return os.path.normpath(caminho)
    return ""


def definir_caminho_jsons(caminho):
    dados = _carregar()
    dados["caminho_jsons"] = os.path.normpath(caminho)
    _salvar(dados)
