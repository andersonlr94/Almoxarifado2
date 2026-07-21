from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QStackedWidget, QLabel, QSizePolicy, QSpacerItem
from PySide6.QtCore import Qt, QSize
from ui.styles import FUSION_QSS
from ui.pages.inicio_page import InicioPage
from ui.pages.programacao_agulhas_page import ProgramacaoAgulhasPage
from ui.pages.digitar_ae_page import DigitarAEPage
from ui.pages.dpp_ativos_page import DppAtivosPage
from ui.pages.transferencia_page import TransferenciaPage
from ui.pages.estoque_page import EstoquePage
from ui.pages.itens_zero_page import ItensZeroPage
from ui.pages.controle_pedidos_page import ControlePedidosPage
from ui.pages.reajuste_precos_page import ReajustePrecosPage
from ui.pages.settings_page import SettingsPage
from ui.pages.fornecedores_page import FornecedoresPage
from ui.pages.pedidos_pendentes_page import PedidosPendentesPage
from ui.pages.testar_contas_page import TestarContasPage


SIDEBAR_WIDTH = 220


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Almoxarifado")
        self.resize(1200, 750)
        self.setStyleSheet(FUSION_QSS)
        self._collapsed = False

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
        self.sidebar = QWidget()
        self.sidebar.setObjectName("sidebar")
        self._sidebar_expanded_width = SIDEBAR_WIDTH
        self.sidebar.setFixedWidth(self._sidebar_expanded_width)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        header = QWidget()
        header.setObjectName("sidebarHeader")
        header.setFixedHeight(72)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 14, 12, 14)
        header_layout.setSpacing(8)

        header_texts = QVBoxLayout()
        header_texts.setSpacing(2)
        self.titulo = QLabel("Almoxarifado")
        self.titulo.setObjectName("sidebarTitle")
        self.titulo.setAlignment(Qt.AlignmentFlag.AlignLeft)
        header_texts.addWidget(self.titulo)

        self.subtitulo = QLabel("Sistema de Gestão")
        self.subtitulo.setObjectName("sidebarSubtitle")
        self.subtitulo.setAlignment(Qt.AlignmentFlag.AlignLeft)
        header_texts.addWidget(self.subtitulo)
        header_layout.addLayout(header_texts)

        header_layout.addStretch()

        self.btn_toggle = QPushButton("≣")
        self.btn_toggle.setObjectName("tabButton")
        self.btn_toggle.setFixedSize(28, 28)
        self.btn_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle.clicked.connect(self._toggle_sidebar)
        header_layout.addWidget(self.btn_toggle)

        sidebar_layout.addWidget(header)

        nav_scroll = QWidget()
        nav_layout = QVBoxLayout(nav_scroll)
        nav_layout.setContentsMargins(0, 8, 0, 8)
        nav_layout.setSpacing(0)

        tab_data = [
            ("inicio", "Início", "⌂"),
            ("programacao_agulhas", "Programação de Agulhas", "⊞"),
            ("digitar_ae", "Digitar AE", "✎"),
            ("dpp_ativos", "DPP Ativos", "📥"),
            ("transferencia", "Transferência", "⇄"),
            ("estoque", "Estoque", "▣"),
            ("itens_zero", "Itens 0", "○"),
            ("fornecedores", "Fornecedores", "⚑"),
            ("controle_pedidos", "Controle de Pedidos", "☐"),
            ("pedidos_pendentes", "Pedidos Pendentes", "◈"),
            ("testar_contas", "Testar Contas", "⬡"),
            ("reajuste_precos", "Reajuste de Preços", "♯"),
            ("configuracoes", "Configurações", "⚙"),
        ]
        self.tabs = {}
        self.buttons = []
        self.tab_data = tab_data
        for key, label, icon in tab_data:
            btn = QPushButton(f"{icon}  {label}")
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
        root_layout.addWidget(self.sidebar)

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
            ("dpp_ativos", DppAtivosPage),
            ("transferencia", TransferenciaPage),
            ("estoque", EstoquePage),
            ("itens_zero", ItensZeroPage),
            ("fornecedores", FornecedoresPage),
            ("controle_pedidos", ControlePedidosPage),
            ("pedidos_pendentes", PedidosPendentesPage),
            ("testar_contas", TestarContasPage),
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

    def _toggle_sidebar(self):
        self._collapsed = not self._collapsed
        if self._collapsed:
            self.sidebar.setFixedWidth(55)
            self.titulo.setVisible(False)
            self.subtitulo.setVisible(False)
            for btn, (_key, label, icon) in zip(self.buttons, self.tab_data):
                btn.setText(icon)
        else:
            self.sidebar.setFixedWidth(self._sidebar_expanded_width)
            self.titulo.setVisible(True)
            self.subtitulo.setVisible(True)
            for btn, (_key, label, icon) in zip(self.buttons, self.tab_data):
                btn.setText(f"{icon}  {label}")
