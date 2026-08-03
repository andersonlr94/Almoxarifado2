import json
import os
import random
from datetime import date

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QStyledItemDelegate, QMessageBox,
)
from PySide6.QtCore import Qt, QSize, QLocale
from PySide6.QtGui import QGuiApplication, QColor, QDoubleValidator


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
        "Primeira contagem", "Segunda contagem", "Divergência", "Observação",
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
        self.filtro_widget.setVisible(False)
        self.card_layout.addWidget(self.filtro_widget)

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
        header.setStretchLastSection(True)
        for i in range(len(self.COLUNAS)):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)

        self.tabela.setStyleSheet(
            "QTableWidget { font-size: 11px; gridline-color: #e2e8f0; }"
            "QTableWidget::item { padding: 6px 12px; }"
            "QTableWidget::item:selected { background-color: #dbeafe; color: #1e293b; }"
        )

        self.tabela.setColumnHidden(0, True)

        self.card_layout.addWidget(self.tabela, stretch=2)

        # ── Área inferior (só aparece no modo acuracidade) ──
        self.bottom_widget = QWidget()
        bottom_layout = QHBoxLayout(self.bottom_widget)
        bottom_layout.setContentsMargins(0, 8, 0, 0)
        bottom_layout.setSpacing(12)

        label_qtde = QLabel("Qtde de itens:")
        label_qtde.setObjectName("statusLabel")
        bottom_layout.addWidget(label_qtde)

        self.campo_qtde = QLineEdit()
        self.campo_qtde.setFixedHeight(34)
        self.campo_qtde.setFixedWidth(100)
        self.campo_qtde.setPlaceholderText("0")
        self.campo_qtde.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bottom_layout.addWidget(self.campo_qtde)

        bottom_layout.addStretch()

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

        self.card_layout.addWidget(self.bottom_widget, stretch=1)

        layout.addWidget(self.card)

    def _alternar_modo(self):
        self._modo_acuracidade = not self._modo_acuracidade
        if self._modo_acuracidade:
            self.titulo.setText("Acuracidade")
            self.btn_toggle.setText("Itens de estoque")
            self.bottom_widget.setVisible(True)
            self.btn_atualizar_itens.setVisible(False)
            self.filtro_widget.setVisible(False)
            self._rebuild_tabela(self.COLUNAS)
            self.tabela.setColumnHidden(0, True)
        else:
            self.titulo.setText("Itens de estoque")
            self.btn_toggle.setText("Acuracidade")
            self.bottom_widget.setVisible(False)
            self.btn_atualizar_itens.setVisible(True)
            self.filtro_widget.setVisible(True)
            self.campo_filtro.clear()
            self._carregar_itens_estoque()

    def _rebuild_tabela(self, colunas):
        self.tabela.setRowCount(0)
        self.tabela.setColumnCount(len(colunas))
        self.tabela.setHorizontalHeaderLabels(colunas)
        header = self.tabela.horizontalHeader()
        for i in range(len(colunas)):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)

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
        self._bloquear_colunas([1, 2, 3, 5, 6])
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
                try:
                    float(item.text().strip())
                except ValueError:
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
                header = self.tabela.horizontalHeaderItem(col).text()
                cell = self.tabela.item(row, col)
                item[header] = cell.text() if cell else ""
            lista.append(item)

        hoje = date.today()
        caminho_base = self._caminho_jsons()
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
            if contagem_texto != qtde_novo:
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

            try:
                segunda_qtde = float(segunda_texto)
            except ValueError:
                continue

            qtde_novo_texto = self._mapa_kardex_qtde.get(kardex, "")
            try:
                qtde_novo = float(qtde_novo_texto)
            except ValueError:
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
            base = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "jsons")
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
            if str(item.get("Item de estoque", "")).strip().lower() == "true":
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
        QMessageBox.information(
            self, "Acuracidade",
            f"{len(itens_estoque)} itens de estoque salvos com sucesso!"
        )

    def _popular_tabela_estoque(self, itens):
        self._rebuild_tabela(self.COLUNAS_ESTOQUE)
        self.tabela.setRowCount(len(itens))
        for row, item in enumerate(itens):
            self.tabela.setItem(row, 0, QTableWidgetItem(str(item.get("Kardex", ""))))
            self.tabela.setItem(row, 1, QTableWidgetItem(str(item.get("Código", ""))))
            self.tabela.setItem(row, 2, QTableWidgetItem(str(item.get("Descrição", ""))))
            self.tabela.setItem(row, 3, QTableWidgetItem(str(item.get("Loc novo", ""))))
            self.tabela.setItem(row, 4, QTableWidgetItem(str(item.get("Qtde novo", ""))))
            self.tabela.setItem(row, 5, QTableWidgetItem(str(item.get("Acuracidade ok", ""))))
