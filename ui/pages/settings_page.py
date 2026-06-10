import os

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFileDialog,
)
from PySide6.QtCore import Qt

import config


PASTA_ALVO = "Almox"


class SettingsPage(QWidget):
    def __init__(self):
        super().__init__()
        self._setup_ui()
        self._carregar_caminho()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(16)

        card = QWidget()
        card.setObjectName("pageCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(28, 28, 28, 28)
        card_layout.setSpacing(16)

        titulo = QLabel("Configurações")
        titulo.setObjectName("pageTitle")
        card_layout.addWidget(titulo)

        label_info = QLabel("Configure o diretório onde os arquivos JSON serão salvos.")
        label_info.setObjectName("pageSubtitle")
        card_layout.addWidget(label_info)

        campo_layout = QHBoxLayout()
        campo_layout.setSpacing(8)

        label_caminho = QLabel("Pasta de destino:")
        label_caminho.setObjectName("statusLabel")
        campo_layout.addWidget(label_caminho)

        self.campo_caminho = QLineEdit()
        self.campo_caminho.setPlaceholderText("Selecione a pasta para salvar os JSONs...")
        self.campo_caminho.setFixedHeight(34)
        self.campo_caminho.setReadOnly(True)
        campo_layout.addWidget(self.campo_caminho)

        btn_selecionar = QPushButton("Selecionar")
        btn_selecionar.setObjectName("btnSecondary")
        btn_selecionar.setFixedHeight(34)
        btn_selecionar.clicked.connect(self._selecionar_pasta)
        campo_layout.addWidget(btn_selecionar)
        card_layout.addLayout(campo_layout)

        info_extra = QLabel(
            'O caminho escolhido criará uma pasta "Almox" '
            "com os arquivos JSON organizados dentro."
        )
        info_extra.setObjectName("pageSubtitle")
        info_extra.setWordWrap(True)
        card_layout.addWidget(info_extra)

        botoes_layout = QHBoxLayout()
        botoes_layout.addStretch()

        btn_salvar = QPushButton("Salvar")
        btn_salvar.setObjectName("btnPrimary")
        btn_salvar.setFixedHeight(34)
        btn_salvar.clicked.connect(self._salvar)
        botoes_layout.addWidget(btn_salvar)

        card_layout.addLayout(botoes_layout)
        layout.addWidget(card)
        layout.addStretch()

    def _carregar_caminho(self):
        caminho = config.obter_caminho_jsons()
        if caminho:
            self.campo_caminho.setText(os.path.join(caminho, PASTA_ALVO))

    def _selecionar_pasta(self):
        pasta = QFileDialog.getExistingDirectory(self, "Selecionar pasta de destino")
        if pasta:
            self.campo_caminho.setText(os.path.join(pasta, PASTA_ALVO))

    def _salvar(self):
        texto = self.campo_caminho.text().strip()
        if texto:
            caminho_base = os.path.dirname(texto) if texto.endswith(PASTA_ALVO) else texto
            config.definir_caminho_jsons(caminho_base)
            os.makedirs(texto, exist_ok=True)
