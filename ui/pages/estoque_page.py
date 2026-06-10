import json
import os

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QStyledItemDelegate,
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QGuiApplication


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
        base = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "jsons")
    return os.path.normpath(os.path.join(base, "Almox", "ItensAlmoxarifado", "ItensAlmoxarifado.json"))


class EstoquePage(QWidget):
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
    ]

    def __init__(self):
        super().__init__()
        self.dados = []
        self._setup_ui()
        self._carregar_dados()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(16)

        card = QWidget()
        card.setObjectName("pageCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(28, 28, 28, 28)
        card_layout.setSpacing(16)

        titulo = QLabel("Estoque")
        titulo.setObjectName("pageTitle")
        card_layout.addWidget(titulo)

        linha_top = QHBoxLayout()
        linha_top.setSpacing(8)

        btn_atualizar = QPushButton("Atualizar")
        btn_atualizar.setObjectName("btnPrimary")
        btn_atualizar.setFixedHeight(34)
        btn_atualizar.clicked.connect(self._atualizar)
        linha_top.addWidget(btn_atualizar)

        self.campo_filtro = QLineEdit()
        self.campo_filtro.setPlaceholderText("Pesquisar...")
        self.campo_filtro.setFixedHeight(30)
        self.campo_filtro.setFixedWidth(200)
        self.campo_filtro.textChanged.connect(self._aplicar_filtro)
        linha_top.addWidget(self.campo_filtro)

        self.label_contador = QLabel("0 itens")
        self.label_contador.setObjectName("statusLabel")
        linha_top.addWidget(self.label_contador)

        linha_top.addStretch()
        card_layout.addLayout(linha_top)

        self.tabela = QTableWidget(0, len(self.COLUNAS))
        self.tabela.setHorizontalHeaderLabels(self.COLUNAS)
        header = self.tabela.horizontalHeader()
        header.setStretchLastSection(False)
        for c in range(self.tabela.columnCount()):
            header.setSectionResizeMode(c, QHeaderView.ResizeMode.Interactive)
            header.resizeSection(c, 100)
        self.tabela.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self.tabela.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked)
        self.tabela.setAlternatingRowColors(False)
        self.tabela.verticalHeader().setDefaultSectionSize(28)
        self.tabela.verticalHeader().setMinimumSectionSize(24)
        self.tabela.verticalHeader().setVisible(False)
        self.tabela.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.tabela.setItemDelegate(EditorDelegate(self.tabela))
        card_layout.addWidget(self.tabela)

        layout.addWidget(card)

    def _carregar_dados(self):
        try:
            with open(_caminho_json(), "r", encoding="utf-8") as f:
                self.dados = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.dados = []
        self._popular_tabela()

    def _popular_tabela(self):
        self.tabela.blockSignals(True)
        self.tabela.setRowCount(0)
        filtro_texto = self.campo_filtro.text().strip().lower()
        for item in self.dados:
            if filtro_texto:
                texto = " ".join(str(v) for v in item.values()).lower()
                if filtro_texto not in texto:
                    continue
            row = self.tabela.rowCount()
            self.tabela.insertRow(row)
            for col, chave in enumerate(self.CHAVES):
                valor = str(item.get(chave, ""))
                cell = QTableWidgetItem(valor)
                cell.setFlags(cell.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.tabela.setItem(row, col, cell)
        self.tabela.blockSignals(False)
        self.label_contador.setText(f"{self.tabela.rowCount()} itens")

    def _atualizar(self):
        clipboard = QGuiApplication.clipboard()
        texto = clipboard.text()
        if not texto.strip():
            return

        linhas = [l.strip() for l in texto.replace("\r\n", "\n").split("\n") if l.strip()]
        if not linhas:
            return

        linha_inicial = 0
        if linhas[0].startswith("Id\t") or linhas[0].startswith("Id\""):
            linha_inicial = 1

        self.dados.clear()

        for i in range(linha_inicial, len(linhas)):
            partes = linhas[i].split("\t")
            if len(partes) < 2:
                continue
            item = {}
            for col, chave in enumerate(self.CHAVES):
                item[chave] = partes[col].strip() if col < len(partes) else ""
            self.dados.append(item)

        self._salvar_json()
        self._popular_tabela()

    def _aplicar_filtro(self):
        self._popular_tabela()

    def _salvar_json(self):
        try:
            os.makedirs(os.path.dirname(_caminho_json()), exist_ok=True)
            with open(_caminho_json(), "w", encoding="utf-8") as f:
                json.dump(self.dados, f, ensure_ascii=False, indent=2)
        except OSError:
            pass
