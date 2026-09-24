import os
import qtawesome
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QStackedWidget, QLabel, QSizePolicy, QSpacerItem, QScrollArea, QMessageBox, QFrame
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
from ui.pages.usuarios_page import UsuariosPage
from core import session as session_core
from core import auth as auth_core
import config
from core.eventos_watcher import EventosWatcher
from core import eventos as eventos_core


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
    "usuarios": ("mdi6.account-group-outline", "account-group"),
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
        self._logout_requested = False
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

        self._atualizar_usuario_footer()

        # ── Watcher de eventos direcionados (inbox do usuário logado) ──
        self._eventos_watcher = EventosWatcher(self)
        self._eventos_watcher.novo_evento.connect(self._on_evento_recebido)
        # banner de notificação (overlay no content)
        self._notif_banner = None
        self._notif_timer = None
        self._iniciar_watcher_eventos()
        # contador de eventos não lidos (sino)
        self._eventos_nao_lidos = 0
        self._badge_notif = None
        self._criar_badge_notificacao()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "sidebar") and hasattr(self, "container"):
            self.sidebar.setGeometry(0, 0, self.sidebar.width(), self.container.height())
            self.sidebar.raise_()
        # reposiciona banner se visível
        try:
            if hasattr(self, "_notif_banner") and self._notif_banner and self._notif_banner.isVisible():
                self._notif_banner.setGeometry(60, 10, self.container.width() - 70, 70)
                self._notif_banner.raise_()
        except Exception:
            pass

    def closeEvent(self, event):
        try:
            self._parar_watcher_eventos()
        except Exception:
            pass
        super().closeEvent(event)

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

        self.header_layout = header_layout
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
            ("usuarios",            "Usuários",            False),
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

        # ── Footer usuário + logout ──
        self._build_user_footer(sidebar_layout)

        self.sidebar.raise_()

    def _build_user_footer(self, sidebar_layout):
        footer = QWidget()
        footer.setObjectName("sidebarFooter")
        footer.setStyleSheet("""
            QWidget#sidebarFooter {
                background-color: #f8fafc;
                border-top: 1px solid #eef1f6;
            }
            QLabel#userNameLabel {
                color: #1e1b4b;
                font-size: 12px;
                font-weight: 700;
            }
            QLabel#userRoleLabel {
                color: #64748b;
                font-size: 10px;
                font-weight: 500;
            }
            QPushButton#btnLogout {
                background-color: #ffffff;
                color: #ef4444;
                border: 1px solid #fecaca;
                border-radius: 8px;
                padding: 6px 6px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton#btnLogout:hover {
                background-color: #fef2f2;
                border-color: #fca5a5;
            }
        """)
        footer_layout = QVBoxLayout(footer)
        footer_layout.setContentsMargins(8, 10, 8, 10)
        footer_layout.setSpacing(6)

        # Linha superior: ícone + nomes
        user_row = QHBoxLayout()
        user_row.setSpacing(8)
        user_row.setContentsMargins(0, 0, 0, 0)

        self.footer_icon = QLabel()
        try:
            icon = self._icon('mdi6.account-circle-outline', '#6366f1')
            if icon:
                self.footer_icon.setPixmap(icon.pixmap(28, 28))
        except Exception:
            self.footer_icon.setText("👤")
        self.footer_icon.setFixedSize(28, 28)
        self.footer_icon.setAlignment(Qt.AlignCenter)
        user_row.addWidget(self.footer_icon)

        texts = QVBoxLayout()
        texts.setSpacing(0)
        texts.setContentsMargins(0, 0, 0, 0)
        self.lbl_user_name = QLabel("Usuário")
        self.lbl_user_name.setObjectName("userNameLabel")
        self.lbl_user_role = QLabel("perfil")
        self.lbl_user_role.setObjectName("userRoleLabel")
        texts.addWidget(self.lbl_user_name)
        texts.addWidget(self.lbl_user_role)
        # badge Auto
        self.lbl_auto = QLabel("Auto")
        self.lbl_auto.setObjectName("autoBadge")
        self.lbl_auto.setStyleSheet("""
            QLabel#autoBadge {
                background-color: #ecfdf5;
                color: #059669;
                border: 1px solid #a7f3d0;
                border-radius: 6px;
                padding: 1px 6px;
                font-size: 9px;
                font-weight: 700;
            }
        """)
        self.lbl_auto.setToolTip("Entrada automática ativa — próximas vezes já entra direto")
        self.lbl_auto.setVisible(False)
        texts.addWidget(self.lbl_auto, alignment=Qt.AlignLeft)
        user_row.addLayout(texts)
        user_row.addStretch()

        footer_layout.addLayout(user_row)

        self.btn_logout = QPushButton(" Sair")
        try:
            self.btn_logout.setIcon(qtawesome.icon("fa6s.right-from-bracket", color="#ef4444"))
        except Exception:
            pass
        self.btn_logout.setObjectName("btnLogout")
        self.btn_logout.setFixedHeight(30)
        self.btn_logout.setCursor(Qt.PointingHandCursor)
        self.btn_logout.setToolTip("Encerrar sessão e voltar ao login")
        self.btn_logout.clicked.connect(self._logout)
        footer_layout.addWidget(self.btn_logout)

        self.footer_widget = footer
        self.footer_layout = footer_layout
        sidebar_layout.addWidget(footer)

        # guarda para collapsed handling
        self._footer_texts = texts

    def _atualizar_usuario_footer(self):
        user = session_core.get_current_user()
        if not user:
            self.lbl_user_name.setText("Deslogado")
            self.lbl_user_role.setText("")
            if hasattr(self, "lbl_auto"):
                self.lbl_auto.setVisible(False)
            self.setWindowTitle("Almoxarifado")
            return
        nome = user.get("display_name") or user.get("username", "")
        role = user.get("role", "user")
        # abrevia se muito longo
        if len(nome) > 16:
            nome = nome[:16] + "…"
        self.lbl_user_name.setText(nome)
        self.lbl_user_role.setText("Administrador" if role == "admin" else "Usuário")
        # mostra badge Auto se entrada automática ativa para este usuário
        if hasattr(self, "lbl_auto"):
            try:
                auto_user, auto_token = config.obter_auto_login()
                is_auto = bool(auto_user and auto_user.lower() == user.get("username","").lower() and config.is_auto_login_enabled())
                # valida token ainda bate com hash atual (se senha mudou, não mostra)
                if is_auto:
                    full = auth_core.find_user(user.get("username",""))
                    if not full or full.get("password_hash") != auto_token:
                        is_auto = False
                self.lbl_auto.setVisible(is_auto)
            except Exception:
                self.lbl_auto.setVisible(False)
        self.setWindowTitle(f"Almoxarifado — {user.get('display_name') or user.get('username','')} ({'Admin' if role=='admin' else 'Usuário'})")
        # controla visibilidade de "Usuários" conforme role
        if hasattr(self, "tabs") and "usuarios" in self.tabs:
            is_admin = session_core.is_admin()
            self.tabs["usuarios"].setVisible(is_admin)
            # se não-admin e estava em usuarios, volta para estoque
            if not is_admin and self.stacked.currentWidget() == self.pages.get("usuarios"):
                self._switch_tab("estoque")
        # atualiza página de usuários se existir
        try:
            if "usuarios" in getattr(self, "pages", {}):
                self.pages["usuarios"].refresh_for_user_change()
        except Exception:
            pass

    def _logout(self):
        # Se auto-login estiver ativo para este usuário, oferece opção de mantê-lo
        auto_user, _ = config.obter_auto_login() if hasattr(config, "obter_auto_login") else (None, None)
        is_auto_for_me = bool(auto_user and auto_user.lower() == session_core.get_username().lower() and config.is_auto_login_enabled())
        if is_auto_for_me:
            box = QMessageBox(self)
            box.setWindowTitle("Sair")
            box.setText(f"Deseja encerrar a sessão de '{session_core.get_display_name()}' e voltar ao login?")
            box.setInformativeText("Entrada automática está ATIVA para você.\n\n• Escolha 'Manter Auto' para continuar entrando direto nas próximas vezes.\n• Escolha 'Desativar Auto' para remover a entrada automática.")
            btn_manter = box.addButton("Manter Auto e Sair", QMessageBox.YesRole)
            btn_desativar = box.addButton("Desativar Auto e Sair", QMessageBox.DestructiveRole)
            btn_cancel = box.addButton(QMessageBox.Cancel)
            box.setDefaultButton(btn_manter)
            box.exec()
            clicked = box.clickedButton()
            if clicked == btn_cancel:
                return
            if clicked == btn_desativar:
                try:
                    auth_core.disable_auto_login()
                except Exception:
                    try:
                        config.limpar_auto_login()
                    except Exception:
                        pass
            # se clicou Manter, mantém auto (não limpa)
            self._logout_requested = True
            self.close()
            return

        resp = QMessageBox.question(
            self, "Sair",
            f"Deseja encerrar a sessão de '{session_core.get_display_name()}' e voltar ao login?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if resp != QMessageBox.Yes:
            return
        self._logout_requested = True
        self.close()

    # ── Eventos direcionados ──
    def _criar_badge_notificacao(self):
        # Badge simples no header (ao lado do sino) — usa QLabel no header_layout
        # Como header já existe, adicionamos após o subtítulo
        try:
            if hasattr(self, "subtitulo") and hasattr(self, "header_layout"):
                self._badge_notif = QLabel("0")
                self._badge_notif.setObjectName("notifBadge")
                self._badge_notif.setAlignment(Qt.AlignCenter)
                self._badge_notif.setFixedSize(22, 22)
                self._badge_notif.setStyleSheet("""
                    QLabel#notifBadge {
                        background-color: #ef4444;
                        color: white;
                        border-radius: 11px;
                        font-size: 11px;
                        font-weight: 700;
                    }
                """)
                self._badge_notif.setVisible(False)
                self._badge_notif.setToolTip("Eventos não lidos")
                self._badge_notif.mousePressEvent = lambda e: self._abrir_programacao_agulhas_separando()
                self.header_layout.addWidget(self._badge_notif)
        except Exception:
            pass

    def _iniciar_watcher_eventos(self):
        try:
            if hasattr(self, "_eventos_watcher") and session_core.is_authenticated():
                self._eventos_watcher.iniciar(session_core.get_username())
        except Exception:
            pass

    def _parar_watcher_eventos(self):
        try:
            if hasattr(self, "_eventos_watcher"):
                self._eventos_watcher.parar()
        except Exception:
            pass

    def _abrir_programacao_agulhas_separando(self):
        try:
            self._switch_tab("programacao_agulhas")
            page = self.pages.get("programacao_agulhas")
            if page and hasattr(page, "_filtrar_por_status"):
                page._filtrar_por_status("Separando")
            self._eventos_nao_lidos = 0
            if hasattr(self, "_badge_notif") and self._badge_notif:
                self._badge_notif.setVisible(False)
        except Exception:
            pass

    def _on_evento_recebido(self, evento: dict):
        # Incrementa badge
        self._eventos_nao_lidos = getattr(self, "_eventos_nao_lidos", 0) + 1
        if hasattr(self, "_badge_notif") and self._badge_notif:
            self._badge_notif.setText(str(self._eventos_nao_lidos))
            self._badge_notif.setVisible(True)

        de_display = evento.get("de_display") or evento.get("de") or "Usuário"
        page = evento.get("page", "")
        extra = evento.get("extra") if isinstance(evento.get("extra"), dict) else {}
        itens = extra.get("itens") if isinstance(extra, dict) else None

        # Se veio com itens (novo fluxo Enviar), imprime automaticamente na impressora de Separando
        if isinstance(itens, list) and len(itens) > 0:
            titulo = "Itens recebidos"
            msg = f"O usuário {de_display} enviou {len(itens)} item(ns) para você"
            detalhe = "Imprimindo automaticamente na impressora de Separando..."
            self._mostrar_banner_evento(titulo, msg, detalhe, evento)
            # imprime independente da página atual (usa impressora salva em Separando/Estoque)
            try:
                from PySide6.QtCore import QTimer
                QTimer.singleShot(400, lambda it=itens, dd=de_display: self._imprimir_itens_recebidos(it, dd))
            except Exception:
                self._imprimir_itens_recebidos(itens, de_display)
            return

        # Fallback legado: apenas notificação de clique
        titulo = "Notificação"
        msg = f"O usuário {de_display} clicou no botão"
        detalhe = f"em Programação de Agulhas • Separando" if page == "programacao_agulhas" else ""
        self._mostrar_banner_evento(titulo, msg, detalhe, evento)

    def _imprimir_itens_recebidos(self, itens: list, de_display: str):
        """Imprime automaticamente na impressora selecionada em Separando (config). Não importa a página atual."""
        try:
            import config
            from core.print_helper import imprimir_itens
            impressora = config.obter_impressora_padrao()
            # Fallback: tenta pegar da página Separando se config estiver vazio mas combo tem valor
            if not impressora:
                try:
                    page = self.pages.get("programacao_agulhas")
                    if page and hasattr(page, "combo_impressoras"):
                        impressora = page.combo_impressoras.currentText().strip()
                        if impressora == "Nenhuma impressora encontrada":
                            impressora = ""
                except Exception:
                    pass

            ok, msg = imprimir_itens(itens, impressora, parent=self)
            # Mostra resultado como segunda notificação
            try:
                from qfluentwidgets import InfoBar, InfoBarPosition
                from PySide6.QtCore import Qt
                if ok:
                    InfoBar.success(
                        title="Impressão automática",
                        content=msg,
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.TOP,
                        duration=5000,
                        parent=self
                    )
                else:
                    InfoBar.warning(
                        title="Impressão pendente",
                        content=f"Recebido de {de_display} ({len(itens)} itens) — {msg}",
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.TOP,
                        duration=8000,
                        parent=self
                    )
            except Exception:
                # fallback banner
                titulo2 = "Impressão automática" if ok else "Impressão pendente"
                self._mostrar_banner_evento(titulo2, msg, f"De {de_display}", {})
        except Exception as e:
            try:
                self._mostrar_banner_evento("Erro na impressão", str(e), f"De {de_display}", {})
            except Exception:
                pass

    def _mostrar_banner_evento(self, titulo: str, msg: str, detalhe: str, evento: dict):
        # Tenta usar qfluentwidgets InfoBar, senão banner custom
        try:
            from qfluentwidgets import InfoBar, InfoBarPosition
            # InfoBar precisa de parent; usa o content
            InfoBar.success(
                title=titulo,
                content=msg + (f" — {detalhe}" if detalhe else ""),
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=6000,
                parent=self
            )
            # mantém badge até usuário clicar
            return
        except Exception:
            pass
        # Fallback: banner custom no topo do content
        try:
            from PySide6.QtCore import QTimer
            if self._notif_banner is None:
                self._notif_banner = QFrame(self.container)
                self._notif_banner.setObjectName("notifBanner")
                self._notif_banner.setStyleSheet("""
                    QFrame#notifBanner {
                        background-color: #eef2ff;
                        border: 1px solid #c7d2fe;
                        border-radius: 10px;
                    }
                    QLabel#notifTitle { color: #4338ca; font-size: 12px; font-weight: 700; }
                    QLabel#notifMsg { color: #1e1b4b; font-size: 13px; }
                    QLabel#notifDetail { color: #64748b; font-size: 11px; }
                """)
                banner_layout = QHBoxLayout(self._notif_banner)
                banner_layout.setContentsMargins(14, 10, 14, 10)
                banner_layout.setSpacing(12)
                icon = QLabel("🔔")
                icon.setFixedSize(24, 24)
                icon.setAlignment(Qt.AlignCenter)
                banner_layout.addWidget(icon)
                texts = QVBoxLayout()
                texts.setSpacing(2)
                self._notif_title = QLabel(titulo)
                self._notif_title.setObjectName("notifTitle")
                self._notif_msg = QLabel(msg)
                self._notif_msg.setObjectName("notifMsg")
                self._notif_msg.setWordWrap(True)
                self._notif_detail = QLabel(detalhe)
                self._notif_detail.setObjectName("notifDetail")
                texts.addWidget(self._notif_title)
                texts.addWidget(self._notif_msg)
                if detalhe:
                    texts.addWidget(self._notif_detail)
                banner_layout.addLayout(texts, 1)
                btn_ver = QPushButton("Ver")
                btn_ver.setObjectName("btnPrimary")
                btn_ver.setFixedHeight(28)
                btn_ver.setCursor(Qt.PointingHandCursor)
                btn_ver.clicked.connect(lambda: (self._abrir_programacao_agulhas_separando(), self._notif_banner.hide()))
                banner_layout.addWidget(btn_ver)
                btn_ok = QPushButton("✕")
                btn_ok.setFixedSize(28, 28)
                btn_ok.setStyleSheet("QPushButton { background: transparent; border: none; color: #64748b; font-weight: 700; } QPushButton:hover { color: #4338ca; }")
                btn_ok.clicked.connect(self._notif_banner.hide)
                banner_layout.addWidget(btn_ok)
                self._notif_banner.setGeometry(60, 10, self.container.width() - 70, 60)
                self._notif_banner.hide()
                self._notif_banner.raise_()

            self._notif_title.setText(titulo)
            self._notif_msg.setText(msg)
            self._notif_detail.setText(detalhe)
            self._notif_detail.setVisible(bool(detalhe))
            # reposiciona se container redimensionado
            self._notif_banner.setGeometry(60, 10, self.container.width() - 70, 70)
            self._notif_banner.show()
            self._notif_banner.raise_()
            if self._notif_timer is None:
                from PySide6.QtCore import QTimer
                self._notif_timer = QTimer(self)
                self._notif_timer.setSingleShot(True)
                self._notif_timer.timeout.connect(lambda: self._notif_banner.hide() if self._notif_banner else None)
            self._notif_timer.stop()
            self._notif_timer.start(6000)
            # Marca evento como lido após 2s (ou ao clicar Ver)
            from PySide6.QtCore import QTimer as QTimer2
            QTimer2.singleShot(2000, lambda ev=evento: self._marcar_evento_lido(ev))
        except Exception:
            # último fallback: QMessageBox
            try:
                QMessageBox.information(self, titulo, msg)
            except Exception:
                pass

    def _marcar_evento_lido(self, evento: dict):
        try:
            path = evento.get("_path")
            if path and os.path.isfile(path):
                from core import eventos as ev
                ev.marcar_lida(path)
        except Exception:
            pass

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
            ("usuarios",              UsuariosPage),
            ("configuracoes",         SettingsPage),
        ]
        for key, PageClass in pages:
            page = PageClass()
            self.pages[key] = page
            self.stacked.addWidget(page)
            if key == "configuracoes":
                page.settings_saved.connect(self._reload_all_pages)

        content_layout.addWidget(self.stacked)
        root_layout.addWidget(content)

    def _reload_all_pages(self):
        for page in self.pages.values():
            # Tenta chamar os métodos de recarregamento conhecidos
            metodos_recarregar = [
                "_carregar_dados",
                "_carregar_itens_estoque",
                "_carregar_lembretes",
                "_carregar_alocacoes"
            ]
            for metodo in metodos_recarregar:
                if hasattr(page, metodo):
                    try:
                        getattr(page, metodo)()
                    except Exception:
                        pass
                    break

    def _switch_tab(self, key):
        # Bloqueia acesso a "usuarios" se não for admin
        if key == "usuarios" and not session_core.is_admin():
            QMessageBox.warning(self, "Permissão", "Apenas administradores podem acessar Usuários.")
            return
        for btn in self.buttons:
            btn.setChecked(False)
        self.tabs[key].setChecked(True)
        self.stacked.setCurrentWidget(self.pages[key])
        # Se entrou em usuários, garante refresh
        if key == "usuarios" and "usuarios" in self.pages and hasattr(self.pages["usuarios"], "_carregar"):
            try:
                self.pages["usuarios"]._carregar()
            except Exception:
                pass

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
            # Footer colapsado: esconde textos e botão logout
            if hasattr(self, "lbl_user_name"):
                self.lbl_user_name.setVisible(False)
                self.lbl_user_role.setVisible(False)
                if hasattr(self, "lbl_auto"):
                    self.lbl_auto.setVisible(False)
                self.btn_logout.setVisible(False)
                self.footer_icon.setFixedSize(28, 28)
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
            if hasattr(self, "lbl_user_name"):
                self.lbl_user_name.setVisible(True)
                self.lbl_user_role.setVisible(True)
                # lbl_auto será reavaliado em _atualizar_usuario_footer, mas garante base visível se auto ativo
                if hasattr(self, "lbl_auto"):
                    try:
                        auto_user, _ = config.obter_auto_login()
                        is_auto = bool(auto_user and config.is_auto_login_enabled() and auto_user.lower() == session_core.get_username().lower())
                        self.lbl_auto.setVisible(is_auto)
                    except Exception:
                        pass
                self.btn_logout.setVisible(True)
            # re-aplica visibilidade admin
            if hasattr(self, "_atualizar_usuario_footer"):
                # evita intercalação durante animação, mas re-aplica
                is_admin = session_core.is_admin()
                if "usuarios" in getattr(self, "tabs", {}):
                    self.tabs["usuarios"].setVisible(is_admin)
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
