import qtawesome
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QStackedWidget, QLabel, QSizePolicy, QSpacerItem, QScrollArea,
)
from PySide6.QtCore import Qt, QSize, QRect, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFont
from ui.styles import FUSION_QSS
from ui.pages.inicio_page import InicioPage
from ui.pages.programacao_agulhas_page import ProgramacaoAgulhasPage
from ui.pages.dpp_ativos_page import DppAtivosPage
from ui.pages.estoque_page import EstoquePage
from ui.pages.itens_zero_page import ItensZeroPage
from ui.pages.controle_pedidos_page import ControlePedidosPage
from ui.pages.reajuste_precos_page import ReajustePrecosPage
from ui.pages.settings_page import SettingsPage
from ui.pages.fornecedores_page import FornecedoresPage
from ui.pages.pedidos_pendentes_page import PedidosPendentesPage
from ui.pages.follow_up_page import FollowUpPage
from ui.pages.acuracidade_page import AcuracidadePage
from ui.pages.fresh_start_page import FreshStartPage
from ui.pages.lembretes_page import LembretesPage
from ui.pages.material_holders_page import MaterialHoldersPage
from ui.pages.automacoes_page import AutomacoesPage


SIDEBAR_WIDTH = 240
SIDEBAR_COLLAPSED_WIDTH = 58

NAV_ICONS = {
    "estoque": ("fa6s.box", "box"),
    "itens_zero": ("mdi6.basket-remove-outline", "basket-remove"),
    "acuracidade": ("mdi6.target", "target"),
    "controle_pedidos": ("mdi6.clipboard-check-outline", "clipboard-check"),
    "pedidos_pendentes": ("mdi6.clock-outline", "clock"),
    "follow_up": ("mdi6.calendar-clock", "follow-up"),
    "programacao_agulhas": ("mdi6.format-align-justify", "agulhas"),
    "fresh_start": ("mdi6.sprout-outline", "sprout"),
    "lembretes": ("mdi6.note-text-outline", "note"),
    "digitar_ae": ("mdi6.pencil-outline", "pencil"),
    "transferencia": ("mdi6.swap-horizontal", "swap"),
    "remove_loc_duplicadas": ("mdi6.delete-sweep-outline", "delete"),
    "testar_contas": ("mdi6.account-check-outline", "account"),
    "baixa_3_7_page": ("mdi6.download-outline", "download"),
    "fornecedores": ("mdi6.truck-outline", "truck"),
    "reajuste_precos": ("mdi6.tag-arrow-up-outline", "price"),
    "dpp_ativos": ("mdi6.archive-arrow-down-outline", "archive"),
    "material_holders": ("mdi6.view-grid-outline", "grid"),
    "automacoes": ("fa6s.bolt", "bolt"),
    "configuracoes": ("fa6s.gear", "gear"),
}


class SidebarWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._on_enter = None
        self._on_leave = None

    def set_hover_callbacks(self, on_enter, on_leave):
        self._on_enter = on_enter
        self._on_leave = on_leave

    def enterEvent(self, event):
        if self._on_enter:
            self._on_enter()
        super().enterEvent(event)

    def leaveEvent(self, event):
        if self._on_leave:
            self._on_leave()
        super().leaveEvent(event)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Almoxarifado")
        self.resize(1280, 800)
        self.setStyleSheet(FUSION_QSS)
        self._collapsed = False

        container = QWidget()
        self.setCentralWidget(container)
        self.container = container
        root_layout = QHBoxLayout(container)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self._build_content(root_layout)
        self._build_sidebar()

        self._set_sidebar_collapsed(True, animar=False)

        if self.buttons:
            self._switch_tab("estoque")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "sidebar") and hasattr(self, "container"):
            self.sidebar.setGeometry(0, 0, self.sidebar.width(), self.container.height())
            self.sidebar.raise_()

    def _icon(self, icon_id, color='#64748b'):
        try:
            return qtawesome.icon(icon_id, color=color)
        except Exception:
            return None

    def _build_sidebar(self):
        self.sidebar = SidebarWidget(self.container)
        self.sidebar.set_hover_callbacks(self._expand_sidebar, self._collapse_sidebar)
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._sidebar_expanded_width = SIDEBAR_WIDTH
        self.sidebar.move(0, 0)
        self._sidebar_anim = QPropertyAnimation(self.sidebar, b"geometry", self)
        self._sidebar_anim.setDuration(180)
        self._sidebar_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._sidebar_anim.finished.connect(self._fim_animacao_sidebar)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        # ── Header ──
        header = QWidget()
        header.setObjectName("sidebarHeader")
        header.setFixedHeight(70)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(18, 14, 12, 14)
        header_layout.setSpacing(10)

        icon_label = QLabel()
        pixmap = self._icon('fa6s.warehouse', '#6366f1')
        if pixmap:
            icon_label.setPixmap(pixmap.pixmap(22, 22))

        header_texts = QVBoxLayout()
        header_texts.setSpacing(1)
        self.titulo = QLabel("Almoxarifado")
        self.titulo.setObjectName("sidebarTitle")
        self.titulo.setAlignment(Qt.AlignmentFlag.AlignLeft)
        header_texts.addWidget(self.titulo)

        self.subtitulo = QLabel("Sistema de Gestão")
        self.subtitulo.setObjectName("sidebarSubtitle")
        self.subtitulo.setAlignment(Qt.AlignmentFlag.AlignLeft)
        header_texts.addWidget(self.subtitulo)

        header_layout.addWidget(icon_label)
        header_layout.addLayout(header_texts)
        header_layout.addStretch()

        self.btn_toggle = QPushButton("≣")
        self.btn_toggle.setObjectName("sidebarToggle")
        self.btn_toggle.setFixedSize(28, 28)
        self.btn_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle.clicked.connect(self._toggle_sidebar)
        header_layout.addWidget(self.btn_toggle)

        sidebar_layout.addWidget(header)

        # ── Navigation ──
        nav_scroll = QWidget()
        nav_layout = QVBoxLayout(nav_scroll)
        nav_layout.setContentsMargins(0, 8, 0, 8)
        nav_layout.setSpacing(2)

        self.tabs = {}
        self.buttons = []

        self._nav_items = [
            ("estoque",           "Estoque",               False),
            ("itens_zero",        "Itens com Estoque 0",   False),
            ("acuracidade",       "Acuracidade",           False),
            ("controle_pedidos",  "Controle de Pedidos",   False),
            ("pedidos_pendentes", "Pedidos Pendentes",     False),
            ("follow_up",         "Follow-up",             False),
            ("programacao_agulhas", "Prog. de Agulhas",    False),
            ("fresh_start",         "Fresh Start",         False),
            ("lembretes",           "Lembretes",           False),
            ("material_holders",    "Material Holders",    False),
            ("automacoes",          "Automações",          False),
            ("fornecedores",        "Fornecedores",        False),
            ("reajuste_precos",     "Reajuste de Preços",  False),
            ("dpp_ativos",          "DPP Ativos",          False),
            ("configuracoes",       "Configurações",       False),
        ]

        for key, label, is_subitem in self._nav_items:
            icon_id = NAV_ICONS.get(key, ("mdi6.circle-outline",))[0]
            icon = self._icon(icon_id, '#64748b')
            btn = QPushButton(icon, f"  {label}") if icon else QPushButton(f"  {label}")
            btn.setObjectName("tabButton")
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(38)
            btn.clicked.connect(lambda checked, k=key: self._switch_tab(k))
            nav_layout.addWidget(btn)
            self.tabs[key] = btn
            self.buttons.append(btn)

        nav_layout.addStretch()
        sidebar_layout.addWidget(nav_scroll)
        self.sidebar.raise_()

    def _build_content(self, root_layout):
        content = QWidget()
        content.setObjectName("contentArea")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        self.content_layout = content_layout

        self.stacked = QStackedWidget()
        self.pages = {}

        pages = [
            ("inicio",                InicioPage),
            ("estoque",               EstoquePage),
            ("itens_zero",            ItensZeroPage),
            ("acuracidade",           AcuracidadePage),
            ("controle_pedidos",      ControlePedidosPage),
            ("pedidos_pendentes",     PedidosPendentesPage),
            ("follow_up",             FollowUpPage),
            ("programacao_agulhas",   ProgramacaoAgulhasPage),
            ("fresh_start",           FreshStartPage),
            ("lembretes",             LembretesPage),
            ("material_holders",      MaterialHoldersPage),
            ("automacoes",            AutomacoesPage),
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

    def _atualizar_margem_conteudo(self):
        if hasattr(self, "content_layout"):
            self.content_layout.setContentsMargins(SIDEBAR_COLLAPSED_WIDTH, 0, 0, 0)

    def _aplicar_estado_botoes(self, collapsed):
        if collapsed:
            self.titulo.setVisible(False)
            self.subtitulo.setVisible(False)
            self.btn_toggle.setVisible(False)
            for key, label, is_subitem in self._nav_items:
                if key in self.tabs:
                    icon_id = NAV_ICONS.get(key, ("mdi6.circle-outline",))[0]
                    icon = self._icon(icon_id, '#64748b')
                    if icon:
                        self.tabs[key].setIcon(icon)
                    self.tabs[key].setText("")
                    self.tabs[key].setFixedWidth(58)
        else:
            self.titulo.setVisible(True)
            self.subtitulo.setVisible(True)
            self.btn_toggle.setVisible(True)
            for key, label, is_subitem in self._nav_items:
                if key in self.tabs:
                    btn = self.tabs[key]
                    btn.setText(f"  {label}")
                    icon_id = NAV_ICONS.get(key, ("mdi6.circle-outline",))[0]
                    icon = self._icon(icon_id, '#64748b')
                    if icon:
                        btn.setIcon(icon)
                    btn.setFixedWidth(0)
                    btn.setMaximumWidth(16777215)
        self.sidebar.raise_()

    def _fim_animacao_sidebar(self):
        self._aplicar_estado_botoes(self._collapsed)

    def _set_sidebar_collapsed(self, collapsed, animar=True):
        self._collapsed = collapsed
        alvo = 58 if collapsed else self._sidebar_expanded_width
        h = self.container.height()
        if collapsed:
            self._aplicar_estado_botoes(True)
        if animar and h > 0:
            self._sidebar_anim.stop()
            self._sidebar_anim.setStartValue(self.sidebar.geometry())
            self._sidebar_anim.setEndValue(QRect(0, 0, alvo, h))
            self._sidebar_anim.start()
        else:
            self.sidebar.setGeometry(0, 0, alvo, h)
            self._aplicar_estado_botoes(collapsed)
        self._atualizar_margem_conteudo()

    def _expand_sidebar(self):
        self._set_sidebar_collapsed(False)

    def _collapse_sidebar(self):
        self._set_sidebar_collapsed(True)

    def _toggle_sidebar(self):
        self._set_sidebar_collapsed(not self._collapsed)
