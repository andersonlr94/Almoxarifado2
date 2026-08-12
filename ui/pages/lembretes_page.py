import json
import os
import math
import wave
import struct
import tempfile
import winsound
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QPlainTextEdit, QScrollArea, QFrame,
    QInputDialog, QMessageBox, QDialog, QFormLayout, QGridLayout, QCheckBox,
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont, QIcon


def _caminho_lembretes_json(nome_arquivo="Lembretes.json"):
    import config
    base = config.obter_caminho_jsons()
    if not base:
        return ""
    pasta = os.path.normpath(os.path.join(base, "Almox", "Lembretes"))
    os.makedirs(pasta, exist_ok=True)
    return os.path.join(pasta, nome_arquivo)


def _caminho_lembretes_pessoais_json():
    documentos = os.path.join(os.path.expanduser("~"), "Documents")
    pasta = os.path.normpath(os.path.join(documentos, "Lembretes - Almoxarifado"))
    os.makedirs(pasta, exist_ok=True)
    return os.path.join(pasta, "LembretesPessoal.json")


def _carregar_som_tock():
    caminho = os.path.join(tempfile.gettempdir(), "almox_tock.wav")
    if os.path.exists(caminho):
        return caminho
    taxa = 44100
    duracao = 0.12
    frames = []
    for i in range(int(taxa * duracao)):
        t = i / taxa
        env = math.exp(-t * 30)
        valor = 0.6 * env * (
            math.sin(2 * math.pi * 2093 * t)
            + 0.5 * math.sin(2 * math.pi * 3139 * t)
        )
        frames.append(int(max(-1.0, min(1.0, valor)) * 32767))
    with wave.open(caminho, "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(taxa)
        w.writeframes(struct.pack("<%dh" % len(frames), *frames))
    return caminho


def _tocar_som():
    winsound.PlaySound(_carregar_som_tock(), winsound.SND_FILENAME | winsound.SND_ASYNC)


class QuadroLembretes(QWidget):
    """Quadro de lembretes dividido em ativos (topo) e finalizados (baixo)."""

    def __init__(self, titulo_ativos="Lembrete do time", caminho_json=""):
        super().__init__()
        self.titulo_ativos = titulo_ativos
        self.caminho_json = caminho_json
        self.todos_lembretes = []
        self._setup_ui()
        self._carregar_lembretes()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        # Cabeçalho do quadro
        linha_cabecalho = QHBoxLayout()
        titulo = QLabel(self.titulo_ativos)
        titulo.setStyleSheet("font-size: 15px; font-weight: 700; color: #1e293b;")
        linha_cabecalho.addWidget(titulo)

        linha_cabecalho.addStretch()

        self.campo_busca = QLineEdit()
        self.campo_busca.setPlaceholderText("Buscar...")
        self.campo_busca.setFixedWidth(140)
        self.campo_busca.setFixedHeight(32)
        self.campo_busca.setStyleSheet("border-radius: 8px; padding: 4px 10px; border: 1px solid #cbd5e1;")
        self.campo_busca.textChanged.connect(self._filtrar_lembretes)
        linha_cabecalho.addWidget(self.campo_busca)

        btn_novo = QPushButton("Novo")
        btn_novo.setFixedHeight(32)
        btn_novo.setStyleSheet(
            "background-color: #4f46e5; color: #fff; border: none; border-radius: 8px; "
            "padding: 4px 14px; font-size: 12px; font-weight: 600;"
        )
        btn_novo.clicked.connect(self._novo_lembrete)
        linha_cabecalho.addWidget(btn_novo)

        layout.addLayout(linha_cabecalho)

        # Área superior: lembretes ativos
        self.scroll_ativos = QScrollArea()
        self.scroll_ativos.setWidgetResizable(True)
        self.scroll_ativos.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        self.container_ativos = QWidget()
        self.container_ativos.setStyleSheet("background: transparent;")
        self.layout_ativos = QVBoxLayout(self.container_ativos)
        self.layout_ativos.setContentsMargins(0, 0, 0, 0)
        self.layout_ativos.setSpacing(4)
        self.layout_ativos.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll_ativos.setWidget(self.container_ativos)

        # Divisor central fixo
        divisao = QFrame()
        divisao.setFrameShape(QFrame.Shape.HLine)
        divisao.setStyleSheet("color: #cbd5e1; background: #cbd5e1; max-height: 2px;")

        # Rótulo da seção finalizados
        label_finalizados = QLabel("Finalizados")
        label_finalizados.setStyleSheet("font-size: 13px; font-weight: 700; color: #94a3b8; border: none;")

        self.btn_alternar = QPushButton("▼")
        self.btn_alternar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_alternar.setFixedSize(22, 22)
        self.btn_alternar.setStyleSheet(
            "QPushButton { background: transparent; color: #64748b; border: none; font-size: 10px; }"
            "QPushButton:hover { color: #4f46e5; }"
        )
        self.btn_alternar.clicked.connect(self._alternar_finalizados)

        linha_finalizados = QHBoxLayout()
        linha_finalizados.setContentsMargins(0, 0, 0, 0)
        linha_finalizados.setSpacing(4)
        linha_finalizados.addWidget(label_finalizados)
        linha_finalizados.addWidget(self.btn_alternar)
        linha_finalizados.addStretch()

        # Área inferior: lembretes finalizados
        self.scroll_finalizados = QScrollArea()
        self.scroll_finalizados.setWidgetResizable(True)
        self.scroll_finalizados.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        self.container_finalizados = QWidget()
        self.container_finalizados.setStyleSheet("background: transparent;")
        self.layout_finalizados = QVBoxLayout(self.container_finalizados)
        self.layout_finalizados.setContentsMargins(0, 0, 0, 0)
        self.layout_finalizados.setSpacing(4)
        self.layout_finalizados.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll_finalizados.setWidget(self.container_finalizados)

        layout.addWidget(self.scroll_ativos, 2)
        layout.addWidget(divisao)
        layout.addLayout(linha_finalizados)
        layout.addWidget(self.scroll_finalizados, 1)

    def _ler_lembretes(self):
        if not self.caminho_json or not os.path.exists(self.caminho_json):
            return []
        try:
            with open(self.caminho_json, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def _salvar_lembretes(self, lista):
        if not self.caminho_json:
            return
        with open(self.caminho_json, "w", encoding="utf-8") as f:
            json.dump(lista, f, ensure_ascii=False, indent=2)

    def _limpar_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def _alternar_finalizados(self):
        if self.scroll_finalizados.isVisible():
            self.scroll_finalizados.hide()
            self.btn_alternar.setText("▲")
        else:
            self.scroll_finalizados.show()
            self.btn_alternar.setText("▼")

    def _carregar_lembretes(self):
        self._limpar_layout(self.layout_ativos)
        self._limpar_layout(self.layout_finalizados)

        lembretes = self._ler_lembretes()
        lembretes.sort(key=lambda item: item.get("id", ""))
        self.todos_lembretes = lembretes
        self._renderizar_cards(lembretes)

    def _renderizar_cards(self, lista):
        self._limpar_layout(self.layout_ativos)
        self._limpar_layout(self.layout_finalizados)

        # Re-populate
        for item in lista:
            card = self._criar_card_widget(item)
            if item.get("status") == "finalizado":
                self.layout_finalizados.addWidget(card)
            else:
                self.layout_ativos.addWidget(card)

    def _criar_card_widget(self, dados):
        card = QFrame()
        card.setFrameShape(QFrame.Shape.StyledPanel)
        card.setFixedHeight(50)
        if dados.get("status") == "finalizado":
            card.setStyleSheet(
                "QFrame { background-color: transparent; border: none; }"
            )
        else:
            card.setStyleSheet(
                "QFrame { background-color: #ffffff; border: 1px solid #e2e8f0; "
                "border-radius: 12px; } QFrame:hover { border-color: #cbd5e1; }"
            )

        layout_card = QHBoxLayout(card)
        layout_card.setContentsMargins(10, 0, 16, 0)
        layout_card.setSpacing(12)

        # Status checkbox
        check = QCheckBox()
        check.setCursor(Qt.CursorShape.PointingHandCursor)
        check.setStyleSheet(
            "QCheckBox { background: transparent; }"
            "QCheckBox::indicator { width: 14px; height: 14px; border-radius: 4px; "
            "border: 2px solid #cbd5e1; background: #ffffff; }"
            "QCheckBox::indicator:hover { border-color: #4f46e5; background: #eef2ff; }"
            "QCheckBox::indicator:checked { background-color: #4f46e5; border-color: #4f46e5; "
            "image: none; }"
            "QCheckBox::indicator:checked:hover { background-color: #4338ca; border-color: #4338ca; }"
        )
        check.setChecked(dados.get("status") == "finalizado")
        check.stateChanged.connect(lambda _, d=dados: self._alternar_status(d, check.isChecked()))
        layout_card.addWidget(check)

        # Content
        label_conteudo = QLabel(dados.get("conteudo") or dados.get("titulo", ""))
        label_conteudo.setStyleSheet("font-size: 13px; color: #475569; border: none;")
        label_conteudo.setWordWrap(True)
        label_conteudo.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        layout_card.addWidget(label_conteudo, 1)

        layout_card.addStretch()

        # Timestamp
        timestamp = dados.get("data", "")
        if dados.get("status") == "finalizado":
            fin = dados.get("data_finalizacao", "")
            texto_data = f"C {timestamp}"
            if fin:
                texto_data += f"   F {fin}"
        else:
            texto_data = f"C {timestamp}"
        label_data = QLabel(texto_data)
        label_data.setStyleSheet("font-size: 11px; color: #94a3b8; border: none;")
        layout_card.addWidget(label_data)

        # Edit button
        btn_editar = QPushButton("Editar")
        btn_editar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_editar.setStyleSheet(
            "QPushButton { background: transparent; color: #0284c7; border: none; font-size: 12px; font-weight: 600; }"
            "QPushButton:hover { color: #0369a1; }"
        )
        btn_editar.clicked.connect(lambda: self._editar_lembrete(dados))
        layout_card.addWidget(btn_editar)

        # Delete button
        btn_deletar = QPushButton("Deletar")
        btn_deletar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_deletar.setStyleSheet(
            "QPushButton { background: transparent; color: #ef4444; border: none; font-size: 12px; font-weight: 600; }"
            "QPushButton:hover { color: #dc2626; }"
        )
        btn_deletar.clicked.connect(lambda: self._deletar_lembrete(dados))
        layout_card.addWidget(btn_deletar)

        return card

    def _remover_linha_nova(self):
        linha = getattr(self, "linha_nova", None)
        if linha:
            self.linha_nova.deleteLater()
            self.linha_nova = None

    def _novo_lembrete(self):
        self._remover_linha_nova()

        linha = QWidget()
        linha.setFixedHeight(50)
        linha.setStyleSheet(
            "QWidget { background-color: #ffffff; border: 2px dashed #4f46e5; border-radius: 12px; }"
        )
        h = QHBoxLayout(linha)
        h.setContentsMargins(12, 0, 12, 0)

        campo = QLineEdit()
        campo.setPlaceholderText("Digite o lembrete e pressione Enter...")
        campo.setStyleSheet("border: none; font-size: 13px; background: transparent;")
        campo.returnPressed.connect(lambda: self._salvar_novo(campo.text()))
        h.addWidget(campo)

        self.linha_nova = linha
        self.layout_ativos.insertWidget(0, self.linha_nova)
        campo.setFocus()

    def _salvar_novo(self, texto):
        texto = texto.strip()
        if texto:
            lembretes = self._ler_lembretes()
            dados = {
                "id": datetime.now().strftime("%Y%m%d%H%M%S%f"),
                "data": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "status": "ativo",
                "titulo": "",
                "conteudo": texto,
            }
            lembretes.append(dados)
            self._salvar_lembretes(lembretes)
        self._remover_linha_nova()
        self._carregar_lembretes()

    def _editar_lembrete(self, dados_originais):
        dlg = LembreteDialog(self, dados_originais)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            novos_dados = dlg.obter_dados()
            lembretes = self._ler_lembretes()
            for item in lembretes:
                if item.get("id") == dados_originais.get("id"):
                    item["conteudo"] = novos_dados["conteudo"]
                    item["data"] = datetime.now().strftime("%d/%m/%Y %H:%M") + " (editado)"
                    break
            self._salvar_lembretes(lembretes)
            self._carregar_lembretes()

    def _deletar_lembrete(self, dados):
        resposta = QMessageBox.question(
            self,
            "Deletar Lembrete",
            f"Deseja realmente deletar o lembrete \"{dados.get('conteudo') or dados.get('titulo', '')}\"?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if resposta == QMessageBox.StandardButton.Yes:
            lembretes = self._ler_lembretes()
            lembretes = [item for item in lembretes if item.get("id") != dados.get("id")]
            self._salvar_lembretes(lembretes)
            self._carregar_lembretes()

    def _alternar_status(self, dados, marcado):
        if not dados.get("id"):
            return
        lembretes = self._ler_lembretes()
        for item in lembretes:
            if item.get("id") == dados.get("id"):
                if marcado:
                    item["status"] = "finalizado"
                    if not item.get("data_finalizacao"):
                        item["data_finalizacao"] = datetime.now().strftime("%d/%m/%Y %H:%M")
                    _tocar_som()
                else:
                    item["status"] = "ativo"
                    item.pop("data_finalizacao", None)
                break
        self._salvar_lembretes(lembretes)
        self._carregar_lembretes()

    def _filtrar_lembretes(self, texto):
        texto = texto.strip().lower()
        if not texto:
            self._carregar_lembretes()
            return
        filtrados = [
            item for item in self.todos_lembretes
            if texto in item.get("titulo", "").lower() or texto in item.get("conteudo", "").lower()
        ]
        self._renderizar_cards(filtrados)


class LembretesPage(QWidget):
    """Página com dois quadros de lembretes lado a lado: time e pessoal."""

    def __init__(self):
        super().__init__()
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(16)

        # Header area
        titulo = QLabel("Lembretes")
        titulo.setObjectName("pageTitle")
        titulo.setStyleSheet("font-size: 24px; font-weight: 700; color: #1e293b;")
        layout.addWidget(titulo)

        linha_quadros = QHBoxLayout()
        linha_quadros.setSpacing(16)

        self.quadro_time = QuadroLembretes(
            "Lembrete do time",
            _caminho_lembretes_json("Lembretes.json"),
        )
        self.quadro_pessoal = QuadroLembretes(
            "Lembretes pessoal",
            _caminho_lembretes_pessoais_json(),
        )

        linha_quadros.addWidget(self.quadro_time, 1)
        linha_quadros.addWidget(self.quadro_pessoal, 1)
        layout.addLayout(linha_quadros, 1)


class LembreteDialog(QDialog):
    """Dialog for creating/editing a reminder."""

    def __init__(self, parent=None, dados=None):
        super().__init__(parent)
        self.setWindowTitle("Lembrete")
        self.setMinimumWidth(400)
        self.dados = dados
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        form = QFormLayout()
        form.setSpacing(8)

        self.campo_conteudo = QPlainTextEdit()
        self.campo_conteudo.setPlaceholderText("Conteúdo do lembrete...")
        self.campo_conteudo.setMinimumHeight(100)
        if self.dados:
            self.campo_conteudo.setPlainText(self.dados.get("conteudo", ""))
        form.addRow("Conteúdo:", self.campo_conteudo)

        layout.addLayout(form)

        linha_btns = QHBoxLayout()
        linha_btns.addStretch()

        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setFixedHeight(32)
        btn_cancelar.clicked.connect(self.reject)
        linha_btns.addWidget(btn_cancelar)

        btn_confirmar = QPushButton("Salvar")
        btn_confirmar.setFixedHeight(32)
        btn_confirmar.setStyleSheet(
            "background-color: #4f46e5; color: #fff; border: none; border-radius: 6px; "
            "padding: 4px 18px; font-weight: 600;"
        )
        btn_confirmar.clicked.connect(self.accept)
        linha_btns.addWidget(btn_confirmar)

        layout.addLayout(linha_btns)

    def obter_dados(self):
        return {
            "titulo": "",
            "conteudo": self.campo_conteudo.toPlainText().strip(),
        }