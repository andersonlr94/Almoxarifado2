import json
import os
from datetime import datetime, timedelta

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QPlainTextEdit, QSplitter,
    QApplication,
)
from PySide6.QtCore import Qt, QEvent
from ui.regras_automacao import esperar_inicio, digitar_texto, enter

DADOS_AE = {
    "STMUCONS": ("STMUCONS Uso e consumo", "6325", "CC55", ""),
    "STAFINDD": ("STAFINDD Primeira Saida", "6325", "CC60", ""),
    "STATFIXO": ("STATFIXO Mais de cinco anos", "6325", "CC60", ""),
    "SRMEMPAT": ("SRMEMPAT Circulação de ferramentas", "3295", "99200", ""),
    "SRMTTDES": ("SRMTTDES Remessa de teste sem retorno para não Aptiv", "8390", "09430", "5032"),
    "SRMINDAF": ("SMMINDAF Remessa para industrialização", "3295", "99200", ""),
    "SRMCONSE": ("SRMCONSE Remessa para conserto", "3295", "99200", ""),
    "STEMBALA": ("STEMBALA Remessa de embalagens (Caixas plasticas)", "3295", "99200", ""),
    "SRMTTRET": ("SRMTTRET Remessa de produto Aptiv para teste com retorno", "2400ADA", "99200", ""),
}


def _caminho_pasta_anotacoes():
    import config
    base = config.obter_caminho_jsons()
    if not base:
        base = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "jsons")
    return os.path.normpath(os.path.join(base, "Almox", "aeAnotacoes"))


def limpar_arquivos_antigos(pasta, dias=30):
    limite = datetime.now() - timedelta(days=dias)
    try:
        for nome in os.listdir(pasta):
            if not nome.endswith(".json"):
                continue
            caminho = os.path.join(pasta, nome)
            try:
                data_arquivo = datetime.strptime(nome.replace(".json", ""), "%d-%m-%Y")
                if data_arquivo < limite:
                    os.remove(caminho)
            except (ValueError, OSError):
                pass
    except FileNotFoundError:
        pass


HEADERS_TABELA = [
    "Item", "Descrição", "Qtde", "UM",
    "Custo", "Clas. fiscal", "Classe", "C-M",
]

INDICE_ITEM = 0
INDICE_QTDE = 2


class DigitarAEPage(QWidget):
    def __init__(self):
        super().__init__()
        self._setup_ui()
        self._carregar_anotacoes()
        self._popular_combo_anotacoes()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(16)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        pagina_esquerda = QWidget()
        pagina_esquerda_layout = QVBoxLayout(pagina_esquerda)
        pagina_esquerda_layout.setContentsMargins(0, 0, 0, 0)
        pagina_esquerda_layout.setSpacing(16)

        card_principal = QWidget()
        card_principal.setObjectName("pageCard")
        card_layout = QVBoxLayout(card_principal)
        card_layout.setContentsMargins(28, 28, 28, 28)
        card_layout.setSpacing(16)

        titulo = QLabel("Digitar AE")
        titulo.setObjectName("pageTitle")
        card_layout.addWidget(titulo)

        self.label_descricao_ae = QLabel("")
        self.label_descricao_ae.setObjectName("pageSubtitle")
        self.label_descricao_ae.setStyleSheet("font-size: 13px; font-weight: 600; color: #a0a0a0; margin-bottom: 4px;")
        card_layout.addWidget(self.label_descricao_ae)

        linha_campos = QHBoxLayout()
        linha_campos.setSpacing(8)

        self.combo_ae = QComboBox()
        for chave in DADOS_AE:
            self.combo_ae.addItem(chave)
        self.combo_ae.setMinimumWidth(137)
        self.combo_ae.setFixedHeight(36)
        self.combo_ae.currentIndexChanged.connect(self._preencher_dados_ae)
        linha_campos.addWidget(self.combo_ae)

        self.campo_conta = QLineEdit()
        self.campo_conta.setPlaceholderText("Conta")
        self.campo_conta.setFixedHeight(34)
        linha_campos.addWidget(self.campo_conta)

        self.campo_subconta = QLineEdit()
        self.campo_subconta.setPlaceholderText("Subconta")
        self.campo_subconta.setFixedHeight(34)
        linha_campos.addWidget(self.campo_subconta)

        self.campo_centro_custo = QLineEdit()
        self.campo_centro_custo.setPlaceholderText("Centro de custo")
        self.campo_centro_custo.setFixedHeight(34)
        linha_campos.addWidget(self.campo_centro_custo)

        self.combo_fornecedor = QComboBox()
        self.combo_fornecedor.addItems(["Pinhal", "Ouros", "Itajuba"])
        self.combo_fornecedor.setMinimumWidth(116)
        self.combo_fornecedor.setFixedHeight(36)
        linha_campos.addWidget(self.combo_fornecedor)

        card_layout.addLayout(linha_campos)

        linha_botoes = QHBoxLayout()
        linha_botoes.setSpacing(8)

        btn_colar = QPushButton("Colar")
        btn_colar.setObjectName("btnSecondary")
        btn_colar.setFixedHeight(34)
        btn_colar.setStyleSheet("background-color: #3b82f6; color: #fff; border: none; border-radius: 8px; padding: 7px 20px; font-size: 13px; font-weight: 600;")
        btn_colar.clicked.connect(self._colar)
        linha_botoes.addWidget(btn_colar)

        btn_executar = QPushButton("Executar")
        btn_executar.setObjectName("btnPrimary")
        btn_executar.setFixedHeight(34)
        btn_executar.setDefault(True)
        btn_executar.setStyleSheet("background-color: #16a34a; color: #fff; border: none; border-radius: 8px; padding: 7px 20px; font-size: 13px; font-weight: 600;")
        btn_executar.clicked.connect(self._executar)
        linha_botoes.addWidget(btn_executar)

        btn_limpar = QPushButton("Limpar")
        btn_limpar.setObjectName("btnSecondary")
        btn_limpar.setFixedHeight(34)
        btn_limpar.setStyleSheet("background-color: #ef4444; color: #fff; border: none; border-radius: 8px; padding: 7px 20px; font-size: 13px; font-weight: 600;")
        btn_limpar.clicked.connect(self._limpar)
        linha_botoes.addWidget(btn_limpar)

        linha_botoes.addStretch()
        card_layout.addLayout(linha_botoes)

        self.tabela = QTableWidget(0, len(HEADERS_TABELA))
        self.tabela.setHorizontalHeaderLabels(HEADERS_TABELA)
        header = self.tabela.horizontalHeader()
        percentuais = [0.17, 0.30, 0.10, 0.05, 0.10, 0.11, 0.09, 0.08]
        for c in range(self.tabela.columnCount()):
            header.setSectionResizeMode(c, QHeaderView.ResizeMode.Interactive)
        self._ajustar_colunas = lambda: None
        self._ajustar_colunas = lambda: [
            header.resizeSection(c, max(30, int(self.tabela.viewport().width() * p)))
            for c, p in enumerate(percentuais)
        ] if self.tabela.viewport().width() > 0 else None
        self.tabela.resizeEvent = lambda e: (
            self._ajustar_colunas(),
            QTableWidget.resizeEvent(self.tabela, e)
        )
        self._ajustar_colunas()
        self.tabela.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabela.setAlternatingRowColors(True)
        self.tabela.verticalHeader().setDefaultSectionSize(36)
        self.tabela.verticalHeader().setMinimumSectionSize(28)
        self.tabela.verticalHeader().setVisible(False)
        card_layout.addWidget(self.tabela)

        pagina_esquerda_layout.addWidget(card_principal)
        splitter.addWidget(pagina_esquerda)

        pagina_direita = QWidget()
        pagina_direita_layout = QVBoxLayout(pagina_direita)
        pagina_direita_layout.setContentsMargins(0, 0, 0, 0)
        pagina_direita_layout.setSpacing(16)

        card_anotacoes = QWidget()
        card_anotacoes.setObjectName("pageCard")
        card_anotacoes_layout = QVBoxLayout(card_anotacoes)
        card_anotacoes_layout.setContentsMargins(28, 28, 28, 28)
        card_anotacoes_layout.setSpacing(12)

        linha_titulo_anotacoes = QHBoxLayout()
        linha_titulo_anotacoes.setSpacing(8)

        titulo_anotacoes = QLabel("Anotações")
        titulo_anotacoes.setObjectName("pageTitle")
        titulo_anotacoes.setStyleSheet("font-size: 16px;")
        linha_titulo_anotacoes.addWidget(titulo_anotacoes)

        linha_titulo_anotacoes.addStretch()

        self.combo_abrir_anotacao = QComboBox()
        self.combo_abrir_anotacao.setMinimumWidth(84)
        self.combo_abrir_anotacao.setFixedHeight(32)
        self.combo_abrir_anotacao.setPlaceholderText("Abrir...")
        self.combo_abrir_anotacao.currentIndexChanged.connect(self._carregar_anotacao_arquivo)
        linha_titulo_anotacoes.addWidget(self.combo_abrir_anotacao)

        card_anotacoes_layout.addLayout(linha_titulo_anotacoes)

        self.campo_anotacoes = QPlainTextEdit()
        self.campo_anotacoes.setPlaceholderText("Digite suas anotações aqui...")
        self.campo_anotacoes.installEventFilter(self)
        card_anotacoes_layout.addWidget(self.campo_anotacoes)

        pagina_direita_layout.addWidget(card_anotacoes)
        splitter.addWidget(pagina_direita)

        splitter.setStretchFactor(0, 20)
        splitter.setStretchFactor(1, 12)

        layout.addWidget(splitter)
        self._preencher_dados_ae()

    def _preencher_dados_ae(self):
        chave = self.combo_ae.currentText()
        dados = DADOS_AE.get(chave)
        if dados:
            self.label_descricao_ae.setText(dados[0])
            self.campo_conta.setText(dados[1] if len(dados) > 1 else "")
            self.campo_subconta.setText(dados[2] if len(dados) > 2 else "")
            self.campo_centro_custo.setText(dados[3] if len(dados) > 3 else "")

    def _executar(self):
        esperar_inicio()
        conta = self.campo_conta.text()
        subconta = self.campo_subconta.text()
        cc = self.campo_centro_custo.text()
        for r in range(self.tabela.rowCount()):
            def obter(i):
                item = self.tabela.item(r, i)
                return item.text() if item and i < self.tabela.columnCount() else ""

            digitar_texto(obter(0))
            enter(3)

            digitar_texto(obter(6))
            enter(3)

            digitar_texto(obter(1))
            enter(2)

            digitar_texto(obter(2))
            enter()

            digitar_texto(obter(3))
            enter()

            digitar_texto(obter(4))
            enter(3)

            digitar_texto(obter(5))
            enter()

            digitar_texto("0")
            enter()

            digitar_texto(obter(7))
            enter(3)

            digitar_texto(conta)
            enter()

            digitar_texto(subconta)
            enter()

            digitar_texto(cc)
            enter(9)

            digitar_texto("01.999.00")
            enter(3)

    def eventFilter(self, obj, event):
        if obj == self.campo_anotacoes and event.type() == QEvent.Type.FocusOut:
            self._salvar_anotacoes()
        return super().eventFilter(obj, event)

    def _colar(self):
        clipboard = QApplication.clipboard()
        texto = clipboard.text()
        if not texto:
            return

        linhas = [l.strip() for l in texto.strip().split("\n") if l.strip()]
        if not linhas:
            return

        colunas_por_linha = [l.split("\t") for l in linhas]

        VALORES_BOOLEANOS = {"true", "false", "sim", "não", "nao", "1", "0", "verdadeiro", "falso"}

        if any(len(c) > 1 for c in colunas_por_linha):
            primeira_col = [c[0].strip().lower() for c in colunas_por_linha if len(c) > 0]
            if primeira_col and all(v in VALORES_BOOLEANOS for v in primeira_col):
                colunas_por_linha = [c[1:] for c in colunas_por_linha]

        inicio = 0
        cabecalhos = None
        primeira = colunas_por_linha[0]
        if primeira and any(h.lower() in [c.strip().lower() for c in primeira] for h in HEADERS_TABELA):
            cabecalhos = [c.strip().lower() for c in primeira]
            inicio = 1

        mapeamento = {}
        if cabecalhos:
            for i, h in enumerate(HEADERS_TABELA):
                try:
                    mapeamento[i] = cabecalhos.index(h.lower())
                except ValueError:
                    mapeamento[i] = None
        else:
            for i in range(len(HEADERS_TABELA)):
                mapeamento[i] = i

        C_M_COL = 7
        agrupados = {}
        for row in colunas_por_linha[inicio:]:
            src_item = mapeamento.get(INDICE_ITEM)
            if src_item is None or src_item >= len(row):
                continue
            item = row[src_item].strip().upper()
            if not item:
                continue

            src_qtde = mapeamento.get(INDICE_QTDE)
            if src_qtde is not None and src_qtde < len(row):
                qtde_texto = row[src_qtde].strip()
                try:
                    qtde = float(qtde_texto.replace(",", "."))
                except ValueError:
                    qtde = 1.0
            else:
                qtde = 1.0

            if item in agrupados:
                agrupados[item]["qtde"] += qtde
            else:
                dados_linha = ["" for _ in range(len(HEADERS_TABELA))]
                for col_dest, col_src in mapeamento.items():
                    if col_src is not None and col_src < len(row):
                        dados_linha[col_dest] = row[col_src].strip().upper()
                agrupados[item] = {"dados": dados_linha, "qtde": qtde}

        # Map existing items in the current table
        existing_items = {}
        for r in range(self.tabela.rowCount()):
            item_obj = self.tabela.item(r, INDICE_ITEM)
            if item_obj:
                existing_items[item_obj.text().strip().upper()] = r

        # Add new rows or update quantities for duplicates
        for item_key, grupo in agrupados.items():
            dados = grupo["dados"]
            dados[INDICE_ITEM] = item_key
            qtde_val = grupo["qtde"]
            qtde_int = int(qtde_val) if qtde_val == int(qtde_val) else qtde_val
            dados[INDICE_QTDE] = str(qtde_int)
            if not dados[C_M_COL].strip():
                dados[C_M_COL] = "C"

            if item_key in existing_items:
                row_idx = existing_items[item_key]
                # Update quantity cell
                qty_item = self.tabela.item(row_idx, INDICE_QTDE)
                try:
                    current_qty = float(qty_item.text().replace(",", "."))
                except (AttributeError, ValueError):
                    current_qty = 0.0
                new_qty = current_qty + qtde_val
                new_qty_int = int(new_qty) if new_qty == int(new_qty) else new_qty
                self.tabela.setItem(row_idx, INDICE_QTDE, QTableWidgetItem(str(new_qty_int)))
                # Keep other columns unchanged
            else:
                row_idx = self.tabela.rowCount()
                self.tabela.insertRow(row_idx)
                for col, valor in enumerate(dados):
                    self.tabela.setItem(row_idx, col, QTableWidgetItem(valor))

    def _limpar(self):
        self.tabela.setRowCount(0)

    def _salvar_anotacoes(self):
        texto = self.campo_anotacoes.toPlainText()
        data = datetime.now().strftime("%d-%m-%Y")
        pasta = _caminho_pasta_anotacoes()
        os.makedirs(pasta, exist_ok=True)
        caminho = os.path.join(pasta, f"{data}.json")
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump({"anotacoes": texto}, f, ensure_ascii=False, indent=2)
        limpar_arquivos_antigos(pasta)

    def _carregar_anotacoes(self):
        pasta = _caminho_pasta_anotacoes()
        os.makedirs(pasta, exist_ok=True)
        data = datetime.now().strftime("%d-%m-%Y")
        caminho = os.path.join(pasta, f"{data}.json")
        if not os.path.exists(caminho):
            with open(caminho, "w", encoding="utf-8") as f:
                json.dump({"anotacoes": ""}, f, ensure_ascii=False, indent=2)
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                dados = json.load(f)
                self.campo_anotacoes.setPlainText(dados.get("anotacoes", ""))
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    def _popular_combo_anotacoes(self):
        self.combo_abrir_anotacao.blockSignals(True)
        self.combo_abrir_anotacao.clear()
        pasta = _caminho_pasta_anotacoes()
        try:
            for nome in sorted(os.listdir(pasta), reverse=True):
                if nome.endswith(".json"):
                    caminho = os.path.join(pasta, nome)
                    data = nome.replace(".json", "")
                    self.combo_abrir_anotacao.addItem(data, caminho)
        except FileNotFoundError:
            pass
        self.combo_abrir_anotacao.blockSignals(False)
        hoje = datetime.now().strftime("%d-%m-%Y")
        indice_hoje = self.combo_abrir_anotacao.findText(hoje)
        if indice_hoje >= 0:
            self.combo_abrir_anotacao.setCurrentIndex(indice_hoje)

    def _carregar_anotacao_arquivo(self, indice):
        caminho = self.combo_abrir_anotacao.currentData()
        if not caminho:
            self.campo_anotacoes.setPlainText("")
            return
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                dados = json.load(f)
                self.campo_anotacoes.setPlainText(dados.get("anotacoes", ""))
        except (FileNotFoundError, json.JSONDecodeError):
            self.campo_anotacoes.setPlainText("")
