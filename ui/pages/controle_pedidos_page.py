import json
import os
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QStyledItemDelegate, QMenu, QInputDialog,
    QDialog, QDialogButtonBox, QComboBox,
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor, QBrush, QPainter, QPalette, QCursor, QShortcut, QKeySequence


def _caminho_fornecedores_json():
    import config
    base = config.obter_caminho_jsons()
    if not base:
        base = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "jsons")
    return os.path.normpath(os.path.join(base, "Almox", "Fornecedores", "fornecedores.json"))


def _carregar_fornecedores():
    try:
        with open(_caminho_fornecedores_json(), "r", encoding="utf-8") as f:
            dados = json.load(f)
        return [item.get("fornecedor", "") for item in dados if item.get("fornecedor")]
    except (FileNotFoundError, json.JSONDecodeError):
        return []


class EditorDelegate(QStyledItemDelegate):
    def __init__(self, parent=None, fornecedores=None):
        super().__init__(parent)
        self.fornecedores = fornecedores or []

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
        if index.column() == 1 and self.fornecedores:
            editor = QComboBox(parent)
            editor.setEditable(True)
            editor.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
            editor.addItems(self.fornecedores)
            editor.setMinimumHeight(34)
            editor.lineEdit().setStyleSheet("padding: 0px; border: none; border-radius: 0px;")
            editor.setStyleSheet(
                "QComboBox { padding: 0px; border: none; border-radius: 0px; }"
                "QComboBox::drop-down { width: 0px; border: none; background: transparent; }"
            )
            return editor
        editor = super().createEditor(parent, option, index)
        if isinstance(editor, QLineEdit):
            editor.setMinimumHeight(34)
            editor.setStyleSheet("border: none; border-bottom: 1px solid #999; border-radius: 0px;")
        return editor

    def setModelData(self, editor, model, index):
        super().setModelData(editor, model, index)
        row = index.row()
        col = index.column()
        if isinstance(editor, QComboBox):
            value = editor.currentText().strip()
        else:
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


def _caminho_pedidos_pendentes():
    import config
    base = config.obter_caminho_jsons()
    if not base:
        base = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "jsons")
    return os.path.normpath(os.path.join(base, "Almox", "ControlePedidos", "PedidosPendentes", "PedidosPendentes.json"))

def _caminho_pedidos_entregues():
    import config
    from datetime import datetime
    ano = datetime.now().strftime("%Y")
    nome_arquivo = f"ControlePedidosEntregues{ano}"
    base = config.obter_caminho_jsons()
    if not base:
        base = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "jsons")
    return os.path.normpath(os.path.join(base, "Almox", "ControlePedidos", f"{nome_arquivo}.json"))


class ControlePedidosPage(QWidget):
    COLUNAS = ["Data", "Fornecedores", "Nome", "Requisição", "DPP", "Observação"]
    CHAVES = ["data", "fornecedores", "nome", "requisicao", "dpp", "observacao"]
    CORES = {"Amarelo": "#FFFF00", "Verde": "#00FF00", "Vermelho": "#FF0000"}

    def __init__(self):
        super().__init__()
        self.dados = []
        self.lista_fornecedores = _carregar_fornecedores()
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

        btn_adicionar = QPushButton("Atualizar")
        btn_adicionar.setObjectName("btnPrimary")
        btn_adicionar.setFixedHeight(34)
        btn_adicionar.clicked.connect(self._adicionar_linha)
        linha_top.addWidget(btn_adicionar)

        btn_entregar = QPushButton("Entregar")
        btn_entregar.setObjectName("btnPrimary")
        btn_entregar.setFixedHeight(34)
        btn_entregar.clicked.connect(self._entregar_item)
        linha_top.addWidget(btn_entregar)

        btn_remover = QPushButton("Remover")
        btn_remover.setObjectName("btnDanger")
        btn_remover.setFixedHeight(34)
        btn_remover.clicked.connect(self._remover_linha)
        linha_top.addWidget(btn_remover)

        linha_top.addStretch()

        self.label_contador = QLabel("0 itens")
        self.label_contador.setObjectName("statusLabel")
        linha_top.addWidget(self.label_contador)

        card_layout.addLayout(linha_top)

        self.tabela = QTableWidget(0, len(self.COLUNAS))
        self.tabela.setStyleSheet(
            "QTableWidget::item:focus { outline: none; border: none; border-bottom: 1px solid #999; }"
        )
        self.tabela.setHorizontalHeaderLabels(self.COLUNAS)
        header = self.tabela.horizontalHeader()
        header.setStyleSheet(
            "QHeaderView::section {"
            "  font-size: 9px;"
            "  font-weight: 600;"
            "  background-color: #f8fafc;"
            "  color: #64748b;"
            "  text-transform: uppercase;"
            "  letter-spacing: 0.5px;"
            "  padding: 8px 12px;"
            "  border: none;"
            "  border-bottom: 2px solid #e2e8f0;"
            "}"
        )
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
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        self.tabela.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabela.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.tabela.setEditTriggers(QAbstractItemView.EditTrigger.CurrentChanged)
        self.tabela.setAlternatingRowColors(False)
        self.tabela.verticalHeader().setDefaultSectionSize(36)
        self.tabela.verticalHeader().setMinimumSectionSize(28)
        self.tabela.verticalHeader().setVisible(False)
        self.tabela.setItemDelegate(EditorDelegate(self.tabela, self.lista_fornecedores))
        self.tabela.itemChanged.connect(self._item_modificado)
        self.tabela.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tabela.customContextMenuRequested.connect(self._context_menu)
        card_layout.addWidget(self.tabela)

        QShortcut(QKeySequence("Ctrl+F"), self, self._buscar_item)
        QShortcut(QKeySequence("Ctrl+L"), self, self._buscar_item)

        layout.addWidget(card)

    def _carregar_dados(self):
        try:
            with open(_caminho_json(), "r", encoding="utf-8") as f:
                self.dados = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.dados = []
        for item in self.dados:
            item.setdefault("cor", "")
            item.setdefault("status", "")
        self._popular_tabela()

    def _extrair_codigo_pedido(self, nome):
        """Extrai o código PC do nome (ex: 'PC16971 - Esofer' -> 'PC16971')"""
        if not nome:
            return nome
        partes = nome.split(" ")
        return partes[0].strip()

    def _carregar_pedidos_pendentes(self):
        """Carrega os dados de pedidos pendentes"""
        try:
            caminho = _caminho_pedidos_pendentes()
            if os.path.exists(caminho):
                with open(caminho, "r", encoding="utf-8") as f:
                    return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        return []

    def _verificar_status_pedidos(self):
        """Verifica o status dos pedidos com base em pedidos pendentes"""
        pedidos_pendentes = self._carregar_pedidos_pendentes()
        
        # Extrair números de pedidos pendentes da coluna "N do pedido"
        pedidos_pendentes_nums = set()
        for item in pedidos_pendentes:
            if isinstance(item, dict):
                n_pedido = item.get("N do pedido", "").strip()
                if n_pedido:
                    pedidos_pendentes_nums.add(n_pedido)
        
        # Verificar cada pedido no controle
        for item in self.dados:
            if not isinstance(item, dict):
                continue
            nome = item.get("nome", "").strip()
            if not nome:
                continue
            
            # Se o nome não começa com "PC", ignorar
            if not nome.startswith("PC"):
                continue
            
            # Pega o código antes do primeiro espaço (ex: "PC17004 - Spot" -> "PC17004")
            codigo = nome.split(" ")[0].strip()
            
            # Se EXISTE nos pedidos pendentes, não faz nada
            if codigo in pedidos_pendentes_nums:
                continue
            
            # Se NÃO existe nos pedidos pendentes, marcar como "Entregue"
            item["status"] = "Entregue"

    def _popular_tabela(self):
        self.tabela.blockSignals(True)
        self.tabela.setRowCount(0)
        for item in self.dados:
            row = self.tabela.rowCount()
            self.tabela.insertRow(row)
            cor_nome = item.get("cor", "")
            cor_hex = self.CORES.get(cor_nome, "")
            status_val = item.get("status", "")
            for col, chave in enumerate(self.CHAVES):
                valor = str(item.get(chave, ""))
                cell = QTableWidgetItem(valor)
                cell.setFlags(cell.flags() | Qt.ItemFlag.ItemIsEditable)
                if status_val == "Entregue":
                    cell.setData(Qt.BackgroundRole, QBrush(QColor("#C8E6C9")))
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
        self._buscar_nos_arquivos(busca)

    def _buscar_nos_arquivos(self, busca):
        from datetime import datetime
        ano_atual = int(datetime.now().strftime("%Y"))
        import config
        base = config.obter_caminho_jsons()
        if not base:
            base = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "jsons")
        for ano in range(ano_atual, 2023, -1):
            caminho = os.path.normpath(os.path.join(base, "Almox", "ControlePedidos", f"ControlePedidosEntregues{ano}.json"))
            try:
                with open(caminho, "r", encoding="utf-8") as f:
                    dados = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                continue
            for item in dados:
                if any(busca in str(v).lower() for v in item.values()):
                    self._exibir_item_encontrado(item, ano)
                    return
        self._mostrar_nao_encontrado()

    def _exibir_item_encontrado(self, item, ano):
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Item encontrado em ControlePedidosEntregues{ano}")
        dialog.setMinimumWidth(int(self.width() * 0.9))
        dialog.setMinimumHeight(200)
        layout = QVBoxLayout(dialog)
        layout.setSpacing(12)
        tabela = QTableWidget(1, len(self.COLUNAS))
        tabela.setHorizontalHeaderLabels(self.COLUNAS)
        for col, chave in enumerate(self.CHAVES):
            celula = QTableWidgetItem(str(item.get(chave, "")))
            celula.setFlags(celula.flags() & ~Qt.ItemFlag.ItemIsEditable)
            tabela.setItem(0, col, celula)
        header = tabela.horizontalHeader()
        header.setStretchLastSection(True)
        header.setStyleSheet(
            "QHeaderView::section {"
            "  font-size: 9px; font-weight: 600;"
            "  background-color: #f8fafc; color: #64748b;"
            "  text-transform: uppercase; letter-spacing: 0.5px;"
            "  padding: 8px 12px; border: none; border-bottom: 2px solid #e2e8f0;"
            "}"
        )
        for i in range(len(self.COLUNAS) - 1):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        tabela.verticalHeader().setVisible(False)
        tabela.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        tabela.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        layout.addWidget(tabela)
        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        btn_box.accepted.connect(dialog.accept)
        layout.addWidget(btn_box)
        dialog.exec()

    def _mostrar_nao_encontrado(self):
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

    def _salvar_pedidos_entregues(self):
        entregues = [item for item in self.dados if item.get("status") == "Entregue"]
        if not entregues:
            return
        caminho = _caminho_pedidos_entregues()
        try:
            os.makedirs(os.path.dirname(caminho), exist_ok=True)
            with open(caminho, "r", encoding="utf-8") as f:
                existentes = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            existentes = []
        ids_existentes = set()
        for item in existentes:
            chave = (item.get("nome", ""), item.get("data", ""))
            ids_existentes.add(chave)
        for item in entregues:
            chave = (item.get("nome", ""), item.get("data", ""))
            if chave not in ids_existentes:
                existentes.append(item)
                ids_existentes.add(chave)
        try:
            with open(caminho, "w", encoding="utf-8") as f:
                json.dump(existentes, f, ensure_ascii=False, indent=2)
        except OSError:
            pass
        self.dados = [item for item in self.dados if item.get("status") != "Entregue"]

    def _adicionar_linha(self):
        self._salvar_pedidos_entregues()
        self._verificar_status_pedidos()
        self._salvar_json()
        self._popular_tabela()
        self.tabela.selectRow(self.tabela.rowCount() - 2)

    def _entregar_item(self):
        selected_rows = self.tabela.selectionModel().selectedRows()
        if not selected_rows:
            return
        indices = sorted(set(index.row() for index in selected_rows), reverse=True)
        for row in indices:
            if 0 <= row < len(self.dados):
                status_atual = self.dados[row].get("status", "")
                self.dados[row]["status"] = "Em andamento" if status_atual == "Entregue" else "Entregue"
        self._salvar_json()
        self._popular_tabela()

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

    def _auto_preencher_nome(self, row):
        nome_anterior = self.dados[row - 1].get("nome", "").strip()
        if not nome_anterior.startswith("PC"):
            return
        codigo = nome_anterior.split(" ")[0].strip()
        import re
        match = re.match(r"PC(\d+)", codigo)
        if not match:
            return
        numero = int(match.group(1)) + 1
        novo_nome = f"PC{numero}"
        self.dados[row]["nome"] = novo_nome
        self.tabela.blockSignals(True)
        celula_nome = self.tabela.item(row, 2)
        if celula_nome:
            celula_nome.setText(novo_nome)
        self.tabela.blockSignals(False)

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
                novo_item["status"] = "Em andamento"
                self.dados.append(novo_item)
                if chave == "requisicao" and row > 0:
                    self._auto_preencher_nome(row)
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
            old_val = self.dados[row].get(chave, "")
            self.dados[row][chave] = item.text()
            if chave == "requisicao" and not old_val and item.text().strip() and row > 0:
                self._auto_preencher_nome(row)
            self._salvar_json()

    def _salvar_json(self):
        try:
            os.makedirs(os.path.dirname(_caminho_json()), exist_ok=True)
            with open(_caminho_json(), "w", encoding="utf-8") as f:
                json.dump(self.dados, f, ensure_ascii=False, indent=2)
        except OSError:
            pass
