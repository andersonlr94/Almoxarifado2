import json
import os
import random
from datetime import date

import matplotlib
matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QStyledItemDelegate, QMessageBox, QComboBox,
)
from PySide6.QtCore import Qt, QSize, QLocale, QMarginsF
from PySide6.QtGui import QGuiApplication, QColor, QDoubleValidator, QTextDocument, QPageLayout, QIntValidator, QPainter, QFont
from PySide6.QtPrintSupport import QPrinter, QPrinterInfo, QPrintPreviewDialog


class EditorDelegate(QStyledItemDelegate):
    def __init__(self, parent=None, colunas_numericas=None):
        super().__init__(parent)
        self._colunas_numericas = colunas_numericas or []

    def createEditor(self, parent, option, index):
        editor = super().createEditor(parent, option, index)
        if isinstance(editor, QLineEdit):
            editor.setFixedHeight(option.rect.height())
            editor.setStyleSheet("padding: 0px; margin: 0px;")
            if index.column() in self._colunas_numericas:
                validator = QDoubleValidator(0, 999999999, 0)
                validator.setNotation(QDoubleValidator.Notation.StandardNotation)
                editor.setValidator(validator)
        return editor


class AcuracidadePage(QWidget):
    COLUNAS = [
        "Kardex", "Item", "Descrição", "LocNovo",
        "Primeira\ncontagem", "Segunda\ncontagem", "Divergência", "Observação",
    ]
    COLUNAS_ESTOQUE = ["Kardex", "Código", "Descrição", "Loc novo", "Qtde novo", "Acuracidade ok"]

    def __init__(self):
        super().__init__()
        self.dados = []
        self._modo_acuracidade = True
        self._mapa_kardex_qtde = {}
        self._prosseguir_count = 0
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(16)

        self.card = QWidget()
        self.card.setObjectName("pageCard")
        self.card_layout = QVBoxLayout(self.card)
        self.card_layout.setContentsMargins(28, 28, 28, 28)
        self.card_layout.setSpacing(16)

        # ── Linha do título ──
        titulo_row = QHBoxLayout()
        titulo_row.setSpacing(12)

        self.titulo = QLabel("Acuracidade")
        self.titulo.setObjectName("pageTitle")
        titulo_row.addWidget(self.titulo)

        titulo_row.addStretch()

        self.btn_toggle = QPushButton("Itens de estoque")
        self.btn_toggle.setObjectName("btnSecondary")
        self.btn_toggle.setFixedHeight(34)
        self.btn_toggle.clicked.connect(self._alternar_modo)
        titulo_row.addWidget(self.btn_toggle)

        self.btn_atualizar_itens = QPushButton("Atualizar itens")
        self.btn_atualizar_itens.setObjectName("btnPrimary")
        self.btn_atualizar_itens.setFixedHeight(34)
        self.btn_atualizar_itens.setVisible(False)
        self.btn_atualizar_itens.clicked.connect(self._atualizar_itens)
        titulo_row.addWidget(self.btn_atualizar_itens)

        self.card_layout.addLayout(titulo_row)

        # ── Linha de conteúdo: tabela à esquerda, gráfico à direita ──
        conteudo_row = QHBoxLayout()
        conteudo_row.setSpacing(16)

        painel_tabela = QWidget()
        painel_tabela_layout = QVBoxLayout(painel_tabela)
        painel_tabela_layout.setContentsMargins(0, 0, 0, 0)
        painel_tabela_layout.setSpacing(12)

        # ── Filtro (só aparece no modo itens de estoque) ──
        self.filtro_widget = QWidget()
        filtro_layout = QHBoxLayout(self.filtro_widget)
        filtro_layout.setContentsMargins(0, 0, 0, 0)
        filtro_layout.setSpacing(8)

        self.campo_filtro = QLineEdit()
        self.campo_filtro.setPlaceholderText("Pesquisar...")
        self.campo_filtro.setFixedHeight(30)
        self.campo_filtro.setFixedWidth(250)
        self.campo_filtro.textChanged.connect(self._aplicar_filtro)
        filtro_layout.addWidget(self.campo_filtro)

        filtro_layout.addStretch()

        self.label_contador_estoque = QLabel("Itens: 0")
        self.label_contador_estoque.setObjectName("statusLabel")
        filtro_layout.addWidget(self.label_contador_estoque)

        self.filtro_widget.setVisible(False)
        painel_tabela_layout.addWidget(self.filtro_widget)

        # ── Tabela ──
        self.tabela = QTableWidget(0, len(self.COLUNAS))
        self.tabela.setStyleSheet("font-size: 11px;")
        self.tabela.setHorizontalHeaderLabels(self.COLUNAS)
        self.tabela.setItemDelegate(EditorDelegate(self.tabela, colunas_numericas=[4, 5]))
        self.tabela.setAlternatingRowColors(True)
        self.tabela.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabela.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tabela.verticalHeader().setVisible(False)

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
        self._rebuild_tabela(self.COLUNAS)
        self.tabela.setColumnHidden(0, False)
        self.tabela.setColumnHidden(2, True)

        painel_tabela_layout.addWidget(self.tabela, stretch=2)

        # ── Área inferior ──
        self.bottom_widget = QWidget()
        bottom_layout = QHBoxLayout(self.bottom_widget)
        bottom_layout.setContentsMargins(0, 8, 0, 0)
        bottom_layout.setSpacing(12)

        self.label_qtde = QLabel("Qtde de itens:")
        self.label_qtde.setObjectName("statusLabel")
        bottom_layout.addWidget(self.label_qtde)

        self.campo_qtde = QLineEdit()
        self.campo_qtde.setFixedHeight(34)
        self.campo_qtde.setFixedWidth(100)
        self.campo_qtde.setPlaceholderText("5")
        self.campo_qtde.setText("5")
        self.campo_qtde.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.campo_qtde.setValidator(QIntValidator(1, 10))
        bottom_layout.addWidget(self.campo_qtde)

        label_impressora = QLabel("Impressora:")
        label_impressora.setObjectName("statusLabel")
        bottom_layout.addWidget(label_impressora)

        self.combo_impressoras = QComboBox()
        self.combo_impressoras.setFixedHeight(34)
        self.combo_impressoras.setMinimumWidth(200)
        self._carregar_impressoras()
        bottom_layout.addWidget(self.combo_impressoras)

        bottom_layout.addStretch()

        self.btn_imprimir = QPushButton("Imprimir")
        self.btn_imprimir.setObjectName("btnSecondary")
        self.btn_imprimir.setFixedHeight(34)
        self.btn_imprimir.clicked.connect(self._abrir_visualizacao_impressao)
        bottom_layout.addWidget(self.btn_imprimir)

        self.btn_gerar = QPushButton("Gerar lista")
        self.btn_gerar.setObjectName("btnPrimary")
        self.btn_gerar.setFixedHeight(34)
        self.btn_gerar.clicked.connect(self._gerar_lista)
        self.btn_gerar.setStyleSheet(
            "QPushButton:disabled { background-color: transparent; color: #94a3b8; border: none; }"
        )
        bottom_layout.addWidget(self.btn_gerar)

        self.btn_prosseguir = QPushButton("Prosseguir")
        self.btn_prosseguir.setObjectName("btnPrimary")
        self.btn_prosseguir.setFixedHeight(34)
        self.btn_prosseguir.clicked.connect(self._prosseguir)
        bottom_layout.addWidget(self.btn_prosseguir)

        painel_tabela_layout.addWidget(self.bottom_widget, stretch=1)

        conteudo_row.addWidget(painel_tabela, stretch=1)

        # ── Card do gráfico de acuracidades (à direita) ──
        grafico_card = QWidget()
        grafico_card.setObjectName("statCard")
        grafico_card.setFixedWidth(320)
        grafico_card_layout = QVBoxLayout(grafico_card)
        grafico_card_layout.setContentsMargins(16, 14, 16, 14)
        grafico_card_layout.setSpacing(8)

        grafico_header = QHBoxLayout()
        self.grafico_titulo = QLabel("Progresso de Acuracidade")
        self.grafico_titulo.setObjectName("sectionTitle")
        grafico_header.addWidget(self.grafico_titulo)
        grafico_header.addStretch()
        self.btn_atualizar_grafico = QPushButton("Atualizar")
        self.btn_atualizar_grafico.setObjectName("btnSecondary")
        self.btn_atualizar_grafico.setFixedHeight(26)
        self.btn_atualizar_grafico.clicked.connect(self._atualizar_grafico)
        grafico_header.addWidget(self.btn_atualizar_grafico)
        grafico_card_layout.addLayout(grafico_header)

        self.canvas_grafico = FigureCanvas(Figure(figsize=(2.6, 2.6)))
        self.canvas_grafico.setMinimumHeight(260)
        self.canvas_grafico.setMinimumWidth(260)
        self.canvas_grafico.setParent(self)
        grafico_card_layout.addWidget(self.canvas_grafico)

        self.grafico_subtitulo = QLabel("")
        self.grafico_subtitulo.setObjectName("pageSubtitle")
        self.grafico_subtitulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        grafico_card_layout.addWidget(self.grafico_subtitulo)

        grafico_card_layout.addStretch()
        conteudo_row.addWidget(grafico_card)

        self.card_layout.addLayout(conteudo_row)

        layout.addWidget(self.card)
        self._atualizar_grafico()

    def _dados_progresso_acuracidade(self):
        """Retorna (acurados, total) de itens já conferidos."""
        caminho_base = self._caminho_jsons()
        arquivo = os.path.join(caminho_base, "Almox", "Acuracidade", "ItensDeEstoque", "ItensDeEstoque.json")
        if not os.path.isfile(arquivo):
            return 0, 0
        try:
            with open(arquivo, "r", encoding="utf-8") as f:
                dados = json.load(f)
        except Exception:
            return 0, 0
        total = len(dados)
        acurados = sum(1 for item in dados if str(item.get("Acuracidade ok", "")).strip())
        return acurados, total

    def _atualizar_grafico(self):
        acurados, total = self._dados_progresso_acuracidade()
        pct = (acurados / total * 100) if total else 0

        self.grafico_subtitulo.setText(
            f"{acurados} de {total} itens acurados" if total else "Nenhum item de estoque cadastrado"
        )

        fig = self.canvas_grafico.figure
        fig.clear()
        ax = fig.add_subplot(111)

        if total == 0:
            ax.text(0.5, 0.5, "Sem itens de estoque", ha="center", va="center",
                    fontsize=12, color="#94a3b8")
            ax.axis("off")
        else:
            ax.pie(
                [acurados, total - acurados],
                colors=["#10b981", "#e5e7eb"],
                startangle=90,
                counterclock=False,
                wedgeprops={"width": 0.28, "edgecolor": "white", "linewidth": 2},
            )
            ax.text(0.5, 0.52, f"{pct:.0f}%", ha="center", va="center",
                    fontsize=26, fontweight="bold", color="#1e1b4b")
            ax.text(0.5, 0.36, "acurado", ha="center", va="center",
                    fontsize=11, color="#94a3b8")
            ax.axis("equal")

        fig.tight_layout()
        self.canvas_grafico.draw()

    def _alternar_modo(self):
        self._modo_acuracidade = not self._modo_acuracidade
        self.bottom_widget.setVisible(True)
        if self._modo_acuracidade:
            self.titulo.setText("Acuracidade")
            self.btn_toggle.setText("Itens de estoque")
            self.label_qtde.setVisible(True)
            self.campo_qtde.setVisible(True)
            self.btn_gerar.setVisible(True)
            self.btn_prosseguir.setVisible(True)
            self.btn_atualizar_itens.setVisible(False)
            self.filtro_widget.setVisible(False)
            self._rebuild_tabela(self.COLUNAS)
            self.tabela.setColumnHidden(0, False)
            self.tabela.setColumnHidden(2, True)
        else:
            self.titulo.setText("Itens de estoque")
            self.btn_toggle.setText("Acuracidade")
            self.label_qtde.setVisible(False)
            self.campo_qtde.setVisible(False)
            self.btn_gerar.setVisible(False)
            self.btn_prosseguir.setVisible(False)
            self.btn_atualizar_itens.setVisible(True)
            self.filtro_widget.setVisible(True)
            self.campo_filtro.clear()
            self._carregar_itens_estoque()

    def _rebuild_tabela(self, colunas):
        self.tabela.setRowCount(0)
        self.tabela.setColumnCount(len(colunas))
        self.tabela.setHorizontalHeaderLabels(colunas)
        header = self.tabela.horizontalHeader()
        header.setStretchLastSection(False)
        for i in range(len(colunas)):
            self.tabela.setColumnHidden(i, False)

        if colunas == self.COLUNAS:
            widths = {0: 130, 1: 120, 2: 180, 3: 110, 4: 110, 5: 110, 6: 100, 7: 250}
            for i, w in widths.items():
                if i < len(colunas):
                    if i == 7:
                        header.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)
                    else:
                        header.setSectionResizeMode(i, QHeaderView.ResizeMode.Fixed)
                        self.tabela.setColumnWidth(i, w)
        else:
            widths = {0: 100, 1: 120, 2: 300, 3: 110, 4: 100, 5: 120}
            for i, w in widths.items():
                if i < len(colunas):
                    if i == 2:
                        header.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)
                    else:
                        header.setSectionResizeMode(i, QHeaderView.ResizeMode.Fixed)
                        self.tabela.setColumnWidth(i, w)

    def _carregar_itens_estoque(self):
        caminho_base = self._caminho_jsons()
        arquivo = os.path.join(caminho_base, "Almox", "Acuracidade", "ItensDeEstoque", "ItensDeEstoque.json")

        self._rebuild_tabela(self.COLUNAS_ESTOQUE)

        if not os.path.isfile(arquivo):
            return

        try:
            with open(arquivo, "r", encoding="utf-8") as f:
                dados = json.load(f)
        except Exception:
            return

        self._dados_estoque = dados
        self._popular_tabela_estoque(dados)

    def _aplicar_filtro(self, texto):
        if not hasattr(self, "_dados_estoque"):
            return
        texto = texto.strip().lower()
        if not texto:
            self._popular_tabela_estoque(self._dados_estoque)
            return
        filtrados = [
            item for item in self._dados_estoque
            if texto in str(item.get("Kardex", "")).lower()
            or texto in str(item.get("Código", "")).lower()
            or texto in str(item.get("Descrição", "")).lower()
            or texto in str(item.get("Loc novo", "")).lower()
        ]
        self._popular_tabela_estoque(filtrados)

    def _gerar_lista(self):
        texto = self.campo_qtde.text().strip()
        if not texto:
            QMessageBox.warning(self, "Aviso", "Informe a quantidade de itens.")
            return
        try:
            qtde = int(texto)
        except ValueError:
            QMessageBox.warning(self, "Aviso", "Quantidade inválida.")
            return
        if qtde < 1 or qtde > 10:
            QMessageBox.warning(self, "Aviso", "A quantidade deve ser entre 1 e 10.")
            return

        caminho_base = self._caminho_jsons()
        arquivo = os.path.join(caminho_base, "Almox", "Acuracidade", "ItensDeEstoque", "ItensDeEstoque.json")

        if not os.path.isfile(arquivo):
            QMessageBox.warning(self, "Aviso", "Arquivo ItensDeEstoque.json não encontrado.\nClique em 'Atualizar itens' primeiro.")
            return

        try:
            with open(arquivo, "r", encoding="utf-8") as f:
                dados = json.load(f)
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao ler arquivo:\n{e}")
            return

        pendentes = [
            item for item in dados
            if str(item.get("Acuracidade ok", "")).strip() == ""
        ]

        if not pendentes:
            QMessageBox.information(self, "Acuracidade", "Todos os itens já foram conferidos.")
            return

        random.shuffle(pendentes)
        selecionados = pendentes[:qtde]

        self._mapa_kardex_qtde = {}
        for item in selecionados:
            kardex = str(item.get("Kardex", ""))
            qtde_novo = str(item.get("Qtde novo", "")).strip()
            if not qtde_novo:
                qtde_novo = self._buscar_qtde_novo(kardex)
            self._mapa_kardex_qtde[kardex] = qtde_novo

        self.tabela.setRowCount(0)
        self.tabela.setRowCount(len(selecionados))
        for row, item in enumerate(selecionados):
            self.tabela.setItem(row, 0, QTableWidgetItem(str(item.get("Kardex", ""))))
            self.tabela.setItem(row, 1, QTableWidgetItem(str(item.get("Código", ""))))
            self.tabela.setItem(row, 2, QTableWidgetItem(str(item.get("Descrição", ""))))
            self.tabela.setItem(row, 3, QTableWidgetItem(str(item.get("Loc novo", ""))))
            self.tabela.setItem(row, 4, QTableWidgetItem(""))
            self.tabela.setItem(row, 5, QTableWidgetItem(""))
            self.tabela.setItem(row, 6, QTableWidgetItem(""))
            self.tabela.setItem(row, 7, QTableWidgetItem(""))

        self._prosseguir_count = 0
        self._bloquear_colunas([0, 1, 2, 3, 5, 6, 7])
        self._desbloquear_coluna(4)
        self.btn_gerar.setEnabled(False)

    def _bloquear_colunas(self, colunas):
        flags_readonly = Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled
        for row in range(self.tabela.rowCount()):
            for col in colunas:
                item = self.tabela.item(row, col)
                if item:
                    item.setFlags(flags_readonly)

    def _desbloquear_coluna(self, col):
        flags_editable = Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsEditable
        for row in range(self.tabela.rowCount()):
            item = self.tabela.item(row, col)
            if item:
                item.setFlags(flags_editable)

    def _bloquear_tudo(self):
        self._bloquear_colunas(range(self.tabela.columnCount()))

    def _marcar_acuracidade_ok(self):
        caminho_base = self._caminho_jsons()
        if not caminho_base:
            import config
            config.avisar_sem_pasta(self)
            return
        arquivo = os.path.join(caminho_base, "Almox", "Acuracidade", "ItensDeEstoque", "ItensDeEstoque.json")

        if not os.path.isfile(arquivo):
            return

        try:
            with open(arquivo, "r", encoding="utf-8") as f:
                dados = json.load(f)
        except Exception:
            return

        kardexes_processados = set()
        for row in range(self.tabela.rowCount()):
            item = self.tabela.item(row, 0)
            if item:
                kardexes_processados.add(item.text())

        for item in dados:
            if str(item.get("Kardex", "")) in kardexes_processados:
                item["Acuracidade ok"] = "OK"

        try:
            with open(arquivo, "w", encoding="utf-8") as f:
                json.dump(dados, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _prosseguir(self):
        if self.tabela.rowCount() == 0:
            QMessageBox.warning(self, "Aviso", "Gere a lista antes de prosseguir.")
            return

        if self._prosseguir_count == 0:
            for row in range(self.tabela.rowCount()):
                item = self.tabela.item(row, 4)
                if not item or not item.text().strip():
                    QMessageBox.warning(self, "Aviso", "Preencha todas as células de Primeira contagem.")
                    return
            self._comparar_primeira_contagem()
            self._bloquear_colunas([4])
            self._desbloquear_coluna(5)
            self._prosseguir_count = 1
        else:
            for row in range(self.tabela.rowCount()):
                item = self.tabela.item(row, 5)
                if not item or not item.text().strip():
                    QMessageBox.warning(self, "Aviso", "Preencha todas as células de Segunda contagem.")
                    return
                if self._para_float(item.text()) is None:
                    QMessageBox.warning(self, "Aviso", f"Valor inválido na Segunda contagem (linha {row + 1}).")
                    return
            self._calcular_divergencia()
            self._bloquear_tudo()
            self._prosseguir_count = 2
            self.btn_gerar.setEnabled(True)
            self._marcar_acuracidade_ok()

        lista = []
        for row in range(self.tabela.rowCount()):
            item = {}
            for col in range(self.tabela.columnCount()):
                header = self.tabela.horizontalHeaderItem(col).text().replace("\n", " ")
                cell = self.tabela.item(row, col)
                item[header] = cell.text() if cell else ""
            lista.append(item)

        hoje = date.today()
        caminho_base = self._caminho_jsons()
        if not caminho_base:
            import config
            config.avisar_sem_pasta(self)
            return
        pasta = os.path.join(caminho_base, "Almox", "Acuracidade", str(hoje.year), f"{hoje.month:02d}")
        os.makedirs(pasta, exist_ok=True)

        seq = 1
        while os.path.isfile(os.path.join(pasta, f"{hoje.day}.{seq}.json")):
            seq += 1
        arquivo = os.path.join(pasta, f"{hoje.day}.{seq}.json")

        try:
            with open(arquivo, "w", encoding="utf-8") as f:
                json.dump(lista, f, ensure_ascii=False, indent=2)
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao salvar arquivo:\n{e}")
            return

        if self._prosseguir_count == 2:
            self._atualizar_grafico()

    @staticmethod
    def _para_float(texto):
        """Converte número no formato brasileiro ('1.800,50') para float."""
        texto = str(texto).strip().replace(" ", "")
        if not texto:
            return None
        try:
            if "," in texto:
                texto = texto.replace(".", "").replace(",", ".")
            elif texto.count(".") > 1:
                texto = texto.replace(".", "")
            return float(texto)
        except ValueError:
            return None

    def _comparar_primeira_contagem(self):
        for row in range(self.tabela.rowCount()):
            kardex_item = self.tabela.item(row, 0)
            contagem_item = self.tabela.item(row, 4)
            if not kardex_item or not contagem_item:
                continue

            kardex = kardex_item.text()
            contagem_texto = contagem_item.text().strip()

            if not contagem_texto:
                continue

            qtde_novo = self._mapa_kardex_qtde.get(kardex, "")
            valor_contagem = self._para_float(contagem_texto)
            valor_sistema = self._para_float(qtde_novo)
            if valor_contagem is not None and valor_sistema is not None:
                diverge = valor_contagem != valor_sistema
            else:
                diverge = contagem_texto != qtde_novo
            if diverge:
                contagem_item.setForeground(QColor("red"))
            else:
                contagem_item.setForeground(QColor())

    def _calcular_divergencia(self):
        for row in range(self.tabela.rowCount()):
            kardex_item = self.tabela.item(row, 0)
            segunda_item = self.tabela.item(row, 5)
            divergencia_item = self.tabela.item(row, 6)
            if not kardex_item or not segunda_item or not divergencia_item:
                continue

            kardex = kardex_item.text()
            segunda_texto = segunda_item.text().strip()

            if not segunda_texto:
                continue

            segunda_qtde = self._para_float(segunda_texto)
            if segunda_qtde is None:
                continue

            qtde_novo_texto = self._mapa_kardex_qtde.get(kardex, "")
            qtde_novo = self._para_float(qtde_novo_texto)
            if qtde_novo is None:
                continue

            divergencia = segunda_qtde - qtde_novo
            divergencia_item.setText(str(int(divergencia) if divergencia == int(divergencia) else divergencia))
            if divergencia != 0:
                divergencia_item.setForeground(QColor("red"))
                segunda_item.setForeground(QColor("red"))
            else:
                divergencia_item.setForeground(QColor())
                segunda_item.setForeground(QColor())

    def _caminho_jsons(self):
        import config
        base = config.obter_caminho_jsons()
        if not base:
            return ""
        return os.path.normpath(base)

    def _buscar_qtde_novo(self, kardex):
        caminho_base = self._caminho_jsons()
        origem = os.path.join(caminho_base, "Almox", "ItensAlmoxarifado", "ItensAlmoxarifado.json")
        if not os.path.isfile(origem):
            return ""
        try:
            with open(origem, "r", encoding="utf-8") as f:
                dados = json.load(f)
            for item in dados:
                if str(item.get("Kardex", "")) == kardex:
                    return str(item.get("Qtde novo", ""))
        except Exception:
            pass
        return ""

    def _atualizar_itens(self):
        caminho_base = self._caminho_jsons()
        if not caminho_base:
            import config
            config.avisar_sem_pasta(self)
            return
        origem = os.path.join(caminho_base, "Almox", "ItensAlmoxarifado", "ItensAlmoxarifado.json")

        if not os.path.isfile(origem):
            QMessageBox.warning(self, "Aviso", f"Arquivo não encontrado:\n{origem}")
            return

        try:
            with open(origem, "r", encoding="utf-8") as f:
                dados = json.load(f)
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao ler arquivo:\n{e}")
            return

        itens_estoque = []
        for item in dados:
            if str(item.get("Item de estoque", "")).strip().lower() == "true" and str(item.get("Loc novo", "")).strip() != "":
                itens_estoque.append({
                    "Kardex": item.get("Kardex", ""),
                    "Código": item.get("Código", ""),
                    "Descrição": item.get("Descrição", ""),
                    "Loc novo": item.get("Loc novo", ""),
                    "Qtde novo": item.get("Qtde novo", ""),
                    "Acuracidade ok": "",
                })

        pasta_destino = os.path.join(caminho_base, "Almox", "Acuracidade", "ItensDeEstoque")
        os.makedirs(pasta_destino, exist_ok=True)
        arquivo_destino = os.path.join(pasta_destino, "ItensDeEstoque.json")

        try:
            with open(arquivo_destino, "w", encoding="utf-8") as f:
                json.dump(itens_estoque, f, ensure_ascii=False, indent=2)
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao salvar arquivo:\n{e}")
            return

        self._popular_tabela_estoque(itens_estoque)
        self._atualizar_grafico()
        QMessageBox.information(
            self, "Acuracidade",
            f"{len(itens_estoque)} itens de estoque salvos com sucesso!"
        )

    def _popular_tabela_estoque(self, itens):
        self._rebuild_tabela(self.COLUNAS_ESTOQUE)
        self.tabela.setRowCount(len(itens))
        self.label_contador_estoque.setText(f"Itens: {len(itens)}")
        for row, item in enumerate(itens):
            self.tabela.setItem(row, 0, QTableWidgetItem(str(item.get("Kardex", ""))))
            self.tabela.setItem(row, 1, QTableWidgetItem(str(item.get("Código", ""))))
            self.tabela.setItem(row, 2, QTableWidgetItem(str(item.get("Descrição", ""))))
            self.tabela.setItem(row, 3, QTableWidgetItem(str(item.get("Loc novo", ""))))
            self.tabela.setItem(row, 4, QTableWidgetItem(str(item.get("Qtde novo", ""))))
            self.tabela.setItem(row, 5, QTableWidgetItem(str(item.get("Acuracidade ok", ""))))

    def _carregar_impressoras(self):
        self.combo_impressoras.clear()
        impressoras = QPrinterInfo.availablePrinterNames()
        if impressoras:
            self.combo_impressoras.addItems(impressoras)
            padrao = QPrinterInfo.defaultPrinterName()
            if padrao in impressoras:
                self.combo_impressoras.setCurrentText(padrao)
        else:
            self.combo_impressoras.addItem("Nenhuma impressora disponível")

    def _abrir_visualizacao_impressao(self):
        if self.tabela.rowCount() == 0:
            QMessageBox.warning(self, "Aviso", "Não há dados na tabela para imprimir.")
            return

        nome_impressora = self.combo_impressoras.currentText()
        if nome_impressora and nome_impressora != "Nenhuma impressora disponível":
            printer_info = QPrinterInfo.printerInfo(nome_impressora)
            printer = QPrinter(printer_info) if not printer_info.isNull() else QPrinter()
        else:
            printer = QPrinter()

        printer.setPageOrientation(QPageLayout.Orientation.Landscape)
        printer.setPageMargins(QMarginsF(10, 10, 10, 10))

        preview = QPrintPreviewDialog(printer, self)
        preview.setWindowTitle("Visualização de Impressão - Acuracidade")
        preview.resize(1050, 750)
        preview.paintRequested.connect(self._renderizar_impressao)
        preview.exec()

    def _renderizar_impressao(self, printer):
        printer.setPageOrientation(QPageLayout.Orientation.Landscape)
        titulo_doc = self.titulo.text()
        meses = ["", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
                 "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
        hoje = date.today()
        data_formatada = f"{hoje.day:02d} de {meses[hoje.month]} de {hoje.year}"

        caminho_base = self._caminho_jsons()
        pasta_assets = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "ui", "assets")
        caminho_imagem = os.path.join(pasta_assets, "versigent.png").replace("\\", "/")

        html = f"""
        <html>
        <head>
            <style>
                @page {{ size: landscape; margin: 10mm; }}
                body {{ font-family: 'Segoe UI', Arial, sans-serif; font-size: 11px; margin: 0; padding: 10px; color: #1e293b; width: 100%; }}
                .header {{ text-align: center; margin-bottom: 15px; position: relative; }}
                .header h2 {{ margin: 0 0 4px 0; color: #0f172a; font-size: 18px; }}
                .header p {{ margin: 0; color: #64748b; font-size: 11px; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 10px; table-layout: fixed; }}
                th {{ background-color: #f1f5f9; color: #334155; font-size: 10px; font-weight: bold; border: 1px solid #cbd5e1; padding: 6px 8px; text-transform: uppercase; text-align: center; word-wrap: break-word; }}
                td {{ border: 1px solid #cbd5e1; padding: 5px 8px; font-size: 10px; text-align: center; word-wrap: break-word; }}
                tr:nth-child(even) {{ background-color: #f8fafc; }}
            </style>
        </head>
        <body>
            <div class="header">
                <img src="file:///{caminho_imagem}" style="position: absolute; right: 0; top: 0;" width="80">
                <h2>Relatório de {titulo_doc}</h2>
            </div>
            <table style="width: 100%; border-collapse: collapse; table-layout: fixed;">
                <thead>
                    <tr>
        """

        colunas_visiveis = []
        larguras = {0: 120, 1: 140, 3: 90, 4: 80, 5: 80, 6: 90, 7: 180}
        estilo_borda = 'border: 1px solid #cbd5e1;'
        for col in range(self.tabela.columnCount()):
            if not self.tabela.isColumnHidden(col):
                colunas_visiveis.append(col)
                header_item = self.tabela.horizontalHeaderItem(col)
                header_text = header_item.text() if header_item else f"Col {col}"
                header_text_html = header_text.replace("\n", "<br>")
                w = larguras.get(col)
                if w:
                    html += f'<th width="{w}" style="{estilo_borda} background-color: #f1f5f9; font-size: 10px; font-weight: bold; text-transform: uppercase; text-align: center; padding: 6px 8px;">{header_text_html}</th>'
                else:
                    html += f'<th style="{estilo_borda} background-color: #f1f5f9; font-size: 10px; font-weight: bold; text-transform: uppercase; text-align: center; padding: 6px 8px;">{header_text_html}</th>'

        html += """
                    </tr>
                </thead>
                <tbody>
        """

        for row in range(self.tabela.rowCount()):
            html += "<tr>"
            for col in colunas_visiveis:
                item = self.tabela.item(row, col)
                texto = item.text() if item else ""
                w = larguras.get(col)
                if w:
                    html += f'<td width="{w}" style="{estilo_borda} text-align: center; padding: 5px 8px; font-size: 10px;">{texto}</td>'
                else:
                    html += f'<td style="{estilo_borda} text-align: center; padding: 5px 8px; font-size: 10px;">{texto}</td>'
            html += "</tr>"

        num_linhas = self.tabela.rowCount()
        altura_linha = 18
        altura_header = 60
        altura_tabela = altura_header + (num_linhas * altura_linha) + 20
        page_height = printer.pageRect(QPrinter.Unit.Point).size().height()
        altura_spacer = max(int(page_height) - altura_tabela - 50, 20)

        html += f"""
                </tbody>
            </table>
            <div style="height: {altura_spacer}px;">&nbsp;</div>
            <div style="text-align: left; font-size: 10px; color: #64748b;">
                {data_formatada}
            </div>
        </body>
        </html>
        """

        doc = QTextDocument()
        page_size = printer.pageRect(QPrinter.Unit.Point).size()
        if page_size.width() > 0:
            doc.setPageSize(page_size)
        doc.setHtml(html)
        doc.print_(printer)

