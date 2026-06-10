from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt


class ReajustePrecosPage(QWidget):
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

        titulo = QLabel("Reajuste de Preços")
        titulo.setObjectName("pageTitle")
        card_layout.addWidget(titulo)

        subtitulo = QLabel("Gerencie reajustes de preços dos itens")
        subtitulo.setObjectName("pageSubtitle")
        card_layout.addWidget(subtitulo)

        layout.addWidget(card)
        layout.addStretch()
