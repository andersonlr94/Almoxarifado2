import json
import os
from datetime import datetime
import urllib.parse
import webbrowser
import qtawesome

from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QStyledItemDelegate, QMenu, QInputDialog,
    QDialog, QDialogButtonBox, QComboBox, QPlainTextEdit,
)
from PySide6.QtCore import Qt, QSize, QTimer, QPoint
from PySide6.QtGui import QColor, QBrush, QPainter, QPalette, QCursor, QShortcut, QKeySequence


def _caminho_fornecedores_json():
    import config
    base = config.obter_caminho_jsons()
    if not base:
        return ""
    return os.path.normpath(os.path.join(base, "Almox", "Fornecedores", "fornecedores.json"))


def _carregar_fornecedores():
    try:
        with open(_caminho_fornecedores_json(), "r", encoding="utf-8") as f:
            dados = json.load(f)
        return [item.get("fornecedor", "") for item in dados if item.get("fornecedor")]
    except (FileNotFoundError, json.JSONDecodeError):
        return []


class EditorDelegate(QStyledItemDelegate):
    def __init__(self, parent=None, fornecedores=None, edit_mode_getter=None):
        super().__init__(parent)
        self.fornecedores = fornecedores or []
        self._edit_mode_getter = edit_mode_getter or (lambda: False)

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
        return QSize(base.width(), max(base.height(), 32))

    def createEditor(self, parent, option, index):
        if index.column() == 5:
            return None
        # Se o modo de edição global está ativo, pular as restrições de bloqueio
        if not self._edit_mode_getter():
            # Se já tem fornecedor preenchido, colunas 0-3 são somente leitura
            if index.column() in (0, 1, 2, 3):
                model = index.model()
                forn_index = model.index(index.row(), 1)
                forn_val = forn_index.data(Qt.DisplayRole)
                if forn_val and str(forn_val).strip():
                    return None
            # Se já tem DPP preenchido, coluna 4 é somente leitura
            if index.column() == 4:
                model = index.model()
                dpp_index = model.index(index.row(), 4)
                dpp_val = dpp_index.data(Qt.DisplayRole)
                if dpp_val and str(dpp_val).strip():
                    return None
        if index.column() == 1 and self.fornecedores:
            editor = QComboBox(parent)
            editor.setEditable(True)
            editor.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
            editor.addItems(self.fornecedores)
            editor.setFixedHeight(option.rect.height() - 6)
            editor.setMaximumWidth(option.rect.width())
            editor.setContentsMargins(0, 0, 0, 0)
            editor.lineEdit().setStyleSheet("padding: 0px; margin: 0px; border: none; border-radius: 0px;")
            editor.setStyleSheet(
                "QComboBox { padding: 0px; margin: 0px; border: none; border-radius: 0px; }"
                "QComboBox::drop-down { width: 0px; border: none; background: transparent; }"
            )
            return editor
        editor = super().createEditor(parent, option, index)
        if isinstance(editor, QLineEdit):
            editor.setFixedHeight(option.rect.height() - 6)
            editor.setMaximumWidth(option.rect.width())
            editor.setContentsMargins(0, 0, 0, 0)
            editor.setStyleSheet(
                "padding: 0px; margin: 0px; border: none; "
                "border-bottom: 2px solid #6366f1; border-radius: 0px;"
            )
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
        return ""
    return os.path.normpath(os.path.join(base, "Almox", "ControlePedidos", "controlePedidos.json"))


def _caminho_pedidos_pendentes():
    import config
    base = config.obter_caminho_jsons()
    if not base:
        return ""
    return os.path.normpath(os.path.join(base, "Almox", "ControlePedidos", "PedidosPendentes", "PedidosPendentes.json"))

def _caminho_pedidos_entregues():
    import config
    from datetime import datetime
    ano = datetime.now().strftime("%Y")
    nome_arquivo = f"ControlePedidosEntregues{ano}"
    base = config.obter_caminho_jsons()
    if not base:
        return ""
    return os.path.normpath(os.path.join(base, "Almox", "ControlePedidos", f"{nome_arquivo}.json"))


class ConfigEmailDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configurar Modelo de E-mail")
        self.setMinimumWidth(450)
        self.setMinimumHeight(350)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        info = QLabel(
            "Defina o modelo de mensagem para o novo e-mail.<br/>"
            "Use o termo <b>{DPP}</b> onde deseja inserir a data limite (DPP) do pedido."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #475569; font-size: 13px; line-height: 1.4;")
        layout.addWidget(info)

        self.txt_template = QPlainTextEdit()
        self.txt_template.setPlaceholderText("Escreva aqui o corpo do email...")
        self.txt_template.setStyleSheet("""
            QPlainTextEdit {
                background-color: #f8fafc;
                color: #1e293b;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                padding: 10px;
                font-size: 13px;
                font-family: inherit;
            }
            QPlainTextEdit:focus {
                border: 1px solid #3b82f6;
                background-color: #ffffff;
            }
        """)
        
        # Carregar template existente
        import config
        dados = config._carregar()
        default_template = "Bom dia!\nPoderia confirmar o recebimento do pedido {DPP}?"
        template = dados.get("template_email_controle_pedidos", default_template)
        self.txt_template.setPlainText(template)
        layout.addWidget(self.txt_template)

        # Botões
        btn_box = QHBoxLayout()
        btn_box.setSpacing(8)
        
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setFixedHeight(34)
        btn_cancelar.setStyleSheet("""
            QPushButton {
                background-color: #f1f5f9;
                color: #475569;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                padding: 0 16px;
                font-weight: 500;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #e2e8f0;
            }
        """)
        btn_cancelar.clicked.connect(self.reject)
        
        btn_salvar = QPushButton("Salvar")
        btn_salvar.setFixedHeight(34)
        btn_salvar.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 0 16px;
                font-weight: 600;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #1d4ed8;
            }
            QPushButton:pressed {
                background-color: #1e40af;
            }
        """)
        btn_salvar.clicked.connect(self._salvar_template)

        btn_box.addStretch()
        btn_box.addWidget(btn_cancelar)
        btn_box.addWidget(btn_salvar)
        
        layout.addLayout(btn_box)

    def _salvar_template(self):
        import config
        dados = config._carregar()
        dados["template_email_controle_pedidos"] = self.txt_template.toPlainText()
        config._salvar(dados)
        self.accept()


class ControlePedidosPage(QWidget):
    COLUNAS = ["Data", "Fornecedores", "Nome", "Requisição", "DPP", "Status", "Email", "Observação"]
    CHAVES = ["data", "fornecedores", "nome", "requisicao", "dpp", "status_cor", "email", "observacao"]
    CORES = {"Amarelo": "#FFFF00", "Verde": "#00FF00", "Vermelho": "#FF0000"}

    def __init__(self):
        super().__init__()
        self.dados = []
        self.lista_fornecedores = _carregar_fornecedores()
        self._linhas_editaveis = set()  # índices de linhas em modo edição
        self._edit_mode = False  # Flag for global edit mode
        self._setup_ui()
        self._carregar_dados()

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(0, lambda: self.tabela.verticalScrollBar().setValue(self.tabela.verticalScrollBar().maximum()))

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # ── Page Header ──
        header_layout = QHBoxLayout()
        header_texts = QVBoxLayout()
        header_texts.setSpacing(4)
        titulo = QLabel("Controle de Pedidos")
        titulo.setObjectName("pageTitle")
        header_texts.addWidget(titulo)
        subtitulo = QLabel("Acompanhamento de pedidos e confirmações de entrega")
        subtitulo.setObjectName("pageSubtitle")
        header_texts.addWidget(subtitulo)
        header_layout.addLayout(header_texts)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        card = QWidget()
        card.setObjectName("pageCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 16, 18, 16)
        card_layout.setSpacing(12)

        # ── Action Buttons Row ──
        linha_top = QHBoxLayout()
        linha_top.setSpacing(8)

        btn_adicionar = QPushButton(qtawesome.icon('mdi6.refresh', color='#ffffff'), "  Atualizar")
        btn_adicionar.setObjectName("btnPrimary")
        btn_adicionar.setFixedHeight(34)
        btn_adicionar.clicked.connect(self._adicionar_linha)
        linha_top.addWidget(btn_adicionar)

        btn_entregar = QPushButton(qtawesome.icon('fa6s.check', color='#ffffff'), "  Entregar")
        btn_entregar.setObjectName("btnGradientGreen")
        btn_entregar.setFixedHeight(34)
        btn_entregar.clicked.connect(self._entregar_item)
        linha_top.addWidget(btn_entregar)

        btn_remover = QPushButton(qtawesome.icon('fa6s.trash', color='#ffffff'), "  Remover")
        btn_remover.setObjectName("btnGradientRose")
        btn_remover.setFixedHeight(34)
        btn_remover.clicked.connect(self._remover_linha)
        linha_top.addWidget(btn_remover)

        btn_pendente = QPushButton(qtawesome.icon('mdi6.backup-restore', color='#6b7280'), "  Marcar como pendente")
        btn_pendente.setObjectName("btnSecondary")
        btn_pendente.setFixedHeight(34)
        btn_pendente.clicked.connect(self._marcar_pendente)
        linha_top.addWidget(btn_pendente)

        self.btn_editar = QPushButton(qtawesome.icon('mdi6.pencil-outline', color='#6b7280'), "  Editar")
        self.btn_editar.setObjectName("btnEditMode")
        self.btn_editar.setFixedHeight(34)
        self.btn_editar.setCheckable(True)
        self.btn_editar.clicked.connect(self._toggle_edicao)
        linha_top.addWidget(self.btn_editar)

        linha_top.addStretch()

        self.campo_busca = QLineEdit()
        self.campo_busca.setPlaceholderText("Pesquisar...")
        self.campo_busca.setFixedHeight(32)
        self.campo_busca.setFixedWidth(200)
        self.campo_busca.textChanged.connect(self._aplicar_filtro)
        linha_top.addWidget(self.campo_busca)

        self.label_contador = QLabel("0 itens")
        self.label_contador.setObjectName("statusLabel")
        linha_top.addWidget(self.label_contador)

        self.btn_config = QPushButton(qtawesome.icon('fa6s.gear', color='#64748b'), "")
        self.btn_config.setObjectName("btnGhost")
        self.btn_config.setFixedSize(34, 34)
        self.btn_config.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_config.setToolTip("Configurar modelo de e-mail")
        self.btn_config.clicked.connect(self._abrir_config_email)
        linha_top.addWidget(self.btn_config)

        card_layout.addLayout(linha_top)

        self.tabela = QTableWidget(0, len(self.COLUNAS))
        self.tabela.setObjectName("tabelaControle")
        self.tabela.setStyleSheet("""
            QTableWidget#tabelaControle {
                background-color: #ffffff;
                border: 1px solid #eef1f6;
                border-radius: 12px;
                gridline-color: transparent;
                selection-background-color: #eef2ff;
                selection-color: #1e1b4b;
                font-size: 13px;
                outline: none;
            }
            QTableWidget#tabelaControle::item {
                padding: 4px 10px;
                border-bottom: 1px solid #f3f4f6;
            }
            QTableWidget#tabelaControle::item:selected {
                background-color: #eef2ff;
                color: #1e1b4b;
            }
            QTableWidget#tabelaControle::item:hover {
                background-color: #f5f3ff;
            }
            QTableWidget#tabelaControle::item:focus {
                outline: none;
                border: 1.5px solid #6366f1;
                border-radius: 4px;
            }
        """)
        self.tabela.setHorizontalHeaderLabels(self.COLUNAS)
        header = self.tabela.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(0, 94) #data
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(1, 180) #fornecedores
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(2, 140) #nome
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(3, 110) #requisição
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(4, 90) #dpp
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(5, 80) #status cor
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(6, 80) #email
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch) #observação
        self.tabela.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabela.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.tabela.setEditTriggers(QAbstractItemView.EditTrigger.CurrentChanged)
        self.tabela.setAlternatingRowColors(True)
        self.tabela.verticalHeader().setDefaultSectionSize(32)
        self.tabela.verticalHeader().setMinimumSectionSize(26)
        self.tabela.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.tabela.verticalHeader().setVisible(False)
        self.tabela.setItemDelegate(EditorDelegate(self.tabela, self.lista_fornecedores, edit_mode_getter=lambda: self._edit_mode))
        self.tabela.itemChanged.connect(self._item_modificado)
        self.tabela.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tabela.customContextMenuRequested.connect(self._context_menu)
        card_layout.addWidget(self.tabela)

        QShortcut(QKeySequence("Ctrl+F"), self, self._buscar_item)
        QShortcut(QKeySequence("Ctrl+L"), self, self._buscar_item)
        QShortcut(QKeySequence("Ctrl+C"), self.tabela, self._copiar_selecao)

        layout.addWidget(card)

    def _copiar_selecao(self):
        """Copia apenas o conteúdo da célula atual/focada para a área de transferência."""
        item = self.tabela.currentItem()
        if item:
            QApplication.clipboard().setText(item.text())
        else:
            row = self.tabela.currentRow()
            col = self.tabela.currentColumn()
            if row >= 0 and col >= 0:
                item_cell = self.tabela.item(row, col)
                if item_cell:
                    QApplication.clipboard().setText(item_cell.text())

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

    def _carregar_pedidos_entregues_filtrados(self, filtro):
        """Carrega dos arquivos anuais os pedidos entregues que casam com o filtro."""
        if not filtro:
            return []
        ano_atual = int(datetime.now().strftime("%Y"))
        import config
        base = config.obter_caminho_jsons()
        if not base:
            return []
        resultado = []
        for ano in range(ano_atual, 2023, -1):
            caminho = os.path.normpath(os.path.join(base, "Almox", "ControlePedidos", f"ControlePedidosEntregues{ano}.json"))
            try:
                with open(caminho, "r", encoding="utf-8") as f:
                    dados = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                continue
            for item in dados:
                if not isinstance(item, dict):
                    continue
                texto = " ".join(str(v) for v in item.values()).lower()
                if filtro in texto:
                    resultado.append(item)
        return resultado

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

    def _aplicar_filtro(self):
        self._popular_tabela()

    def _popular_tabela(self):
        # Salvar posições dos scrollbars e célula atual
        v_scroll = self.tabela.verticalScrollBar().value()
        h_scroll = self.tabela.horizontalScrollBar().value()
        curr_row = self.tabela.currentRow()
        curr_col = self.tabela.currentColumn()

        self.tabela.blockSignals(True)
        self.tabela.setRowCount(0)
        filtro = self.campo_busca.text().strip().lower()
        itens_exibidos = []
        origens = []
        if filtro:
            entregues = self._carregar_pedidos_entregues_filtrados(filtro)
            itens_exibidos.extend(entregues)
            origens.extend([-1] * len(entregues))
        for idx, item in enumerate(self.dados):
            if filtro:
                texto = " ".join(str(v) for v in item.values()).lower()
                if filtro not in texto:
                    continue
            itens_exibidos.append(item)
            origens.append(idx)
        for item, origem in zip(itens_exibidos, origens):
            row = self.tabela.rowCount()
            self.tabela.insertRow(row)
            cor_nome = item.get("cor", "")
            cor_hex = self.CORES.get(cor_nome, "")
            status_val = "Entregue" if origem == -1 else item.get("status", "")
            for col, chave in enumerate(self.CHAVES):
                if col == 6:
                    dpp_val = item.get("dpp", "").strip()
                    if dpp_val:
                        btn_container = self._criar_botao_enviar(self._on_enviar_clicado)
                        self.tabela.setCellWidget(row, col, btn_container)
                    
                    cell = QTableWidgetItem("")
                    cell.setFlags(cell.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    if status_val == "Entregue":
                        cell.setData(Qt.BackgroundRole, QBrush(QColor("#C8E6C9")))
                    self.tabela.setItem(row, col, cell)
                elif col == 5:
                    btn_container = self._criar_botao_cor(self._on_cor_clicado)
                    self.tabela.setCellWidget(row, col, btn_container)
                    
                    cell = QTableWidgetItem("")
                    cell.setFlags(cell.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    if status_val == "Entregue":
                        cell.setData(Qt.BackgroundRole, QBrush(QColor("#C8E6C9")))
                    self.tabela.setItem(row, col, cell)
                else:
                    valor = str(item.get(chave, ""))
                    cell = QTableWidgetItem(valor)
                    # Colunas 0-3 são somente leitura se o fornecedor já está preenchido
                    fornecedor_preenchido = bool(item.get("fornecedores", "").strip())
                    # Coluna 4 (DPP) é somente leitura se já tiver valor
                    dpp_preenchido = bool(item.get("dpp", "").strip())
                    # Verifica se a linha está em modo edição (liberada pelo botão Editar)
                    # Determine editability based on global edit mode
                    if self._edit_mode:
                        # Global edit mode: allow editing for all editable columns (except action columns 5 and 6)
                        cell.setFlags(cell.flags() | Qt.ItemFlag.ItemIsEditable)
                    else:
                        # Preserve existing per‑row edit restrictions
                        em_edicao = row in self._linhas_editaveis
                        if em_edicao:
                            cell.setFlags(cell.flags() | Qt.ItemFlag.ItemIsEditable)
                        elif col in (0, 1, 2, 3) and fornecedor_preenchido:
                            cell.setFlags(cell.flags() & ~Qt.ItemFlag.ItemIsEditable)
                        elif col == 4 and dpp_preenchido:
                            cell.setFlags(cell.flags() & ~Qt.ItemFlag.ItemIsEditable)
                        else:
                            cell.setFlags(cell.flags() | Qt.ItemFlag.ItemIsEditable)
                    if status_val == "Entregue":
                        cell.setData(Qt.BackgroundRole, QBrush(QColor("#C8E6C9")))
                    if cor_hex and col == 4:
                        cell.setData(Qt.BackgroundRole, QBrush(QColor(cor_hex)))
                    self.tabela.setItem(row, col, cell)
            celula_origem = self.tabela.item(row, 0)
            if celula_origem:
                celula_origem.setData(Qt.ItemDataRole.UserRole, origem)
        self._inserir_linha_vazia()
        self.tabela.blockSignals(False)
        self._atualizar_contador()

        # Restaurar célula selecionada e foco
        if curr_row >= 0 and curr_row < self.tabela.rowCount() and curr_col >= 0 and curr_col < self.tabela.columnCount():
            self.tabela.setCurrentCell(curr_row, curr_col)

        # Restaurar posições dos scrollbars
        self.tabela.verticalScrollBar().setValue(v_scroll)
        self.tabela.horizontalScrollBar().setValue(h_scroll)

    def _inserir_linha_vazia(self):
        row = self.tabela.rowCount()
        self.tabela.insertRow(row)
        for col in range(len(self.COLUNAS)):
            cell = QTableWidgetItem("")
            if col in (5, 6):
                cell.setFlags(cell.flags() & ~Qt.ItemFlag.ItemIsEditable)
            else:
                cell.setFlags(cell.flags() | Qt.ItemFlag.ItemIsEditable)
            self.tabela.setItem(row, col, cell)

    def _atualizar_contador(self):
        total = max(0, self.tabela.rowCount() - 1)
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
            self._mostrar_nao_encontrado()
            return
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
            if col == 6:
                btn_container = self._criar_botao_enviar(lambda checked=False, tbl=tabela: self._enviar_email_dialog(tbl))
                tabela.setCellWidget(0, col, btn_container)
                
                celula = QTableWidgetItem("")
                celula.setFlags(celula.flags() & ~Qt.ItemFlag.ItemIsEditable)
                tabela.setItem(0, col, celula)
            elif col == 5:
                btn_container = self._criar_botao_cor(lambda checked=False, tbl=tabela: self._on_cor_dialog_clicado(tbl))
                tabela.setCellWidget(0, col, btn_container)
                
                celula = QTableWidgetItem("")
                celula.setFlags(celula.flags() & ~Qt.ItemFlag.ItemIsEditable)
                tabela.setItem(0, col, celula)
            else:
                celula = QTableWidgetItem(str(item.get(chave, "")))
                celula.setFlags(celula.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if col == 4:
                    cor_nome = item.get("cor", "")
                    cor_hex = self.CORES.get(cor_nome, "")
                    if cor_hex:
                        celula.setData(Qt.BackgroundRole, QBrush(QColor(cor_hex)))
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
        if not caminho:
            import config
            config.avisar_sem_pasta(self)
            return
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

    def _indice_por_linha(self, row):
        """Retorna o índice real no self.dados da linha exibida, ou None se não mapeia."""
        celula = self.tabela.item(row, 0)
        if celula is None:
            return None
        origem = celula.data(Qt.ItemDataRole.UserRole)
        if isinstance(origem, int) and 0 <= origem < len(self.dados):
            return origem
        return None

    def _entregar_item(self):
        selected_rows = self.tabela.selectionModel().selectedRows()
        if not selected_rows:
            return
        indices = sorted(set(index.row() for index in selected_rows), reverse=True)
        for row in indices:
            idx = self._indice_por_linha(row)
            if idx is None:
                continue
            status_atual = self.dados[idx].get("status", "")
            self.dados[idx]["status"] = "Em andamento" if status_atual == "Entregue" else "Entregue"
        self._salvar_json()
        self._popular_tabela()

    def _remover_linha(self):
        selected_rows = self.tabela.selectionModel().selectedRows()
        if not selected_rows:
            return
        indices = sorted(
            {i for i in (self._indice_por_linha(index.row()) for index in selected_rows) if i is not None},
            reverse=True,
        )
        removidos = False
        for idx in indices:
            self.dados.pop(idx)
            removidos = True
        if removidos:
            self._salvar_json()
        self._popular_tabela()

    def _marcar_pendente(self):
        selected_rows = self.tabela.selectionModel().selectedRows()
        if not selected_rows:
            return
        indices = sorted(set(index.row() for index in selected_rows), reverse=True)
        for row in indices:
            idx = self._indice_por_linha(row)
            if idx is None:
                continue
            self.dados[idx]["status"] = "Em andamento"
        self._salvar_json()
        self._popular_tabela()

    def _toggle_edicao(self):
        """Alterna o modo de edição global para a tabela.
        Quando ativado, todas as células (exceto colunas de ação) ficam editáveis.
        Quando desativado, volta ao comportamento padrão de bloqueio.
        """
        # Toggle global edit mode based on button state
        self._edit_mode = self.btn_editar.isChecked()
        # Ensure button visual reflects state
        self.btn_editar.setChecked(self._edit_mode)
        # Refresh table to apply editability changes
        self._popular_tabela()

    def _context_menu(self, pos):
        item = self.tabela.itemAt(pos)
        if not item:
            return
        col = item.column()
        row = item.row()
        idx = self._indice_por_linha(row)
        if idx is None:
            return
        # Coluna DPP (4) → menu de cor
        if col == 4:
            menu = QMenu(self)
            for nome, hex_cor in self.CORES.items():
                pix = self._color_pixmap(hex_cor)
                acao = menu.addAction(pix, nome)
                acao.triggered.connect(lambda checked, n=nome, i=idx: self._aplicar_cor(i, n))
            menu.exec(QCursor.pos())
            return
        # Coluna Nome (2) → menu "Verificar requisição"
        if col == 2:
            req_val = self.dados[idx].get("requisicao", "").strip()
            if not req_val:
                return
            menu = QMenu(self)
            verificar = menu.addAction("Verificar requisição")
            verificar.triggered.connect(lambda checked=False, i=idx: self._abrir_requisicao(i))
            menu.exec(QCursor.pos())
            return

    def _abrir_requisicao(self, idx):
        """Abre o link do IntelleCat para a requisição da linha informada."""
        req_val = self.dados[idx].get("requisicao", "").strip()
        if not req_val:
            return
        url = (
            f"https://aptiv.intellecat.com/IntelleCat/CartServlet"
            f"?ic_action=viewReq&reqID={urllib.parse.quote(req_val)}"
            f"&view=viewRequestor&role=REQUESTOR"
        )
        webbrowser.open(url)


    def _color_pixmap(self, hex_cor):
        from PySide6.QtGui import QPixmap, QPainter
        pix = QPixmap(16, 16)
        pix.fill(QColor(hex_cor))
        return pix

    def _aplicar_cor(self, idx, nome_cor):
        if self.dados[idx].get("cor") == nome_cor:
            nome_cor = ""
        self.dados[idx]["cor"] = nome_cor
        self._salvar_json()
        self._popular_tabela()

    def _auto_preencher_nome(self, row, sufixo=""):
        nome_anterior = self.dados[row - 1].get("nome", "").strip()
        if not nome_anterior.startswith("PC"):
            return
        codigo = nome_anterior.split(" ")[0].strip()
        import re
        match = re.match(r"PC(\d+)", codigo)
        if not match:
            return
        numero = int(match.group(1)) + 1
        novo_nome = f"PC{numero}{sufixo}"
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
        sem_filtro = not self.campo_busca.text().strip()

        idx = self._indice_por_linha(row)
        if idx is None:
            if row != self.tabela.rowCount() - 1:
                return
            texto = item.text().strip()
            if texto:
                novo_item = {}
                for c, ch in enumerate(self.CHAVES):
                    celula = self.tabela.item(row, c)
                    valor = celula.text().strip() if celula else ""
                    if ch in ("fornecedores", "dpp"):
                        valor = valor.upper()
                        self.tabela.blockSignals(True)
                        if celula:
                            celula.setText(valor)
                        self.tabela.blockSignals(False)
                    novo_item[ch] = valor
                novo_item["cor"] = ""
                novo_item["status"] = "Em andamento"
                self.dados.append(novo_item)
                novo_idx = len(self.dados) - 1
                if chave == "requisicao" and sem_filtro and row > 0:
                    self._auto_preencher_nome(row, " | Capex")
                    QTimer.singleShot(0, lambda r=row: self.tabela.setCurrentCell(r, 1))
                self._salvar_json()
                self.tabela.blockSignals(True)

                # Guarda o índice real na célula da coluna Data
                celula_origem = self.tabela.item(row, 0)
                if celula_origem:
                    celula_origem.setData(Qt.ItemDataRole.UserRole, novo_idx)

                # Add "Cor" button
                btn_container_cor = self._criar_botao_cor(self._on_cor_clicado)
                self.tabela.setCellWidget(row, 5, btn_container_cor)

                # Add the "Enviar" button to the newly added row if DPP is filled
                if novo_item.get("dpp", "").strip():
                    btn_container = self._criar_botao_enviar(self._on_enviar_clicado)
                    self.tabela.setCellWidget(row, 6, btn_container)

                self.tabela.insertRow(row + 1)
                for c in range(len(self.COLUNAS)):
                    celula = QTableWidgetItem("")
                    if c in (5, 6):
                        celula.setFlags(celula.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    else:
                        celula.setFlags(celula.flags() | Qt.ItemFlag.ItemIsEditable)
                    self.tabela.setItem(row + 1, c, celula)
                self.tabela.blockSignals(False)
                self._atualizar_contador()
            return

        old_val = self.dados[idx].get(chave, "")
        valor = item.text()
        if chave in ("fornecedores", "dpp"):
            valor_upper = valor.upper()
            if valor_upper != valor:
                self.tabela.blockSignals(True)
                item.setText(valor_upper)
                self.tabela.blockSignals(False)
                valor = valor_upper
        self.dados[idx][chave] = valor
        if chave == "requisicao" and not old_val and valor.strip() and sem_filtro and idx > 0:
            self._auto_preencher_nome(row, " | Capex")
            QTimer.singleShot(0, lambda r=row: self.tabela.setCurrentCell(r, 1))
        if chave == "dpp":
            if valor.strip():
                if not self.tabela.cellWidget(row, 6):
                    btn_container = self._criar_botao_enviar(self._on_enviar_clicado)
                    self.tabela.setCellWidget(row, 6, btn_container)
            else:
                self.tabela.removeCellWidget(row, 6)
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

    def _on_celula_clicada(self, row, col):
        """Abre o link do InteleCat ao clicar na coluna Nome quando já bloqueada."""
        if col != 2:
            return
        if row < 0 or row >= len(self.dados):
            return
        # Só abre o link se a célula está bloqueada (fornecedor preenchido)
        fornecedor_preenchido = bool(self.dados[row].get("fornecedores", "").strip())
        if not fornecedor_preenchido:
            return
        req_val = self.dados[row].get("requisicao", "").strip()
        if not req_val:
            return
        url = (
            f"https://aptiv.intellecat.com/IntelleCat/CartServlet"
            f"?ic_action=viewReq&reqID={urllib.parse.quote(req_val)}"
            f"&view=viewRequestor&role=REQUESTOR"
        )
        webbrowser.open(url)

    def _criar_botao_enviar(self, clicked_slot):
        container = QWidget()
        layout_btn = QHBoxLayout(container)
        layout_btn.setContentsMargins(0, 0, 0, 0)
        layout_btn.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        btn = QPushButton("Enviar")
        btn.setFixedSize(54, 22)
        btn.setStyleSheet("""
            QPushButton {
                background-color: #6366f1;
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: 600;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #4f46e5;
            }
            QPushButton:pressed {
                background-color: #4338ca;
            }
        """)
        btn.clicked.connect(clicked_slot)
        layout_btn.addWidget(btn)
        return container

    def _on_enviar_clicado(self):
        button = self.sender()
        if not button:
            return
        # Mapear a posição do botão para o viewport da tabela
        pos = button.mapTo(self.tabela.viewport(), button.rect().center())
        index = self.tabela.indexAt(pos)
        row = index.row()
        if row < 0:
            return
        self._enviar_email(row)

    def _criar_botao_cor(self, clicked_slot):
        container = QWidget()
        layout_btn = QHBoxLayout(container)
        layout_btn.setContentsMargins(0, 0, 0, 0)
        layout_btn.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        btn = QPushButton("")
        btn.setFixedSize(36, 18)
        btn.setStyleSheet("""
            QPushButton {
                background-color: #cbd5e1;
                border: 1px solid #94a3b8;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #94a3b8;
            }
            QPushButton:pressed {
                background-color: #64748b;
            }
        """)
        btn.clicked.connect(clicked_slot)
        layout_btn.addWidget(btn)
        return container

    def _on_cor_clicado(self):
        button = self.sender()
        if not button:
            return
        pos = button.mapTo(self.tabela.viewport(), button.rect().center())
        index = self.tabela.indexAt(pos)
        row = index.row()
        idx = self._indice_por_linha(row)
        if idx is None:
            return

        cor_atual = self.dados[idx].get("cor", "")
        if cor_atual == "Amarelo":
            nova_cor = "Verde"
        elif cor_atual == "Verde":
            nova_cor = "Vermelho"
        elif cor_atual == "Vermelho":
            nova_cor = ""
        else:
            nova_cor = "Amarelo"

        self.dados[idx]["cor"] = nova_cor
        self._salvar_json()
        self._popular_tabela()

    def _on_cor_dialog_clicado(self, tabela):
        button = self.sender()
        if not button:
            return
        dpp_item = tabela.item(0, 4)
        if not dpp_item:
            return
        
        bg_brush = dpp_item.data(Qt.BackgroundRole)
        bg_color = bg_brush.color().name().upper() if bg_brush else ""
        
        cor_atual = ""
        for nome, hex_val in self.CORES.items():
            if bg_color == hex_val:
                cor_atual = nome
                break
                
        if cor_atual == "Amarelo":
            nova_cor_nome = "Verde"
        elif cor_atual == "Verde":
            nova_cor_nome = "Vermelho"
        elif cor_atual == "Vermelho":
            nova_cor_nome = ""
        else:
            nova_cor_nome = "Amarelo"
            
        if nova_cor_nome:
            hex_cor = self.CORES[nova_cor_nome]
            dpp_item.setData(Qt.BackgroundRole, QBrush(QColor(hex_cor)))
        else:
            dpp_item.setData(Qt.BackgroundRole, None)

    def _obter_email_fornecedor(self, fornecedor_nome):
        if not fornecedor_nome:
            return ""
        fornecedor_nome = fornecedor_nome.strip().upper()
        try:
            with open(_caminho_fornecedores_json(), "r", encoding="utf-8") as f:
                dados = json.load(f)
            for item in dados:
                f_nome = item.get("fornecedor", "").strip().upper()
                if f_nome == fornecedor_nome:
                    return item.get("email", "").strip()
        except Exception:
            pass
        return ""

    def _obter_corpo_email(self, dpp_val):
        import config
        dados = config._carregar()
        default_template = "Bom dia!\nPoderia confirmar o recebimento do pedido {DPP}?"
        template = dados.get("template_email_controle_pedidos", default_template)
        corpo = template
        for placeholder in ["{DPP}", "{dpp}", "{Dpp}", "{dPP}"]:
            corpo = corpo.replace(placeholder, dpp_val)
        return corpo

    def _enviar_email(self, row):
        # Obtain supplier name and look up its email
        fornecedor_item = self.tabela.item(row, 1)
        fornecedor_val = fornecedor_item.text().strip() if fornecedor_item else ""
        destinatario = self._obter_email_fornecedor(fornecedor_val)

        # Get DPP value
        dpp_item = self.tabela.item(row, 4)
        dpp_val = dpp_item.text().strip() if dpp_item else ""
        corpo = self._obter_corpo_email(dpp_val)
        
        # Build mailto URL
        assunto = f"Confirmação de recebimento do pedido {dpp_val}"
        if destinatario:
            url = f"mailto:{destinatario}?subject={urllib.parse.quote(assunto)}&body={urllib.parse.quote(corpo)}"
        else:
            url = f"mailto:?subject={urllib.parse.quote(assunto)}&body={urllib.parse.quote(corpo)}"
        
        # Open in email client
        webbrowser.open(url)

        # Change DPP cell color to yellow in the UI
        if dpp_item:
            dpp_item.setData(Qt.BackgroundRole, QBrush(QColor("#FFFF00")))

        # Update and save the color in the JSON data model
        idx = self._indice_por_linha(row)
        if idx is not None:
            self.dados[idx]["cor"] = "Amarelo"
            self._salvar_json()

    def _enviar_email_dialog(self, tabela):
        # Obtain supplier name and look up its email
        fornecedor_item = tabela.item(0, 1)
        fornecedor_val = fornecedor_item.text().strip() if fornecedor_item else ""
        destinatario = self._obter_email_fornecedor(fornecedor_val)

        # Get DPP value
        dpp_item = tabela.item(0, 4)
        dpp_val = dpp_item.text().strip() if dpp_item else ""
        corpo = self._obter_corpo_email(dpp_val)
        
        # Build mailto URL
        assunto = f"Confirmação de recebimento do pedido {dpp_val}"
        if destinatario:
            url = f"mailto:{destinatario}?subject={urllib.parse.quote(assunto)}&body={urllib.parse.quote(corpo)}"
        else:
            url = f"mailto:?subject={urllib.parse.quote(assunto)}&body={urllib.parse.quote(corpo)}"
        
        # Open in email client
        webbrowser.open(url)

        # Change DPP cell color to yellow in the dialog UI
        if dpp_item:
            dpp_item.setData(Qt.BackgroundRole, QBrush(QColor("#FFFF00")))

    def _abrir_config_email(self):
        dialog = ConfigEmailDialog(self)
        dialog.exec()
