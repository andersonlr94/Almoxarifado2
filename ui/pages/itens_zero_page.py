import json
import os

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QStyledItemDelegate, QStyleOptionViewItem,
    QStyle,
)
from PySide6.QtCore import Qt, QSize, QRect, Signal, QMimeData
from PySide6.QtGui import QPainter, QMouseEvent, QGuiApplication, QColor, QBrush, QPalette, QDrag, QKeySequence


class TabelaReordenavel(QTableWidget):
    ordemAlterada = Signal(int, int)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.setDropIndicatorShown(True)
        self.setDefaultDropAction(Qt.MoveAction)
        self._origem_drag = None

    def dragEnterEvent(self, event):
        event.acceptProposedAction()

    def dragMoveEvent(self, event):
        event.acceptProposedAction()

    def startDrag(self, actions):
        rows = set(index.row() for index in self.selectionModel().selectedIndexes())
        if not rows:
            return
        self._origem_drag = min(rows)
        mime = QMimeData()
        mime.setText(f"row:{self._origem_drag}")
        drag = QDrag(self)
        drag.setMimeData(mime)
        if self.columnCount() > 0:
            rect = self.visualRect(self.model().index(self._origem_drag, 0))
            if rect.isValid():
                pixmap = self.viewport().grab(QRect(
                    0, rect.y(), self.viewport().width(), rect.height()
                ))
                drag.setPixmap(pixmap)
        drag.exec(Qt.MoveAction)

    def dropEvent(self, event):
        if self._origem_drag is None:
            event.ignore()
            return
        pos = event.position().toPoint()
        target_row = self.rowAt(pos.y())
        if target_row < 0:
            target_row = self.rowCount() - 1
        origem = self._origem_drag
        self._origem_drag = None
        event.setDropAction(Qt.MoveAction)
        event.accept()
        self.ordemAlterada.emit(origem, target_row)

    def keyPressEvent(self, event):
        if event.matches(QKeySequence.StandardKey.Copy):
            index = self.currentIndex()
            if index.isValid():
                texto = index.data(Qt.DisplayRole)
                if texto:
                    QGuiApplication.clipboard().setText(str(texto))
            return
        super().keyPressEvent(event)


class EditorDelegate(QStyledItemDelegate):
    def __init__(self, parent=None, chaves=None):
        super().__init__(parent)
        self._chaves = chaves or []

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
            editor.setStyleSheet("padding: 4px 8px;")
            col = index.column()
            if col < len(self._chaves) and self._chaves[col] not in ("dpp", "observacao"):
                editor.setReadOnly(True)
        return editor


def _caminho_json():
    import config
    base = config.obter_caminho_jsons()
    if not base:
        base = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "jsons")
    return os.path.normpath(os.path.join(base, "Almox", "ItensZero", "itensZero.json"))


def _caminho_itens_almoxarifado_json():
    import config
    base = config.obter_caminho_jsons()
    if not base:
        base = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "jsons")
    return os.path.normpath(os.path.join(base, "Almox", "ItensAlmoxarifado", "ItensAlmoxarifado.json"))


class ItensZeroPage(QWidget):
    COLUNAS = ["Kardex", "Código", "Descrição", "Cons Med", "Qtde prog", "DPP", "Observação"]
    CHAVES = ["kardex", "codigo", "descricao", "consumo_medio", "qtde_prog", "dpp", "observacao"]
    CORES = {
        "branco": "#FFFFFF",
        "azul": "#B3D9FF",
        "verde": "#B3FFB3",
        "amarelo": "#FFFFB3",
        "vermelho": "#FFB3B3",
    }

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

        titulo = QLabel("Itens com estoque zero")
        titulo.setObjectName("pageTitle")
        card_layout.addWidget(titulo)

        linha_top = QHBoxLayout()
        linha_top.setSpacing(8)

        btn_colar = QPushButton("Colar")
        btn_colar.setObjectName("btnPrimary")
        btn_colar.setFixedHeight(34)
        btn_colar.clicked.connect(self._colar)
        linha_top.addWidget(btn_colar)

        btn_sincronizar = QPushButton("Atualizar")
        btn_sincronizar.setObjectName("btnPrimary")
        btn_sincronizar.setFixedHeight(34)
        btn_sincronizar.clicked.connect(self._sincronizar)
        linha_top.addWidget(btn_sincronizar)

        linha_top.addStretch()

        for nome, hex_cor in self.CORES.items():
            btn = QPushButton()
            btn.setFixedSize(28, 28)
            btn.setStyleSheet(
                f"background-color: {hex_cor}; border: 1px solid #999; border-radius: 4px;"
            )
            btn.setToolTip(nome.capitalize())
            btn.clicked.connect(lambda checked, c=nome: self._aplicar_cor(c))
            linha_top.addWidget(btn)

        btn_sobe = QPushButton("▲")
        btn_sobe.setFixedSize(28, 28)
        btn_sobe.setToolTip("Mover para cima")
        btn_sobe.clicked.connect(lambda: self._mover_linha(-1))
        linha_top.addWidget(btn_sobe)

        btn_desce = QPushButton("▼")
        btn_desce.setFixedSize(28, 28)
        btn_desce.setToolTip("Mover para baixo")
        btn_desce.clicked.connect(lambda: self._mover_linha(1))
        linha_top.addWidget(btn_desce)

        card_layout.addLayout(linha_top)

        info_linha = QHBoxLayout()
        info_linha.setSpacing(16)
        info_linha.addStretch()
        self.label_contador = QLabel("0 itens")
        self.label_contador.setObjectName("statusLabel")
        info_linha.addWidget(self.label_contador)
        card_layout.addLayout(info_linha)

        self.tabela = TabelaReordenavel(0, len(self.COLUNAS))
        self.tabela.setHorizontalHeaderLabels(self.COLUNAS)
        header = self.tabela.horizontalHeader()
        header.setStretchLastSection(True)
        for c in range(self.tabela.columnCount()):
            header.setSectionResizeMode(c, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(0, 140)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(1, 140)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(3, 80)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(4, 80)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(5, 80)
        self.tabela.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabela.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.tabela.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked)
        self.tabela.setAlternatingRowColors(False)
        self.tabela.verticalHeader().setDefaultSectionSize(36)
        self.tabela.verticalHeader().setMinimumSectionSize(28)
        self.tabela.verticalHeader().setVisible(False)
        self.tabela.setItemDelegate(EditorDelegate(self.tabela, self.CHAVES))
        self.tabela.itemChanged.connect(self._item_modificado)
        self.tabela.ordemAlterada.connect(self._sincronizar_ordem)
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
        for item in self.dados:
            row = self.tabela.rowCount()
            self.tabela.insertRow(row)
            cor = item.get("cor", "")
            cor_hex = self.CORES.get(cor, "")
            for col, chave in enumerate(self.CHAVES):
                valor = str(item.get(chave, ""))
                cell = QTableWidgetItem(valor)
                cell.setFlags(cell.flags() | Qt.ItemFlag.ItemIsEditable)
                if cor_hex:
                    cell.setData(Qt.BackgroundRole, QBrush(QColor(cor_hex)))
                self.tabela.setItem(row, col, cell)
        self.tabela.blockSignals(False)
        self._atualizar_contador()

    def _aplicar_cor(self, nome_cor):
        selection_model = self.tabela.selectionModel()
        selected_rows = selection_model.selectedRows()
        if not selected_rows:
            return
        indices_modificados = set()
        for index in selected_rows:
            row = index.row()
            kardex_item = self.tabela.item(row, 0)
            if not kardex_item:
                continue
            for i, dado in enumerate(self.dados):
                if dado.get("kardex") == kardex_item.text():
                    self.dados[i]["cor"] = nome_cor
                    indices_modificados.add(i)
                    break
        if indices_modificados:
            self._salvar_json()
            self._popular_tabela()

    def _mover_linha(self, direcao):
        selection_model = self.tabela.selectionModel()
        selected_rows = selection_model.selectedRows()
        if not selected_rows:
            return
        row = selected_rows[0].row()
        nova_row = row + direcao
        if nova_row < 0 or nova_row >= len(self.dados):
            return
        self.dados[row], self.dados[nova_row] = self.dados[nova_row], self.dados[row]
        self._salvar_json()
        self._popular_tabela()
        self.tabela.selectRow(nova_row)
        self._atualizar_contador()

    def _atualizar_contador(self):
        total = self.tabela.rowCount()
        self.label_contador.setText(f"{total} itens")

    def _sincronizar_ordem(self, origem, destino):
        if origem == destino:
            return
        item = self.dados.pop(origem)
        self.dados.insert(destino, item)
        self._salvar_json()
        self._popular_tabela()
        self.tabela.selectRow(destino)

    def _colar(self):
        clipboard = QGuiApplication.clipboard()
        texto = clipboard.text()
        if not texto.strip():
            return

        linhas = texto.strip().split("\n")
        novos_kardex = set()
        novos_itens = []

        for linha in linhas:
            partes = linha.strip().split("\t")
            if len(partes) < 11:
                continue
            kardex = partes[1].strip()
            if not kardex:
                continue
            novos_kardex.add(kardex)
            item = {
                "kardex": kardex,
                "codigo": partes[2].strip(),
                "descricao": partes[3].strip(),
                "consumo_medio": partes[7].strip(),
                "qtde_prog": partes[9].strip(),
                "dpp": "",
                "observacao": "",
                "cor": "",
            }
            novos_itens.append(item)

        self.dados = [d for d in self.dados if d.get("kardex") in novos_kardex]

        kardex_existentes = {d.get("kardex") for d in self.dados}
        for item in novos_itens:
            if item["kardex"] not in kardex_existentes:
                self.dados.append(item)
                kardex_existentes.add(item["kardex"])

        self._salvar_json()
        self._popular_tabela()

    def _sincronizar(self):
        try:
            with open(_caminho_itens_almoxarifado_json(), "r", encoding="utf-8") as f:
                itens_almox = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            itens_almox = []

        kardex_zero = set()
        novos_itens = []

        for item in itens_almox:
            try:
                # Formato brasileiro: 1.800,00 -> remove ponto (milhar) e substitui vírgula por ponto
                qtde_novo_str = str(item.get("Qtde novo", "0")).replace(".", "").replace(",", ".")
                qtde_retorno_str = str(item.get("Qtde retorno", "0")).replace(".", "").replace(",", ".")
                qtde_novo = float(qtde_novo_str)
                qtde_retorno = float(qtde_retorno_str)
            except (ValueError, TypeError):
                qtde_novo = 0.0
                qtde_retorno = 0.0
            
            if (
                qtde_novo == 0
                and qtde_retorno == 0
                and item.get("Item de estoque", "false") == "true"
                and item.get("Ativo/Obsol.", "").upper() == "ATIVO"
            ):
                kard = item.get("Kardex", "").strip()
                if not kard:
                    continue
                kardex_zero.add(kard)
                novos_itens.append({
                    "kardex": kard,
                    "codigo": item.get("Código", ""),
                    "descricao": item.get("Descrição", ""),
                    "consumo_medio": item.get("Consumo médio", ""),
                    "qtde_prog": item.get("Pend. entrega compras", ""),
                    "dpp": "",
                    "observacao": "",
                    "cor": "",
                })

        # Criar mapa para lookup dos novos dados
        mapa_novos = {item["kardex"]: item for item in novos_itens}

        # Manter apenas dados que ainda estão em kardex_zero
        self.dados = [
            d for d in self.dados if d.get("kardex") in kardex_zero
        ]

        # Atualizar campos nos itens existentes
        for dado in self.dados:
            kardex = dado.get("kardex")
            if kardex in mapa_novos:
                novo_item = mapa_novos[kardex]
                dado["codigo"] = novo_item["codigo"]
                dado["descricao"] = novo_item["descricao"]
                dado["consumo_medio"] = novo_item["consumo_medio"]
                dado["qtde_prog"] = novo_item["qtde_prog"]

        # Adicionar novos itens
        kardex_existentes = {d.get("kardex") for d in self.dados}
        for item in novos_itens:
            if item["kardex"] not in kardex_existentes:
                self.dados.append(item)

        self._salvar_json()
        self._popular_tabela()

    def _item_modificado(self, item):
        row = item.row()
        col = item.column()
        chave = self.CHAVES[col]
        if chave not in ("dpp", "observacao"):
            return
        kardex_item = self.tabela.item(row, 0)
        if not kardex_item:
            return
        for dado in self.dados:
            if dado.get("kardex") == kardex_item.text():
                dado[chave] = item.text()
                break
        self._salvar_json()

    def _salvar_json(self):
        try:
            os.makedirs(os.path.dirname(_caminho_json()), exist_ok=True)
            with open(_caminho_json(), "w", encoding="utf-8") as f:
                json.dump(self.dados, f, ensure_ascii=False, indent=2)
        except OSError:
            pass
