import json
import os

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QStyledItemDelegate, QMessageBox,
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont
from PySide6.QtGui import QGuiApplication


class EditorDelegate(QStyledItemDelegate):
    def sizeHint(self, option, index):
        base = super().sizeHint(option, index)
        return QSize(base.width(), max(base.height(), 34))

    def createEditor(self, parent, option, index):
        editor = super().createEditor(parent, option, index)
        if isinstance(editor, QLineEdit):
            editor.setMinimumHeight(34)
            editor.setStyleSheet("padding: 4px 8px;")
        return editor


def _caminho_json():
    import config
    base = config.obter_caminho_jsons()
    if not base:
        return ""
    return os.path.normpath(os.path.join(base, "Almox", "ItensAlmoxarifado", "ItensAlmoxarifado.json"))


class EstoquePage(QWidget):
    COLUNAS_RESUMIDAS = [1, 2, 3, 4, 5, 6, 7, 8, 20, 22]
    HEADERS_RESUMIDOS = ["Kardex", "Código", "Descrição", "Loc novo", "Qtde novo", "Loc retorno", "Qtde retorno", "Fornecedor", "Custo", "Consumo médio"]

    COLUNAS = [
        "Id", "Kardex", "Código", "Descrição", "Loc novo", "Qtde novo",
        "Loc retorno", "Qtde retorno", "Fornecedor", "Provável fornecedor",
        "Ordem", "Lote Pedido", "Lote Compra", "Leadtime", "Fator Segurança",
        "UM", "Pendente DPH", "Pend. entrega compras", "Pendente para SA",
        "Lugar de uso", "Custo", "Curva custo", "Consumo médio", "Curva demanda",
        "Equipamento", "Tipo de uso", "Estoque mínimo", "Estoque máximo",
        "Estoque estratégico", "Mostrar cons. med./prog. no mês",
        "Separar p/ holder", "Separar p/ mesa", "Item de estoque",
        "Pino de contato", "Ativo/Obsol.", "Classificação Fiscal", "IPI",
        "Observações", "Doc. evidência", "Descrição de evidência",
    ]
    CHAVES = [
        "Id", "Kardex", "Código", "Descrição", "Loc novo", "Qtde novo",
        "Loc retorno", "Qtde retorno", "Fornecedor", "Provável fornecedor",
        "Ordem", "Lote Pedido", "Lote Compra", "Leadtime", "Fator Segurança",
        "UM", "Pendente DPH", "Pend. entrega compras", "Pendente para SA",
        "Lugar de uso", "Custo", "Curva custo", "Consumo médio", "Curva demanda",
        "Equipamento", "Tipo de uso", "Estoque mínimo", "Estoque máximo",
        "Estoque estratégico", "Mostrar cons. med./prog. no mês",
        "Separar p/ holder", "Separar p/ mesa", "Item de estoque",
        "Pino de contato", "Ativo/Obsol.", "Classificação Fiscal", "IPI",
        "Observações", "Doc. evidência", "Descrição de evidência",
    ]
    CAMPOS_DETALHES = [
        ("Código", "Código"),
        ("Kardex", "Kardex"),
        ("Descrição", "Descrição"),
        ("Loc novo", "Loc novo"),
        ("Qtde novo", "Qtde novo"),
        ("Loc retorno", "Loc retorno"),
        ("Qtde retorno", "Qtde retorno"),
        ("Consumo médio", "Consumo médio"),
        ("Qtde comprada", "Pend. entrega compras"),
    ]

    def __init__(self):
        super().__init__()
        self.dados = []
        self.modo_resumido = True
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

        titulo = QLabel("Estoque")
        titulo.setObjectName("pageTitle")
        card_layout.addWidget(titulo)

        linha_top = QHBoxLayout()
        linha_top.setSpacing(8)

        btn_atualizar = QPushButton("Atualizar")
        btn_atualizar.setObjectName("btnPrimary")
        btn_atualizar.setFixedHeight(34)
        btn_atualizar.clicked.connect(self._atualizar)
        linha_top.addWidget(btn_atualizar)

        self.campo_filtro = QLineEdit()
        self.campo_filtro.setPlaceholderText("Pesquisar...")
        self.campo_filtro.setFixedHeight(30)
        self.campo_filtro.setFixedWidth(200)
        self.campo_filtro.textChanged.connect(self._aplicar_filtro)
        linha_top.addWidget(self.campo_filtro)

        self.detalhes_box = QWidget()
        self.detalhes_box.setObjectName("detalhesBox")
        grid = QGridLayout(self.detalhes_box)
        grid.setContentsMargins(16, 10, 16, 10)
        grid.setHorizontalSpacing(24)
        grid.setVerticalSpacing(4)

        self._labels_valores = {}

        def _adicionar_campo(linha, coluna, rotulo, chave, span_valor=1):
            lbl_nome = QLabel(rotulo.upper())
            lbl_nome.setObjectName("fieldLabel")
            lbl_valor = QLabel("-")
            lbl_valor.setObjectName("infoValue")
            self._labels_valores[chave] = lbl_valor
            grid.addWidget(lbl_nome, linha, coluna)
            grid.addWidget(lbl_valor, linha, coluna + 1, 1, span_valor)

        _adicionar_campo(0, 0, "Código", "Código")
        _adicionar_campo(0, 2, "Kardex", "Kardex")
        _adicionar_campo(1, 0, "Descrição", "Descrição", span_valor=3)
        _adicionar_campo(2, 0, "Loc novo", "Loc novo")
        _adicionar_campo(2, 2, "Qtde novo", "Qtde novo")
        _adicionar_campo(3, 0, "Loc retorno", "Loc retorno")
        _adicionar_campo(3, 2, "Qtde retorno", "Qtde retorno")
        _adicionar_campo(4, 0, "Consumo médio", "Consumo médio")
        _adicionar_campo(4, 2, "Qtde comprada", "Pend. entrega compras")

        grid.setColumnStretch(1, 3)
        grid.setColumnStretch(3, 2)
        linha_top.addWidget(self.detalhes_box)

        self.label_contador = QLabel("0 itens")
        self.label_contador.setObjectName("statusLabel")
        linha_top.addWidget(self.label_contador)

        linha_top.addStretch()

        self.btn_toggle = QPushButton("Visão completa")
        self.btn_toggle.setObjectName("btnSecondary")
        self.btn_toggle.setFixedHeight(34)
        self.btn_toggle.setCheckable(True)
        self.btn_toggle.clicked.connect(self._alternar_modo)
        linha_top.addWidget(self.btn_toggle)
        card_layout.addLayout(linha_top)

        self.tabela = QTableWidget(0, len(self.COLUNAS))
        self.tabela.setStyleSheet("font-size: 11px;")
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
        header.setStretchLastSection(False)
        for c in range(self.tabela.columnCount()):
            header.setSectionResizeMode(c, QHeaderView.ResizeMode.Interactive)
            largura = 150 if c == 1 else 180 if c == 2 else 250 if c == 3 else 100
            header.resizeSection(c, largura)
        self.tabela.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self.tabela.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked)
        self.tabela.setAlternatingRowColors(False)
        self.tabela.verticalHeader().setDefaultSectionSize(28)
        self.tabela.verticalHeader().setMinimumSectionSize(24)
        self.tabela.verticalHeader().setVisible(False)
        self.tabela.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.tabela.setItemDelegate(EditorDelegate(self.tabela))
        self.tabela.itemSelectionChanged.connect(self._atualizar_detalhes)
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
        filtro_texto = self.campo_filtro.text().strip().lower()
        for item in self.dados:
            if self.modo_resumido:
                ativo = str(item.get("Ativo/Obsol.", "")).strip().lower()
                if "ativo" not in ativo:
                    continue
            if filtro_texto:
                texto = " ".join(str(v) for v in item.values()).lower()
                if filtro_texto not in texto:
                    continue
            row = self.tabela.rowCount()
            self.tabela.insertRow(row)
            for col, chave in enumerate(self.CHAVES):
                valor = str(item.get(chave, ""))
                cell = QTableWidgetItem(valor)
                cell.setFlags(cell.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.tabela.setItem(row, col, cell)
        if self.modo_resumido:
            for c in range(len(self.COLUNAS)):
                self.tabela.setColumnHidden(c, c not in self.COLUNAS_RESUMIDAS)
        else:
            for c in range(len(self.COLUNAS)):
                self.tabela.setColumnHidden(c, False)
        self.tabela.blockSignals(False)
        self.label_contador.setText(f"{self.tabela.rowCount()} itens")
        self._atualizar_detalhes()

    def _atualizar(self):
        modo_anterior = self.modo_resumido
        if self.modo_resumido:
            self.modo_resumido = False
            self.btn_toggle.setText("Visão resumida")

        clipboard = QGuiApplication.clipboard()
        texto = clipboard.text()
        if not texto.strip():
            QMessageBox.warning(self, "Aviso", "A área de transferência está vazia.")
            self.modo_resumido = modo_anterior
            return

        linhas = [l.strip() for l in texto.replace("\r\n", "\n").split("\n") if l.strip()]
        if not linhas:
            self.modo_resumido = modo_anterior
            return

        header, dados_linha = self._separar_cabecalho(linhas)
        if not dados_linha:
            QMessageBox.warning(self, "Aviso", "Não há dados válidos para atualizar.")
            self.modo_resumido = modo_anterior
            return

        colunas = len(dados_linha[0].split("\t"))

        if colunas == 40:
            resposta = QMessageBox.question(
                self,
                "Confirmação",
                "Atualizar completamente o estoque?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if resposta != QMessageBox.StandardButton.Yes:
                self.modo_resumido = modo_anterior
                return

            self._fazer_atualizacao_completa(dados_linha)
        elif colunas == 24:
            self._fazer_atualizacao_parcial(dados_linha, header)
        else:
            QMessageBox.warning(
                self,
                "Formato inválido",
                "A tabela copiada deve ter 40 ou 24 colunas."
            )
            self.modo_resumido = modo_anterior
            return

        self.modo_resumido = modo_anterior
        if modo_anterior:
            self.btn_toggle.setText("Visão completa")
        self._popular_tabela()

        # Sincronizar itens com estoque zero
        main_win = self.window()
        if main_win and hasattr(main_win, "pages"):
            itens_zero_page = main_win.pages.get("itens_zero")
            if itens_zero_page:
                itens_zero_page._sincronizar()

        QMessageBox.information(
            self,
            "Sucesso",
            "Estoque atualizado com sucesso!"
        )

    def _fazer_atualizacao_completa(self, linhas):
        self.dados.clear()

        for linha in linhas:
            partes = linha.split("\t")
            if len(partes) < 2:
                continue
            item = {}
            for col, chave in enumerate(self.CHAVES):
                item[chave] = partes[col].strip() if col < len(partes) else ""
            self.dados.append(item)

        self._salvar_json()
        self._popular_tabela()

    def _fazer_atualizacao_parcial(self, linhas, header):
        # Fallbacks padrão caso não tenha cabeçalho ou alguma coluna não seja encontrada
        kardex_idx = 0
        qtde_novo_idx = 6
        qtde_retorno_idx = 4
        consumo_medio_idx = 18
        loc_novo_idx = 5
        loc_retorno_idx = 3

        if header:
            mapa = self._obter_indices_parciais(header)
            if "Kardex" in mapa:
                kardex_idx = mapa["Kardex"]
            if "Qtde novo" in mapa:
                qtde_novo_idx = mapa["Qtde novo"]
            if "Qtde retorno" in mapa:
                qtde_retorno_idx = mapa["Qtde retorno"]
            if "Consumo médio" in mapa:
                consumo_medio_idx = mapa["Consumo médio"]
            if "Loc novo" in mapa:
                loc_novo_idx = mapa["Loc novo"]
            if "Loc retorno" in mapa:
                loc_retorno_idx = mapa["Loc retorno"]

        max_idx = max(kardex_idx, qtde_novo_idx, qtde_retorno_idx, consumo_medio_idx, loc_novo_idx, loc_retorno_idx)

        dados_por_kardex = {
            str(item.get("Kardex", "")).strip(): item
            for item in self.dados
            if str(item.get("Kardex", "")).strip()
        }

        atualizou = False
        for linha in linhas:
            partes = linha.split("\t")
            if len(partes) <= max_idx:
                continue

            chave_kardex = partes[kardex_idx].strip()
            item = dados_por_kardex.get(chave_kardex)
            if not item:
                continue

            item["Qtde novo"] = partes[qtde_novo_idx].strip()
            item["Qtde retorno"] = partes[qtde_retorno_idx].strip()
            item["Consumo médio"] = partes[consumo_medio_idx].strip()
            item["Loc novo"] = partes[loc_novo_idx].strip()
            item["Loc retorno"] = partes[loc_retorno_idx].strip()
            atualizou = True

        if atualizou:
            self._salvar_json()
            self._popular_tabela()

    def _separar_cabecalho(self, linhas):
        if not linhas:
            return None, []

        primeiras_partes = linhas[0].split("\t")
        if self._eh_linha_cabecalho(primeiras_partes):
            return [p.strip() for p in primeiras_partes], linhas[1:]

        return None, linhas

    def _normalizar_coluna(self, texto):
        texto = texto.strip().lower()
        for original, substituicao in {
            "á": "a",
            "é": "e",
            "í": "i",
            "ó": "o",
            "ú": "u",
            "ã": "a",
            "õ": "o",
            "â": "a",
            "ê": "e",
            "ô": "o",
            "ç": "c",
        }.items():
            texto = texto.replace(original, substituicao)
        return "".join(ch for ch in texto if ch.isalnum())

    def _eh_linha_cabecalho(self, partes):
        if not partes:
            return False
        nome_normalizado = self._normalizar_coluna(partes[0])
        return nome_normalizado in {"id", "kardex", "codigo", "descricao"}

    def _obter_indices_parciais(self, header):
        mapa = {}
        mapeamento_nomes = {
            "kardex": "Kardex",
            "codkardex": "Kardex",
            
            "qtdenovo": "Qtde novo",
            "quantidadenovo": "Qtde novo",
            
            "qtderetorno": "Qtde retorno",
            "quantidaderetorno": "Qtde retorno",
            
            "consumomedio": "Consumo médio",
            "consumo": "Consumo médio",
            
            "locnovo": "Loc novo",
            "localnovo": "Loc novo",
            "localizacaonovo": "Loc novo",
            
            "locretorno": "Loc retorno",
            "localretorno": "Loc retorno",
            "localizacaoretorno": "Loc retorno",
        }

        for indice, coluna in enumerate(header):
            chave = self._normalizar_coluna(coluna)
            if chave in mapeamento_nomes:
                mapa[mapeamento_nomes[chave]] = indice

        return mapa

    def _aplicar_filtro(self):
        self._popular_tabela()

    def _atualizar_detalhes(self):
        kardex = ""
        row = self.tabela.currentRow()
        if row >= 0:
            cell = self.tabela.item(row, self.COLUNAS.index("Kardex"))
            if cell:
                kardex = cell.text().strip()

        item = None
        if kardex:
            item = next(
                (d for d in self.dados if str(d.get("Kardex", "")).strip() == kardex),
                None,
            )

        for chave, lbl in self._labels_valores.items():
            valor = str(item.get(chave, "")).strip() if item else ""
            lbl.setText(valor if valor else "-")

    def _alternar_modo(self):
        self.modo_resumido = not self.modo_resumido
        if self.modo_resumido:
            self.btn_toggle.setText("Visão completa")
        else:
            self.btn_toggle.setText("Visão resumida")
        self._popular_tabela()

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
