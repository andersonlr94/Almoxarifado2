import json
import os
import sys

if sys.platform == "win32":
    _APP_DIR = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "Almoxarifado2")
else:
    _APP_DIR = os.path.join(os.path.expanduser("~"), ".almoxarifado2")

os.makedirs(_APP_DIR, exist_ok=True)

ARQUIVO_CONFIG = os.path.join(_APP_DIR, "settings.json")


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


def exigir_caminho_jsons():
    caminho = obter_caminho_jsons()
    if not caminho:
        raise RuntimeError("Não existe uma pasta selecionada para salvar os dados.")
    return caminho


def avisar_sem_pasta(parent=None):
    from PySide6.QtWidgets import QMessageBox
    QMessageBox.warning(
        parent,
        "Pasta não selecionada",
        "Não existe uma pasta selecionada para salvar os dados.\n"
        "Selecione uma pasta em Configurações antes de continuar.",
    )


def definir_caminho_jsons(caminho):
    dados = _carregar()
    dados["caminho_jsons"] = os.path.normpath(caminho)
    _salvar(dados)


def obter_impressora_padrao():
    dados = _carregar()
    return dados.get("impressora_padrao", "")


def definir_impressora_padrao(nome):
    dados = _carregar()
    dados["impressora_padrao"] = nome
    _salvar(dados)

