import json
import os

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QStyledItemDelegate, QMessageBox, QFrame,
    QDialog, QGroupBox, QComboBox, QRadioButton, QButtonGroup,
    QFormLayout, QDialogButtonBox,
)
from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtGui import QGuiApplication, QIntValidator, QPainter, QKeySequence, QShortcut
from PySide6.QtPrintSupport import QPrinter, QPrinterInfo

from PySide6.QtWidgets import QFileDialog
import pandas as pd


class DetalhesEstoqueDialog(QDialog):
    def __init__(self, item, parent=None):
        super().__init__(parent)
        self.item = item
        self.setWindowTitle("Detalhes do item")
        self.setMinimumWidth(600)
        self._montar_ui()

    def _montar_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        cabecalho_layout = QHBoxLayout()
        cabecalho_layout.setSpacing(14)
        grupo_kardex = QWidget()
        grupo_kardex_layout = QVBoxLayout(grupo_kardex)
        grupo_kardex_layout.setContentsMargins(0, 0, 0, 0)
        grupo_kardex_layout.addWidget(QLabel("Kardex"))
        self.campo_kardex = QLineEdit(str(self.item.get("Kardex", "")))
        grupo_kardex_layout.addWidget(self.campo_kardex)
        cabecalho_layout.addWidget(grupo_kardex, 1)
        self.campo_kardex.editingFinished.connect(self._carregar_kardex)
        grupo_codigo = QWidget()
        grupo_codigo_layout = QVBoxLayout(grupo_codigo)
        grupo_codigo_layout.setContentsMargins(0, 0, 0, 0)
        grupo_codigo_layout.addWidget(QLabel("Código"))
        self.campo_codigo = QLineEdit(str(self.item.get("Código", "")))
        self.campo_codigo.setReadOnly(True)
        grupo_codigo_layout.addWidget(self.campo_codigo)
        cabecalho_layout.addWidget(grupo_codigo, 1)
        layout.addLayout(cabecalho_layout)

        self.descricao = QLabel(str(self.item.get("Descrição", "")))
        self.descricao.setWordWrap(True)
        self.descricao.setStyleSheet("color: #52648f; font-size: 13px;")
        layout.addWidget(self.descricao)

        colunas = QHBoxLayout()
        colunas.setSpacing(14)

        locais = QGroupBox("Locações")
        locais.setFixedWidth(350)
        locais_form = QFormLayout(locais)
        self.campo_loc_novo = QLineEdit(str(self.item.get("Loc novo", "")))
        self.campo_loc_retorno = QLineEdit(str(self.item.get("Loc retorno", "")))
        self.campo_loc_aux = QLineEdit(str(self.item.get("Loc aux", "")))
        for campo in (self.campo_loc_novo, self.campo_loc_retorno, self.campo_loc_aux):
            campo.setFixedWidth(170)
        self.campo_qtde_loc_novo = QLineEdit(str(self.item.get("Qtde novo", "")))
        self.campo_qtde_loc_retorno = QLineEdit(str(self.item.get("Qtde retorno", "")))
        self.campo_qtde_loc_aux = QLineEdit(str(self.item.get("Qtde aux", "")))
        self.campo_entrada_loc_novo = QLineEdit(str(self.item.get("Entrada novo", "")))
        self.campo_entrada_loc_retorno = QLineEdit(str(self.item.get("Entrada retorno", "")))
        self.campo_entrada_loc_aux = QLineEdit(str(self.item.get("Entrada aux", "")))
        for campo in (self.campo_qtde_loc_novo, self.campo_qtde_loc_retorno, self.campo_qtde_loc_aux):
            campo.setPlaceholderText("Qtde")
            campo.setValidator(QIntValidator(0, 999999, self))
            campo.setFixedWidth(70)
        for campo in (self.campo_entrada_loc_novo, self.campo_entrada_loc_retorno, self.campo_entrada_loc_aux):
            campo.setFixedWidth(70)
        for campo in (
            self.campo_loc_novo,
            self.campo_loc_retorno,
            self.campo_loc_aux,
            self.campo_qtde_loc_novo,
            self.campo_qtde_loc_retorno,
            self.campo_qtde_loc_aux,
            self.campo_entrada_loc_novo,
            self.campo_entrada_loc_retorno,
            self.campo_entrada_loc_aux,
        ):
            campo.setStyleSheet("padding: 1px 4px;")
            campo.setFixedHeight(campo.sizeHint().height() + 4)
        for campo in (self.campo_qtde_loc_novo, self.campo_qtde_loc_retorno, self.campo_qtde_loc_aux):
            campo.setReadOnly(True)

        def criar_linha_local(titulo, campos):
            linha = QWidget()
            linha_layout = QVBoxLayout(linha)
            linha_layout.setContentsMargins(0, 0, 0, 0)
            linha_layout.setSpacing(4)

            campos_layout = QHBoxLayout()
            campos_layout.setContentsMargins(0, 0, 0, 0)
            campos_layout.setSpacing(0)
            for rotulo, campo in campos:
                grupo = QWidget()
                grupo_layout = QVBoxLayout(grupo)
                grupo_layout.setContentsMargins(0, 0, 0, 0)
                grupo_layout.setSpacing(0)
                if rotulo:
                    grupo_layout.addWidget(QLabel(rotulo))
                grupo_layout.addWidget(campo)
                campos_layout.addWidget(grupo)
            linha_layout.addLayout(campos_layout)
            return linha

        locais_form.addRow(criar_linha_local("Novo", (
            ("Novo", self.campo_loc_novo),
            ("Qtde", self.campo_qtde_loc_novo),
            ("Entrada", self.campo_entrada_loc_novo),
        )))
        locais_form.addRow(criar_linha_local("Retorno", (
            ("Retorno", self.campo_loc_retorno),
            ("Qtde", self.campo_qtde_loc_retorno),
            ("Entrada", self.campo_entrada_loc_retorno),
        )))
        locais_form.addRow(criar_linha_local("Aux", (
            ("Aux", self.campo_loc_aux),
            ("Qtde", self.campo_qtde_loc_aux),
            ("Entrada", self.campo_entrada_loc_aux),
        )))
        colunas.addWidget(locais, 1)

        transferencia = QGroupBox("Transferência")
        transferencia.setFixedWidth(310)
        transferencia_form = QFormLayout(transferencia)
        self.campo_qtde_transferencia = QLineEdit()
        self.campo_qtde_transferencia.setValidator(QIntValidator(1, 999999, self))
        self.campo_qtde_transferencia.setFixedWidth(80)
        tipos = QWidget()
        tipos_layout = QHBoxLayout(tipos)
        tipos_layout.setContentsMargins(0, 0, 0, 0)
        tipos_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.grupo_tipo = QButtonGroup(self)
        for texto in ("Novo", "Retorno", "Aux"):
            radio = QRadioButton(texto)
            self.grupo_tipo.addButton(radio)
            tipos_layout.addWidget(radio)
            if texto == "Novo":
                radio.setChecked(True)
        qtde_tipos = QWidget()
        qtde_tipos_layout = QHBoxLayout(qtde_tipos)
        qtde_tipos_layout.setContentsMargins(0, 0, 0, 0)
        qtde_tipos_layout.setSpacing(8)
        qtde_tipos_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        grupo_qtde_transferencia = QWidget()
        grupo_qtde_transferencia_layout = QVBoxLayout(grupo_qtde_transferencia)
        grupo_qtde_transferencia_layout.setContentsMargins(0, 0, 0, 0)
        grupo_qtde_transferencia_layout.setSpacing(0)
        grupo_qtde_transferencia_layout.addWidget(QLabel("Qtde"))
        grupo_qtde_transferencia_layout.addWidget(self.campo_qtde_transferencia)
        qtde_tipos_layout.addWidget(grupo_qtde_transferencia)
        qtde_tipos_layout.addWidget(tipos)
        transferencia_form.addRow("", qtde_tipos)
        self.combo_destino = QComboBox()
        self.combo_destino.addItem("Manutenção")
        self.btn_imprimir = QPushButton("Imprimir")
        self.btn_imprimir.setFixedWidth(self.btn_imprimir.sizeHint().width() - 10)
        self.btn_imprimir.clicked.connect(self._imprimir)
        self.btn_transferir = QPushButton("Transferir")
        self.btn_transferir.clicked.connect(self._transferir)
        destino_controles = QWidget()
        destino_controles_layout = QHBoxLayout(destino_controles)
        destino_controles_layout.setContentsMargins(0, 0, 0, 0)
        destino_controles_layout.setSpacing(8)
        grupo_destino = QWidget()
        grupo_destino_layout = QVBoxLayout(grupo_destino)
        grupo_destino_layout.setContentsMargins(0, 0, 0, 0)
        grupo_destino_layout.setSpacing(0)
        grupo_destino_layout.addWidget(QLabel("Destino"))
        grupo_destino_layout.addWidget(self.combo_destino)
        destino_controles_layout.addWidget(grupo_destino, 1)
        destino_controles_layout.addWidget(self.btn_transferir)
        transferencia_form.addRow("", destino_controles)

        coluna_direita = QWidget()
        coluna_direita_layout = QVBoxLayout(coluna_direita)
        coluna_direita_layout.setContentsMargins(0, 0, 0, 0)
        coluna_direita_layout.setSpacing(14)
        coluna_direita_layout.addWidget(transferencia)

        imprimir = QGroupBox()
        imprimir.setFixedWidth(310)
        imprimir.setStyleSheet("QGroupBox { background-color: #dbeafe; }")
        imprimir_form = QVBoxLayout(imprimir)
        imprimir_form.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.combo_impressoras = QComboBox()
        impressoras = QPrinterInfo.availablePrinterNames()
        self.combo_impressoras.addItems(impressoras or ["Nenhuma impressora disponível"])
        imprimir_form.addWidget(self.combo_impressoras, 0, Qt.AlignmentFlag.AlignLeft)
        quantidades = QWidget()
        quantidades_layout = QHBoxLayout(quantidades)
        quantidades_layout.setContentsMargins(0, 0, 0, 0)
        quantidades_layout.setSpacing(2)
        quantidades_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        grupo_qtde_item = QWidget()
        grupo_qtde_item_layout = QVBoxLayout(grupo_qtde_item)
        grupo_qtde_item_layout.setContentsMargins(0, 0, 0, 0)
        grupo_qtde_item_layout.setSpacing(0)
        grupo_qtde_item_layout.addWidget(QLabel("Qtde item"))
        self.campo_qtde_item = QLineEdit("1")
        self.campo_qtde_item.setValidator(QIntValidator(1, 999999, self))
        self.campo_qtde_item.setStyleSheet("padding: 1px;")
        self.campo_qtde_item.setFixedWidth(max(20, (self.campo_qtde_item.sizeHint().width() - 10) // 2 + 20))
        self.campo_qtde_item.setFixedHeight(self.campo_qtde_item.sizeHint().height() + 5)
        grupo_qtde_item_layout.addWidget(self.campo_qtde_item)
        grupo_qtde_item.setFixedWidth(max(
            grupo_qtde_item_layout.sizeHint().width(),
            self.campo_qtde_item.width(),
        ))
        quantidades_layout.addWidget(grupo_qtde_item)
        grupo_qtde_etiqueta = QWidget()
        grupo_qtde_etiqueta_layout = QHBoxLayout(grupo_qtde_etiqueta)
        grupo_qtde_etiqueta_layout.setContentsMargins(0, 0, 0, 0)
        grupo_qtde_etiqueta_layout.setSpacing(0)
        campo_etiqueta = QWidget()
        campo_etiqueta_layout = QVBoxLayout(campo_etiqueta)
        campo_etiqueta_layout.setContentsMargins(0, 0, 0, 0)
        campo_etiqueta_layout.setSpacing(0)
        campo_etiqueta_layout.addWidget(QLabel("Qtde etq"))
        self.campo_qtde_etiqueta = QLineEdit("1")
        self.campo_qtde_etiqueta.setValidator(QIntValidator(1, 999999, self))
        self.campo_qtde_etiqueta.setStyleSheet("padding: 1px;")
        self.campo_qtde_etiqueta.setFixedWidth(max(20, (self.campo_qtde_etiqueta.sizeHint().width() - 10) // 2 + 20))
        self.campo_qtde_etiqueta.setFixedHeight(self.campo_qtde_etiqueta.sizeHint().height() + 5)
        self.campo_qtde_etiqueta.setFixedWidth(max(
            self.campo_qtde_etiqueta.width(),
            campo_etiqueta_layout.sizeHint().width(),
        ))
        campo_etiqueta_layout.addWidget(self.campo_qtde_etiqueta)
        grupo_qtde_etiqueta_layout.addWidget(campo_etiqueta)
        botoes_etiqueta = QWidget()
        botoes_etiqueta_layout = QVBoxLayout(botoes_etiqueta)
        botoes_etiqueta_layout.setContentsMargins(4, 0, 0, 0)
        botoes_etiqueta_layout.setSpacing(0)
        self.grupo_botoes_etiqueta = QButtonGroup(self)
        for texto in ("Loc novo", "Loc retorno"):
            radio = QRadioButton(texto)
            self.grupo_botoes_etiqueta.addButton(radio)
            botoes_etiqueta_layout.addWidget(radio)
            if texto == "Loc novo":
                radio.setChecked(True)
        grupo_qtde_etiqueta_layout.addWidget(botoes_etiqueta)
        quantidades_layout.addWidget(grupo_qtde_etiqueta)
        controles_impressao = QHBoxLayout()
        controles_impressao.setContentsMargins(0, 0, 0, 0)
        controles_impressao.setSpacing(0)
        controles_impressao.setAlignment(Qt.AlignmentFlag.AlignLeft)
        controles_impressao.addWidget(quantidades)
        controles_impressao.addWidget(self.btn_imprimir)
        imprimir_form.addLayout(controles_impressao, 0)
        coluna_direita_layout.addWidget(imprimir)
        coluna_direita_layout.addStretch()
        colunas.addWidget(coluna_direita, 1)
        layout.addLayout(colunas)
        botoes = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        botoes.rejected.connect(self.reject)
        layout.addWidget(botoes)

    def _carregar_kardex(self):
        kardex = self.campo_kardex.text().strip()
        dados = getattr(self.parent(), "dados", [])
        item = next(
            (item for item in dados
             if str(item.get("Kardex", "")).strip() == kardex),
            None,
        )
        if not item:
            QMessageBox.warning(self, "Kardex", "Kardex não encontrado.")
            return

        self.item = item
        self.campo_codigo.setText(str(item.get("Código", "")))
        self.descricao.setText(str(item.get("Descrição", "")))
        campos = (
            (self.campo_loc_novo, "Loc novo"),
            (self.campo_loc_retorno, "Loc retorno"),
            (self.campo_loc_aux, "Loc aux"),
            (self.campo_qtde_loc_novo, "Qtde novo"),
            (self.campo_qtde_loc_retorno, "Qtde retorno"),
            (self.campo_qtde_loc_aux, "Qtde aux"),
            (self.campo_entrada_loc_novo, "Entrada novo"),
            (self.campo_entrada_loc_retorno, "Entrada retorno"),
            (self.campo_entrada_loc_aux, "Entrada aux"),
        )
        for campo, chave in campos:
            campo.setText(str(item.get(chave, "")))

    def _transferir(self):
        if not self.campo_qtde_transferencia.text().strip():
            QMessageBox.warning(self, "Transferência", "Informe a quantidade a transferir.")
            return
        tipo = self.grupo_tipo.checkedButton().text()
        destino = self.combo_destino.currentText()
        QMessageBox.information(self, "Transferência", f"Transferência preparada: {tipo}, {self.campo_qtde_transferencia.text()} item(ns) para {destino}.")

    def _imprimir(self):
        impressora = self.combo_impressoras.currentText()
        if impressora == "Nenhuma impressora disponível":
            QMessageBox.warning(self, "Impressão", "Não há impressoras disponíveis.")
            return

        try:
            quantidade = int(self.campo_qtde_etiqueta.text())
        except ValueError:
            QMessageBox.warning(self, "Impressão", "Informe uma quantidade válida de etiquetas.")
            return

        if quantidade <= 0:
            QMessageBox.warning(self, "Impressão", "Informe uma quantidade maior que zero.")
            return

        item = self.item
        codigo = str(item.get("Código", "")).strip()
        kardex = str(item.get("Kardex", "")).strip()
        descricao = str(item.get("Descrição", "")).strip()
        local = self.campo_loc_novo.text().strip() or str(item.get("Loc novo", "")).strip()
        qtde_item = self.campo_qtde_item.text().strip() or "1"
        requisitante = "ESTOQUE"

        def mm_to_dots(mm, dpi=203):
            return int(mm * dpi / 25.4)

        zpl_jobs = []
        for _ in range(quantidade):
            width = mm_to_dots(100)
            height = mm_to_dots(40)
            zpl = [
                "^XA",
                "^PON",
                f"^PW{width}",
                f"^LL{height}",
                "^LH0,0",
                f"^FO{mm_to_dots(2)},{mm_to_dots(2)}^GB{width - mm_to_dots(4)},{height - mm_to_dots(4)},2^FS",
                f"^FO{mm_to_dots(5)},{mm_to_dots(5)}^A0N,40,40^FD{codigo}^FS",
                f"^FO{mm_to_dots(5)},{mm_to_dots(12)}^A0N,30,30^FD{kardex}^FS",
                f"^FO{mm_to_dots(5)},{mm_to_dots(20)}^A0N,25,25^FD{descricao[:40]}^FS",
                f"^FO{mm_to_dots(5)},{mm_to_dots(28)}^A0N,25,25^FDReq: {requisitante}^FS",
                f"^FO{mm_to_dots(5)},{mm_to_dots(34)}^A0N,30,30^FDQtde: {qtde_item}^FS",
                f"^FO{mm_to_dots(50)},{mm_to_dots(34)}^A0N,30,30^FDLOC: {local}^FS",
                "^PQ1",
                "^XZ",
            ]
            zpl_jobs.append("\n".join(zpl))

        try:
            import win32print
        except Exception:
            QMessageBox.warning(self, "Impressão", "Envio direto de ZPL requer a biblioteca pywin32 (win32print).")
            return

        payload = "".join(zpl_jobs).encode("utf-8")
        try:
            hPrinter = win32print.OpenPrinter(impressora)
            try:
                win32print.StartDocPrinter(hPrinter, 1, ("ZPL Print", None, "RAW"))
                try:
                    pos = 0
                    while pos < len(payload):
                        written = win32print.WritePrinter(hPrinter, payload[pos:])
                        if written <= 0:
                            raise IOError("Falha ao gravar dados na impressora")
                        pos += written
                finally:
                    win32print.EndDocPrinter(hPrinter)
            finally:
                win32print.ClosePrinter(hPrinter)
        except Exception as erro:
            QMessageBox.critical(self, "Erro de Impressão", f"Falha ao enviar ZPL para a impressora: {erro}")
            return

        QMessageBox.information(self, "Impressão", "Etiquetas enviadas para a impressora usando o layout da programação de agulhas.")


class EditorDelegate(QStyledItemDelegate):
    def sizeHint(self, option, index):
        base = super().sizeHint(option, index)
        return QSize(base.width(), max(base.height(), 34))

    def createEditor(self, parent, option, index):
        editor = super().createEditor(parent, option, index)
        if isinstance(editor, QLineEdit):
            editor.setMinimumHeight(34)
            editor.setStyleSheet("padding: 4px 8px;")
        return editor


def _caminho_json():
    import config
    base = config.obter_caminho_jsons()
    if not base:
        return ""
    return os.path.normpath(
        os.path.join(
            base,
            "Almox",
            "ItensAlmoxarifado",
            "ItensAlmoxarifado.json"
        )
    )


class EstoquePage(QWidget):
    COLUNAS_RESUMIDAS = [1, 2, 3, 4, 5, 6, 7, 40, 41, 8, 20, 22]

    HEADERS_RESUMIDOS = [
        "Kardex",
        "Código",
        "Descrição",
        "Loc novo",
        "Qtde novo",
        "Loc retorno",
        "Qtde retorno",
        "QtdeDPH",
        "Qtde QAD",
        "Fornecedor",
        "Custo",
        "Consumo médio",
    ]

    COLUNAS = [
        "Id", "Kardex", "Código", "Descrição", "Loc novo", "Qtde novo",
        "Loc retorno", "Qtde retorno", "Fornecedor", "Provável fornecedor",
        "Ordem", "Lote Pedido", "Lote Compra", "Leadtime", "Fator Segurança",
        "UM", "Pendente DPH", "Pend. entrega compras", "Pendente para SA",
        "Lugar de uso", "Custo", "Curva custo", "Consumo médio", "Curva demanda",
        "Equipamento", "Tipo de uso", "Estoque mínimo", "Estoque máximo",
        "Estoque estratégico", "Mostrar cons. med./prog. no mês",
        "Separar p/ holder", "Separar p/ mesa", "Item de estoque",
        "Pino de contato", "Ativo/Obsol.", "Classificação Fiscal", "IPI",
        "Observações", "Doc. evidência", "Descrição de evidência",
        "QtdeDPH", "Qtde QAD",
    ]

    CHAVES = [
        "Id", "Kardex", "Código", "Descrição", "Loc novo", "Qtde novo",
        "Loc retorno", "Qtde retorno", "Fornecedor", "Provável fornecedor",
        "Ordem", "Lote Pedido", "Lote Compra", "Leadtime", "Fator Segurança",
        "UM", "Pendente DPH", "Pend. entrega compras", "Pendente para SA",
        "Lugar de uso", "Custo", "Curva custo", "Consumo médio", "Curva demanda",
        "Equipamento", "Tipo de uso", "Estoque mínimo", "Estoque máximo",
        "Estoque estratégico", "Mostrar cons. med./prog. no mês",
        "Separar p/ holder", "Separar p/ mesa", "Item de estoque",
        "Pino de contato", "Ativo/Obsol.", "Classificação Fiscal", "IPI",
        "Observações", "Doc. evidência", "Descrição de evidência",
        "QtdeDPH", "Qtde QAD",
    ]

    CAMPOS_DETALHES = [
        ("Código", "Código"),
        ("Kardex", "Kardex"),
        ("Descrição", "Descrição"),
        ("Loc novo", "Loc novo"),
        ("Qtde novo", "Qtde novo"),
        ("Loc retorno", "Loc retorno"),
        ("Qtde retorno", "Qtde retorno"),
        ("Consumo médio", "Consumo médio"),
        ("Qtde comprada", "Pend. entrega compras"),
    ]

    def __init__(self):
        super().__init__()
        self.dados = []
        self._texto_filtro_cache = []
        self.modo_resumido = True
        self._setup_ui()
        self.atalho_detalhes = QShortcut(QKeySequence("Ctrl+P"), self)
        self.atalho_detalhes.setContext(Qt.ShortcutContext.WindowShortcut)
        self.atalho_detalhes.activated.connect(self._abrir_detalhes_item)
        self._carregar_dados()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(0)

        card = QWidget()
        card.setObjectName("pageCard")

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(28, 24, 28, 24)
        card_layout.setSpacing(18)

        # =====================================================
        # =====================================================
        topo = QHBoxLayout()
        topo.setSpacing(18)

        coluna_esquerda = QVBoxLayout()
        coluna_esquerda.setSpacing(12)

        titulo = QLabel("Estoque")
        titulo.setObjectName("pageTitle")
        titulo.setStyleSheet("""
            QLabel {
                color: #11163d;
                font-size: 25px;
                font-weight: 700;
            }
        """)
        coluna_esquerda.addWidget(titulo, 0, Qt.AlignmentFlag.AlignLeft)

        btn_atualizar = QPushButton("⟳  Atualizar")
        btn_atualizar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_atualizar.setFixedSize(168, 44)

        btn_atualizar.setStyleSheet("""
            QPushButton {
                background-color: #5b61f6;
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 14px;
                font-weight: 600;
            }

            QPushButton:hover {
                background-color: #4b51e6;
            }

            QPushButton:pressed {
                background-color: #4147d2;
            }
        """)

        btn_atualizar.clicked.connect(self._atualizar)

        linha_botoes = QHBoxLayout()
        linha_botoes.setSpacing(10)
        linha_botoes.addWidget(btn_atualizar)

        btn_exportar = QPushButton("📊 Exportar Excel")
        btn_exportar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_exportar.setFixedSize(168, 44)
        btn_exportar.setStyleSheet("""
            QPushButton {
                background-color: #16a34a;
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #15803d;
            }
            QPushButton:pressed {
                background-color: #166534;
            }
        """)
        btn_exportar.clicked.connect(self._exportar_excel)

        linha_botoes.addWidget(btn_exportar)
        coluna_esquerda.addLayout(linha_botoes)

        filtro_layout = QHBoxLayout()
        filtro_layout.setSpacing(6)
        filtro_layout.setContentsMargins(0, 0, 0, 0)

        self.campo_filtro = QLineEdit()
        self.campo_filtro.setPlaceholderText("⌕   Pesquisar...")
        self.campo_filtro.setFixedHeight(44)
        self.campo_filtro.setMinimumWidth(200)
        # Timer debounce para não travar digitação (filtro só após 280ms sem digitar)
        self._filtro_timer = QTimer(self)
        self._filtro_timer.setSingleShot(True)
        self._filtro_timer.setInterval(280)
        self._filtro_timer.timeout.connect(self._on_filtro_timeout)
        self.campo_filtro.textChanged.connect(self._on_filtro_text_changed)

        self.campo_filtro.setStyleSheet("""
            QLineEdit {
                background: white;
                color: #17203f;
                border: 1px solid #dce3ee;
                border-radius: 10px;
                padding-left: 15px;
                padding-right: 40px;
                font-size: 13px;
            }

            QLineEdit:focus {
                border: 1px solid #6366f1;
            }
        """)

        self.btn_limpar_filtro = QPushButton("✕")
        self.btn_limpar_filtro.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_limpar_filtro.setFixedSize(32, 32)
        self.btn_limpar_filtro.setToolTip("Limpar filtro")
        self.btn_limpar_filtro.clicked.connect(self._limpar_filtro)
        self.btn_limpar_filtro.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #9ca3af;
                border: none;
                border-radius: 6px;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #f3f4f6;
                color: #6b7280;
            }
            QPushButton:pressed {
                background: #e5e7eb;
                color: #4b5563;
            }
        """)

        filtro_layout.addWidget(self.campo_filtro)
        filtro_layout.addWidget(self.btn_limpar_filtro)

        coluna_esquerda.addLayout(filtro_layout)
        coluna_esquerda.addStretch()

        topo.addLayout(coluna_esquerda)

        # =====================================================
        # CARD CENTRAL - ITEM SELECIONADO
        # =====================================================
        self.detalhes_box = QWidget()
        self.detalhes_box.setObjectName("detalhesBox")
        self.detalhes_box.setMinimumHeight(128)
        self.detalhes_box.setMaximumWidth(630)

        self.detalhes_box.setStyleSheet("""
            QWidget#detalhesBox {
                background: #ffffff;
                border: 1px solid #dce3ee;
                border-radius: 12px;
            }

            QLabel {
                border: none;
                background: transparent;
            }
        """)

        detalhes_layout = QVBoxLayout(self.detalhes_box)
        detalhes_layout.setContentsMargins(14, 6, 14, 6)
        detalhes_layout.setSpacing(2)

        lbl_visao = QLabel("VISÃO GERAL DO ITEM SELECIONADO")
        lbl_visao.setContentsMargins(0, 0, 0, 0)
        lbl_visao.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        lbl_visao.setStyleSheet("""
            QLabel {
                color: #65769d;
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 0.5px;
                margin: 0;
                padding: 0;
                background: transparent;
                border: none;
            }
        """)
        detalhes_layout.addWidget(lbl_visao, 0, Qt.AlignmentFlag.AlignTop)

        self._labels_valores = {}

        def criar_linha(rotulo, chave, simbolo="", cor="#5f6cf5", largura_label=105, word_wrap=False):
            widget = QWidget()
            widget.setMinimumHeight(24)

            lay = QHBoxLayout(widget)
            lay.setContentsMargins(0, 0, 0, 0)
            lay.setSpacing(8)

            icone = QLabel(simbolo)
            icone.setFixedWidth(22)
            icone.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icone.setStyleSheet(f"""
                QLabel {{
                    color: {cor};
                    font-size: 17px;
                    font-weight: 700;
                }}
            """)

            lbl_nome = QLabel(rotulo.upper())
            lbl_nome.setFixedWidth(largura_label)
            lbl_nome.setStyleSheet("""
                QLabel {
                    color: #7183aa;
                    font-size: 12px;
                    font-weight: 600;
                }
            """)

            lbl_valor = QLabel("-")
            lbl_valor.setWordWrap(word_wrap)
            lbl_valor.setStyleSheet("""
                QLabel {
                    color: #17203f;
                    font-size: 14px;
                    font-weight: 600;
                }
            """)

            lbl_valor.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse
            )

            self._labels_valores[chave] = lbl_valor

            lay.addWidget(icone)
            lay.addWidget(lbl_nome)
            lay.addWidget(lbl_valor, 1)

            return widget

        def separador():
            linha = QFrame()
            linha.setFrameShape(QFrame.Shape.HLine)
            linha.setStyleSheet("""
                QFrame {
                    border: none;
                    background: #edf0f5;
                    max-height: 1px;
                }
            """)
            return linha

        def separador_vertical():
            linha = QFrame()
            linha.setFrameShape(QFrame.Shape.VLine)
            linha.setStyleSheet("""
                QFrame {
                    border: none;
                    background: #edf0f5;
                    max-width: 1px;
                }
            """)
            return linha

        # ── Linha 1: Código | Kardex ──
        linha1 = QHBoxLayout()
        linha1.setSpacing(20)
        linha1.setContentsMargins(0, 0, 0, 0)
        linha1.addWidget(criar_linha("Código", "Código", "◇", "#5865f2"), 1)
        linha1.addWidget(separador_vertical())
        linha1.addWidget(criar_linha("Kardex", "Kardex", "▤", "#5865f2"), 1)
        linha1_widget = QWidget()
        linha1_widget.setLayout(linha1)
        detalhes_layout.addWidget(linha1_widget)
        detalhes_layout.addWidget(separador())

        # ── Linha 2: Descrição (linha inteira, sem dividir) ──
        descricao_linha = criar_linha("Descrição", "Descrição", "▣", "#5865f2", word_wrap=True)
        descricao_linha.setMinimumHeight(28)
        detalhes_layout.addWidget(descricao_linha)
        detalhes_layout.addWidget(separador())

        # ── Linha 3: três colunas fixas ──
        linha3 = QHBoxLayout()
        linha3.setSpacing(12)
        linha3.setContentsMargins(0, 0, 0, 0)
        w_loc_novo = criar_linha("Loc novo", "Loc novo", "⌖", "#5865f2", largura_label=68)
        w_loc_novo.setFixedWidth(220)
        w_qtde_novo = criar_linha("Qtde", "Qtde novo", "▣", "#16b86c", largura_label=40)
        w_qtde_novo.setFixedWidth(135)
        w_consumo = criar_linha("Consumo médio", "Consumo médio", "⌁", "#5865f2", largura_label=95)
        w_consumo.setFixedWidth(185)
        linha3.addWidget(w_loc_novo)
        linha3.addWidget(separador_vertical())
        linha3.addWidget(w_qtde_novo)
        linha3.addWidget(separador_vertical())
        linha3.addWidget(w_consumo)
        linha3.addStretch(1)
        linha3_widget = QWidget()
        linha3_widget.setLayout(linha3)
        detalhes_layout.addWidget(linha3_widget)
        detalhes_layout.addWidget(separador())

        # ── Linha 4: três colunas fixas (terceira vazia) ──
        linha4 = QHBoxLayout()
        linha4.setSpacing(12)
        linha4.setContentsMargins(0, 0, 0, 0)
        w_loc_ret = criar_linha("Loc ret", "Loc retorno", "⌖", "#5865f2", largura_label=68)
        w_loc_ret.setFixedWidth(220)
        w_qtde_ret = criar_linha("Qtde", "Qtde retorno", "▣", "#ff7a21", largura_label=40)
        w_qtde_ret.setFixedWidth(135)
        w_custo = criar_linha("Custo", "Custo", "＄", "#16b86c", largura_label=68)
        w_custo.setFixedWidth(185)
        linha4.addWidget(w_loc_ret)
        linha4.addWidget(separador_vertical())
        linha4.addWidget(w_qtde_ret)
        linha4.addWidget(separador_vertical())
        linha4.addWidget(w_custo)
        linha4.addStretch(1)
        linha4_widget = QWidget()
        linha4_widget.setLayout(linha4)
        detalhes_layout.addWidget(linha4_widget)

        detalhes_layout.addStretch(1)
        topo.addWidget(self.detalhes_box, 1)

        # =====================================================
        # CARD CONTADOR
        # =====================================================
        contador_box = QWidget()
        contador_box.setFixedWidth(141)
        contador_box.setFixedHeight(96)

        contador_box.setStyleSheet("""
            QWidget {
                background: white;
                border: 1px solid #dce3ee;
                border-radius: 12px;
            }

            QLabel {
                border: none;
                background: transparent;
            }
        """)

        contador_layout = QVBoxLayout(contador_box)
        contador_layout.setContentsMargins(8, 5, 8, 5)
        contador_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        contador_layout.setSpacing(2)

        circulo = QLabel("◇")
        circulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        circulo.setFixedSize(34, 34)
        circulo.setStyleSheet("""
            QLabel {
                background: #f0f1ff;
                color: #5b61f6;
                border: 1px solid #e0e3ff;
                border-radius: 17px;
                font-size: 20px;
                font-weight: 600;
            }
        """)

        contador_layout.addWidget(
            circulo,
            alignment=Qt.AlignmentFlag.AlignCenter
        )

        self.label_contador = QLabel("0")
        self.label_contador.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_contador.setStyleSheet("""
            QLabel {
                color: #11163d;
                font-size: 20px;
                font-weight: 700;
            }
        """)

        contador_layout.addWidget(self.label_contador)

        lbl_itens = QLabel("itens cadastrados")
        lbl_itens.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_itens.setStyleSheet("""
            QLabel {
                color: #63739a;
                font-size: 11px;
                font-weight: 500;
            }
        """)

        contador_layout.addWidget(lbl_itens)
        contador_layout.addStretch()

        self.btn_toggle = QPushButton("⛶  Visão completa")
        self.btn_toggle.setObjectName("btnSecondary")
        self.btn_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle.setFixedSize(141, 35)
        self.btn_toggle.setCheckable(True)
        self.btn_toggle.clicked.connect(self._alternar_modo)

        self.btn_toggle.setStyleSheet("""
            QPushButton {
                background: white;
                color: #52648f;
                border: 1px solid #dce3ee;
                border-radius: 10px;
                font-size: 13px;
                font-weight: 500;
                padding: 0 14px;
            }

            QPushButton:hover {
                background: #f8faff;
                border-color: #bcc9e0;
            }

            QPushButton:pressed {
                background: #eef2ff;
            }
        """)

        coluna_direita_superior = QWidget()
        coluna_direita_superior.setFixedWidth(141)
        coluna_superior_layout = QVBoxLayout(coluna_direita_superior)
        coluna_superior_layout.setContentsMargins(0, 0, 0, 0)
        coluna_superior_layout.setSpacing(12)

        coluna_superior_layout.addWidget(contador_box)
        coluna_superior_layout.addWidget(self.btn_toggle)

        topo.addWidget(coluna_direita_superior)
        card_layout.addLayout(topo)

        # =====================================================
        # TABELA
        # =====================================================
        self.tabela = QTableWidget(0, len(self.COLUNAS))
        self.tabela.setHorizontalHeaderLabels(self.COLUNAS)

        self.tabela.setStyleSheet("""
            QTableWidget {
                background: white;
                color: #111827;
                border: 1px solid #dfe5ee;
                border-radius: 11px;
                gridline-color: #edf0f5;
                font-size: 11px;
                selection-background-color: #eef0ff;
                selection-color: #111827;
            }

            QTableWidget::item {
                padding: 0px;
                border-bottom: 1px solid #eef1f5;
            }

            QTableWidget::item:selected {
                background: #eef0ff;
                color: #111827;
            }

            QScrollBar:vertical {
                background: transparent;
                width: 16px;
                margin: 4px;
            }

            QScrollBar::handle:vertical {
                background: #cbd2df;
                border-radius: 8px;
                min-height: 30px;
            }

            QScrollBar::handle:vertical:hover {
                background: #aeb8ca;
            }

            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0px;
            }

            QScrollBar:horizontal {
                background: transparent;
                height: 10px;
            }

            QScrollBar::handle:horizontal {
                background: #cbd2df;
                border-radius: 5px;
                min-width: 30px;
            }
        """)

        header = self.tabela.horizontalHeader()
        header.setStyleSheet("""
            QHeaderView::section {
                background-color: #fbfcfe;
                color: #63739a;
                font-size: 9px;
                font-weight: 700;
                padding: 12px 8px;
                border: none;
                border-bottom: 1px solid #dfe5ee;
            }
        """)

        header.setStretchLastSection(False)

        for c in range(self.tabela.columnCount()):
            header.setSectionResizeMode(
                c,
                QHeaderView.ResizeMode.Interactive
            )

            if c == 1:
                largura = 132
            elif c == 2:
                largura = 180
            elif c == 3:
                largura = 290
            elif c in (4, 6):
                largura = 100
            elif c in (5, 7):
                largura = 79
            elif c == 8:
                largura = 150
            elif c == 20:
                largura = 110
            elif c == 22:
                largura = 125
            elif c in (40, 41):
                largura = 66
            else:
                largura = 120

            header.resizeSection(c, largura)

        self.tabela.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )

        self.tabela.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )

        self.tabela.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked
        )

        self.tabela.setAlternatingRowColors(False)
        self.tabela.verticalHeader().setDefaultSectionSize(24)
        self.tabela.verticalHeader().setMinimumSectionSize(20)
        self.tabela.verticalHeader().setVisible(False)

        self.tabela.setHorizontalScrollMode(
            QAbstractItemView.ScrollMode.ScrollPerPixel
        )

        self.tabela.setVerticalScrollMode(
            QAbstractItemView.ScrollMode.ScrollPerPixel
        )

        self.tabela.setItemDelegate(
            EditorDelegate(self.tabela)
        )

        self.tabela.itemSelectionChanged.connect(
            self._atualizar_detalhes
        )

        card_layout.addWidget(self.tabela, 1)

        card.setStyleSheet("""
            QWidget#pageCard {
                background: #ffffff;
                border: 1px solid #e2e7ef;
                border-radius: 16px;
            }
        """)

        layout.addWidget(card)

    def _obter_item_selecionado(self):
        row = self.tabela.currentRow()
        if row < 0:
            return None

        coluna_kardex = self.COLUNAS.index("Kardex")
        cell = self.tabela.item(row, coluna_kardex)
        if not cell:
            return None

        kardex = cell.text().strip()
        return next(
            (item for item in self.dados
             if str(item.get("Kardex", "")).strip() == kardex),
            None,
        )

    def _abrir_detalhes_item(self):
        item = self._obter_item_selecionado()
        if not item:
            QMessageBox.information(
                self,
                "Detalhes do item",
                "Selecione um item na tabela para abrir os detalhes.",
            )
            return

        dialogo = DetalhesEstoqueDialog(item, self)
        dialogo.exec()

    def _rebuild_cache_filtro(self):
        # cache de texto lowercased para filtro instantâneo
        try:
            self._texto_filtro_cache = [
                " ".join(str(v) for v in item.values()).lower()
                for item in self.dados
            ]
        except Exception:
            self._texto_filtro_cache = []

    def _carregar_dados(self):
        try:
            with open(_caminho_json(), "r", encoding="utf-8") as f:
                self.dados = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.dados = []
        self._rebuild_cache_filtro()
        self._popular_tabela()

    def _popular_tabela(self):
        # otimizado: desativa updates, usa cache e setRowCount batch
        if len(self._texto_filtro_cache) != len(self.dados):
            self._rebuild_cache_filtro()
        self.tabela.setUpdatesEnabled(False)
        self.tabela.blockSignals(True)

        filtro_texto = self.campo_filtro.text().strip().lower()

        # filtra usando cache
        filtrados = []
        cache = self._texto_filtro_cache
        for idx, item in enumerate(self.dados):
            if self.modo_resumido:
                ativo = str(item.get("Ativo/Obsol.", "")).strip().lower()
                if "ativo" not in ativo:
                    continue
                codigo = str(item.get("Código", "")).strip().upper()
                if codigo.endswith("AT") or codigo.endswith("(AT)"):
                    continue

            if filtro_texto:
                if idx < len(cache):
                    texto = cache[idx]
                else:
                    texto = " ".join(str(v) for v in item.values()).lower()
                if filtro_texto not in texto:
                    continue

            filtrados.append(item)

        self.tabela.setRowCount(len(filtrados))

        for row, item in enumerate(filtrados):
            for col, chave in enumerate(self.CHAVES):
                valor = str(item.get(chave, ""))

                cell = QTableWidgetItem(valor)

                cell.setFlags(
                    cell.flags() & ~Qt.ItemFlag.ItemIsEditable
                )

                self.tabela.setItem(row, col, cell)

        if self.modo_resumido:
            for c in range(len(self.COLUNAS)):
                self.tabela.setColumnHidden(
                    c,
                    c not in self.COLUNAS_RESUMIDAS
                )

            header = self.tabela.horizontalHeader()
            ordem = [
                self.COLUNAS.index(col)
                for col in self.HEADERS_RESUMIDOS
            ]

            for i, logico in enumerate(ordem):
                pos = header.visualIndex(logico)

                if pos != i:
                    header.moveSection(pos, i)
        else:
            for c in range(len(self.COLUNAS)):
                self.tabela.setColumnHidden(c, False)

        self.tabela.blockSignals(False)
        self.tabela.setUpdatesEnabled(True)

        self.label_contador.setText(
            str(self.tabela.rowCount())
        )

        self._atualizar_detalhes()

    def _on_filtro_text_changed(self, texto):
        # debounce: só filtra após usuário parar de digitar
        try:
            self._filtro_timer.stop()
        except Exception:
            pass
        # filtro vazio responde mais rápido
        if not texto.strip():
            self._filtro_timer.start(80)
        else:
            self._filtro_timer.start(280)

    def _on_filtro_timeout(self):
        self._popular_tabela()
        if self.tabela.rowCount() == 1:
            self.tabela.selectRow(0)

    def _atualizar(self):
        modo_anterior = self.modo_resumido

        if self.modo_resumido:
            self.modo_resumido = False
            self.btn_toggle.setText("▣  Visão resumida")

        clipboard = QGuiApplication.clipboard()
        texto = clipboard.text()

        if not texto.strip():
            QMessageBox.warning(
                self,
                "Aviso",
                "A área de transferência está vazia."
            )

            self.modo_resumido = modo_anterior

            if modo_anterior:
                self.btn_toggle.setText("⛶  Visão completa")

            return

        linhas = [
            l.strip()
            for l in texto.replace("\r\n", "\n").split("\n")
            if l.strip()
        ]

        if not linhas:
            self.modo_resumido = modo_anterior

            if modo_anterior:
                self.btn_toggle.setText("⛶  Visão completa")

            return

        header, dados_linha = self._separar_cabecalho(linhas)

        if not dados_linha:
            QMessageBox.warning(
                self,
                "Aviso",
                "Não há dados válidos para atualizar."
            )

            self.modo_resumido = modo_anterior

            if modo_anterior:
                self.btn_toggle.setText("⛶  Visão completa")

            return

        colunas = len(dados_linha[0].split("\t"))

        if colunas == 40:
            resposta = QMessageBox.question(
                self,
                "Confirmação",
                "Atualizar completamente o estoque?",
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )

            if resposta != QMessageBox.StandardButton.Yes:
                self.modo_resumido = modo_anterior

                if modo_anterior:
                    self.btn_toggle.setText("⛶  Visão completa")

                return

            self._fazer_atualizacao_completa(
                dados_linha
            )

        elif colunas == 24:
            self._fazer_atualizacao_parcial(
                dados_linha,
                header
            )

        else:
            QMessageBox.warning(
                self,
                "Formato inválido",
                "A tabela copiada deve ter 40 ou 24 colunas."
            )

            self.modo_resumido = modo_anterior

            if modo_anterior:
                self.btn_toggle.setText("⛶  Visão completa")

            return

        self.modo_resumido = modo_anterior

        if modo_anterior:
            self.btn_toggle.setText(
                "⛶  Visão completa"
            )
        else:
            self.btn_toggle.setText(
                "▣  Visão resumida"
            )

        self._popular_tabela()

        # Sincronizar itens com estoque zero
        main_win = self.window()

        if main_win and hasattr(main_win, "pages"):
            itens_zero_page = main_win.pages.get(
                "itens_zero"
            )

            if itens_zero_page:
                itens_zero_page._sincronizar()

        QMessageBox.information(
            self,
            "Sucesso",
            "Estoque atualizado com sucesso!"
        )

    def _fazer_atualizacao_completa(self, linhas):
        novos_por_kardex = {}

        for linha in linhas:
            partes = linha.split("\t")

            if len(partes) < 2:
                continue

            item = {}

            for col, chave in enumerate(self.CHAVES):
                if col < len(partes):
                    item[chave] = partes[col].strip()

            chave_kardex = str(
                item.get("Kardex", "")
            ).strip()

            if chave_kardex:
                novos_por_kardex[
                    chave_kardex
                ] = item

        existentes_por_kardex = {
            str(item.get("Kardex", "")).strip(): item
            for item in self.dados
            if str(item.get("Kardex", "")).strip()
        }

        for kardex, item_novo in (
            novos_por_kardex.items()
        ):
            item_atual = (
                existentes_por_kardex.get(kardex)
            )

            if item_atual is not None:
                item_atual.update(item_novo)
            else:
                self.dados.append(item_novo)

        self._salvar_json()
        self._popular_tabela()

    def _fazer_atualizacao_parcial(self, linhas, header):
        kardex_idx = 0
        qtde_novo_idx = 6
        qtde_retorno_idx = 4
        consumo_medio_idx = 18
        loc_novo_idx = 5
        loc_retorno_idx = 3

        dph_idx = 7
        qad_idx = 8

        if header:
            mapa = self._obter_indices_parciais(header)

            if "Kardex" in mapa:
                kardex_idx = mapa["Kardex"]

            if "Qtde novo" in mapa:
                qtde_novo_idx = mapa["Qtde novo"]

            if "Qtde retorno" in mapa:
                qtde_retorno_idx = mapa["Qtde retorno"]

            if "Consumo médio" in mapa:
                consumo_medio_idx = mapa["Consumo médio"]

            if "Loc novo" in mapa:
                loc_novo_idx = mapa["Loc novo"]

            if "Loc retorno" in mapa:
                loc_retorno_idx = mapa["Loc retorno"]

        max_idx = max(
            kardex_idx,
            qtde_novo_idx,
            qtde_retorno_idx,
            consumo_medio_idx,
            loc_novo_idx,
            loc_retorno_idx
        )

        dados_por_kardex = {
            str(item.get("Kardex", "")).strip(): item
            for item in self.dados
            if str(item.get("Kardex", "")).strip()
        }

        atualizou = False

        for linha in linhas:
            partes = linha.split("\t")

            if len(partes) <= max_idx:
                continue

            chave_kardex = partes[kardex_idx].strip()

            item = dados_por_kardex.get(
                chave_kardex
            )

            if not item:
                continue

            item["Qtde novo"] = (
                partes[qtde_novo_idx].strip()
            )

            item["Qtde retorno"] = (
                partes[qtde_retorno_idx].strip()
            )

            item["Consumo médio"] = (
                partes[consumo_medio_idx].strip()
            )

            item["Loc novo"] = (
                partes[loc_novo_idx].strip()
            )

            item["Loc retorno"] = (
                partes[loc_retorno_idx].strip()
            )

            if dph_idx >= 0 and len(partes) > dph_idx:
                item["QtdeDPH"] = (
                    partes[dph_idx].strip()
                )

            if qad_idx >= 0 and len(partes) > qad_idx:
                item["Qtde QAD"] = (
                    partes[qad_idx].strip()
                )

            atualizou = True

        if atualizou:
            self._salvar_json()
            self._popular_tabela()

    def _separar_cabecalho(self, linhas):
        if not linhas:
            return None, []

        primeiras_partes = linhas[0].split("\t")

        if self._eh_linha_cabecalho(
            primeiras_partes
        ):
            return (
                [
                    p.strip()
                    for p in primeiras_partes
                ],
                linhas[1:]
            )

        return None, linhas

    def _normalizar_coluna(self, texto):
        texto = texto.strip().lower()

        for original, substituicao in {
            "á": "a",
            "é": "e",
            "í": "i",
            "ó": "o",
            "ú": "u",
            "ã": "a",
            "õ": "o",
            "â": "a",
            "ê": "e",
            "ô": "o",
            "ç": "c",
        }.items():
            texto = texto.replace(
                original,
                substituicao
            )

        return "".join(
            ch for ch in texto
            if ch.isalnum()
        )

    def _eh_linha_cabecalho(self, partes):
        if not partes:
            return False

        nome_normalizado = self._normalizar_coluna(
            partes[0]
        )

        return nome_normalizado in {
            "id",
            "kardex",
            "codigo",
            "descricao",
        }

    def _obter_indices_parciais(self, header):
        mapa = {}

        mapeamento_nomes = {
            "kardex": "Kardex",
            "codkardex": "Kardex",

            "qtdenovo": "Qtde novo",
            "quantidadenovo": "Qtde novo",

            "qtderetorno": "Qtde retorno",
            "quantidaderetorno": "Qtde retorno",

            "consumomedio": "Consumo médio",
            "consumo": "Consumo médio",

            "locnovo": "Loc novo",
            "localnovo": "Loc novo",
            "localizacaonovo": "Loc novo",

            "locretorno": "Loc retorno",
            "localretorno": "Loc retorno",
            "localizacaoretorno": "Loc retorno",

            "qtedph": "QtdeDPH",
            "qtdedph": "QtdeDPH",
            "qtdph": "QtdeDPH",

            "qtdeqad": "Qtde QAD",
            "qtdqad": "Qtde QAD",
        }

        for indice, coluna in enumerate(header):
            chave = self._normalizar_coluna(
                coluna
            )

            if chave in mapeamento_nomes:
                mapa[
                    mapeamento_nomes[chave]
                ] = indice

        return mapa

    def _aplicar_filtro(self):
        # mantido por compatibilidade: usa debounce
        self._on_filtro_text_changed(self.campo_filtro.text())

    def _limpar_filtro(self):
        try:
            self._filtro_timer.stop()
        except Exception:
            pass
        self.campo_filtro.clear()
        self.campo_filtro.setFocus()
        # limpa imediatamente sem esperar debounce
        self._popular_tabela()
        if self.tabela.rowCount() == 1:
            self.tabela.selectRow(0)

    def _atualizar_detalhes(self):
        kardex = ""

        row = self.tabela.currentRow()

        if row >= 0:
            cell = self.tabela.item(
                row,
                self.COLUNAS.index("Kardex")
            )

            if cell:
                kardex = cell.text().strip()

        item = None

        if kardex:
            item = next(
                (
                    d for d in self.dados
                    if str(
                        d.get("Kardex", "")
                    ).strip() == kardex
                ),
                None,
            )

        for chave, lbl in self._labels_valores.items():
            valor = (
                str(item.get(chave, "")).strip()
                if item
                else ""
            )

            lbl.setText(
                valor if valor else "-"
            )

    def _alternar_modo(self):
        self.modo_resumido = (
            not self.modo_resumido
        )

        if self.modo_resumido:
            self.btn_toggle.setText(
                "⛶  Visão completa"
            )
        else:
            self.btn_toggle.setText(
                "▣  Visão resumida"
            )

        self._popular_tabela()

    def _salvar_json(self):
        caminho = _caminho_json()

        if not caminho:
            import config
            config.avisar_sem_pasta(self)
            return

        try:
            os.makedirs(
                os.path.dirname(caminho),
                exist_ok=True
            )

            with open(
                caminho,
                "w",
                encoding="utf-8"
            ) as f:
                json.dump(
                    self.dados,
                    f,
                    ensure_ascii=False,
                    indent=2
                )

        except OSError:
            pass

    def _exportar_excel(self):
        if not self.dados:
            QMessageBox.warning(
                self,
                "Aviso",
                "Não existem dados para exportar."
            )
            return

        arquivo, _ = QFileDialog.getSaveFileName(
            self,
            "Salvar Excel",
            "estoque.xlsx",
            "Arquivos Excel (*.xlsx)"
        )

        if not arquivo:
            return

        try:
            dados_exportacao = []

            for row in range(self.tabela.rowCount()):
                linha = {}

                for col in range(self.tabela.columnCount()):
                    if self.tabela.isColumnHidden(col):
                        continue

                    cabecalho = self.COLUNAS[col]

                    item = self.tabela.item(row, col)

                    linha[cabecalho] = (
                        item.text() if item else ""
                    )

                dados_exportacao.append(linha)

            df = pd.DataFrame(dados_exportacao)

            df.to_excel(
                arquivo,
                index=False,
                engine="openpyxl"
            )

            QMessageBox.information(
                self,
                "Sucesso",
                f"Arquivo exportado com sucesso:\n{arquivo}"
            )

        except Exception as e:
            QMessageBox.critical(
                self,
                "Erro",
                f"Falha ao exportar:\n{str(e)}"
            )