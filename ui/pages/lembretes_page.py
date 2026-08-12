import json
import os
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QPlainTextEdit, QScrollArea, QFrame,
    QInputDialog, QMessageBox, QDialog, QFormLayout, QGridLayout,
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont, QIcon

def _caminho_lembretes_json():
    import config
    base = config.obter_caminho_jsons()
    if not base:
        return ""
    pasta = os.path.normpath(os.path.join(base, "Almox", "Lembretes"))
    os.makedirs(pasta, exist_ok=True)
    return os.path.join(pasta, "Lembretes.json")


class LembretesPage(QWidget):
    """Page that displays a list of reminders in a beautiful card grid layout."""

    def __init__(self):
        super().__init__()
        self._setup_ui()
        self._carregar_lembretes()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(16)

        # Header area
        linha_cabecalho = QHBoxLayout()
        titulo = QLabel("Lembretes")
        titulo.setObjectName("pageTitle")
        titulo.setStyleSheet("font-size: 24px; font-weight: 700; color: #1e293b;")
        linha_cabecalho.addWidget(titulo)
        
        linha_cabecalho.addStretch()

        # Search field
        self.campo_busca = QLineEdit()
        self.campo_busca.setPlaceholderText("Buscar lembrete...")
        self.campo_busca.setFixedWidth(200)
        self.campo_busca.setFixedHeight(34)
        self.campo_busca.setStyleSheet("border-radius: 8px; padding: 4px 10px; border: 1px solid #cbd5e1;")
        self.campo_busca.textChanged.connect(self._filtrar_lembretes)
        linha_cabecalho.addWidget(self.campo_busca)

        # Create reminder button
        btn_novo = QPushButton("Novo Lembrete")
        btn_novo.setFixedHeight(34)
        btn_novo.setStyleSheet(
            "background-color: #4f46e5; color: #fff; border: none; border-radius: 8px; "
            "padding: 6px 16px; font-size: 13px; font-weight: 600;"
        )
        btn_novo.clicked.connect(self._novo_lembrete)
        linha_cabecalho.addWidget(btn_novo)

        layout.addLayout(linha_cabecalho)

        # Scroll Area for Grid of Cards
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("background: transparent; border: none;")

        self.container_cards = QWidget()
        self.container_cards.setStyleSheet("background: transparent;")
        self.layout_grid = QGridLayout(self.container_cards)
        self.layout_grid.setContentsMargins(0, 0, 0, 0)
        self.layout_grid.setSpacing(16)
        
        self.scroll.setWidget(self.container_cards)
        layout.addWidget(self.scroll)

    def _ler_lembretes(self):
        caminho = _caminho_lembretes_json()
        if not caminho or not os.path.exists(caminho):
            return []
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def _salvar_lembretes(self, lista):
        caminho = _caminho_lembretes_json()
        if not caminho:
            return
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(lista, f, ensure_ascii=False, indent=2)

    def _carregar_lembretes(self):
        # Clear grid
        while self.layout_grid.count():
            item = self.layout_grid.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        lembretes = self._ler_lembretes()
        self.todos_lembretes = lembretes
        self._renderizar_cards(lembretes)

    def _renderizar_cards(self, lista):
        # Clear grid widgets
        for i in range(self.layout_grid.count()):
            widget = self.layout_grid.itemAt(i).widget()
            if widget:
                widget.setVisible(False)
                
        # Re-populate
        colunas = 3
        for idx, item in enumerate(lista):
            card = self._criar_card_widget(item)
            row = idx // colunas
            col = idx % colunas
            self.layout_grid.addWidget(card, row, col)

    def _criar_card_widget(self, dados):
        card = QFrame()
        card.setFrameShape(QFrame.Shape.StyledPanel)
        card.setStyleSheet(
            "QFrame { background-color: #ffffff; border: 1px solid #e2e8f0; "
            "border-radius: 12px; } QFrame:hover { border-color: #cbd5e1; }"
        )
        
        layout_card = QVBoxLayout(card)
        layout_card.setContentsMargins(16, 16, 16, 16)
        layout_card.setSpacing(10)

        # Title
        label_titulo = QLabel(dados.get("titulo", "Sem Título"))
        label_titulo.setStyleSheet("font-size: 16px; font-weight: 700; color: #1e293b; border: none;")
        label_titulo.setWordWrap(True)
        layout_card.addWidget(label_titulo)

        # Content
        label_conteudo = QLabel(dados.get("conteudo", ""))
        label_conteudo.setStyleSheet("font-size: 13px; color: #475569; border: none;")
        label_conteudo.setWordWrap(True)
        label_conteudo.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        layout_card.addWidget(label_conteudo)

        layout_card.addStretch()

        # Date & Action Buttons Line
        linha_rodape = QHBoxLayout()
        
        # Timestamp
        timestamp = dados.get("data", "")
        label_data = QLabel(timestamp)
        label_data.setStyleSheet("font-size: 11px; color: #94a3b8; border: none;")
        linha_rodape.addWidget(label_data)
        
        linha_rodape.addStretch()

        # Edit button
        btn_editar = QPushButton("Editar")
        btn_editar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_editar.setStyleSheet(
            "QPushButton { background: transparent; color: #0284c7; border: none; font-size: 12px; font-weight: 600; }"
            "QPushButton:hover { color: #0369a1; }"
        )
        btn_editar.clicked.connect(lambda: self._editar_lembrete(dados))
        linha_rodape.addWidget(btn_editar)

        # Delete button
        btn_deletar = QPushButton("Deletar")
        btn_deletar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_deletar.setStyleSheet(
            "QPushButton { background: transparent; color: #ef4444; border: none; font-size: 12px; font-weight: 600; }"
            "QPushButton:hover { color: #dc2626; }"
        )
        btn_deletar.clicked.connect(lambda: self._deletar_lembrete(dados))
        linha_rodape.addWidget(btn_deletar)

        layout_card.addLayout(linha_rodape)
        return card

    def _novo_lembrete(self):
        dlg = LembreteDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            dados = dlg.obter_dados()
            lembretes = self._ler_lembretes()
            # Generate UUID/Id based on timestamp
            dados["id"] = datetime.now().strftime("%Y%m%d%H%M%S%f")
            dados["data"] = datetime.now().strftime("%d/%m/%Y %H:%M")
            lembretes.append(dados)
            self._salvar_lembretes(lembretes)
            self._carregar_lembretes()

    def _editar_lembrete(self, dados_originais):
        dlg = LembreteDialog(self, dados_originais)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            novos_dados = dlg.obter_dados()
            lembretes = self._ler_lembretes()
            for item in lembretes:
                if item.get("id") == dados_originais.get("id"):
                    item["titulo"] = novos_dados["titulo"]
                    item["conteudo"] = novos_dados["conteudo"]
                    item["data"] = datetime.now().strftime("%d/%m/%Y %H:%M") + " (editado)"
                    break
            self._salvar_lembretes(lembretes)
            self._carregar_lembretes()

    def _deletar_lembrete(self, dados):
        resposta = QMessageBox.question(
            self,
            "Deletar Lembrete",
            f"Deseja realmente deletar o lembrete \"{dados.get('titulo')}\"?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if resposta == QMessageBox.StandardButton.Yes:
            lembretes = self._ler_lembretes()
            lembretes = [item for item in lembretes if item.get("id") != dados.get("id")]
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
        # Clean grid first
        while self.layout_grid.count():
            item = self.layout_grid.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self._renderizar_cards(filtrados)


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

        self.campo_titulo = QLineEdit()
        self.campo_titulo.setPlaceholderText("Título do lembrete")
        self.campo_titulo.setFixedHeight(32)
        if self.dados:
            self.campo_titulo.setText(self.dados.get("titulo", ""))
        form.addRow("Título:", self.campo_titulo)

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
            "titulo": self.campo_titulo.text().strip(),
            "conteudo": self.campo_conteudo.toPlainText().strip(),
        }
