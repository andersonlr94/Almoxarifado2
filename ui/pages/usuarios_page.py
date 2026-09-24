import qtawesome as qta
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QMessageBox, QDialog, QComboBox, QCheckBox,
    QFrame
)
from PySide6.QtCore import Qt, QSize

from core import auth as auth_core
from core import session as session_core


class CriarEditarUsuarioDialog(QDialog):
    def __init__(self, parent=None, edit_user: dict | None = None):
        super().__init__(parent)
        self.edit_user = edit_user
        self.setWindowTitle("Editar usuário" if edit_user else "Novo usuário")
        self.setModal(True)
        self.setFixedSize(420, 400)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self._setup_ui()

    def _setup_ui(self):
        self.setStyleSheet("""
            QDialog { background-color: #ffffff; }
            QLabel#label { color: #334155; font-size: 12px; font-weight: 600; }
            QLineEdit, QComboBox { background: #ffffff; color: #1e293b; border: 1.5px solid #e2e8f0; border-radius: 8px; padding: 8px 10px; font-size: 13px; }
            QLineEdit:focus, QComboBox:focus { border: 1.5px solid #6366f1; }
            QLineEdit:disabled, QComboBox:disabled { background: #f1f5f9; color: #94a3b8; }
            QCheckBox { color: #475569; font-size: 12px; }
            QCheckBox:disabled { color: #94a3b8; }
            QPushButton#btnPrimary { background-color: #6366f1; color: #ffffff; border: none; border-radius: 8px; padding: 9px 16px; font-weight: 700; }
            QPushButton#btnPrimary:hover { background-color: #4f46e5; }
            QPushButton#btnSecondary { background-color: #f1f5f9; color: #475569; border: 1px solid #e2e8f0; border-radius: 8px; padding: 9px 16px; font-weight: 600; }
            QPushButton#btnSecondary:hover { background-color: #e2e8f0; }
            QLabel#error { color: #ef4444; font-size: 11px; background: #fef2f2; border: 1px solid #fecaca; border-radius: 6px; padding: 6px 8px; }
            QLabel#hint { color: #64748b; font-size: 10px; }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(8)

        is_edit = self.edit_user is not None

        titulo = QLabel("Editar usuário" if is_edit else "Novo usuário")
        titulo.setStyleSheet("color: #1e1b4b; font-size: 15px; font-weight: 800;")
        layout.addWidget(titulo)

        layout.addWidget(QLabel("Usuário (sem espaços)", objectName="label"))
        self.campo_user = QLineEdit()
        self.campo_user.setPlaceholderText("ex: joao.silva")
        if is_edit:
            self.campo_user.setText(self.edit_user.get("username", ""))
            self.campo_user.setReadOnly(True)
            self.campo_user.setStyleSheet("background: #f1f5f9; color: #64748b;")
        layout.addWidget(self.campo_user)

        layout.addWidget(QLabel("Nome de exibição", objectName="label"))
        self.campo_nome = QLineEdit()
        self.campo_nome.setPlaceholderText("ex: João Silva")
        if is_edit:
            self.campo_nome.setText(self.edit_user.get("display_name", ""))
        layout.addWidget(self.campo_nome)

        layout.addWidget(QLabel("Perfil", objectName="label"))
        self.combo_role = QComboBox()
        self.combo_role.addItems(["user", "admin"])
        self.combo_role.setToolTip("admin pode gerenciar usuários")
        if is_edit:
            self.combo_role.setCurrentText(self.edit_user.get("role", "user"))
        layout.addWidget(self.combo_role)

        self.chk_active = QCheckBox("Usuário ativo")
        self.chk_active.setChecked(True if not is_edit else bool(self.edit_user.get("active", True)))
        layout.addWidget(self.chk_active)

        # Restrição para não-admin editando a si mesmo: não pode alterar perfil/ativo
        try:
            is_self = is_edit and self.edit_user.get("username", "").lower() == session_core.get_username().lower()
            if not session_core.is_admin():
                # non-admin: desabilita campos privilegiados
                self.combo_role.setEnabled(False)
                self.combo_role.setToolTip("Apenas administradores podem alterar perfil")
                self.chk_active.setEnabled(False)
                self.chk_active.setToolTip("Apenas administradores podem ativar/desativar")
                if is_self:
                    # self-edit ainda permite nome/senha
                    pass
        except Exception:
            pass

        layout.addWidget(QLabel("Senha", objectName="label"))
        self.campo_senha = QLineEdit()
        self.campo_senha.setPlaceholderText("mín. 4 caracteres" + (" (deixe em branco para manter)" if is_edit else ""))
        self.campo_senha.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.campo_senha)

        layout.addWidget(QLabel("Confirmar senha", objectName="label"))
        self.campo_conf = QLineEdit()
        self.campo_conf.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.campo_conf)

        hint = QLabel("Dica: use senhas simples para ambiente interno, mas evite '1234' para admin.")
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.lbl_erro = QLabel("")
        self.lbl_erro.setObjectName("error")
        self.lbl_erro.setWordWrap(True)
        self.lbl_erro.setVisible(False)
        layout.addWidget(self.lbl_erro)

        botoes = QHBoxLayout()
        botoes.addStretch()
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setObjectName("btnSecondary")
        btn_cancel.clicked.connect(self.reject)
        btn_ok = QPushButton("Salvar" if is_edit else "Criar")
        btn_ok.setObjectName("btnPrimary")
        btn_ok.clicked.connect(self._salvar)
        botoes.addWidget(btn_cancel)
        botoes.addWidget(btn_ok)
        layout.addLayout(botoes)

    def _salvar(self):
        username = self.campo_user.text().strip()
        display = self.campo_nome.text().strip()
        role = self.combo_role.currentText()
        active = self.chk_active.isChecked()
        senha = self.campo_senha.text()
        conf = self.campo_conf.text()

        is_edit = self.edit_user is not None

        if not username:
            self.lbl_erro.setText("Usuário não pode ser vazio.")
            self.lbl_erro.setVisible(True)
            return

        if not is_edit:
            if not senha:
                self.lbl_erro.setText("Informe uma senha.")
                self.lbl_erro.setVisible(True)
                return
            if senha != conf:
                self.lbl_erro.setText("Senhas não conferem.")
                self.lbl_erro.setVisible(True)
                return
            try:
                auth_core.create_user(username, senha, display_name=display, role=role, created_by=session_core.get_username() or "system")
                # aplica active se desmarcado na criação
                if not active:
                    auth_core.update_user(username, active=False)
                self.accept()
            except ValueError as e:
                self.lbl_erro.setText(str(e))
                self.lbl_erro.setVisible(True)
            except Exception as e:
                self.lbl_erro.setText(f"Erro: {e}")
                self.lbl_erro.setVisible(True)
        else:
            # edição
            try:
                # se senha preenchida, valida
                new_pass = None
                if senha or conf:
                    if senha != conf:
                        self.lbl_erro.setText("Senhas não conferem.")
                        self.lbl_erro.setVisible(True)
                        return
                    if len(senha) < 4:
                        self.lbl_erro.setText("Senha deve ter ao menos 4 caracteres.")
                        self.lbl_erro.setVisible(True)
                        return
                    new_pass = senha
                auth_core.update_user(username, display_name=display or None, role=role, active=active, new_password=new_pass)
                self.accept()
            except ValueError as e:
                self.lbl_erro.setText(str(e))
                self.lbl_erro.setVisible(True)
            except Exception as e:
                self.lbl_erro.setText(f"Erro: {e}")
                self.lbl_erro.setVisible(True)


class UsuariosPage(QWidget):
    def __init__(self):
        super().__init__()
        self._setup_ui()
        self._carregar()

    def showEvent(self, event):
        super().showEvent(event)
        self._carregar()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(16)

        card = QWidget()
        card.setObjectName("pageCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(28, 28, 28, 28)
        card_layout.setSpacing(14)

        header = QHBoxLayout()
        titulo_box = QVBoxLayout()
        titulo = QLabel("Usuários")
        titulo.setObjectName("pageTitle")
        subtitulo = QLabel("Gerencie logins do sistema. Apenas administradores acessam esta página.")
        subtitulo.setObjectName("pageSubtitle")
        subtitulo.setWordWrap(True)
        titulo_box.addWidget(titulo)
        titulo_box.addWidget(subtitulo)
        header.addLayout(titulo_box, 1)
        header.addStretch()

        card_layout.addLayout(header)

        # Barra de ações
        acoes = QHBoxLayout()
        acoes.setSpacing(8)

        self.btn_novo = QPushButton()
        try:
            self.btn_novo.setIcon(qta.icon("fa6s.user-plus", color="#ffffff"))
        except Exception:
            pass
        self.btn_novo.setText("  Novo usuário")
        self.btn_novo.setObjectName("btnPrimary")
        self.btn_novo.setFixedHeight(34)
        self.btn_novo.setCursor(Qt.PointingHandCursor)
        self.btn_novo.clicked.connect(self._novo)
        acoes.addWidget(self.btn_novo)

        self.btn_editar = QPushButton()
        try:
            self.btn_editar.setIcon(qta.icon("fa6s.pen", color="#475569"))
        except Exception:
            pass
        self.btn_editar.setText("  Editar")
        self.btn_editar.setObjectName("btnSecondary")
        self.btn_editar.setFixedHeight(34)
        self.btn_editar.clicked.connect(self._editar)
        acoes.addWidget(self.btn_editar)

        self.btn_remover = QPushButton()
        try:
            self.btn_remover.setIcon(qta.icon("fa6s.trash", color="#ffffff"))
        except Exception:
            pass
        self.btn_remover.setText("  Remover")
        self.btn_remover.setObjectName("btnDanger")
        self.btn_remover.setFixedHeight(34)
        self.btn_remover.clicked.connect(self._remover)
        acoes.addWidget(self.btn_remover)

        self.btn_recarregar = QPushButton()
        try:
            self.btn_recarregar.setIcon(qta.icon("fa6s.rotate-right", color="#6366f1"))
        except Exception:
            pass
        self.btn_recarregar.setToolTip("Recarregar")
        self.btn_recarregar.setObjectName("btnSecondary")
        self.btn_recarregar.setFixedSize(34, 34)
        self.btn_recarregar.clicked.connect(self._carregar)
        acoes.addWidget(self.btn_recarregar)

        acoes.addStretch()

        self.lbl_contador = QLabel("0 usuários")
        self.lbl_contador.setObjectName("statusLabel")
        acoes.addWidget(self.lbl_contador)

        # Info storage + Auto-login status
        self.lbl_storage = QLabel()
        self.lbl_storage.setStyleSheet("color: #64748b; font-size: 11px;")
        self.lbl_storage.setWordWrap(True)
        acoes2 = QHBoxLayout()
        acoes2.setSpacing(12)
        acoes2.addWidget(self.lbl_storage, 1)

        self.lbl_auto_status = QLabel()
        self.lbl_auto_status.setStyleSheet("color: #059669; font-size: 11px; font-weight: 600; background: #ecfdf5; border: 1px solid #a7f3d0; border-radius: 6px; padding: 4px 8px;")
        self.lbl_auto_status.setVisible(False)
        acoes2.addWidget(self.lbl_auto_status)

        self.btn_desativar_auto = QPushButton("Desativar entrada automática")
        self.btn_desativar_auto.setObjectName("btnSecondary")
        self.btn_desativar_auto.setFixedHeight(28)
        self.btn_desativar_auto.setCursor(Qt.PointingHandCursor)
        self.btn_desativar_auto.setToolTip("Remove o login automático neste PC")
        self.btn_desativar_auto.clicked.connect(self._desativar_auto)
        self.btn_desativar_auto.setVisible(False)
        acoes2.addWidget(self.btn_desativar_auto)

        card_layout.addLayout(acoes)
        card_layout.addLayout(acoes2)

        # Tabela
        self.tabela = QTableWidget(0, 5)
        self.tabela.setHorizontalHeaderLabels(["Usuário", "Nome", "Perfil", "Ativo", "Criado em"])
        self.tabela.setStyleSheet("""
            QTableWidget {
                background: #ffffff;
                border: 1px solid #eef1f6;
                border-radius: 12px;
                gridline-color: #f3f4f6;
                selection-background-color: #eef2ff;
                selection-color: #1e1b4b;
                font-size: 13px;
            }
            QHeaderView::section {
                background: #f9fafb;
                color: #64748b;
                font-size: 11px;
                font-weight: 700;
                padding: 10px 12px;
                border: none;
                border-bottom: 1.5px solid #e5e7eb;
            }
        """)
        header_tbl = self.tabela.horizontalHeader()
        header_tbl.setSectionResizeMode(0, QHeaderView.Fixed)
        header_tbl.resizeSection(0, 140)
        header_tbl.setSectionResizeMode(1, QHeaderView.Stretch)
        header_tbl.setSectionResizeMode(2, QHeaderView.Fixed)
        header_tbl.resizeSection(2, 90)
        header_tbl.setSectionResizeMode(3, QHeaderView.Fixed)
        header_tbl.resizeSection(3, 80)
        header_tbl.setSectionResizeMode(4, QHeaderView.Fixed)
        header_tbl.resizeSection(4, 160)
        self.tabela.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabela.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tabela.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabela.verticalHeader().setVisible(False)
        self.tabela.setAlternatingRowColors(True)
        self.tabela.verticalHeader().setDefaultSectionSize(30)
        self.tabela.doubleClicked.connect(self._editar)

        card_layout.addWidget(self.tabela, 1)

        # Rodapé aviso
        aviso = QLabel("• Usuários são compartilhados entre PCs quando a pasta em Configurações aponta para a rede (S:). Senhas são armazenadas com hash PBKDF2.")
        aviso.setWordWrap(True)
        aviso.setStyleSheet("color: #94a3b8; font-size: 11px;")
        card_layout.addWidget(aviso)

        layout.addWidget(card, 1)

        self._aplicar_permissao()

    def _aplicar_permissao(self):
        is_admin = session_core.is_admin()
        if is_admin:
            self.btn_novo.setEnabled(True)
            self.btn_novo.setToolTip("")
            self.btn_remover.setEnabled(True)
            self.btn_editar.setEnabled(True)
            self.btn_editar.setToolTip("")
        else:
            # Não-admin: pode editar próprio usuário/senha, mas não criar/remover
            self.btn_novo.setEnabled(False)
            self.btn_novo.setToolTip("Apenas administradores podem criar usuários")
            self.btn_remover.setEnabled(False)
            self.btn_remover.setToolTip("Apenas administradores podem remover")
            self.btn_editar.setEnabled(True)
            self.btn_editar.setToolTip("Você pode editar apenas seu próprio usuário")
            # atualiza subtítulo para não-admin
            try:
                # encontra subtitulo no header se existir
                pass
            except Exception:
                pass

    def _carregar(self):
        try:
            # Garante admin
            auth_core.ensure_default_admin()
        except Exception:
            pass
        # Atualiza status auto-login
        try:
            import config
            auto_user, auto_token = config.obter_auto_login()
            if auto_user and config.is_auto_login_enabled():
                full = auth_core.find_user(auto_user)
                if full and full.get("password_hash") == auto_token and full.get("active", True):
                    self.lbl_auto_status.setText(f"Entrada automática ativa para: {auto_user}")
                    self.lbl_auto_status.setVisible(True)
                    self.btn_desativar_auto.setVisible(True)
                else:
                    # token desatualizado (senha mudou) -> limpa
                    if full and full.get("password_hash") != auto_token:
                        config.limpar_auto_login()
                    self.lbl_auto_status.setVisible(False)
                    self.btn_desativar_auto.setVisible(False)
            else:
                self.lbl_auto_status.setVisible(False)
                self.btn_desativar_auto.setVisible(False)
        except Exception:
            pass
        users = auth_core.list_users(sanitize=True)
        # ordena por username
        users.sort(key=lambda x: x.get("username", "").lower())
        self.tabela.setRowCount(0)
        for u in users:
            row = self.tabela.rowCount()
            self.tabela.insertRow(row)
            self.tabela.setItem(row, 0, QTableWidgetItem(u.get("username", "")))
            self.tabela.setItem(row, 1, QTableWidgetItem(u.get("display_name", "")))
            role = u.get("role", "user")
            item_role = QTableWidgetItem(role)
            if role == "admin":
                item_role.setForeground(Qt.darkMagenta)
            self.tabela.setItem(row, 2, item_role)
            ativo = "Sim" if u.get("active", True) else "Não"
            item_ativo = QTableWidgetItem(ativo)
            if ativo == "Não":
                item_ativo.setForeground(Qt.red)
            self.tabela.setItem(row, 3, item_ativo)
            self.tabela.setItem(row, 4, QTableWidgetItem(u.get("created_at", "")[:19] if u.get("created_at") else ""))
            # guarda username no UserRole da coluna 0
            self.tabela.item(row, 0).setData(Qt.UserRole, u.get("username", ""))
        self.lbl_contador.setText(f"{len(users)} usuários")
        # storage info
        try:
            comp = auth_core.obter_caminho_usuarios_compartilhado()
            if comp:
                self.lbl_storage.setText(f"Compartilhado: {comp}")
            else:
                self.lbl_storage.setText(f"Local (este PC): {auth_core.obter_caminho_usuarios_local()}  • Configure a pasta em Configurações para compartilhar")
        except Exception:
            pass
        # destaca usuário logado
        cur = session_core.get_username()
        for r in range(self.tabela.rowCount()):
            if self.tabela.item(r, 0).data(Qt.UserRole) == cur:
                for c in range(self.tabela.columnCount()):
                    it = self.tabela.item(r, c)
                    if it:
                        f = it.font()
                        f.setBold(True)
                        it.setFont(f)

    def _get_selected_username(self) -> str | None:
        row = self.tabela.currentRow()
        if row < 0:
            return None
        item = self.tabela.item(row, 0)
        if not item:
            return None
        return item.data(Qt.UserRole) or item.text().strip()

    def _novo(self):
        if not session_core.is_admin():
            QMessageBox.warning(self, "Permissão", "Apenas administradores podem criar usuários.")
            return
        dlg = CriarEditarUsuarioDialog(self, edit_user=None)
        if dlg.exec() == QDialog.Accepted:
            self._carregar()

    def _editar(self):
        username = self._get_selected_username()
        if not username:
            QMessageBox.information(self, "Usuários", "Selecione um usuário para editar.")
            return
        # Não-admin só pode editar a si mesmo? Por enquanto só admin edita qualquer
        if not session_core.is_admin() and username != session_core.get_username():
            QMessageBox.warning(self, "Permissão", "Você só pode editar seu próprio usuário.")
            return
        user = auth_core.find_user(username)
        if not user:
            QMessageBox.warning(self, "Usuários", "Usuário não encontrado.")
            return
        # remove hash para diálogo
        user.pop("password_hash", None)
        dlg = CriarEditarUsuarioDialog(self, edit_user=user)
        if dlg.exec() == QDialog.Accepted:
            self._carregar()

    def _remover(self):
        if not session_core.is_admin():
            QMessageBox.warning(self, "Permissão", "Apenas administradores podem remover usuários.")
            return
        username = self._get_selected_username()
        if not username:
            QMessageBox.information(self, "Usuários", "Selecione um usuário para remover.")
            return
        if username == session_core.get_username():
            QMessageBox.warning(self, "Usuários", "Você não pode remover seu próprio usuário logado.")
            return
        resp = QMessageBox.question(self, "Confirmar", f"Remover usuário '{username}'?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if resp != QMessageBox.Yes:
            return
        try:
            auth_core.delete_user(username)
            self._carregar()
        except ValueError as e:
            QMessageBox.warning(self, "Usuários", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Falha ao remover: {e}")

    def _desativar_auto(self):
        try:
            import config
            config.limpar_auto_login()
            QMessageBox.information(self, "Entrada automática", "Entrada automática desativada neste PC.\nNa próxima vez será necessário digitar usuário e senha.")
            self._carregar()
            # também atualiza footer da MainWindow se existir
            try:
                win = self.window()
                if hasattr(win, "_atualizar_usuario_footer"):
                    win._atualizar_usuario_footer()
            except Exception:
                pass
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Falha ao desativar: {e}")

    def refresh_for_user_change(self):
        self._aplicar_permissao()
        self._carregar()
