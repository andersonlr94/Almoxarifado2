import json
import os
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QStyledItemDelegate, QMenu,
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor, QBrush, QPainter, QPalette, QCursor


class EditorDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)

    def paint(self, painter, option, index):
        self.initStyleOption(option, index)
        bg = index.data(Qt.BackgroundRole)
        if bg is not None:
            painter.save()
            painter.fillRect(option.rect, QBrush(bg) if not isinstance(bg, QBrush) else bg)
            painter.restore()
            option.palette.setColor(QPalette.ColorRole.Highlight, Qt.GlobalColor.transparent)
            option.palette.setColor(QPalette.ColorRole.Base, Qt.GlobalColor.transparent)
        super().paint(painter, option, index)

    def sizeHint(self, option, index):
        base = super().sizeHint(option, index)
        return QSize(base.width(), max(base.height(), 34))

    def createEditor(self, parent, option, index):
        editor = super().createEditor(parent, option, index)
        if isinstance(editor, QLineEdit):
            editor.setMinimumHeight(34)
            editor.setStyleSheet("padding: 4px 8px; border: none; border-bottom: 1px solid #999; border-radius: 0px;")
        return editor

    def setModelData(self, editor, model, index):
        super().setModelData(editor, model, index)
        row = index.row()
        col = index.column()
        value = str(editor.text()).strip()
        if value:
            data_index = model.index(row, 0)
            if not data_index.data(Qt.DisplayRole):
                hoje = datetime.now().strftime("%d/%m/%Y")
                model.setData(data_index, hoje)


def _caminho_json():
    import config
    base = config.obter_caminho_jsons()
    if not base:
        base = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "jsons")
    return os.path.normpath(os.path.join(base, "Almox", "ControlePedidos", "controlePedidos.json"))


class ControlePedidosPage(QWidget):
    COLUNAS = ["Data", "Fornecedores", "Nome", "Requisição", "DPP", "Observação"]
    CHAVES = ["data", "fornecedores", "nome", "requisicao", "dpp", "observacao"]
    CORES = {"Amarelo": "#FFFF00", "Verde": "#00FF00", "Vermelho": "#FF0000"}

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

        titulo = QLabel("Controle de Pedidos")
        titulo.setObjectName("pageTitle")
        card_layout.addWidget(titulo)

        linha_top = QHBoxLayout()
        linha_top.setSpacing(8)

        btn_adicionar = QPushButton("Adicionar")
        btn_adicionar.setObjectName("btnPrimary")
        btn_adicionar.setFixedHeight(34)
        btn_adicionar.clicked.connect(self._adicionar_linha)
        linha_top.addWidget(btn_adicionar)

        btn_remover = QPushButton("Remover")
        btn_remover.setObjectName("btnDanger")
        btn_remover.setFixedHeight(34)
        btn_remover.clicked.connect(self._remover_linha)
        linha_top.addWidget(btn_remover)

        linha_top.addStretch()

        card_layout.addLayout(linha_top)

        info_linha = QHBoxLayout()
        info_linha.setSpacing(16)
        info_linha.addStretch()
        self.label_contador = QLabel("0 itens")
        self.label_contador.setObjectName("statusLabel")
        info_linha.addWidget(self.label_contador)
        card_layout.addLayout(info_linha)

        self.tabela = QTableWidget(0, len(self.COLUNAS))
        self.tabela.setStyleSheet(
            "QTableWidget::item:focus { outline: none; border: none; border-bottom: 1px solid #999; }"
        )
        self.tabela.setHorizontalHeaderLabels(self.COLUNAS)
        header = self.tabela.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(0, 75) #data
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(1, 120) #fornecedores
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(2, 120) #nome
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(3, 100) #requisição
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(4, 100) #dpp      
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(5, 75) #observação    
        self.tabela.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabela.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.tabela.setEditTriggers(QAbstractItemView.EditTrigger.CurrentChanged)
        self.tabela.setAlternatingRowColors(False)
        self.tabela.verticalHeader().setDefaultSectionSize(36)
        self.tabela.verticalHeader().setMinimumSectionSize(28)
        self.tabela.verticalHeader().setVisible(False)
        self.tabela.setItemDelegate(EditorDelegate(self.tabela))
        self.tabela.itemChanged.connect(self._item_modificado)
        self.tabela.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tabela.customContextMenuRequested.connect(self._context_menu)
        card_layout.addWidget(self.tabela)

        layout.addWidget(card)

    def _carregar_dados(self):
        try:
            with open(_caminho_json(), "r", encoding="utf-8") as f:
                self.dados = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.dados = []
        for item in self.dados:
            item.setdefault("cor", "")
        self._popular_tabela()

    def _popular_tabela(self):
        self.tabela.blockSignals(True)
        self.tabela.setRowCount(0)
        for item in self.dados:
            row = self.tabela.rowCount()
            self.tabela.insertRow(row)
            cor_nome = item.get("cor", "")
            cor_hex = self.CORES.get(cor_nome, "")
            for col, chave in enumerate(self.CHAVES):
                valor = str(item.get(chave, ""))
                cell = QTableWidgetItem(valor)
                cell.setFlags(cell.flags() | Qt.ItemFlag.ItemIsEditable)
                if cor_hex and col == 4:
                    cell.setData(Qt.BackgroundRole, QBrush(QColor(cor_hex)))
                self.tabela.setItem(row, col, cell)
        self._inserir_linha_vazia()
        self.tabela.blockSignals(False)
        self._atualizar_contador()

    def _inserir_linha_vazia(self):
        row = self.tabela.rowCount()
        self.tabela.insertRow(row)
        for col in range(len(self.COLUNAS)):
            cell = QTableWidgetItem("")
            cell.setFlags(cell.flags() | Qt.ItemFlag.ItemIsEditable)
            self.tabela.setItem(row, col, cell)

    def _atualizar_contador(self):
        total = len(self.dados)
        self.label_contador.setText(f"{total} itens")

    def _adicionar_linha(self):
        item = {chave: "" for chave in self.CHAVES}
        item["cor"] = ""
        self.dados.append(item)
        self._salvar_json()
        self._popular_tabela()
        self.tabela.selectRow(self.tabela.rowCount() - 2)

    def _remover_linha(self):
        selected_rows = self.tabela.selectionModel().selectedRows()
        if not selected_rows:
            return
        indices = sorted(set(index.row() for index in selected_rows), reverse=True)
        removidos = False
        for row in indices:
            if 0 <= row < len(self.dados):
                self.dados.pop(row)
                removidos = True
        if removidos:
            self._salvar_json()
        self._popular_tabela()

    def _context_menu(self, pos):
        item = self.tabela.itemAt(pos)
        if not item:
            return
        col = item.column()
        if col != 4:
            return
        row = item.row()
        if row >= len(self.dados):
            return
        menu = QMenu(self)
        for nome, hex_cor in self.CORES.items():
            pix = self._color_pixmap(hex_cor)
            acao = menu.addAction(pix, nome)
            acao.triggered.connect(lambda checked, n=nome, r=row: self._aplicar_cor(r, n))
        menu.exec(QCursor.pos())

    def _color_pixmap(self, hex_cor):
        from PySide6.QtGui import QPixmap, QPainter
        pix = QPixmap(16, 16)
        pix.fill(QColor(hex_cor))
        return pix

    def _aplicar_cor(self, row, nome_cor):
        if self.dados[row].get("cor") == nome_cor:
            nome_cor = ""
        self.dados[row]["cor"] = nome_cor
        self._salvar_json()
        self._popular_tabela()

    def _item_modificado(self, item):
        row = item.row()
        col = item.column()
        chave = self.CHAVES[col]

        if row == len(self.dados):
            texto = item.text().strip()
            if texto:
                novo_item = {}
                for c, ch in enumerate(self.CHAVES):
                    celula = self.tabela.item(row, c)
                    valor = celula.text().strip() if celula else ""
                    novo_item[ch] = valor
                novo_item["cor"] = ""
                self.dados.append(novo_item)
                self._salvar_json()
                self.tabela.blockSignals(True)
                self.tabela.insertRow(row + 1)
                for c in range(len(self.COLUNAS)):
                    celula = QTableWidgetItem("")
                    celula.setFlags(celula.flags() | Qt.ItemFlag.ItemIsEditable)
                    self.tabela.setItem(row + 1, c, celula)
                self.tabela.blockSignals(False)
                self._atualizar_contador()
        elif 0 <= row < len(self.dados):
            self.dados[row][chave] = item.text()
            self._salvar_json()

    def _salvar_json(self):
        try:
            os.makedirs(os.path.dirname(_caminho_json()), exist_ok=True)
            with open(_caminho_json(), "w", encoding="utf-8") as f:
                json.dump(self.dados, f, ensure_ascii=False, indent=2)
        except OSError:
            pass
