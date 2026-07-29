from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QStackedWidget, QLabel, QSizePolicy, QSpacerItem, QScrollArea,
)
from PySide6.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve
from ui.styles import FUSION_QSS
from ui.pages.inicio_page import InicioPage
from ui.pages.programacao_agulhas_page import ProgramacaoAgulhasPage
from ui.pages.digitar_ae_page import DigitarAEPage
from ui.pages.dpp_ativos_page import DppAtivosPage
from ui.pages.transferencia_page import TransferenciaPage
from ui.pages.remove_loc_duplicadas_page import RemoveLocDuplicadasPage
from ui.pages.estoque_page import EstoquePage
from ui.pages.itens_zero_page import ItensZeroPage
from ui.pages.controle_pedidos_page import ControlePedidosPage
from ui.pages.reajuste_precos_page import ReajustePrecosPage
from ui.pages.settings_page import SettingsPage
from ui.pages.fornecedores_page import FornecedoresPage
from ui.pages.pedidos_pendentes_page import PedidosPendentesPage
from ui.pages.testar_contas_page import TestarContasPage
from ui.pages.baixa_3_7_page import Baixa37Page


SIDEBAR_WIDTH = 230


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Almoxarifado")
        self.resize(1200, 750)
        self.setStyleSheet(FUSION_QSS)
        self._collapsed = False
        self._automacoes_expanded = True

        container = QWidget()
        self.setCentralWidget(container)
        root_layout = QHBoxLayout(container)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self._build_sidebar(root_layout)
        self._build_content(root_layout)

        if self.buttons:
            self._switch_tab("estoque")

    def _build_sidebar(self, root_layout):
        self.sidebar = QWidget()
        self.sidebar.setObjectName("sidebar")
        self._sidebar_expanded_width = SIDEBAR_WIDTH
        self.sidebar.setFixedWidth(self._sidebar_expanded_width)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        # ── Header ──
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

        # ── Navigation ──
        nav_scroll = QWidget()
        nav_layout = QVBoxLayout(nav_scroll)
        nav_layout.setContentsMargins(0, 8, 0, 8)
        nav_layout.setSpacing(0)

        # Menu items: (key, label, icon)
        # key=None means it's a group header
        self.tabs = {}
        self.buttons = []

        # Each entry: (key_or_none, label, icon, is_subitem)
        self._nav_items = [
            ("estoque",           "Estoque",               "▣", False),
            ("itens_zero",        "Itens 0",               "○", False),
            ("controle_pedidos",  "Controle de Pedidos",   "☐", False),
            ("pedidos_pendentes", "Pedidos Pendentes",     "◈", False),
            ("programacao_agulhas", "Prog. de Agulhas",    "⊞", False),
            # Automações group header
            (None, "Automações", "⚡", False),
            ("digitar_ae",        "Digitar AE",            "✎", True),
            ("transferencia",     "Transferência",         "⇄", True),
            ("remove_loc_duplicadas", "Remove Loc Dup.",   "⇄", True),
            ("testar_contas",     "Testar Contas",         "⬡", True),
            ("baixa_3_7_page",     "Baixa 3.7",         "⬡", True),
            # Back to top level
            ("fornecedores",      "Fornecedores",          "⚑", False),
            ("reajuste_precos",   "Reajuste de Preços",    "♯", False),
            ("dpp_ativos",        "DPP Ativos",            "📥", False),
            ("configuracoes",     "Configurações",         "⚙", False),
        ]

        # Sub-item keys
        self._subitem_keys = {
            "digitar_ae", "transferencia", "remove_loc_duplicadas", "testar_contas", "baixa_3_7_page"
        }

        # Create the group header button for "Automações"
        self._btn_automacoes = None
        # Container widget for the submenu items
        self._submenu_widget = QWidget()
        submenu_layout = QVBoxLayout(self._submenu_widget)
        submenu_layout.setContentsMargins(0, 0, 0, 0)
        submenu_layout.setSpacing(0)
        self._submenu_widget.setVisible(False)
        self._subitem_buttons = []

        for key, label, icon, is_subitem in self._nav_items:
            if key is None:
                # Group header for "Automações"
                btn = QPushButton(f"{icon}  {label}")
                btn.setObjectName("tabButton")
                btn.setCheckable(False)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.setFixedHeight(40)
                btn.setStyleSheet(
                    "QPushButton#tabButton { color: #60a5fa; font-weight: 600; }"
                )
                btn.setEnabled(False)  # label only, not clickable
                nav_layout.addWidget(btn)
                self._btn_automacoes = btn
                self._submenu_widget.setVisible(True)
                nav_layout.addWidget(self._submenu_widget)
            elif is_subitem:
                btn = QPushButton(f"  {icon}  {label}")
                btn.setObjectName("tabSubButton")
                btn.setCheckable(True)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.setFixedHeight(36)
                btn.clicked.connect(lambda checked, k=key: self._switch_tab(k))
                submenu_layout.addWidget(btn)
                self.tabs[key] = btn
                self.buttons.append(btn)
                self._subitem_buttons.append(btn)
            else:
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

    def _toggle_automacoes(self):
        pass  # Automações submenu is always open

    def _build_content(self, root_layout):
        content = QWidget()
        content.setObjectName("contentArea")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        self.stacked = QStackedWidget()
        self.pages = {}

        pages = [
            ("inicio",                InicioPage),
            ("estoque",               EstoquePage),
            ("itens_zero",            ItensZeroPage),
            ("controle_pedidos",      ControlePedidosPage),
            ("pedidos_pendentes",     PedidosPendentesPage),
            ("programacao_agulhas",   ProgramacaoAgulhasPage),
            ("digitar_ae",            DigitarAEPage),
            ("transferencia",         TransferenciaPage),
            ("remove_loc_duplicadas", RemoveLocDuplicadasPage),
            ("testar_contas",         TestarContasPage),
            ("baixa_3_7_page",         Baixa37Page),
            ("fornecedores",          FornecedoresPage),
            ("reajuste_precos",       ReajustePrecosPage),
            ("dpp_ativos",            DppAtivosPage),
            ("configuracoes",         SettingsPage),
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
        # Auto-expand submenu when a sub-item is selected
        if key in self._subitem_keys and not self._automacoes_expanded:
            self._toggle_automacoes()

    def _toggle_sidebar(self):
        self._collapsed = not self._collapsed
        if self._collapsed:
            self.sidebar.setFixedWidth(55)
            self.titulo.setVisible(False)
            self.subtitulo.setVisible(False)
            # Collapse icons only
            for key, label, icon, is_subitem in self._nav_items:
                if key is None:
                    self._btn_automacoes.setText("⚡")
                elif key in self.tabs:
                    self.tabs[key].setText(icon)
        else:
            self.sidebar.setFixedWidth(self._sidebar_expanded_width)
            self.titulo.setVisible(True)
            self.subtitulo.setVisible(True)
            for key, label, icon, is_subitem in self._nav_items:
                if key is None:
                    arrow = "▾" if self._automacoes_expanded else "▸"
                    self._btn_automacoes.setText(f"{icon}  {label}  {arrow}")
                elif key in self.tabs:
                    prefix = "  " if is_subitem else ""
                    self.tabs[key].setText(f"{prefix}{icon}  {label}")
