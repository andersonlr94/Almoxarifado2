import qtawesome as qta
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QCheckBox, QMessageBox, QWidget
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont

import config
from core import auth as auth_core
from core import session as session_core


class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Almoxarifado - Login")
        self.setModal(True)
        self.setFixedSize(420, 560)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self._tentativas = 0
        self._setup_ui()
        # Garante admin padrão existe
        try:
            auth_core.ensure_default_admin()
        except Exception:
            pass
        self._atualizar_info_storage()
        self._verificar_primeiro_acesso()

    def _setup_ui(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #f8fafc;
            }
            QLabel#appTitle {
                color: #1e1b4b;
                font-size: 26px;
                font-weight: 800;
            }
            QLabel#appSubtitle {
                color: #64748b;
                font-size: 13px;
            }
            QLabel#fieldLabel {
                color: #334155;
                font-size: 12px;
                font-weight: 600;
            }
            QLineEdit {
                background-color: #ffffff;
                color: #1e293b;
                border: 1.5px solid #e2e8f0;
                border-radius: 10px;
                padding: 10px 14px;
                font-size: 14px;
                selection-background-color: #6366f1;
            }
            QLineEdit:focus {
                border: 1.5px solid #6366f1;
            }
            QLineEdit:hover {
                border: 1.5px solid #cbd5e1;
            }
            QCheckBox {
                color: #475569;
                font-size: 12px;
                spacing: 6px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border-radius: 4px;
                border: 1.5px solid #cbd5e1;
                background: #ffffff;
            }
            QCheckBox::indicator:checked {
                background: #6366f1;
                border-color: #6366f1;
                image: url(none);
            }
            QPushButton#btnPrimary {
                background-color: #6366f1;
                color: #ffffff;
                border: none;
                border-radius: 10px;
                padding: 11px 18px;
                font-size: 14px;
                font-weight: 700;
            }
            QPushButton#btnPrimary:hover {
                background-color: #4f46e5;
            }
            QPushButton#btnPrimary:pressed {
                background-color: #4338ca;
            }
            QPushButton#btnPrimary:disabled {
                background-color: #cbd5e1;
                color: #94a3b8;
            }
            QPushButton#btnGhost {
                background-color: transparent;
                color: #6366f1;
                border: none;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton#btnGhost:hover {
                color: #4f46e5;
                background-color: #eef2ff;
                border-radius: 6px;
            }
            QLabel#errorLabel {
                color: #ef4444;
                font-size: 12px;
                font-weight: 600;
                background-color: #fef2f2;
                border: 1px solid #fecaca;
                border-radius: 8px;
                padding: 8px 10px;
            }
            QLabel#infoLabel {
                color: #64748b;
                font-size: 11px;
                background-color: #f1f5f9;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                padding: 8px 10px;
            }
            QPushButton#iconBtn {
                background: transparent;
                border: none;
                color: #94a3b8;
                font-size: 14px;
            }
            QPushButton#iconBtn:hover {
                color: #6366f1;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        # Logo / ícone
        header = QVBoxLayout()
        header.setSpacing(6)
        header.setAlignment(Qt.AlignHCenter)

        icon_label = QLabel()
        icon_label.setAlignment(Qt.AlignHCenter)
        try:
            icon = qta.icon("fa6s.warehouse", color="#6366f1")
            icon_label.setPixmap(icon.pixmap(48, 48))
        except Exception:
            icon_label.setText("🏭")
            icon_label.setStyleSheet("font-size: 38px;")

        titulo = QLabel("Almoxarifado")
        titulo.setObjectName("appTitle")
        titulo.setAlignment(Qt.AlignHCenter)

        subtitulo = QLabel("Sistema de Gestão • Faça login para continuar")
        subtitulo.setObjectName("appSubtitle")
        subtitulo.setAlignment(Qt.AlignHCenter)
        subtitulo.setWordWrap(True)

        header.addWidget(icon_label)
        header.addWidget(titulo)
        header.addWidget(subtitulo)
        layout.addLayout(header)

        # Linha separadora
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("QFrame { border: none; background: #e2e8f0; max-height: 1px; }")
        layout.addWidget(sep)

        # Info storage (onde os usuários estão salvos)
        self.lbl_info_storage = QLabel()
        self.lbl_info_storage.setObjectName("infoLabel")
        self.lbl_info_storage.setWordWrap(True)
        self.lbl_info_storage.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.lbl_info_storage)

        # Campo usuário
        lbl_user = QLabel("Usuário")
        lbl_user.setObjectName("fieldLabel")
        layout.addWidget(lbl_user)

        user_row = QHBoxLayout()
        user_row.setSpacing(0)
        self.campo_usuario = QLineEdit()
        self.campo_usuario.setPlaceholderText("Digite seu usuário")
        self.campo_usuario.setFixedHeight(42)
        self.campo_usuario.returnPressed.connect(self._tentar_login)
        user_row.addWidget(self.campo_usuario, 1)
        layout.addLayout(user_row)

        # Campo senha
        lbl_pass = QLabel("Senha")
        lbl_pass.setObjectName("fieldLabel")
        layout.addWidget(lbl_pass)

        pass_container = QWidget()
        pass_layout = QHBoxLayout(pass_container)
        pass_layout.setContentsMargins(0, 0, 0, 0)
        pass_layout.setSpacing(0)

        self.campo_senha = QLineEdit()
        self.campo_senha.setPlaceholderText("Digite sua senha")
        self.campo_senha.setEchoMode(QLineEdit.Password)
        self.campo_senha.setFixedHeight(42)
        self.campo_senha.returnPressed.connect(self._tentar_login)

        self.btn_mostrar = QPushButton()
        self.btn_mostrar.setObjectName("iconBtn")
        self.btn_mostrar.setFixedSize(36, 36)
        self.btn_mostrar.setCursor(Qt.PointingHandCursor)
        try:
            self.btn_mostrar.setIcon(qta.icon("fa6s.eye-slash", color="#94a3b8"))
        except Exception:
            self.btn_mostrar.setText("👁")
        self.btn_mostrar.setCheckable(True)
        self.btn_mostrar.toggled.connect(self._toggle_senha)

        pass_layout.addWidget(self.campo_senha, 1)
        # sobreposição: colocar botão dentro do line edit visualmente -> usar layout separado com margens negativas
        # para simplificar, colocamos ao lado
        pass_layout.addWidget(self.btn_mostrar)
        layout.addWidget(pass_container)

        # Lembrar usuário + Entrar diretamente
        self.chk_lembrar = QCheckBox("Lembrar meu usuário")
        self.chk_auto = QCheckBox("Entrar diretamente (pula login nas próximas vezes)")
        self.chk_auto.setToolTip("Se marcado, nas próximas vezes o app já entra automaticamente com este usuário. Use em PCs pessoais.")
        # carregar do config se houver
        try:
            dados = config._carregar()
            ultimo = dados.get("ultimo_usuario", "")
            auto_enabled = bool(dados.get("auto_login") and dados.get("auto_user"))
            auto_user = dados.get("auto_user", "")
            if auto_enabled and auto_user:
                # Auto-login ativo -> pré-preenche com auto_user e já marca ambas caixas
                self.campo_usuario.setText(auto_user)
                self.chk_lembrar.setChecked(True)
                self.chk_auto.setChecked(True)
                self.campo_senha.setFocus()
                # mostra dica de auto no info
                self.campo_senha.setPlaceholderText("Senha já salva para entrada automática (ou digite novamente)")
            elif ultimo:
                self.campo_usuario.setText(ultimo)
                self.chk_lembrar.setChecked(True)
                # se só lembrar, deixa auto desmarcado
                self.chk_auto.setChecked(False)
                self.campo_senha.setFocus()
            else:
                self.campo_usuario.setFocus()
        except Exception:
            pass
        # Auto implica Lembrar: quando marca auto, força lembrar; quando desmarca auto, mantém lembrar como estava
        def _on_auto_toggled(checked: bool):
            if checked:
                self.chk_lembrar.setChecked(True)
            # não desmarca lembrar ao desmarcar auto

        self.chk_auto.toggled.connect(_on_auto_toggled)
        layout.addWidget(self.chk_lembrar)
        layout.addWidget(self.chk_auto)

        # Erro
        self.lbl_erro = QLabel("")
        self.lbl_erro.setObjectName("errorLabel")
        self.lbl_erro.setWordWrap(True)
        self.lbl_erro.setVisible(False)
        layout.addWidget(self.lbl_erro)

        # Botão entrar
        self.btn_entrar = QPushButton("Entrar")
        self.btn_entrar.setObjectName("btnPrimary")
        self.btn_entrar.setFixedHeight(44)
        self.btn_entrar.setCursor(Qt.PointingHandCursor)
        try:
            self.btn_entrar.setIcon(qta.icon("fa6s.right-to-bracket", color="#ffffff"))
        except Exception:
            pass
        self.btn_entrar.clicked.connect(self._tentar_login)
        layout.addWidget(self.btn_entrar)

        # Link criar conta / primeiro acesso
        self.btn_criar = QPushButton("Primeiro acesso? Criar conta de administrador")
        self.btn_criar.setObjectName("btnGhost")
        self.btn_criar.setCursor(Qt.PointingHandCursor)
        self.btn_criar.clicked.connect(self._abrir_criar_admin)
        layout.addWidget(self.btn_criar)

        layout.addStretch()

        # Rodapé
        rodape = QLabel("Dica padrão: usuário <b>admin</b> / senha <b>admin</b> no primeiro uso. Troque após entrar.")
        rodape.setStyleSheet("color: #94a3b8; font-size: 10px;")
        rodape.setAlignment(Qt.AlignCenter)
        rodape.setWordWrap(True)
        layout.addWidget(rodape)

        # Atalho Enter
        self.campo_usuario.textChanged.connect(self._limpar_erro)
        self.campo_senha.textChanged.connect(self._limpar_erro)

    def _atualizar_info_storage(self):
        try:
            comp = auth_core.obter_caminho_usuarios_compartilhado()
            if comp:
                # mostra relativo à base
                import os
                base = config.obter_caminho_jsons()
                rel = os.path.relpath(comp, base) if base and comp.startswith(base) else comp
                self.lbl_info_storage.setText(f"Usuários compartilhados em: <b>{rel}</b>  •  Sincronizado entre PCs")
                self.lbl_info_storage.setStyleSheet("QLabel#infoLabel { color: #065f46; background-color: #ecfdf5; border: 1px solid #a7f3d0; font-size: 11px; border-radius: 8px; padding: 8px 10px; }")
            else:
                local = auth_core.obter_caminho_usuarios_local()
                self.lbl_info_storage.setText(f"Modo local: usuários salvos apenas neste PC<br><span style='color:#64748b; font-size:10px;'>{local}</span><br>Configure a pasta em <b>Configurações</b> para compartilhar entre PCs.")
        except Exception:
            pass

    def _verificar_primeiro_acesso(self):
        # Se não há usuários, já deixa botão criar em evidência
        try:
            if auth_core.count_users() == 0:
                self.lbl_erro.setText("Nenhum usuário encontrado. Clique em 'Criar conta de administrador' ou use admin/admin.")
                self.lbl_erro.setVisible(True)
                self.btn_criar.setStyleSheet("background-color: #eef2ff; color: #4f46e5; border: 1.5px solid #c7d2fe; border-radius: 8px; padding: 8px; font-weight: 700;")
        except Exception:
            pass

    def _toggle_senha(self, checked: bool):
        self.campo_senha.setEchoMode(QLineEdit.Normal if checked else QLineEdit.Password)
        try:
            self.btn_mostrar.setIcon(qta.icon("fa6s.eye" if checked else "fa6s.eye-slash", color="#6366f1" if checked else "#94a3b8"))
        except Exception:
            pass

    def _limpar_erro(self):
        self.lbl_erro.setVisible(False)

    def _mostrar_erro(self, texto: str):
        self.lbl_erro.setText(texto)
        self.lbl_erro.setVisible(True)

    def _tentar_login(self):
        usuario = self.campo_usuario.text().strip()
        senha = self.campo_senha.text()

        if not usuario or not senha:
            self._mostrar_erro("Preencha usuário e senha.")
            return

        self.btn_entrar.setEnabled(False)
        self.btn_entrar.setText("Verificando...")

        # Garante que admin padrão existe antes de autenticar (caso tenha sido deletado arquivo)
        try:
            auth_core.ensure_default_admin()
        except Exception:
            pass

        user = auth_core.authenticate(usuario, senha)

        self.btn_entrar.setEnabled(True)
        self.btn_entrar.setText("Entrar")

        if user:
            # Salva preferência de lembrar / entrar diretamente
            try:
                if self.chk_auto.isChecked():
                    # Entrar diretamente implica lembrar; salva hash atual como token
                    try:
                        auth_core.enable_auto_login(user["username"])
                    except Exception as e:
                        # fallback: apenas salva último usuário se falhar
                        dados = config._carregar()
                        dados["ultimo_usuario"] = user["username"]
                        config._salvar(dados)
                else:
                    # Se auto estava ativo, desativa quando usuário desmarcou
                    if config.is_auto_login_enabled():
                        try:
                            # Só limpa se o auto_user for o mesmo que acabou de logar,
                            # ou se o usuário explicitamente desmarcou auto (caso de troca de usuário)
                            auto_user, _ = config.obter_auto_login()
                            if auto_user and auto_user.lower() == user["username"].lower():
                                auth_core.disable_auto_login()
                            else:
                                # troca de usuário sem auto -> limpa auto antigo para não ficar preso
                                auth_core.disable_auto_login()
                        except Exception:
                            pass
                    # Lida com "Lembrar meu usuário" separadamente
                    dados = config._carregar()
                    if self.chk_lembrar.isChecked():
                        dados["ultimo_usuario"] = user["username"]
                    else:
                        dados.pop("ultimo_usuario", None)
                    config._salvar(dados)
            except Exception:
                pass

            session_core.set_current_user(user)
            self.accept()
        else:
            self._tentativas += 1
            # Verifica se é usuário inexistente ou senha errada / inativo
            found = auth_core.find_user(usuario)
            if not found:
                self._mostrar_erro(f"Usuário '{usuario}' não encontrado.")
            elif not found.get("active", True):
                self._mostrar_erro("Usuário desativado. Contate o administrador.")
            else:
                self._mostrar_erro("Senha incorreta. Tente novamente.")
                self.campo_senha.selectAll()
                self.campo_senha.setFocus()
            if self._tentativas >= 5:
                QMessageBox.warning(self, "Muitas tentativas", "Muitas tentativas falhas. Verifique suas credenciais ou contate o administrador.")

    def _abrir_criar_admin(self):
        # Se já existem usuários, só admin pode criar; senão permite criar primeiro admin
        count = auth_core.count_users()
        if count > 0:
            # exige autenticação de admin atual? Para simplificar, abre diálogo de criação com verificação
            # Vamos apenas abrir um diálogo simples que pede usuário/senha novo e verifica se já existe admin logado
            # Se não há sessão, pede para logar como admin
            if not session_core.is_authenticated() or not session_core.is_admin():
                # tenta pedir credenciais de admin
                from PySide6.QtWidgets import QInputDialog
                # Diálogo minimalista para criar usuário - na prática, direciona para gestão após login
                QMessageBox.information(self, "Acesso restrito", "Faça login como administrador para criar novos usuários.\n\nApós logar, vá em Usuários no menu lateral.")
                return

        dlg = CriarAdminDialog(self)
        if dlg.exec() == QDialog.Accepted:
            self._atualizar_info_storage()
            QMessageBox.information(self, "Sucesso", f"Usuário '{dlg.criado_username}' criado com sucesso! Faça login agora.")
            self.campo_usuario.setText(dlg.criado_username)
            self.campo_senha.setFocus()
            self._verificar_primeiro_acesso()


class CriarAdminDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Criar conta")
        self.setModal(True)
        self.setFixedSize(380, 360)
        self.criado_username = ""
        self._setup_ui()

    def _setup_ui(self):
        self.setStyleSheet("""
            QDialog { background-color: #ffffff; }
            QLabel#label { color: #334155; font-size: 12px; font-weight: 600; }
            QLineEdit { background: #ffffff; color: #1e293b; border: 1.5px solid #e2e8f0; border-radius: 8px; padding: 8px 10px; font-size: 13px; }
            QLineEdit:focus { border: 1.5px solid #6366f1; }
            QPushButton#btnPrimary { background-color: #6366f1; color: #ffffff; border: none; border-radius: 8px; padding: 9px 16px; font-weight: 700; }
            QPushButton#btnPrimary:hover { background-color: #4f46e5; }
            QPushButton#btnSecondary { background-color: #f1f5f9; color: #475569; border: 1px solid #e2e8f0; border-radius: 8px; padding: 9px 16px; font-weight: 600; }
            QPushButton#btnSecondary:hover { background-color: #e2e8f0; }
            QLabel#error { color: #ef4444; font-size: 11px; background: #fef2f2; border: 1px solid #fecaca; border-radius: 6px; padding: 6px 8px; }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(10)

        titulo = QLabel("Criar usuário administrador")
        titulo.setStyleSheet("color: #1e1b4b; font-size: 15px; font-weight: 800;")
        layout.addWidget(titulo)

        info = QLabel("Este será o primeiro acesso. Crie seu usuário e senha. Você poderá criar outros depois em <b>Usuários</b>.")
        info.setWordWrap(True)
        info.setStyleSheet("color: #64748b; font-size: 11px;")
        layout.addWidget(info)

        layout.addWidget(QLabel("Usuário", objectName="label"))
        self.campo_user = QLineEdit()
        self.campo_user.setPlaceholderText("ex: anderson.ribeiro")
        layout.addWidget(self.campo_user)

        layout.addWidget(QLabel("Nome de exibição", objectName="label"))
        self.campo_nome = QLineEdit()
        self.campo_nome.setPlaceholderText("ex: Anderson Ribeiro")
        layout.addWidget(self.campo_nome)

        layout.addWidget(QLabel("Senha", objectName="label"))
        self.campo_senha = QLineEdit()
        self.campo_senha.setPlaceholderText("mín. 4 caracteres")
        self.campo_senha.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.campo_senha)

        layout.addWidget(QLabel("Confirmar senha", objectName="label"))
        self.campo_conf = QLineEdit()
        self.campo_conf.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.campo_conf)

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
        btn_ok = QPushButton("Criar")
        btn_ok.setObjectName("btnPrimary")
        btn_ok.clicked.connect(self._criar)
        botoes.addWidget(btn_cancel)
        botoes.addWidget(btn_ok)
        layout.addLayout(botoes)

        self.campo_user.setFocus()

    def _criar(self):
        user = self.campo_user.text().strip()
        nome = self.campo_nome.text().strip()
        senha = self.campo_senha.text()
        conf = self.campo_conf.text()

        if not user or not senha:
            self.lbl_erro.setText("Preencha usuário e senha.")
            self.lbl_erro.setVisible(True)
            return
        if senha != conf:
            self.lbl_erro.setText("Senhas não conferem.")
            self.lbl_erro.setVisible(True)
            return
        if len(senha) < 4:
            self.lbl_erro.setText("Senha deve ter ao menos 4 caracteres.")
            self.lbl_erro.setVisible(True)
            return

        # Se já há usuários, verifica se o solicitante é admin (sessão)
        count = auth_core.count_users()
        created_by = session_core.get_username() if session_core.is_authenticated() else "primeiro_acesso"
        # Primeiro usuário sempre admin
        role = "admin" if count == 0 else "admin"  # por simplicidade, este diálogo sempre cria admin; gestão normal cria user/admin

        try:
            auth_core.create_user(user, senha, display_name=nome, role=role, created_by=created_by)
            self.criado_username = user
            self.accept()
        except ValueError as e:
            self.lbl_erro.setText(str(e))
            self.lbl_erro.setVisible(True)
        except Exception as e:
            self.lbl_erro.setText(f"Erro ao criar usuário: {e}")
            self.lbl_erro.setVisible(True)
