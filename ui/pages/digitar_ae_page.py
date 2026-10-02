import json
import os
import re
from datetime import datetime, timedelta
from functools import partial

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QPlainTextEdit, QSplitter,
    QApplication, QInputDialog, QMessageBox, QScrollArea, QFrame,
    QDialog, QFormLayout, QStyledItemDelegate, QStyle,
    QStyleOptionViewItem,
)
from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QColor, QBrush, QPalette
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
    "SRTTESTE": ("SRTTESTE Devolução de material para teste com retorno", "2400ADA", "99100", "")
}


def _caminho_pasta_anotacoes():
    import config
    base = config.obter_caminho_jsons()
    if not base:
        return ""
    return os.path.normpath(os.path.join(base, "Almox", "aeAnotacoes"))


def _caminho_fornecedores_json():
    import config
    base = config.obter_caminho_jsons()
    if not base:
        return ""
    return os.path.normpath(os.path.join(base, "Almox", "Fornecedores", "fornecedores.json"))


def _caminho_classificacao_fiscal_json():
    import config
    base = config.obter_caminho_jsons()
    if not base:
        return ""
    pasta = os.path.normpath(os.path.join(base, "Almox", "aeAnotacoes"))
    os.makedirs(pasta, exist_ok=True)
    return os.path.join(pasta, "ClassificacaoFiscal.json")


def _parse_br_number(texto):
    texto = texto.strip()
    if not texto:
        return 0.0
    if "," in texto or re.search(r"\.\d{3}", texto):
        texto = texto.replace(".", "").replace(",", ".")
    return float(texto)


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


def _parse_comentario_nf(comentario):
    """Parse a NF comment to extract ID, items, and costs.

    Expected format fragments:
      - ID at start: "ID 1732"
      - Items between "PRIMEIRA SAÍDA -" and "- VALOR CONTÁBIL UNITÁRIO",
        separated by "/"
      - Costs between "VALOR CONTÁBIL UNITÁRIO" and "- ATIVO",
        separated by "/"

    If the comment contains "ATIVO COM MENOS DE 01 ANO DE USO", the item is the
    number after "ATIVO:" or "AF", and the description is the text between
    "Comentário NF:" and "- VALOR CONTÁBIL UNITÁRIO".
    """
    resultado = {
        "id": "",
        "itens": [],
        "custos": [],
        "descricao": "",
        "comentario_original": comentario,
    }

    # Extract ID
    match_id = re.search(r'\bID\s*[:\s]*(\d+)', comentario, re.IGNORECASE)
    if match_id:
        resultado["id"] = match_id.group(1)

    if (re.search(r'ATIVO\s+COM\s+MENOS\s+DE\s+01\s+ANO\s+DE\s+USO', comentario, re.IGNORECASE)
            or "STATFIXO" in comentario):
        # Extract item(s): the number(s) after "ATIVO:" ou "AF"
        afs = []
        # 1) "ATIVO: 77412/77413/77414"
        match_item = re.search(r'ATIVO\s*:\s*([\d/]+)', comentario, re.IGNORECASE)
        if match_item:
            afs = [a for a in match_item.group(1).split("/") if a.strip()]
        # 2) múltiplos blocos "ATIVO: 35565 - ASSET: .../ATIVO: 35566 - ASSET: ..."
        if len(afs) <= 1:
            ativos = re.findall(r'ATIVO\s*:\s*(\d+)', comentario, re.IGNORECASE)
            if len(ativos) > 1:
                afs = ativos
        # 3) "AF: <num>"
        if not afs:
            match_af = re.search(r'\bAF\s*[:.\s]*([\d/]+)', comentario, re.IGNORECASE)
            if match_af:
                afs = [a for a in match_af.group(1).split("/") if a.strip()]

        # Extract description: between "Comentário NF:" and "- VALOR CONTÁBIL UNITÁRIO"
        match_desc = re.search(
            r'COMENT[AÁ]RIO\s+NF\s*:\s*(.*?)\s*[-–]\s*VALOR\s+CONT[AÁ]BIL\s+UNIT[AÁ]RIO',
            comentario, re.IGNORECASE | re.DOTALL
        )

        if afs:
            if match_desc:
                texto_desc = match_desc.group(1).strip()
                desc_itens = [d.strip() for d in texto_desc.split("/") if d.strip()]
                if len(afs) > 1 and len(desc_itens) > 1:
                    # Múltiplos AFs e múltiplos itens: casa por índice
                    resultado["itens"] = afs
                    resultado["descricoes"] = desc_itens
                else:
                    resultado["itens"] = afs
                    resultado["descricao"] = texto_desc
            else:
                resultado["itens"] = afs
    else:
        # Microcomputer pattern: "5 MICROCOMPUTADOR ( AR: ... AF's: 81082/81084/... E AF:81427 ...)"
        match_micro = re.search(
            r'(?<![\d])(?<!\bID\s)(\d+)\s+(.+?)\s*\(\s*AR:([^)]*)\)',
            comentario, re.IGNORECASE
        )
        if match_micro:
            afs = []
            for m in re.finditer(r'\bAF\'?s?\s*:\s*([\d/]+)', match_micro.group(3), re.IGNORECASE):
                afs.extend(a for a in m.group(1).split("/") if a.strip())
            if afs:
                resultado["itens"] = afs
                resultado["descricao"] = match_micro.group(2).strip().upper()
        else:
            # Extract items: between "PRIMEIRA SAÍDA -" and "- VALOR CONTÁBIL UNITÁRIO"
            match_itens = re.search(
                r'PRIMEIRA\s+SA[IÍ]DA\s*[-–]\s*(.*?)\s*[-–]\s*VALOR\s+CONT[AÁ]BIL\s+UNIT[AÁ]RIO',
                comentario, re.IGNORECASE
            )
            if match_itens:
                texto_itens = match_itens.group(1).strip()
                itens = [item.strip() for item in texto_itens.split("/") if item.strip()]

                # Se item tiver "(AF:<número>" entre parênteses, o AF é o item e o texto
                # antes do parênteses é a descrição. Ex: "LEITOR ZEBRA (AF:81110 AR: C04547)"
                descricoes = []
                novos_itens = []
                tem_af = False
                for it in itens:
                    m_af = re.search(r'\(\s*AF\s*:\s*(\d+)', it, re.IGNORECASE)
                    if m_af:
                        tem_af = True
                        novos_itens.append(m_af.group(1))
                        desc = re.sub(r'\s*\(\s*AF\s*:.*$', '', it, flags=re.IGNORECASE).strip()
                        descricoes.append(desc)
                    else:
                        novos_itens.append(it)
                        descricoes.append("")
                resultado["itens"] = novos_itens
                if tem_af:
                    resultado["descricoes"] = descricoes

    # Extract costs: between "VALOR CONTÁBIL UNITÁRIO" and "- ATIVO"
    match_custos = re.search(
        r'VALOR\s+CONT[AÁ]BIL\s+UNIT[AÁ]RIO\s+R?\$?\s*(.*?)\s*[-–]\s*ATIVO',
        comentario, re.IGNORECASE
    )
    if match_custos:
        texto_custos = match_custos.group(1).strip()
        partes_custo = [c.strip() for c in texto_custos.split("/") if c.strip()]
        custos = []
        for parte in partes_custo:
            # Remove leading "R$" if present
            parte_limpa = re.sub(r'^R?\$\s*', '', parte).strip()
            if parte_limpa:
                custos.append(parte_limpa)
        resultado["custos"] = custos

    return resultado


HEADERS_TABELA = [
    "Item", "Descrição", "Qtde", "UM",
    "Custo", "Clas. fiscal", "Classe", "C-M",
]

INDICE_ITEM = 0
INDICE_QTDE = 2


class DelegateItemCor(QStyledItemDelegate):
    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        if option.state & QStyle.StateFlag.State_Selected:
            brush = index.data(Qt.ItemDataRole.ForegroundRole)
            if isinstance(brush, QBrush) and brush.style() != Qt.BrushStyle.NoBrush:
                option.palette.setBrush(QPalette.ColorRole.Text, brush)
                option.palette.setBrush(QPalette.ColorRole.HighlightedText, brush)

    def createEditor(self, parent, option, index):
        editor = super().createEditor(parent, option, index)
        if isinstance(editor, QLineEdit):
            def aplicar_cor(texto):
                cor = "red" if len(texto) > 18 else "#374151"
                editor.setStyleSheet(f"color: {cor};")
            aplicar_cor(index.data(Qt.ItemDataRole.DisplayRole) or "")
            editor.textChanged.connect(aplicar_cor)
        return editor


class DigitarAEPage(QWidget):
    def __init__(self):
        super().__init__()
        self._comentarios_salvos = {}  # {id: {"comentario": str, "dados_parseados": dict}}
        self._setup_ui()
        self._carregar_anotacoes()
        self._popular_combo_anotacoes()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        pagina_esquerda = QWidget()
        pagina_esquerda_layout = QVBoxLayout(pagina_esquerda)
        pagina_esquerda_layout.setContentsMargins(0, 0, 0, 0)
        pagina_esquerda_layout.setSpacing(16)

        card_principal = QWidget()
        card_principal.setObjectName("pageCard")
        card_layout = QVBoxLayout(card_principal)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(12)

        titulo = QLabel("Digitar AE")
        titulo.setObjectName("pageTitle")
        card_layout.addWidget(titulo)

        linha_descricao = QHBoxLayout()
        linha_descricao.setSpacing(8)

        self.label_descricao_ae = QLabel("")
        self.label_descricao_ae.setObjectName("pageSubtitle")
        self.label_descricao_ae.setStyleSheet("font-size: 13px; font-weight: 600; color: #a0a0a0; margin-bottom: 4px;")
        linha_descricao.addWidget(self.label_descricao_ae)

        linha_descricao.addStretch()

        self.label_duns = QLabel("DUNS: ---")
        self.label_duns.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.label_duns.setStyleSheet("font-size: 11px; color: #888;")
        linha_descricao.addWidget(self.label_duns)
        card_layout.addLayout(linha_descricao)

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
        self.campo_conta.setFixedWidth(153)
        linha_campos.addWidget(self.campo_conta)

        self.campo_subconta = QLineEdit()
        self.campo_subconta.setPlaceholderText("Subconta")
        self.campo_subconta.setFixedHeight(34)
        self.campo_subconta.setFixedWidth(153)
        linha_campos.addWidget(self.campo_subconta)

        self.campo_centro_custo = QLineEdit()
        self.campo_centro_custo.setPlaceholderText("Centro de custo")
        self.campo_centro_custo.setFixedHeight(34)
        self.campo_centro_custo.setFixedWidth(153)
        linha_campos.addWidget(self.campo_centro_custo)

        self.combo_fornecedor = QComboBox()
        caminho_fornecedores = _caminho_fornecedores_json()
        self.fornecedores = []
        try:
            with open(caminho_fornecedores, "r", encoding="utf-8") as f:
                self.fornecedores = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        for f in self.fornecedores:
            nome = f.get("fornecedor", "")
            duns = f.get("duns", "")
            self.combo_fornecedor.addItem(f"{nome} {duns}", duns)
        self.combo_fornecedor.setMinimumWidth(116)
        self.combo_fornecedor.setFixedHeight(36)
        self.combo_fornecedor.currentIndexChanged.connect(self._atualizar_label_duns)
        linha_campos.addWidget(self.combo_fornecedor)

        self._atualizar_label_duns()

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

        btn_criar = QPushButton("Criar")
        btn_criar.setObjectName("btnSecondary")
        btn_criar.setFixedHeight(34)
        btn_criar.setStyleSheet("background-color: #8b5cf6; color: #fff; border: none; border-radius: 8px; padding: 7px 20px; font-size: 13px; font-weight: 600;")
        btn_criar.clicked.connect(self._criar_de_comentario)
        linha_botoes.addWidget(btn_criar)

        btn_cf = QPushButton("CF")
        btn_cf.setObjectName("btnSecondary")
        btn_cf.setFixedHeight(34)
        btn_cf.setStyleSheet("background-color: #0ea5e9; color: #fff; border: none; border-radius: 8px; padding: 7px 20px; font-size: 13px; font-weight: 600;")
        btn_cf.clicked.connect(self._abrir_cf)
        linha_botoes.addWidget(btn_cf)

        linha_botoes.addStretch()

        btn_identificacao = QPushButton("Identificação")
        btn_identificacao.setObjectName("btnGradientAmber")
        btn_identificacao.setFixedHeight(34)
        btn_identificacao.clicked.connect(self._abrir_identificacao)
        linha_botoes.addWidget(btn_identificacao)

        card_layout.addLayout(linha_botoes)

        # Layout for dynamically created ID buttons
        self.linha_ids = QHBoxLayout()
        self.linha_ids.setSpacing(6)
        self.linha_ids.addStretch()
        card_layout.addLayout(self.linha_ids)

        self.tabela = QTableWidget(0, len(HEADERS_TABELA))
        self.tabela.setObjectName("tabelaDigitarAE")
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
        self.tabela.verticalHeader().setDefaultSectionSize(28)
        self.tabela.verticalHeader().setMinimumSectionSize(24)
        self.tabela.verticalHeader().setVisible(False)
        self.tabela.setStyleSheet("""
            QLineEdit { padding: 0; border-radius: 0; }
        """)
        self._aplicando_cor = False
        self.tabela.itemChanged.connect(self._aplicar_cor_item)
        self.tabela.setItemDelegate(DelegateItemCor())
        card_layout.addWidget(self.tabela)

        pagina_esquerda_layout.addWidget(card_principal)
        splitter.addWidget(pagina_esquerda)

        pagina_direita = QWidget()
        pagina_direita.setMinimumWidth(200)
        pagina_direita_layout = QVBoxLayout(pagina_direita)
        pagina_direita_layout.setContentsMargins(0, 0, 0, 0)
        pagina_direita_layout.setSpacing(16)

        card_anotacoes = QWidget()
        card_anotacoes.setObjectName("pageCard")
        card_anotacoes_layout = QVBoxLayout(card_anotacoes)
        card_anotacoes_layout.setContentsMargins(16, 16, 16, 16)
        card_anotacoes_layout.setSpacing(12)

        linha_titulo_anotacoes = QHBoxLayout()
        linha_titulo_anotacoes.setSpacing(8)

        titulo_anotacoes = QLabel("Anotações")
        titulo_anotacoes.setObjectName("pageTitle")
        titulo_anotacoes.setStyleSheet("font-size: 16px;")
        linha_titulo_anotacoes.addWidget(titulo_anotacoes)

        linha_titulo_anotacoes.addStretch()

        self.combo_abrir_anotacao = QComboBox()
        self.combo_abrir_anotacao.setMinimumWidth(110)
        self.combo_abrir_anotacao.setFixedHeight(35)
        self.combo_abrir_anotacao.setStyleSheet("padding: 0px 4px; text-align: center;")
        self.combo_abrir_anotacao.setPlaceholderText("Abrir...")
        self.combo_abrir_anotacao.currentIndexChanged.connect(self._carregar_anotacao_arquivo)
        linha_titulo_anotacoes.addWidget(self.combo_abrir_anotacao)

        card_anotacoes_layout.addLayout(linha_titulo_anotacoes)

        self.campo_anotacoes = QPlainTextEdit()
        self.campo_anotacoes.setMinimumWidth(0)
        self.campo_anotacoes.setPlaceholderText("Digite suas anotações aqui...")
        self.campo_anotacoes.installEventFilter(self)
        card_anotacoes_layout.addWidget(self.campo_anotacoes)

        pagina_direita_layout.addWidget(card_anotacoes)
        splitter.addWidget(pagina_direita)

        splitter.setStretchFactor(0, 8)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([928, 232])
        splitter.setHandleWidth(8)

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

    def _atualizar_label_duns(self):
        duns = self.combo_fornecedor.currentData()
        if duns:
            self.label_duns.setText(f"DUNS: {duns}")
        else:
            self.label_duns.setText("DUNS: ---")

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

    def _criar_de_comentario(self):
        """Open an input dialog for NF comment, parse it, create an ID button, and populate the table."""
        comentario, ok = QInputDialog.getMultiLineText(
            self,
            "Criar a partir de Comentário NF",
            "Cole o comentário NF abaixo:",
            "",
        )
        if not ok or not comentario.strip():
            return

        if "STATFIXO" in comentario:
            idx = self.combo_ae.findText("STATFIXO")
            if idx >= 0:
                self.combo_ae.setCurrentIndex(idx)
        elif "STAFINDD" in comentario:
            idx = self.combo_ae.findText("STAFINDD")
            if idx >= 0:
                self.combo_ae.setCurrentIndex(idx)

        dados = _parse_comentario_nf(comentario)

        if not dados["itens"]:
            QMessageBox.warning(
                self,
                "Comentário inválido",
                "Não foi possível extrair itens do comentário.\n\n"
                "Certifique-se de que o comentário contém o trecho entre "
                "\"PRIMEIRA SAÍDA\" e \"VALOR CONTÁBIL UNITÁRIO\" com itens separados por \"/\".",
            )
            return

        id_valor = dados["id"] or "SEM_ID"

        # Save parsed data for this ID
        self._comentarios_salvos[id_valor] = {
            "comentario": comentario,
            "dados_parseados": dados,
        }

        # Create the ID button (insert before the stretch at the end)
        btn_id = IDButton(f"ID{id_valor}", id_valor, self)
        btn_id.clicked.connect(partial(self._carregar_dados_id, id_valor))
        # Insert before the stretch (last item)
        self.linha_ids.insertWidget(self.linha_ids.count() - 1, btn_id)

        # Populate the table with the parsed items
        self._popular_tabela_de_comentario(dados)

    def _remover_id_button(self, id_valor, button_widget):
        """Remove saved ID data and delete the button widget."""
        if id_valor in self._comentarios_salvos:
            del self._comentarios_salvos[id_valor]
        self.linha_ids.removeWidget(button_widget)
        button_widget.deleteLater()

    def _carregar_dados_id(self, id_valor):
        """Load the saved comment data for a given ID into the table."""
        salvo = self._comentarios_salvos.get(id_valor)
        if not salvo:
            return
        self._limpar()
        self._popular_tabela_de_comentario(salvo["dados_parseados"])

    def _popular_tabela_de_comentario(self, dados):
        """Populate the table from parsed comment data."""
        self._limpar()
        itens = dados["itens"]
        custos = dados["custos"]
        comentario = dados.get("comentario_original", "")

        # Load ClassificacaoFiscal.json to match items
        cf_caminho = _caminho_classificacao_fiscal_json()
        cf_dados = []
        if cf_caminho and os.path.exists(cf_caminho):
            try:
                with open(cf_caminho, "r", encoding="utf-8") as f:
                    cf_dados = json.load(f)
            except (json.JSONDecodeError, OSError):
                pass
        
        # Create a helper function to find a match where the registered item name is a substring of the parsed item name (or vice versa)
        def encontrar_correspondencia(nome_do_item):
            nome_do_item_upper = nome_do_item.strip().upper()
            for cf in cf_dados:
                item_cf = cf.get("item", "").strip().upper()
                if not item_cf:
                    continue
                # Match if item_cf is contained in the parsed item name (e.g. "RACK" in "CAVITYPLUG -RACK LINHA")
                # or if the parsed item name is contained in item_cf
                if item_cf in nome_do_item_upper or nome_do_item_upper in item_cf:
                    return cf
            return None

        forca_isu = "STAFINDD" in comentario
        cf_classe_statfixo = "STATFIXO" in comentario

        for i, item_nome in enumerate(itens):
            row = self.tabela.rowCount()
            self.tabela.insertRow(row)
            
            nome_chave = item_nome.strip().upper()
            descricoes = dados.get("descricoes", [])
            descricao = dados.get("descricao", "")
            if i < len(descricoes) and descricoes[i].strip():
                descricao = descricoes[i].strip()

            # CF lookup usa a descrição quando disponível, senão o item
            referencia_cf = descricao.upper() if descricao else nome_chave
            cf_match = encontrar_correspondencia(referencia_cf)

            # Item (col 0) - use the item name
            self.tabela.setItem(row, 0, QTableWidgetItem(nome_chave))

            # Descrição (col 1) - description from comment or same as item name
            self.tabela.setItem(row, 1, QTableWidgetItem(descricao or nome_chave))

            # Qtde (col 2) - always 1
            self.tabela.setItem(row, 2, QTableWidgetItem("1"))

            # UM (col 3) - always PC
            self.tabela.setItem(row, 3, QTableWidgetItem("PC"))

            # Custo (col 4) - from parsed costs, matching by index
            custo = custos[i] if i < len(custos) else ""
            self.tabela.setItem(row, 4, QTableWidgetItem(custo))

            # Clas. fiscal (col 5)
            clas_fiscal = cf_match.get("classificacao_fiscal", "") if cf_match else ""
            self.tabela.setItem(row, 5, QTableWidgetItem(clas_fiscal))

            # Classe (col 6) - ISU se comentário tem STAFINDD; STATFIXO usa a CF pela descrição
            classe_val = ""
            if forca_isu:
                classe_val = "ISU"
            elif cf_classe_statfixo and cf_match:
                classe_val = cf_match.get("classe_imposto", "")
            self.tabela.setItem(row, 6, QTableWidgetItem(classe_val))

            # C-M (col 7)
            cm_val = cf_match.get("cm", "") if cf_match else ""
            self.tabela.setItem(row, 7, QTableWidgetItem(cm_val))

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
                    qtde = _parse_br_number(qtde_texto)
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
                    current_qty = _parse_br_number(qty_item.text())
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

        self._completar_cf_pela_descricao()

    def _buscar_cf(self, texto):
        cf_caminho = _caminho_classificacao_fiscal_json()
        try:
            with open(cf_caminho, "r", encoding="utf-8") as f:
                cf_dados = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return None
        texto_upper = texto.strip().upper()
        for cf in cf_dados:
            item_cf = cf.get("item", "").strip().upper()
            if not item_cf:
                continue
            if item_cf in texto_upper or texto_upper in item_cf:
                return cf
        return None

    def _completar_cf_pela_descricao(self):
        for r in range(self.tabela.rowCount()):
            cf5 = self.tabela.item(r, 5)
            cf6 = self.tabela.item(r, 6)
            v5 = cf5.text() if cf5 else ""
            v6 = cf6.text() if cf6 else ""
            if v5.strip().upper() == "N/A" and v6.strip().upper() == "N/A":
                desc_obj = self.tabela.item(r, 1)
                desc = desc_obj.text() if desc_obj else ""
                cf = self._buscar_cf(desc)
                if cf:
                    self.tabela.setItem(r, 5, QTableWidgetItem(cf.get("classificacao_fiscal", "")))
                    self.tabela.setItem(r, 6, QTableWidgetItem(cf.get("classe_imposto", "")))

    def _limpar(self):
        self.tabela.setRowCount(0)

    def _aplicar_cor_item(self, item):
        if self._aplicando_cor or item.column() != 0:
            return
        self._aplicando_cor = True
        try:
            vermelho = len(item.text()) > 18
            cor_atual = item.foreground().color().name().lower()
            eh_vermelho = cor_atual in ("#ff0000", "red")
            if vermelho and not eh_vermelho:
                item.setForeground(QColor("red"))
            elif not vermelho and eh_vermelho:
                item.setForeground(QColor("#374151"))
        finally:
            self._aplicando_cor = False

    def _salvar_anotacoes(self):
        texto = self.campo_anotacoes.toPlainText()
        data = self.combo_abrir_anotacao.currentText() or datetime.now().strftime("%d-%m-%Y")
        pasta = _caminho_pasta_anotacoes()
        if not pasta:
            import config
            config.avisar_sem_pasta(self)
            return
        os.makedirs(pasta, exist_ok=True)
        caminho = os.path.join(pasta, f"{data}.json")
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump({"anotacoes": texto}, f, ensure_ascii=False, indent=2)
        limpar_arquivos_antigos(pasta)

    def _carregar_anotacoes(self):
        pasta = _caminho_pasta_anotacoes()
        if not pasta:
            return
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

    def _abrir_cf(self):
        """Open the Classificação Fiscal dialog."""
        dlg = ClassificacaoFiscalDialog(self)
        dlg.exec()

    def _abrir_identificacao(self):
        """Open the Identificação print layout dialog."""
        dlg = IdentificacaoDialog(self)
        dlg.exec()


class IdentificacaoDialog(QDialog):
    """Dialog for printing identification layout with three sections:
    - Envio para Pinhal (top)
    - A/C: (middle)
    - NF: (bottom)
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Identificação - Layout para Impressão")
        self.setMinimumSize(1200, 770)
        self.tamanho_quadro = 'A4'
        self._setup_ui()

    def _setup_ui(self):
        from PySide6.QtPrintSupport import QPrintPreviewWidget, QPrinter, QPrinterInfo
        from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QLineEdit, QLabel, QPushButton, QWidget, QComboBox
        from PySide6.QtGui import QPageSize, QPageLayout
        from PySide6.QtCore import QMarginsF, Qt

        self.setStyleSheet("QDialog { background-color: #f8fafc; }")

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(24)

        # Configurar a impressora base para o preview
        self.printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        self.printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
        self.printer.setPageOrientation(QPageLayout.Orientation.Landscape)
        self.printer.setPageMargins(QMarginsF(17.8, 19.1, 17.8, 19.1), QPageLayout.Unit.Millimeter)

        # Lado Esquerdo: Widget de preview
        self.preview_widget = QPrintPreviewWidget(self.printer, self)
        self.preview_widget.setZoomMode(QPrintPreviewWidget.ZoomMode.FitInView)
        self.preview_widget.paintRequested.connect(self._desenhar_impressao)
        self.preview_widget.setStyleSheet("""
            QPrintPreviewWidget {
                border: none;
                background-color: transparent;
            }
            QGraphicsView {
                background-color: #e2e8f0;
                border: 1px solid #cbd5e1;
                border-radius: 16px;
            }
        """)
        main_layout.addWidget(self.preview_widget, stretch=7)

        # Lado Direito: Painel de controles (Card)
        right_card = QWidget()
        right_card.setMinimumWidth(320)
        right_card.setStyleSheet("""
            QWidget#rightCard {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 16px;
            }
        """)
        right_card.setObjectName("rightCard")
        right_panel = QVBoxLayout(right_card)
        right_panel.setContentsMargins(24, 28, 24, 28)
        right_panel.setSpacing(24)

        titulo_painel = QLabel("Dados da Etiqueta")
        titulo_painel.setStyleSheet("font-size: 18px; font-weight: 800; color: #0f172a; border: none; background: transparent;")
        right_panel.addWidget(titulo_painel)

        # Campos de entrada
        campos_layout = QVBoxLayout()
        campos_layout.setSpacing(16)

        estilo_label = "font-size: 12px; font-weight: 700; color: #64748b; border: none; background: transparent;"
        estilo_campo = """
            QLineEdit {
                font-size: 15px;
                font-weight: 600;
                color: #0f172a;
                border: 2px solid #e2e8f0;
                border-radius: 8px;
                padding: 10px 14px;
                background-color: #f8fafc;
            }
            QLineEdit:focus {
                border-color: #3b82f6;
                background-color: #ffffff;
            }
            QLineEdit:hover {
                border-color: #cbd5e1;
            }
        """
        
        # Destino
        layout_destino = QVBoxLayout()
        layout_destino.setSpacing(6)
        label_destino = QLabel("ENVIO PARA")
        label_destino.setStyleSheet(estilo_label)
        self.campo_destino = QLineEdit()
        self.campo_destino.setPlaceholderText("Ex: PINHAL")
        self.campo_destino.setStyleSheet(estilo_campo)
        self.campo_destino.textChanged.connect(self._atualizar_preview)
        layout_destino.addWidget(label_destino)
        layout_destino.addWidget(self.campo_destino)
        campos_layout.addLayout(layout_destino)

        # A/C
        layout_ac = QVBoxLayout()
        layout_ac.setSpacing(6)
        label_ac = QLabel("A/C")
        label_ac.setStyleSheet(estilo_label)
        self.campo_ac = QLineEdit()
        self.campo_ac.setPlaceholderText("Nome ou Setor")
        self.campo_ac.setStyleSheet(estilo_campo)
        self.campo_ac.textChanged.connect(self._atualizar_preview)
        layout_ac.addWidget(label_ac)
        layout_ac.addWidget(self.campo_ac)
        campos_layout.addLayout(layout_ac)

        # NF
        layout_nf = QVBoxLayout()
        layout_nf.setSpacing(6)
        label_nf = QLabel("NOTA FISCAL")
        label_nf.setStyleSheet(estilo_label)
        self.campo_nf = QLineEdit()
        self.campo_nf.setPlaceholderText("Nº da Nota")
        self.campo_nf.setStyleSheet(estilo_campo)
        self.campo_nf.textChanged.connect(self._atualizar_preview)
        layout_nf.addWidget(label_nf)
        layout_nf.addWidget(self.campo_nf)
        campos_layout.addLayout(layout_nf)

        # Separador
        linha = QWidget()
        linha.setFixedHeight(1)
        linha.setStyleSheet("background-color: #f1f5f9; border: none;")
        campos_layout.addWidget(linha)

        # Seleção de Impressora
        layout_impressora = QVBoxLayout()
        layout_impressora.setSpacing(6)
        label_impressora = QLabel("IMPRESSORA")
        label_impressora.setStyleSheet(estilo_label)
        
        self.combo_impressora = QComboBox()
        self.combo_impressora.setStyleSheet(estilo_campo.replace("QLineEdit", "QComboBox") + """
            QComboBox::drop-down { border-left: 1px solid #e2e8f0; width: 34px; }
        """)
        impressoras = QPrinterInfo.availablePrinterNames()
        self.combo_impressora.addItems(impressoras)
        
        impressora_padrao = QPrinterInfo.defaultPrinterName()
        if impressora_padrao in impressoras:
            self.combo_impressora.setCurrentText(impressora_padrao)
            
        layout_impressora.addWidget(label_impressora)
        layout_impressora.addWidget(self.combo_impressora)
        campos_layout.addLayout(layout_impressora)

        # Tamanho A4 / A5
        layout_tamanho = QVBoxLayout()
        layout_tamanho.setSpacing(8)
        label_tamanho = QLabel("FORMATO DA ETIQUETA")
        label_tamanho.setStyleSheet(estilo_label)
        layout_tamanho.addWidget(label_tamanho)

        estilo_btn_toggle = """
            QPushButton {
                background-color: #f1f5f9;
                color: #64748b;
                border: none;
                border-radius: 8px;
                padding: 10px;
                font-weight: 700;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #e2e8f0;
                color: #475569;
            }
            QPushButton:checked {
                background-color: #1e1b4b;
                color: #ffffff;
            }
        """

        tamanho_layout = QHBoxLayout()
        tamanho_layout.setSpacing(8)
        self.btn_a4 = QPushButton("A4")
        self.btn_a4.setCheckable(True)
        self.btn_a4.setChecked(True)
        self.btn_a4.setStyleSheet(estilo_btn_toggle)
        self.btn_a4.clicked.connect(lambda: self._mudar_tamanho('A4'))

        self.btn_a5 = QPushButton("A5")
        self.btn_a5.setCheckable(True)
        self.btn_a5.setStyleSheet(estilo_btn_toggle)
        self.btn_a5.clicked.connect(lambda: self._mudar_tamanho('A5'))

        tamanho_layout.addWidget(self.btn_a4)
        tamanho_layout.addWidget(self.btn_a5)
        
        layout_tamanho.addLayout(tamanho_layout)
        campos_layout.addLayout(layout_tamanho)

        # Quantidade de Cópias
        layout_qtd = QHBoxLayout()
        layout_qtd.setSpacing(10)
        
        label_qtd = QLabel("QTDE")
        label_qtd.setStyleSheet(estilo_label)
        
        btn_layout_setas = QVBoxLayout()
        btn_layout_setas.setSpacing(2)
        btn_up = QPushButton("▲")
        btn_down = QPushButton("▼")
        btn_up.setFixedSize(22, 18)
        btn_down.setFixedSize(22, 18)
        
        estilo_btn_seta = """
            QPushButton {
                background-color: #f1f5f9;
                color: #475569;
                border: 1px solid #cbd5e1;
                border-radius: 4px;
                font-size: 9px;
            }
            QPushButton:hover {
                background-color: #e2e8f0;
            }
        """
        btn_up.setStyleSheet(estilo_btn_seta)
        btn_down.setStyleSheet(estilo_btn_seta)
        btn_layout_setas.addWidget(btn_up)
        btn_layout_setas.addWidget(btn_down)
        
        self.campo_qtd = QLineEdit("1")
        self.campo_qtd.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.campo_qtd.setStyleSheet(estilo_campo)
        self.campo_qtd.setFixedWidth(60)
        
        def increment_qtd():
            try: val = int(self.campo_qtd.text())
            except: val = 1
            if val < 999: self.campo_qtd.setText(str(val + 1))
            
        def decrement_qtd():
            try: val = int(self.campo_qtd.text())
            except: val = 1
            if val > 1: self.campo_qtd.setText(str(val - 1))
            
        btn_up.clicked.connect(increment_qtd)
        btn_down.clicked.connect(decrement_qtd)
        
        layout_qtd.addWidget(label_qtd)
        layout_qtd.addWidget(self.campo_qtd)
        layout_qtd.addLayout(btn_layout_setas)
        layout_qtd.addStretch(1)

        campos_layout.addLayout(layout_qtd)

        right_panel.addLayout(campos_layout)
        
        # Espaçador para empurrar os botões para baixo
        right_panel.addStretch(1)

        # Botões Principais
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(10)

        btn_imprimir = QPushButton("Imprimir Etiqueta")
        btn_imprimir.setFixedHeight(44)
        btn_imprimir.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;
                color: #ffffff;
                border: none;
                border-radius: 10px;
                font-size: 15px;
                font-weight: 700;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
            QPushButton:pressed {
                background-color: #1d4ed8;
            }
        """)
        btn_imprimir.clicked.connect(self._imprimir)
        btn_layout.addWidget(btn_imprimir)

        btn_fechar = QPushButton("Cancelar")
        btn_fechar.setFixedHeight(44)
        btn_fechar.setStyleSheet("""
            QPushButton {
                background-color: #f1f5f9;
                color: #475569;
                border: none;
                border-radius: 10px;
                font-size: 15px;
                font-weight: 700;
            }
            QPushButton:hover {
                background-color: #e2e8f0;
                color: #0f172a;
            }
            QPushButton:pressed {
                background-color: #cbd5e1;
            }
        """)
        btn_fechar.clicked.connect(self.accept)
        btn_layout.addWidget(btn_fechar)

        right_panel.addLayout(btn_layout)

        main_layout.addWidget(right_card, stretch=3)

    def showEvent(self, event):
        super().showEvent(event)
        # Forçar o preview a se desenhar após exibir o dialog
        self._atualizar_preview()

    def _mudar_tamanho(self, tamanho):
        self.tamanho_quadro = tamanho
        self.btn_a4.setChecked(tamanho == 'A4')
        self.btn_a5.setChecked(tamanho == 'A5')
        self._atualizar_preview()

    def _atualizar_preview(self):
        if hasattr(self, 'preview_widget'):
            self.preview_widget.updatePreview()

    def _desenhar_impressao(self, printer):
        """Função unificada que desenha tanto na tela (preview) quanto na impressora real."""
        from PySide6.QtGui import QPainter, QFont, QPen, QColor
        from PySide6.QtCore import Qt, QRectF
        from PySide6.QtPrintSupport import QPrinter

        painter = QPainter(printer)
        
        # O (0,0) do QPainter no QPrinter começa na margem imprimível (pageRect).
        page_rect = printer.pageRect(QPrinter.Unit.DevicePixel)
        
        width = page_rect.width()
        height = page_rect.height()

        if getattr(self, 'tamanho_quadro', 'A4') == 'A5':
            # Usa apenas a metade esquerda da folha (formato retrato A5)
            width = width / 2

        # Para garantir que o quadro fique centralizado e não seja cortado por
        # margens não imprimíveis da impressora, criamos uma margem extra de 5%.
        margem_x = width * 0.05
        margem_y = height * 0.05

        # Importante: Como o QPainter já considera (0,0) o início da área útil,
        # não devemos somar page_rect.left() ou top().
        content_rect = QRectF(
            margem_x, 
            margem_y, 
            width - 2 * margem_x, 
            height - 2 * margem_y
        )

        # Desenhar quadro da folha
        pen_width = int(content_rect.width() * 0.003)
        if pen_width < 1: pen_width = 1
        painter.setPen(QPen(QColor("#1e1b4b"), pen_width))
        painter.drawRect(content_rect)

        third_height = content_rect.height() / 3

        painter.setPen(QPen(QColor("#1e1b4b"), pen_width))
        painter.drawLine(content_rect.left(), int(content_rect.top() + third_height), content_rect.right(), int(content_rect.top() + third_height))
        painter.drawLine(content_rect.left(), int(content_rect.top() + 2 * third_height), content_rect.right(), int(content_rect.top() + 2 * third_height))

        # Configuração de fonte dinâmica baseada na menor dimensão
        ref_size = min(content_rect.width(), content_rect.height())

        font_texto = QFont("Arial")
        font_texto.setBold(True)
        # Tamanho adaptado para caber o texto na mesma linha
        font_texto.setPixelSize(int(ref_size * 0.07))

        # Seção 1: Envio para Pinhal / Destino
        destino = self.campo_destino.text().strip().upper() if hasattr(self, 'campo_destino') else ""
        if not destino:
            destino = "PINHAL"
        texto_destino = f"ENVIO PARA {destino}"

        painter.setFont(font_texto)
        painter.setPen(QColor("#1e1b4b"))
        painter.drawText(QRectF(content_rect.left(), content_rect.top(), content_rect.width(), third_height), Qt.AlignmentFlag.AlignCenter, texto_destino)

        # Seção 2: A/C
        ac_text = self.campo_ac.text().strip() if hasattr(self, 'campo_ac') else ""
        texto_ac = f"A/C: {ac_text}" if ac_text else "A/C:"
        rect_secao_2 = QRectF(content_rect.left(), content_rect.top() + third_height, content_rect.width(), third_height)
        painter.drawText(rect_secao_2, Qt.AlignmentFlag.AlignCenter, texto_ac)

        # Seção 3: NF
        nf_text = self.campo_nf.text().strip() if hasattr(self, 'campo_nf') else ""
        texto_nf = f"NF: {nf_text}" if nf_text else "NF:"
        rect_secao_3 = QRectF(content_rect.left(), content_rect.top() + 2 * third_height, content_rect.width(), third_height)
        painter.drawText(rect_secao_3, Qt.AlignmentFlag.AlignCenter, texto_nf)

        painter.end()

    def _imprimir(self):
        from PySide6.QtWidgets import QMessageBox

        nome_impressora = self.combo_impressora.currentText()
        if nome_impressora:
            self.printer.setPrinterName(nome_impressora)

        if hasattr(self, 'campo_qtd'):
            try:
                qtd = int(self.campo_qtd.text())
            except:
                qtd = 1
            self.printer.setCopyCount(qtd)

        try:
            self._desenhar_impressao(self.printer)
            QMessageBox.information(self, "Sucesso", f"Identificação enviada para a impressora {nome_impressora}!")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Ocorreu um erro ao tentar imprimir: {e}")


class ClassificacaoFiscalDialog(QDialog):
    """Dialog to manage fiscal classification entries."""

    HEADERS = ["Item", "Clas. Fiscal", "Classe Imposto", "C-M"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Classificação Fiscal")
        self.setMinimumSize(620, 480)
        self._setup_ui()
        self._carregar_dados()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        titulo = QLabel("Classificação Fiscal")
        titulo.setStyleSheet("font-size: 16px; font-weight: 700;")
        layout.addWidget(titulo)

        form = QFormLayout()
        form.setSpacing(8)

        self.campo_item = QLineEdit()
        self.campo_item.setPlaceholderText("Ex: CAVITYPLUG")
        self.campo_item.setFixedHeight(32)
        self.campo_item.textChanged.connect(self._filtrar_tabela)
        form.addRow("Item:", self.campo_item)

        self.campo_clas_fiscal = QLineEdit()
        self.campo_clas_fiscal.setPlaceholderText("Ex: 8538.90.90")
        self.campo_clas_fiscal.setFixedHeight(32)
        form.addRow("Classificação Fiscal:", self.campo_clas_fiscal)

        self.campo_classe_imposto = QLineEdit()
        self.campo_classe_imposto.setPlaceholderText("Ex: ISU")
        self.campo_classe_imposto.setFixedHeight(32)
        form.addRow("Classe de Imposto:", self.campo_classe_imposto)

        self.campo_cm = QLineEdit()
        self.campo_cm.setPlaceholderText("Ex: C")
        self.campo_cm.setFixedHeight(32)
        form.addRow("C-M:", self.campo_cm)

        layout.addLayout(form)

        linha_btns = QHBoxLayout()
        linha_btns.setSpacing(8)

        btn_salvar = QPushButton("Salvar")
        btn_salvar.setFixedHeight(32)
        btn_salvar.setStyleSheet(
            "background-color: #16a34a; color: #fff; border: none; border-radius: 8px; "
            "padding: 6px 20px; font-size: 13px; font-weight: 600;"
        )
        btn_salvar.clicked.connect(self._salvar_item)
        linha_btns.addWidget(btn_salvar)

        btn_excluir = QPushButton("Excluir Selecionado")
        btn_excluir.setFixedHeight(32)
        btn_excluir.setStyleSheet(
            "background-color: #ef4444; color: #fff; border: none; border-radius: 8px; "
            "padding: 6px 20px; font-size: 13px; font-weight: 600;"
        )
        btn_excluir.clicked.connect(self._excluir_item)
        linha_btns.addWidget(btn_excluir)

        linha_btns.addStretch()
        layout.addLayout(linha_btns)

        self.tabela = QTableWidget(0, len(self.HEADERS))
        self.tabela.setHorizontalHeaderLabels(self.HEADERS)
        header = self.tabela.horizontalHeader()
        percentuais = [0.40, 0.25, 0.25, 0.10]
        for c in range(self.tabela.columnCount()):
            header.setSectionResizeMode(c, QHeaderView.ResizeMode.Interactive)
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
        self.tabela.verticalHeader().setVisible(False)
        self.tabela.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabela.doubleClicked.connect(self._preencher_campos_da_linha)
        layout.addWidget(self.tabela)

    def _caminho_json(self):
        return _caminho_classificacao_fiscal_json()

    def _carregar_dados(self):
        caminho = self._caminho_json()
        if not caminho:
            return
        self.tabela.setRowCount(0)
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                itens = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            itens = []
        for item in sorted(itens, key=lambda x: x.get("item", "").upper()):
            row = self.tabela.rowCount()
            self.tabela.insertRow(row)
            self.tabela.setItem(row, 0, QTableWidgetItem(item.get("item", "")))
            self.tabela.setItem(row, 1, QTableWidgetItem(item.get("classificacao_fiscal", "")))
            self.tabela.setItem(row, 2, QTableWidgetItem(item.get("classe_imposto", "")))
            self.tabela.setItem(row, 3, QTableWidgetItem(item.get("cm", "")))
        self._filtrar_tabela(self.campo_item.text())

    def _filtrar_tabela(self, texto):
        texto = texto.strip().upper()
        for row in range(self.tabela.rowCount()):
            item_obj = self.tabela.item(row, 0)
            nome = item_obj.text().upper() if item_obj else ""
            self.tabela.setRowHidden(row, bool(texto) and texto not in nome)

    def _ler_json(self):
        caminho = self._caminho_json()
        if not caminho:
            return []
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def _gravar_json(self, itens):
        caminho = self._caminho_json()
        if not caminho:
            return
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(itens, f, ensure_ascii=False, indent=2)

    def _salvar_item(self):
        item = self.campo_item.text().strip().upper()
        if not item:
            QMessageBox.warning(self, "Campo obrigatório", "Preencha o campo Item.")
            return
        clas = self.campo_clas_fiscal.text().strip()
        classe = self.campo_classe_imposto.text().strip().upper()
        cm = self.campo_cm.text().strip().upper()

        itens = self._ler_json()

        # Update if item already exists, otherwise append
        encontrado = False
        for entrada in itens:
            if entrada.get("item", "").upper() == item:
                entrada["classificacao_fiscal"] = clas
                entrada["classe_imposto"] = classe
                entrada["cm"] = cm
                encontrado = True
                break
        if not encontrado:
            itens.append({
                "item": item,
                "classificacao_fiscal": clas,
                "classe_imposto": classe,
                "cm": cm,
            })

        self._gravar_json(itens)
        self._carregar_dados()

        # Clear fields
        self.campo_item.clear()
        self.campo_clas_fiscal.clear()
        self.campo_classe_imposto.clear()
        self.campo_cm.clear()

    def _excluir_item(self):
        row = self.tabela.currentRow()
        if row < 0:
            return
        item_obj = self.tabela.item(row, 0)
        if not item_obj:
            return
        item_nome = item_obj.text().upper()

        itens = self._ler_json()
        itens = [e for e in itens if e.get("item", "").upper() != item_nome]
        self._gravar_json(itens)
        self._carregar_dados()

    def _preencher_campos_da_linha(self, index):
        """Double-click a row to fill the form fields for editing."""
        row = index.row()
        self.campo_item.setText(self.tabela.item(row, 0).text() if self.tabela.item(row, 0) else "")
        self.campo_clas_fiscal.setText(self.tabela.item(row, 1).text() if self.tabela.item(row, 1) else "")
        self.campo_classe_imposto.setText(self.tabela.item(row, 2).text() if self.tabela.item(row, 2) else "")
        self.campo_cm.setText(self.tabela.item(row, 3).text() if self.tabela.item(row, 3) else "")


class IDButton(QPushButton):
    """A custom button that supports a context menu (right-click) to remove itself."""

    def __init__(self, text, id_valor, parent_page):
        super().__init__(text)
        self.id_valor = id_valor
        self.parent_page = parent_page
        self.setFixedHeight(28)
        self.setStyleSheet(
            "background-color: #f59e0b; color: #fff; border: none; border-radius: 6px; "
            "padding: 4px 14px; font-size: 12px; font-weight: 700;"
        )
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._mostrar_menu)

    def _mostrar_menu(self, pos):
        from PySide6.QtWidgets import QMenu
        menu = QMenu(self)
        acao_remover = menu.addAction("Remover")
        acao_remover.triggered.connect(self._remover)
        menu.exec(self.mapToGlobal(pos))

    def _remover(self):
        self.parent_page._remover_id_button(self.id_valor, self)
