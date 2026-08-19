from PySide6.QtWidgets import QWidget, QVBoxLayout, QTabWidget

from ui.pages.digitar_ae_page import DigitarAEPage
from ui.pages.transferencia_page import TransferenciaPage
from ui.pages.remove_loc_duplicadas_page import RemoveLocDuplicadasPage
from ui.pages.testar_contas_page import TestarContasPage
from ui.pages.baixa_3_7_page import Baixa37Page


class AutomacoesPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setStyleSheet(
            "QTabWidget::pane { border: none; background: transparent; }"
            "QTabWidget::tab-bar { left: 30px; }"
            "QTabBar::tab { background: transparent; color: #64748b; padding: 10px 22px; "
            "font-size: 13px; font-weight: 600; border: none; margin-right: 4px; margin-top: 6px; }"
            "QTabBar::tab:hover { color: #4f46e5; }"
            "QTabBar::tab:selected { color: #4f46e5; background: #eef2ff; "
            "border-radius: 10px; }"
        )
        self.tabs.addTab(DigitarAEPage(), "Digitar AE")
        self.tabs.addTab(TransferenciaPage(), "Transferência")
        self.tabs.addTab(RemoveLocDuplicadasPage(), "Remove Loc. Dup.")
        self.tabs.addTab(TestarContasPage(), "Testar Contas")
        self.tabs.addTab(Baixa37Page(), "Baixa 3.7")
        layout.addWidget(self.tabs, 1)