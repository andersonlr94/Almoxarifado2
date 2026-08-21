import time
import os
import subprocess
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QDialog, QFormLayout, QApplication, QMessageBox
)
from ui.regras_automacao import digitar_texto, enter
from urllib.parse import quote

class CredentialsDialog(QDialog):
    """Diálogo simplificado para inserção de usuário e senha."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Credenciais - DPP Ativos")
        self.setMinimumWidth(340)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        titulo = QLabel("Inserir Credenciais")
        titulo.setStyleSheet("font-size: 16px; font-weight: 700; color: #0f172a;")
        layout.addWidget(titulo)

        subtitulo = QLabel("Entre com usuário e senha para conectar ao servidor SFTP:")
        subtitulo.setWordWrap(True)
        subtitulo.setStyleSheet("font-size: 12px; color: #64748b; margin-bottom: 4px;")
        layout.addWidget(subtitulo)

        form_layout = QFormLayout()
        form_layout.setSpacing(10)

        self.campo_usuario = QLineEdit()
        self.campo_usuario.setPlaceholderText("Usuário")
        self.campo_usuario.setFixedHeight(34)
        
        self.campo_senha = QLineEdit()
        self.campo_senha.setPlaceholderText("Senha")
        self.campo_senha.setEchoMode(QLineEdit.EchoMode.Password)
        self.campo_senha.setFixedHeight(34)

        form_layout.addRow(QLabel("Usuário:"), self.campo_usuario)
        form_layout.addRow(QLabel("Senha:"), self.campo_senha)

        layout.addLayout(form_layout)

        botoes_layout = QHBoxLayout()
        botoes_layout.setSpacing(8)
        botoes_layout.addStretch()

        self.btn_cancelar = QPushButton("Cancelar")
        self.btn_cancelar.setObjectName("btnSecondary")
        self.btn_cancelar.setFixedHeight(34)
        self.btn_cancelar.clicked.connect(self.reject)
        botoes_layout.addWidget(self.btn_cancelar)

        self.btn_confirmar = QPushButton("Confirmar")
        self.btn_confirmar.setObjectName("btnPrimary")
        self.btn_confirmar.setFixedHeight(34)
        self.btn_confirmar.clicked.connect(self.accept)
        botoes_layout.addWidget(self.btn_confirmar)

        layout.addLayout(botoes_layout)

    def obter_dados(self):
        return {
            "usuario": self.campo_usuario.text(),
            "senha": self.campo_senha.text()
        }


class DppAtivosPage(QWidget):
    def __init__(self):
        super().__init__()
        self._credenciais = None
        self._setup_ui()

    from urllib.parse import quote

    def _baixar_com_winscp(self, usuario, senha, destino_local):

        caminhos = [
            r"C:\Program Files (x86)\WinSCp-FTP\WinSCP.com",
            r"C:\Program Files (x86)\WinSCp-FTP\WinSCP\WinSCP.com",
        ]

        winscp = None

        for caminho in caminhos:
            if os.path.exists(caminho):
                winscp = caminho
                break

        if not winscp:
            raise Exception("WinSCP.com não encontrado.")

        usuario_url = quote(usuario, safe="")
        senha_url = quote(senha, safe="")

        comando = [
            winscp,
            #"/ini=nul",
            "/command",
            "option batch abort",
            "option confirm off",
            f"open sftp://{usuario_url}:{senha_url}@10.251.70.27:22/ ",
            f'get DPP.prn "{destino_local}"',
            "exit"
        ]

        try:
            resultado = subprocess.run(
                comando,
                capture_output=True,
                text=True,
                timeout=60,
            )
        except subprocess.TimeoutExpired as erro:
            raise Exception(
                "O WinSCP excedeu o limite de 60 segundos. "
                "Verifique a conexão e o servidor SFTP."
            ) from erro

        print(resultado.stdout)
        print(resultado.stderr)

        if resultado.returncode != 0:
            raise Exception(resultado.stderr or resultado.stdout)

        return resultado.stdout

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(16)

        card = QWidget()
        card.setObjectName("pageCard")

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(32, 32, 32, 32)
        card_layout.setSpacing(20)

        titulo = QLabel("DPP Ativos")
        titulo.setObjectName("pageTitle")
        card_layout.addWidget(titulo)

        subtitulo = QLabel(
            "Esta ferramenta automatiza a geração do DPP e faz o download "
            "do arquivo DPP.prn através do WinSCP."
        )

        subtitulo.setObjectName("pageSubtitle")
        subtitulo.setWordWrap(True)
        card_layout.addWidget(subtitulo)

        acoes_layout = QHBoxLayout()

        self.btn_baixar = QPushButton("Baixar")
        self.btn_baixar.clicked.connect(self._executar_baixar)

        acoes_layout.addWidget(self.btn_baixar)

        self.lbl_status = QLabel("Aguardando início...")
        acoes_layout.addWidget(self.lbl_status)

        acoes_layout.addStretch()

        card_layout.addLayout(acoes_layout)

        layout.addWidget(card)
        layout.addStretch()

    def _atualizar_status(self, texto, cor="#64748b"):
        self.lbl_status.setText(texto)
        self.lbl_status.setStyleSheet(
            f"font-size:13px; font-weight:600; color:{cor};"
        )
        QApplication.processEvents()

    def _obter_pasta_almox(self):
        import config

        base = config.obter_caminho_jsons()

        if not base:
            return ""

        return os.path.normpath(
            os.path.join(base, "Almox")
        )

    def _executar_baixar(self):

        self.btn_baixar.setEnabled(False)

        try:

            for i in range(5, 0, -1):

                self._atualizar_status(
                    f"Foque a janela de destino! Iniciando em {i}s...",
                    "#d97706"
                )

                time.sleep(1)

            self._atualizar_status(
                "Digitando sequência...",
                "#2563eb"
            )

            digitar_texto("5.8")
            enter(8)

            digitar_texto("DPP")
            enter(2)

            if self._credenciais is None:
                dialog = CredentialsDialog(self)

                if dialog.exec() != QDialog.DialogCode.Accepted:
                    self._atualizar_status(
                        "Operação cancelada.",
                        "#dc2626"
                    )
                    return

                dados = dialog.obter_dados()
                self._credenciais = (dados["usuario"], dados["senha"])
            else:
                resposta = QMessageBox(self)
                resposta.setWindowTitle("Relatório")
                resposta.setText("Clicar em OK depois que o relatorio for gerado")
                resposta.setIcon(QMessageBox.Icon.Information)
                resposta.setStandardButtons(QMessageBox.StandardButton.Ok)
                resposta.exec()

            usuario, senha = self._credenciais

            pasta_almox = self._obter_pasta_almox()

            if not pasta_almox:
                import config
                config.avisar_sem_pasta(self)
                return

            os.makedirs(
                pasta_almox,
                exist_ok=True
            )

            caminho_local_prn = os.path.join(
                pasta_almox,
                "DPP.prn"
            )

            self._atualizar_status(
                "Baixando DPP.prn...",
                "#2563eb"
            )

            self._baixar_com_winscp(
                usuario,
                senha,
                caminho_local_prn
            )

            if (
    os.path.exists(caminho_local_prn)
    and os.path.getsize(caminho_local_prn) > 0
):

                self._atualizar_status(
                    f"Sucesso! Arquivo salvo em:\n{caminho_local_prn}",
                    "#16a34a"
                )

            else:

                self._atualizar_status(
                    "Arquivo não foi baixado.",
                    "#dc2626"
                )

        except Exception as e:

            self._atualizar_status(
                f"Erro: {str(e)}",
                "#dc2626"
            )

        finally:

            self.btn_baixar.setEnabled(True)