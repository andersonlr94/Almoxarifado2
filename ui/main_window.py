from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QStackedWidget, QLabel, QSizePolicy, QSpacerItem
from PySide6.QtCore import Qt, QSize
from ui.styles import FUSION_QSS
from ui.pages.inicio_page import InicioPage
from ui.pages.programacao_agulhas_page import ProgramacaoAgulhasPage
from ui.pages.digitar_ae_page import DigitarAEPage
from ui.pages.transferencia_page import TransferenciaPage
from ui.pages.estoque_page import EstoquePage
from ui.pages.itens_zero_page import ItensZeroPage
from ui.pages.reajuste_precos_page import ReajustePrecosPage
from ui.pages.settings_page import SettingsPage


SIDEBAR_WIDTH = 220


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Almoxarifado")
        self.resize(1200, 750)
        self.setStyleSheet(FUSION_QSS)

        container = QWidget()
        self.setCentralWidget(container)
        root_layout = QHBoxLayout(container)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self._build_sidebar(root_layout)
        self._build_content(root_layout)

        if self.buttons:
            self._switch_tab("inicio")

    def _build_sidebar(self, root_layout):
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(SIDEBAR_WIDTH)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        header = QWidget()
        header.setObjectName("sidebarHeader")
        header.setFixedHeight(72)
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(16, 14, 16, 14)
        header_layout.setSpacing(2)

        titulo = QLabel("Almoxarifado")
        titulo.setObjectName("sidebarTitle")
        titulo.setAlignment(Qt.AlignmentFlag.AlignLeft)
        header_layout.addWidget(titulo)

        subtitulo = QLabel("Sistema de Gestão")
        subtitulo.setObjectName("sidebarSubtitle")
        subtitulo.setAlignment(Qt.AlignmentFlag.AlignLeft)
        header_layout.addWidget(subtitulo)

        sidebar_layout.addWidget(header)

        nav_scroll = QWidget()
        nav_layout = QVBoxLayout(nav_scroll)
        nav_layout.setContentsMargins(0, 8, 0, 8)
        nav_layout.setSpacing(0)

        tab_data = [
            ("inicio", "Início"),
            ("programacao_agulhas", "Programação de Agulhas"),
            ("digitar_ae", "Digitar AE"),
            ("transferencia", "Transferência"),
            ("estoque", "Estoque"),
            ("itens_zero", "Itens 0"),
            ("reajuste_precos", "Reajuste de Preços"),
            ("configuracoes", "Configurações"),
        ]
        self.tabs = {}
        self.buttons = []
        for key, label in tab_data:
            btn = QPushButton(label)
            btn.setObjectName("tabButton")
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(40)
            btn.clicked.connect(lambda checked, k=key: self._switch_tab(k))
            nav_layout.addWidget(btn)
            self.tabs[key] = btn
            self.buttons.append(btn)

        nav_layout.addStretch()
        sidebar_layout.addWidget(nav_scroll)
        root_layout.addWidget(sidebar)

    def _build_content(self, root_layout):
        content = QWidget()
        content.setObjectName("contentArea")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        self.stacked = QStackedWidget()
        self.pages = {}

        pages = [
            ("inicio", InicioPage),
            ("programacao_agulhas", ProgramacaoAgulhasPage),
            ("digitar_ae", DigitarAEPage),
            ("transferencia", TransferenciaPage),
            ("estoque", EstoquePage),
            ("itens_zero", ItensZeroPage),
            ("reajuste_precos", ReajustePrecosPage),
            ("configuracoes", SettingsPage),
        ]
        for key, PageClass in pages:
            page = PageClass()
            self.pages[key] = page
            self.stacked.addWidget(page)

        content_layout.addWidget(self.stacked)
        root_layout.addWidget(content)

    def _switch_tab(self, key):
        for btn in self.buttons:
            btn.setChecked(False)
        self.tabs[key].setChecked(True)
        self.stacked.setCurrentWidget(self.pages[key])
