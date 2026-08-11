import json
import os

import qtawesome

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QStyledItemDelegate,
)
from PySide6.QtCore import Qt, QSize

import config


def _caminho_json():
    base = config.obter_caminho_jsons()
    if not base:
        return ""
    return os.path.normpath(os.path.join(base, "Almox", "FreshStart", "fresh_start.json"))


def _caminho_zcentral():
    base = config.obter_caminho_jsons()
    if not base:
        return ""
    return os.path.normpath(os.path.join(base, "Almox", "zCentral.prn"))


def _caminho_estoque():
    base = config.obter_caminho_jsons()
    if not base:
        return ""
    return os.path.normpath(os.path.join(base, "Almox", "ItensAlmoxarifado", "ItensAlmoxarifado.json"))


def _caminho_zcusto():
    base = config.obter_caminho_jsons()
    if not base:
        return ""
    return os.path.normpath(os.path.join(base, "Almox", "zCusto.prn"))


def _parse_numero(texto):
    texto = texto.strip()
    if not texto:
        return 0.0
    return float(texto.replace(".", "").replace(",", "."))


class EditorDelegate(QStyledItemDelegate):
    def sizeHint(self, option, index):
        base = super().sizeHint(option, index)
        return QSize(base.width(), max(base.height(), 34))


class FreshStartPage(QWidget):
    COLUNAS = [
        "Local", "Kardex", "Descrição", "Loc", "Qtde Qad", "Qtde Sci",
        "Compras", "Fornecedor", "Pedido", "Lugar transferido",
    ]
    CHAVES = [
        "local", "kardex", "descricao", "loc", "qtde_qad", "qtde_sci",
        "compras", "fornecedor", "pedido", "lugar_transferido",
    ]

    def __init__(self):
        super().__init__()
        self.dados = []
        self._setup_ui()
        self._carregar_dados()

    # ── UI ──
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        header_layout = QHBoxLayout()
        header_texts = QVBoxLayout()
        header_texts.setSpacing(4)
        titulo = QLabel("Fresh Start")
        titulo.setObjectName("pageTitle")
        header_texts.addWidget(titulo)
        subtitulo = QLabel("Itens para o novo início / transferência")
        subtitulo.setObjectName("pageSubtitle")
        header_texts.addWidget(subtitulo)
        header_layout.addLayout(header_texts)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        table_card = QWidget()
        table_card.setObjectName("pageCard")
        table_card_layout = QVBoxLayout(table_card)
        table_card_layout.setContentsMargins(18, 14, 18, 14)
        table_card_layout.setSpacing(10)

        # ── Filtro ──
        filter_row = QHBoxLayout()
        filter_row.setSpacing(8)

        btn_atualizar = QPushButton(qtawesome.icon('fa6s.rotate', color='#ffffff'), "  Atualizar")
        btn_atualizar.setObjectName("btnPrimary")
        btn_atualizar.setFixedHeight(32)
        btn_atualizar.clicked.connect(self._atualizar_do_prn)
        filter_row.addWidget(btn_atualizar)

        self.campo_filtro = QLineEdit()
        self.campo_filtro.setPlaceholderText("Pesquisar...")
        self.campo_filtro.setFixedHeight(30)
        self.campo_filtro.setFixedWidth(220)
        self.campo_filtro.textChanged.connect(self._aplicar_filtro)
        filter_row.addWidget(self.campo_filtro)

        filter_row.addStretch()

        self.label_contador = QLabel("0 itens")
        self.label_contador.setObjectName("statusLabel")
        filter_row.addWidget(self.label_contador)

        table_card_layout.addLayout(filter_row)

        self.tabela = QTableWidget(0, len(self.COLUNAS))
        self.tabela.setObjectName("tabelaFreshStart")
        self.tabela.setHorizontalHeaderLabels(self.COLUNAS)
        header = self.tabela.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        larguras = [50, 140, 200, 100, 100, 100, 100, 150, 100]
        for c, largura in enumerate(larguras):
            header.resizeSection(c, largura)
        self.tabela.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabela.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked)
        self.tabela.setAlternatingRowColors(True)
        self.tabela.setWordWrap(False)
        self.tabela.verticalHeader().setDefaultSectionSize(34)
        self.tabela.verticalHeader().setVisible(False)
        self.tabela.setItemDelegate(EditorDelegate(self.tabela))
        self.tabela.itemChanged.connect(self._item_modificado)
        table_card_layout.addWidget(self.tabela)

        total_row = QHBoxLayout()
        total_row.setSpacing(8)
        total_row.addStretch()
        label_total = QLabel("Valor total zCentral:")
        label_total.setObjectName("statusLabel")
        total_row.addWidget(label_total)
        self.label_total_zcentral = QLabel("R$ 0,00")
        self.label_total_zcentral.setObjectName("statusLabel")
        self.label_total_zcentral.setStyleSheet("font-size: 15px; font-weight: 700; color: #6366f1;")
        total_row.addWidget(self.label_total_zcentral)
        table_card_layout.addLayout(total_row)

        layout.addWidget(table_card)

        self._inserir_linha_vazia()

    # ── Dados ──
    def _carregar_dados(self):
        caminho = _caminho_json()
        if not caminho:
            return
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                dados = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            dados = []
        self.dados = [
            {chave: str(item.get(chave, "")) for chave in self.CHAVES}
            for item in dados
        ]
        self._popular_tabela()
        self._calcular_total_zcentral()

    def _salvar_json(self):
        caminho = _caminho_json()
        if not caminho:
            config.avisar_sem_pasta(self)
            return
        try:
            os.makedirs(os.path.dirname(caminho), exist_ok=True)
            with open(caminho, "w", encoding="utf-8") as f:
                json.dump(self.dados, f, ensure_ascii=False, indent=2)
        except OSError:
            pass

    # ── Atualizar (zCentral.prn) ──
    def _atualizar_do_prn(self):
        caminho = _caminho_zcentral()
        if not caminho:
            config.avisar_sem_pasta(self)
            return
        if not os.path.exists(caminho):
            config.avisar_sem_pasta(self)
            return

        novos = []
        with open(caminho, "r", encoding="latin-1") as f:
            for linha in f:
                linha = linha.rstrip("\n")
                if len(linha) < 80:
                    continue
                local = linha[0:9].strip()
                kardex = linha[18:37].strip()
                loc = linha[37:56].strip()
                qtde_qad = linha[60:72].strip()
                if local.isdigit() and kardex and loc and qtde_qad:
                    novos.append({
                        "local": local,
                        "kardex": kardex,
                        "loc": loc,
                        "qtde_qad": qtde_qad,
                    })

        if not novos:
            return

        estoque_por_kardex = {}
        caminho_estoque = _caminho_estoque()
        if caminho_estoque and os.path.exists(caminho_estoque):
            try:
                with open(caminho_estoque, "r", encoding="utf-8") as f:
                    for item in json.load(f):
                        k = str(item.get("Kardex", "")).strip().upper()
                        if k:
                            estoque_por_kardex[k] = item
            except (FileNotFoundError, json.JSONDecodeError):
                pass

        por_chave = {
            (item.get("local", ""), item.get("kardex", "").upper(), item.get("loc", "").upper()): item
            for item in self.dados
        }
        for item in novos:
            chave = (item["local"], item["kardex"].upper(), item["loc"].upper())
            existente = por_chave.get(chave)
            estoque = estoque_por_kardex.get(item["kardex"].upper())
            if estoque is not None:
                item["descricao"] = str(estoque.get("Descrição", ""))
                item["qtde_sci"] = str(estoque.get("Qtde novo", ""))
                item["fornecedor"] = str(estoque.get("Fornecedor", ""))
            if existente is not None:
                existente["loc"] = item["loc"]
                existente["qtde_qad"] = item["qtde_qad"]
                if estoque is not None:
                    existente["descricao"] = item["descricao"]
                    existente["qtde_sci"] = item["qtde_sci"]
                    existente["fornecedor"] = item["fornecedor"]
            else:
                novo_item = {chave: "" for chave in self.CHAVES}
                novo_item.update(item)
                self.dados.append(novo_item)
                por_chave[chave] = novo_item

        self._salvar_json()
        self._popular_tabela()
        self._calcular_total_zcentral()

    # ── Custo zCentral ──
    def _ler_custos_unitarios(self):
        caminho = _caminho_zcusto()
        if not caminho or not os.path.exists(caminho):
            return {}
        custos = {}
        with open(caminho, "r", encoding="latin-1") as f:
            for linha in f:
                linha = linha.rstrip("\n")
                if len(linha) < 120:
                    continue
                codigo = linha[1:19].strip()
                if not codigo:
                    continue
                if codigo.startswith("-") or not (codigo[0].isdigit() or codigo[0].isalpha()):
                    continue
                custo = linha[105:118].strip()
                if custo and custo != "0,00" and any(ch.isdigit() for ch in custo):
                    custos[codigo.upper()] = _parse_numero(custo)
        return custos

    def _calcular_total_zcentral(self):
        total = 0.0
        custos = self._ler_custos_unitarios()
        for item in self.dados:
            kardex = str(item.get("kardex", "")).strip()
            if not kardex:
                continue
            custo = custos.get(kardex.upper(), 0.0)
            qtde = _parse_numero(str(item.get("qtde_qad", "")))
            total += custo * qtde
        self.label_total_zcentral.setText(f"R$ {total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

    # ── Tabela ──
    def _popular_tabela(self):
        self.tabela.blockSignals(True)
        self.tabela.setRowCount(0)
        filtro = self.campo_filtro.text().strip().lower()
        for idx, item in enumerate(self.dados):
            if filtro:
                texto = " ".join(str(v) for v in item.values()).lower()
                if filtro not in texto:
                    continue
            row = self.tabela.rowCount()
            self.tabela.insertRow(row)
            for col, chave in enumerate(self.CHAVES):
                cell = QTableWidgetItem(str(item.get(chave, "")))
                cell.setFlags(cell.flags() | Qt.ItemFlag.ItemIsEditable)
                self.tabela.setItem(row, col, cell)
            origem = self.tabela.item(row, 0)
            origem.setData(Qt.ItemDataRole.UserRole, idx)
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

    def _item_modificado(self, item):
        row = item.row()
        col = item.column()
        chave = self.CHAVES[col]

        idx = None
        celula_origem = self.tabela.item(row, 0)
        if celula_origem:
            origem = celula_origem.data(Qt.ItemDataRole.UserRole)
            if isinstance(origem, int):
                idx = origem

        if idx is None:
            if row != self.tabela.rowCount() - 1:
                return
            if item.text().strip():
                novo_item = {}
                for c, ch in enumerate(self.CHAVES):
                    celula = self.tabela.item(row, c)
                    novo_item[ch] = celula.text().strip() if celula else ""
                self.dados.append(novo_item)
                celula_origem.setData(Qt.ItemDataRole.UserRole, len(self.dados) - 1)
                self._salvar_json()
                self._inserir_linha_vazia()
            return

        self.dados[idx][chave] = item.text()
        self._salvar_json()
        if chave == "qtde_qad":
            self._calcular_total_zcentral()

    def _aplicar_filtro(self):
        self._popular_tabela()

    def _atualizar_contador(self):
        total = max(0, self.tabela.rowCount() - 1)
        self.label_contador.setText(f"{total} itens")
