import os

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt, Signal

import config


PASTA_ALVO = "Almox"


class SettingsPage(QWidget):
    settings_saved = Signal()

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
        
        # --- NOVO QUADRO PARA MATERIAL HOLDERS ---
        card_holders = QWidget()
        card_holders.setObjectName("pageCard")
        card_holders_layout = QVBoxLayout(card_holders)
        card_holders_layout.setContentsMargins(28, 28, 28, 28)
        card_holders_layout.setSpacing(16)

        titulo_holders = QLabel("Material para Holders")
        titulo_holders.setObjectName("pageTitle")
        card_holders_layout.addWidget(titulo_holders)

        label_info_holders = QLabel("Configure o diretório onde os arquivos de Material para Holders serão salvos.")
        label_info_holders.setObjectName("pageSubtitle")
        card_holders_layout.addWidget(label_info_holders)

        campo_layout_holders = QHBoxLayout()
        campo_layout_holders.setSpacing(8)

        label_caminho_holders = QLabel("Pasta de destino:")
        label_caminho_holders.setObjectName("statusLabel")
        campo_layout_holders.addWidget(label_caminho_holders)

        self.campo_caminho_holders = QLineEdit()
        self.campo_caminho_holders.setPlaceholderText("Selecione a pasta para salvar Material para Holders...")
        self.campo_caminho_holders.setFixedHeight(34)
        self.campo_caminho_holders.setReadOnly(True)
        campo_layout_holders.addWidget(self.campo_caminho_holders)

        btn_selecionar_holders = QPushButton("Selecionar")
        btn_selecionar_holders.setObjectName("btnSecondary")
        btn_selecionar_holders.setFixedHeight(34)
        btn_selecionar_holders.clicked.connect(self._selecionar_pasta_holders)
        campo_layout_holders.addWidget(btn_selecionar_holders)
        card_holders_layout.addLayout(campo_layout_holders)
        
        botoes_layout_holders = QHBoxLayout()
        botoes_layout_holders.addStretch()

        btn_salvar_holders = QPushButton("Salvar")
        btn_salvar_holders.setObjectName("btnPrimary")
        btn_salvar_holders.setFixedHeight(34)
        btn_salvar_holders.clicked.connect(self._salvar)
        botoes_layout_holders.addWidget(btn_salvar_holders)

        card_holders_layout.addLayout(botoes_layout_holders)
        layout.addWidget(card_holders)
        
        layout.addStretch()

    def _carregar_caminho(self):
        caminho = config.obter_caminho_jsons()
        if caminho:
            self.campo_caminho.setText(os.path.join(caminho, PASTA_ALVO))
            
        caminho_holders = config.obter_caminho_material_holders()
        if caminho_holders:
            self.campo_caminho_holders.setText(os.path.join(caminho_holders, "AlmoxMat"))

    def _selecionar_pasta(self):
        pasta = QFileDialog.getExistingDirectory(self, "Selecionar pasta de destino")
        if pasta:
            self.campo_caminho.setText(os.path.join(pasta, PASTA_ALVO))

    def _selecionar_pasta_holders(self):
        pasta = QFileDialog.getExistingDirectory(self, "Selecionar pasta para Material Holders")
        if pasta:
            self.campo_caminho_holders.setText(os.path.join(pasta, "AlmoxMat"))

    def _salvar(self):
        texto = self.campo_caminho.text().strip()
        texto_holders = getattr(self, "campo_caminho_holders", None)
        texto_holders_val = texto_holders.text().strip() if texto_holders else ""
        
        if texto or texto_holders_val:
            resposta = QMessageBox.question(
                self,
                "Confirmar",
                "Deseja salvar as novas configurações?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if resposta == QMessageBox.StandardButton.Yes:
                if texto:
                    caminho_base = os.path.dirname(texto) if texto.endswith(PASTA_ALVO) else texto
                    config.definir_caminho_jsons(caminho_base)
                    os.makedirs(texto, exist_ok=True)
                if texto_holders_val:
                    caminho_base_holders = os.path.dirname(texto_holders_val) if texto_holders_val.endswith("AlmoxMat") else texto_holders_val
                    config.definir_caminho_material_holders(caminho_base_holders)
                    os.makedirs(texto_holders_val, exist_ok=True)
                
                self.settings_saved.emit()
                
                QMessageBox.information(
                    self,
                    "Sucesso",
                    "Configurações salvas com sucesso!"
                )
