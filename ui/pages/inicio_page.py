from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt


class InicioPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(16)

        card = QWidget()
        card.setObjectName("pageCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(32, 32, 32, 32)
        card_layout.setSpacing(8)

        titulo = QLabel("Início")
        titulo.setObjectName("pageTitle")
        card_layout.addWidget(titulo)

        subtitulo = QLabel("Bem-vindo ao sistema de Almoxarifado")
        subtitulo.setObjectName("pageSubtitle")
        card_layout.addWidget(subtitulo)

        layout.addWidget(card)
        layout.addStretch()
