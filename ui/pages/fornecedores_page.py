import json
import os
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QStyledItemDelegate, QInputDialog,
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor, QBrush, QShortcut, QKeySequence


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
        super().paint(painter, option, index)

    def sizeHint(self, option, index):
        base = super().sizeHint(option, index)
        return QSize(base.width(), max(base.height(), 34))

    def createEditor(self, parent, option, index):
        editor = super().createEditor(parent, option, index)
        try:
            from PySide6.QtWidgets import QLineEdit
            if isinstance(editor, QLineEdit):
                editor.setMinimumHeight(34)
                editor.setStyleSheet("padding: 4px 8px; border: none; border-bottom: 1px solid #999; border-radius: 0px;")
        except Exception:
            pass
        return editor


def _caminho_json():
    import config
    base = config.obter_caminho_jsons()
    if not base:
        return ""
    return os.path.normpath(os.path.join(base, "Almox", "Fornecedores", "fornecedores.json"))


class FornecedoresPage(QWidget):
    COLUNAS = ["Índice", "Fornecedor", "Email", "Telefone", "DUNS"]
    CHAVES = ["indice", "fornecedor", "email", "telefone", "duns"]

    def __init__(self):
        super().__init__()
        self.dados = []
        self._setup_ui()
        self._setup_search_shortcuts()
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

        titulo = QLabel("Fornecedores")
        titulo.setObjectName("pageTitle")
        card_layout.addWidget(titulo)

        linha_top = QHBoxLayout()
        linha_top.setSpacing(8)

        btn_editar = QPushButton("Editar")
        btn_editar.setObjectName("btnPrimary")
        btn_editar.setFixedHeight(34)
        btn_editar.clicked.connect(self._editar_linha)
        linha_top.addWidget(btn_editar)

        btn_excluir = QPushButton("Excluir")
        btn_excluir.setObjectName("btnDanger")
        btn_excluir.setFixedHeight(34)
        btn_excluir.clicked.connect(self._remover_linha)
        linha_top.addWidget(btn_excluir)

        linha_top.addStretch()

        self.campo_busca = QLineEdit()
        self.campo_busca.setPlaceholderText("Pesquisar...")
        self.campo_busca.setFixedHeight(30)
        self.campo_busca.setFixedWidth(200)
        self.campo_busca.textChanged.connect(self._aplicar_filtro)
        linha_top.addWidget(self.campo_busca)
        card_layout.addLayout(linha_top)

        info_linha = QHBoxLayout()
        info_linha.addStretch()
        self.label_contador = QLabel("0 fornecedores")
        self.label_contador.setObjectName("statusLabel")
        info_linha.addWidget(self.label_contador)
        card_layout.addLayout(info_linha)

        self.tabela = QTableWidget(0, len(self.COLUNAS))
        self.tabela.setHorizontalHeaderLabels(self.COLUNAS)
        header = self.tabela.horizontalHeader()
        header.setStretchLastSection(True)
        # set some reasonable column widths
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(0, 70)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(2, 220)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(3, 120)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(4, 100)

        # não mostrar a coluna de índice na tabela
        self.tabela.setColumnHidden(0, True)

        self.tabela.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabela.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tabela.setEditTriggers(QAbstractItemView.EditTrigger.CurrentChanged)
        self.tabela.verticalHeader().setDefaultSectionSize(36)
        self.tabela.verticalHeader().setVisible(False)
        self.tabela.setItemDelegate(EditorDelegate(self.tabela))
        self.tabela.itemChanged.connect(self._item_modificado)

        card_layout.addWidget(self.tabela)
        layout.addWidget(card)

    def _carregar_dados(self):
        try:
            with open(_caminho_json(), "r", encoding="utf-8") as f:
                self.dados = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.dados = []
        self.dados.sort(key=lambda x: x.get("fornecedor", "").strip().lower())
        self._popular_tabela()

    def _setup_search_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+F"), self, self._buscar_item)
        QShortcut(QKeySequence("Ctrl+L"), self, self._buscar_item)

    def _buscar_item(self):
        texto, ok = QInputDialog.getText(self, "Pesquisar", "Digite o texto para buscar:")
        if not ok or not texto.strip():
            return
        busca = texto.strip().lower()
        for row in range(self.tabela.rowCount()):
            for col in range(self.tabela.columnCount()):
                item = self.tabela.item(row, col)
                if item and busca in item.text().lower():
                    self.tabela.selectRow(row)
                    self.tabela.scrollToItem(item)
                    return
        msg = QLabel("Texto não encontrado!", self)
        msg.setStyleSheet("background-color: #f8d7da; color: #721c24; padding: 8px 16px; border-radius: 4px;")
        msg.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg.adjustSize()
        parent_rect = self.rect()
        msg.move((parent_rect.width() - msg.width()) // 2, (parent_rect.height() - msg.height()) // 2)
        msg.show()
        from PySide6.QtCore import QTimer
        QTimer.singleShot(2000, msg.close)

    def _aplicar_filtro(self):
        self._popular_tabela()

    def _popular_tabela(self):
        self.tabela.blockSignals(True)
        self.tabela.setRowCount(0)
        filtro = self.campo_busca.text().strip().lower()
        for item in self.dados:
            if filtro:
                texto = " ".join(str(v) for v in item.values()).lower()
                if filtro not in texto:
                    continue
            row = self.tabela.rowCount()
            self.tabela.insertRow(row)
            for col, chave in enumerate(self.CHAVES):
                valor = str(item.get(chave, ""))
                cell = QTableWidgetItem(valor)
                # índice não editável
                if col == 0:
                    cell.setFlags(cell.flags() & ~Qt.ItemFlag.ItemIsEditable)
                else:
                    cell.setFlags(cell.flags() | Qt.ItemFlag.ItemIsEditable)
                self.tabela.setItem(row, col, cell)
        self._inserir_linha_vazia()
        self.tabela.blockSignals(False)
        self._atualizar_contador()

    def _inserir_linha_vazia(self):
        row = self.tabela.rowCount()
        self.tabela.insertRow(row)
        for col in range(len(self.COLUNAS)):
            cell = QTableWidgetItem("")
            if col == 0:
                # índice vazio até salvar
                cell.setFlags(cell.flags() & ~Qt.ItemFlag.ItemIsEditable)
            else:
                cell.setFlags(cell.flags() | Qt.ItemFlag.ItemIsEditable)
            self.tabela.setItem(row, col, cell)

    def _atualizar_contador(self):
        total = len(self.dados)
        self.label_contador.setText(f"{total} fornecedores")

    def _editar_linha(self):
        selected = self.tabela.selectionModel().selectedRows()
        if not selected:
            return
        row = selected[0].row()
        if row >= self.tabela.rowCount():
            return
        # start editing the first cell in the selected row
        self.tabela.setCurrentCell(row, 0)
        self.tabela.editItem(self.tabela.item(row, 0))

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

    def _item_modificado(self, item):
        row = item.row()
        col = item.column()

        if row == len(self.dados):
            texto = item.text().strip()
            if texto:
                novo_item = {}
                for c, ch in enumerate(self.CHAVES):
                    celula = self.tabela.item(row, c)
                    valor = celula.text().strip() if celula else ""
                    novo_item[ch] = valor
                # atribui índice incremental único
                novo_item["indice"] = self._next_indice()
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
            chave = self.CHAVES[col]
            self.dados[row][chave] = item.text()
            self._salvar_json()

    def _salvar_json(self):
        caminho = _caminho_json()
        if not caminho:
            import config
            config.avisar_sem_pasta(self)
            return
        try:
            os.makedirs(os.path.dirname(caminho), exist_ok=True)
            with open(caminho, "w", encoding="utf-8") as f:
                json.dump(self.dados, f, ensure_ascii=False, indent=2)
        except OSError:
            pass

    def _next_indice(self):
        max_id = 0
        for d in self.dados:
            try:
                v = int(d.get("indice", 0) or 0)
                if v > max_id:
                    max_id = v
            except Exception:
                continue
        return max_id + 1
