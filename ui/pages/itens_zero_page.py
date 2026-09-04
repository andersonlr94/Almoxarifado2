import json
import os

import matplotlib

matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QStyledItemDelegate, QStyleOptionViewItem,
    QStyle,
)
from PySide6.QtCore import Qt, QSize, QRect, Signal, QMimeData, QPropertyAnimation, QEasingCurve, Property
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
        return QSize(base.width(), max(base.height(), 26))

    def createEditor(self, parent, option, index):
        editor = super().createEditor(parent, option, index)
        if isinstance(editor, QLineEdit):
            editor.setMinimumHeight(26)
            editor.setStyleSheet("padding: 2px 6px; font-size: 11px;")
            col = index.column()
            if col < len(self._chaves) and self._chaves[col] not in ("dpp", "observacao"):
                editor.setReadOnly(True)
        return editor


class PainelLateral(QWidget):
    LARGURA_MINIMA = 58

    def __init__(self, parent=None):
        super().__init__(parent)
        self._largura = self.LARGURA_MINIMA
        self._expandido = False
        self.setFixedWidth(self.LARGURA_MINIMA)
        self.setObjectName("painelLateral")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self._anim = QPropertyAnimation(self, b"largura", self)
        self._anim.setDuration(200)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutCubic)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 12, 0, 12)
        layout.setSpacing(0)

        self.btn_toggle = QPushButton("+")
        self.btn_toggle.setObjectName("btnLateral")
        self.btn_toggle.setFixedSize(34, 34)
        self.btn_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle.setToolTip("Expandir painel")
        self.btn_toggle.clicked.connect(self._alternar)
        layout.addWidget(self.btn_toggle, 0, Qt.AlignmentFlag.AlignHCenter)

        self.grafico_titulo = QLabel("Itens zerados por dia")
        self.grafico_titulo.setObjectName("pageSubtitle")
        self.grafico_titulo.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.grafico_titulo.setContentsMargins(0, 12, 0, 8)
        layout.addWidget(self.grafico_titulo)

        self.figure = Figure(figsize=(3, 4), facecolor="none")
        self.figure.subplots_adjust(left=0.08, right=0.97, top=0.96, bottom=0.14)
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)
        altura_tela = QGuiApplication.primaryScreen().availableGeometry().height()
        self.canvas.setFixedHeight(altura_tela // 2)
        layout.addWidget(self.canvas, 0, Qt.AlignmentFlag.AlignTop)

        layout.addStretch()

    def atualizar_grafico(self):
        self.ax.clear()
        self.ax.set_facecolor("none")
        for spine in self.ax.spines.values():
            spine.set_visible(False)
        self.ax.tick_params(left=False, labelleft=False, length=0)

        registros = _carregar_historico()
        if not registros:
            self.ax.tick_params(bottom=False, labelbottom=False)
            self.ax.text(
                0.5, 0.5, "Sem dados ainda",
                transform=self.ax.transAxes,
                ha="center", va="center",
                fontsize=12, color="#94a3b8",
            )
            self.canvas.draw()
            return

        datas = [r[0] for r in registros]
        valores = [r[1] for r in registros]
        xs = list(range(len(registros)))

        self.ax.plot(
            xs, valores,
            color="#6366f1", linewidth=2.5, zorder=3,
            marker="o", markersize=6,
            markerfacecolor="#ffffff", markeredgecolor="#6366f1", markeredgewidth=2,
        )
        self.ax.fill_between(xs, valores, color="#6366f1", alpha=0.12, zorder=2)

        for x, v in zip(xs, valores):
            self.ax.annotate(
                str(v), (x, v),
                textcoords="offset points", xytext=(0, 9),
                ha="center", va="bottom",
                fontsize=8, fontweight="bold", color="#1e1b4b",
            )

        self.ax.set_xticks(xs)
        self.ax.set_xticklabels(datas, rotation=45, ha="right", fontsize=8, color="#94a3b8")
        self.ax.tick_params(axis="x", pad=6)
        self.ax.grid(axis="y", color="#e5e7eb", linewidth=0.8, alpha=0.7)
        self.ax.set_axisbelow(True)
        self.ax.set_ylim(0, max(valores) * 1.25 + 1)

        self.canvas.draw()

    def _obter_largura(self):
        return self._largura

    def _definir_largura(self, valor):
        self._largura = valor
        self.setFixedWidth(int(valor))

    largura = Property(int, _obter_largura, _definir_largura)

    def _alternar(self):
        if self._expandido:
            self._colapsar()
        else:
            self._expandir()

    def _expandir(self):
        alvo = int(self.parentWidget().width() * 0.30) if self.parentWidget() else 400
        self._anim.stop()
        self._anim.setStartValue(self._largura)
        self._anim.setEndValue(alvo)
        self._anim.start()
        self._expandido = True
        self.btn_toggle.setText("-")
        self.btn_toggle.setToolTip("Recolher painel")

    def _colapsar(self):
        self._anim.stop()
        self._anim.setStartValue(self._largura)
        self._anim.setEndValue(self.LARGURA_MINIMA)
        self._anim.start()
        self._expandido = False
        self.btn_toggle.setText("+")
        self.btn_toggle.setToolTip("Expandir painel")


def _caminho_json():
    import config
    base = config.obter_caminho_jsons()
    if not base:
        return ""
    return os.path.normpath(os.path.join(base, "Almox", "ItensZero", "itensZero.json"))


def _caminho_itens_almoxarifado_json():
    import config
    base = config.obter_caminho_jsons()
    if not base:
        return ""
    return os.path.normpath(os.path.join(base, "Almox", "ItensAlmoxarifado", "ItensAlmoxarifado.json"))


def _caminho_fresh_start_json():
    import config
    base = config.obter_caminho_jsons()
    if not base:
        return ""
    return os.path.normpath(os.path.join(base, "Almox", "FreshStart", "fresh_start.json"))


def _caminho_historico_json():
    import config
    base = config.obter_caminho_jsons()
    if not base:
        return ""
    return os.path.normpath(os.path.join(base, "Almox", "ItensZero", "dadosItensZero.json"))


def _carregar_historico():
    caminho = _caminho_historico_json()
    if not caminho or not os.path.isfile(caminho):
        return []
    registros = []
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            for linha in f:
                linha = linha.strip()
                if not linha or " - " not in linha:
                    continue
                data, valor = linha.split(" - ", 1)
                try:
                    registros.append((data, int(valor)))
                except ValueError:
                    continue
    except OSError:
        return []
    return registros


class ItensZeroPage(QWidget):
    COLUNAS = ["Kardex", "Código", "Descrição", "Fornecedor", "Cons Med", "Qtde prog", "DPP", "Observação"]
    CHAVES = ["kardex", "codigo", "descricao", "fornecedor", "consumo_medio", "qtde_prog", "dpp", "observacao"]
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
        layout = QHBoxLayout(self)
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

        filtro_linha = QHBoxLayout()
        filtro_linha.setSpacing(6)
        filtro_linha.setContentsMargins(0, 0, 0, 0)

        self.campo_filtro = QLineEdit()
        self.campo_filtro.setPlaceholderText("⌕   Pesquisar...")
        self.campo_filtro.setFixedHeight(32)
        self.campo_filtro.setMinimumWidth(200)
        self.campo_filtro.setMaximumWidth(320)
        self.campo_filtro.textChanged.connect(self._aplicar_filtro)
        self.campo_filtro.setStyleSheet("""
            QLineEdit {
                background: white;
                color: #1e293b;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                padding-left: 10px;
                padding-right: 10px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #6366f1;
            }
        """)
        filtro_linha.addWidget(self.campo_filtro)

        self.btn_limpar_filtro = QPushButton("✕")
        self.btn_limpar_filtro.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_limpar_filtro.setFixedSize(28, 28)
        self.btn_limpar_filtro.setToolTip("Limpar filtro")
        self.btn_limpar_filtro.clicked.connect(self._limpar_filtro)
        self.btn_limpar_filtro.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #9ca3af;
                border: none;
                border-radius: 6px;
                font-size: 12px;
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
        filtro_linha.addWidget(self.btn_limpar_filtro)
        filtro_linha.addStretch()

        self.label_contador = QLabel("0 itens")
        self.label_contador.setObjectName("statusLabel")
        filtro_linha.addWidget(self.label_contador)
        card_layout.addLayout(filtro_linha)

        self.tabela = TabelaReordenavel(0, len(self.COLUNAS))
        self.tabela.setObjectName("tabelaItensZero")
        self.tabela.setHorizontalHeaderLabels(self.COLUNAS)
        header = self.tabela.horizontalHeader()
        header.setStretchLastSection(True)
        for c in range(self.tabela.columnCount()):
            header.setSectionResizeMode(c, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(0, 126)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(1, 140)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(3, 140)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(4, 80)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(5, 80)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(6, 80)
        # ocultar coluna Cons Med (índice 4 após adição de Fornecedor)
        self.tabela.setColumnHidden(4, True)
        self.tabela.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabela.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.tabela.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked)
        self.tabela.setAlternatingRowColors(False)
        self.tabela.verticalHeader().setDefaultSectionSize(28)
        self.tabela.verticalHeader().setMinimumSectionSize(24)
        self.tabela.verticalHeader().setVisible(False)
        self.tabela.setItemDelegate(EditorDelegate(self.tabela, self.CHAVES))
        self.tabela.itemChanged.connect(self._item_modificado)
        self.tabela.ordemAlterada.connect(self._sincronizar_ordem)
        card_layout.addWidget(self.tabela)

        layout.addWidget(card, 7)

        self.painel_lateral = PainelLateral()
        layout.addWidget(self.painel_lateral)

        self.painel_lateral.atualizar_grafico()

    def _carregar_dados(self):
        try:
            with open(_caminho_json(), "r", encoding="utf-8") as f:
                self.dados = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.dados = []
        self._popular_tabela()

    def _aplicar_filtro(self):
        self._popular_tabela()

    def _limpar_filtro(self):
        self.campo_filtro.clear()
        self.campo_filtro.setFocus()

    def _popular_tabela(self):
        self.tabela.blockSignals(True)
        self.tabela.setRowCount(0)
        filtro = ""
        if hasattr(self, "campo_filtro"):
            filtro = self.campo_filtro.text().strip().lower()
        for item in self.dados:
            if filtro:
                texto = " ".join(str(v) for v in item.values()).lower()
                if filtro not in texto:
                    continue
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
        # manter Cons Med oculta
        self.tabela.setColumnHidden(4, True)
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
            # tenta obter fornecedor da coluna 4 se existir, senão deixa vazio (será preenchido via _sincronizar)
            fornecedor_val = partes[4].strip() if len(partes) > 4 else ""
            # se parecer numérico (qtde/loc), ignora
            if fornecedor_val and fornecedor_val.replace(".", "").replace(",", "").strip().isdigit():
                fornecedor_val = ""
            item = {
                "kardex": kardex,
                "codigo": partes[2].strip(),
                "descricao": partes[3].strip(),
                "fornecedor": fornecedor_val,
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
                    "fornecedor": item.get("Fornecedor", ""),
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
                dado["fornecedor"] = novo_item["fornecedor"]
                dado["consumo_medio"] = novo_item["consumo_medio"]
                dado["qtde_prog"] = novo_item["qtde_prog"]

        # Adicionar novos itens
        kardex_existentes = {d.get("kardex") for d in self.dados}
        for item in novos_itens:
            if item["kardex"] not in kardex_existentes:
                self.dados.append(item)

        # Verificar no fresh start se tem loc == "RECEBE"
        try:
            with open(_caminho_fresh_start_json(), "r", encoding="utf-8") as f:
                dados_fresh = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            dados_fresh = []

        kardex_recebe = set()
        for df in dados_fresh:
            k = df.get("kardex", "").strip()
            loc = df.get("loc", "").strip().upper()
            if loc == "RECEBE":
                kardex_recebe.add(k)

        for dado in self.dados:
            kardex = dado.get("kardex", "").strip()
            if kardex in kardex_recebe:
                dado["cor"] = "verde"
            elif dado.get("cor") == "verde" and kardex not in kardex_recebe:
                # Opcional: remover a cor se não for mais RECEBE (comentei para deixar a critério)
                dado["cor"] = ""

        self._salvar_json()
        self._popular_tabela()
        self._salvar_historico()
        self.painel_lateral.atualizar_grafico()

    def _salvar_historico(self):
        from datetime import date

        caminho = _caminho_historico_json()
        if not caminho:
            return
        qtde = self.tabela.rowCount()
        hoje = date.today().strftime("%d/%m/%Y")
        prefixo = f"{hoje} - "

        linhas = []
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                linhas = [linha.rstrip("\n") for linha in f]
        except (FileNotFoundError, OSError):
            linhas = []

        encontrou_hoje = False
        for i, linha in enumerate(linhas):
            if not linha.startswith(prefixo):
                continue
            encontrou_hoje = True
            try:
                valor_antigo = int(linha[len(prefixo):])
            except ValueError:
                valor_antigo = -1
            if qtde > valor_antigo:
                linhas[i] = f"{prefixo}{qtde}"
            break

        if not encontrou_hoje:
            linhas.append(f"{prefixo}{qtde}")

        try:
            os.makedirs(os.path.dirname(caminho), exist_ok=True)
            with open(caminho, "w", encoding="utf-8") as f:
                f.write("\n".join(linhas) + "\n")
        except OSError:
            pass

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
