import json
import os

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QStyledItemDelegate, QMessageBox, QFrame,
)
from PySide6.QtCore import Qt, QSize
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
    return os.path.normpath(
        os.path.join(
            base,
            "Almox",
            "ItensAlmoxarifado",
            "ItensAlmoxarifado.json"
        )
    )


class EstoquePage(QWidget):
    COLUNAS_RESUMIDAS = [1, 2, 3, 4, 5, 6, 7, 40, 41, 8, 20, 22]

    HEADERS_RESUMIDOS = [
        "Kardex",
        "Código",
        "Descrição",
        "Loc novo",
        "Qtde novo",
        "Loc retorno",
        "Qtde retorno",
        "QtdeDPH",
        "Qtde QAD",
        "Fornecedor",
        "Custo",
        "Consumo médio",
    ]

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
        "QtdeDPH", "Qtde QAD",
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
        "QtdeDPH", "Qtde QAD",
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
        layout.setSpacing(0)

        card = QWidget()
        card.setObjectName("pageCard")

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(28, 24, 28, 24)
        card_layout.setSpacing(18)

        # =====================================================
        # CABEÇALHO
        # =====================================================
        topo = QHBoxLayout()
        topo.setSpacing(18)

        coluna_esquerda = QVBoxLayout()
        coluna_esquerda.setSpacing(12)

        titulo = QLabel("Estoque")
        titulo.setObjectName("pageTitle")
        titulo.setStyleSheet("""
            QLabel {
                color: #11163d;
                font-size: 25px;
                font-weight: 700;
            }
        """)
        coluna_esquerda.addWidget(titulo, 0, Qt.AlignmentFlag.AlignLeft)

        btn_atualizar = QPushButton("⟳  Atualizar")
        btn_atualizar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_atualizar.setFixedSize(168, 44)

        btn_atualizar.setStyleSheet("""
            QPushButton {
                background-color: #5b61f6;
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 14px;
                font-weight: 600;
            }

            QPushButton:hover {
                background-color: #4b51e6;
            }

            QPushButton:pressed {
                background-color: #4147d2;
            }
        """)

        btn_atualizar.clicked.connect(self._atualizar)
        coluna_esquerda.addWidget(btn_atualizar)

        self.campo_filtro = QLineEdit()
        self.campo_filtro.setPlaceholderText("⌕   Pesquisar...")
        self.campo_filtro.setFixedSize(250, 44)
        self.campo_filtro.textChanged.connect(self._aplicar_filtro)

        self.campo_filtro.setStyleSheet("""
            QLineEdit {
                background: white;
                color: #17203f;
                border: 1px solid #dce3ee;
                border-radius: 10px;
                padding-left: 15px;
                padding-right: 12px;
                font-size: 13px;
            }

            QLineEdit:focus {
                border: 1px solid #6366f1;
            }
        """)

        coluna_esquerda.addWidget(self.campo_filtro)
        coluna_esquerda.addStretch()

        topo.addLayout(coluna_esquerda)

        # =====================================================
        # CARD CENTRAL - ITEM SELECIONADO
        # =====================================================
        self.detalhes_box = QWidget()
        self.detalhes_box.setObjectName("detalhesBox")
        self.detalhes_box.setMinimumHeight(205)
        self.detalhes_box.setMaximumWidth(620)

        self.detalhes_box.setStyleSheet("""
            QWidget#detalhesBox {
                background: #ffffff;
                border: 1px solid #dce3ee;
                border-radius: 12px;
            }

            QLabel {
                border: none;
                background: transparent;
            }
        """)

        detalhes_layout = QVBoxLayout(self.detalhes_box)
        detalhes_layout.setContentsMargins(18, 14, 18, 14)
        detalhes_layout.setSpacing(8)

        lbl_visao = QLabel("VISÃO GERAL DO ITEM SELECIONADO")
        lbl_visao.setStyleSheet("""
            QLabel {
                color: #65769d;
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 0.5px;
            }
        """)
        detalhes_layout.addWidget(lbl_visao)

        corpo_detalhes = QHBoxLayout()
        corpo_detalhes.setSpacing(20)

        coluna_esquerda = QVBoxLayout()
        coluna_direita = QVBoxLayout()
        coluna_esquerda.setSpacing(0)
        coluna_direita.setSpacing(0)

        self._labels_valores = {}

        def criar_linha(rotulo, chave, simbolo="", cor="#5f6cf5"):
            widget = QWidget()
            widget.setMinimumHeight(39)

            lay = QHBoxLayout(widget)
            lay.setContentsMargins(0, 0, 0, 0)
            lay.setSpacing(8)

            icone = QLabel(simbolo)
            icone.setFixedWidth(22)
            icone.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icone.setStyleSheet(f"""
                QLabel {{
                    color: {cor};
                    font-size: 15px;
                    font-weight: 700;
                }}
            """)

            lbl_nome = QLabel(rotulo.upper())
            lbl_nome.setFixedWidth(105)
            lbl_nome.setStyleSheet("""
                QLabel {
                    color: #7183aa;
                    font-size: 10px;
                    font-weight: 600;
                }
            """)

            lbl_valor = QLabel("-")
            lbl_valor.setStyleSheet("""
                QLabel {
                    color: #17203f;
                    font-size: 12px;
                    font-weight: 600;
                }
            """)

            lbl_valor.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse
            )

            self._labels_valores[chave] = lbl_valor

            lay.addWidget(icone)
            lay.addWidget(lbl_nome)
            lay.addWidget(lbl_valor, 1)

            return widget

        def separador():
            linha = QFrame()
            linha.setFrameShape(QFrame.Shape.HLine)
            linha.setStyleSheet("""
                QFrame {
                    border: none;
                    background: #edf0f5;
                    max-height: 1px;
                }
            """)
            return linha

        coluna_esquerda.addWidget(
            criar_linha("Código", "Código", "◇", "#5865f2")
        )
        coluna_esquerda.addWidget(separador())

        coluna_esquerda.addWidget(
            criar_linha("Descrição", "Descrição", "▣", "#5865f2")
        )
        coluna_esquerda.addWidget(separador())

        coluna_esquerda.addWidget(
            criar_linha("Loc novo", "Loc novo", "⌖", "#5865f2")
        )
        coluna_esquerda.addWidget(separador())

        coluna_esquerda.addWidget(
            criar_linha("Loc retorno", "Loc retorno", "⌖", "#5865f2")
        )

        divisor_vertical = QFrame()
        divisor_vertical.setFrameShape(QFrame.Shape.VLine)
        divisor_vertical.setStyleSheet("""
            QFrame {
                border: none;
                background: #edf0f5;
                max-width: 1px;
            }
        """)

        coluna_direita.addWidget(
            criar_linha("Kardex", "Kardex", "▤", "#5865f2")
        )
        coluna_direita.addWidget(separador())

        coluna_direita.addWidget(
            criar_linha("Qtde novo", "Qtde novo", "▣", "#16b86c")
        )
        coluna_direita.addWidget(separador())

        coluna_direita.addWidget(
            criar_linha("Qtde retorno", "Qtde retorno", "▣", "#ff7a21")
        )
        coluna_direita.addWidget(separador())

        coluna_direita.addWidget(
            criar_linha("Consumo médio", "Consumo médio", "⌁", "#5865f2")
        )

        corpo_detalhes.addLayout(coluna_esquerda, 1)
        corpo_detalhes.addWidget(divisor_vertical)
        corpo_detalhes.addLayout(coluna_direita, 1)

        detalhes_layout.addLayout(corpo_detalhes)
        topo.addWidget(self.detalhes_box, 1)

        # =====================================================
        # CARD CONTADOR
        # =====================================================
        contador_box = QWidget()
        contador_box.setFixedWidth(160)
        contador_box.setFixedHeight(161)

        contador_box.setStyleSheet("""
            QWidget {
                background: white;
                border: 1px solid #dce3ee;
                border-radius: 12px;
            }

            QLabel {
                border: none;
                background: transparent;
            }
        """)

        contador_layout = QVBoxLayout(contador_box)
        contador_layout.setContentsMargins(16, 12, 16, 12)
        contador_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        contador_layout.setSpacing(6)

        circulo = QLabel("◇")
        circulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        circulo.setFixedSize(56, 56)
        circulo.setStyleSheet("""
            QLabel {
                background: #f0f1ff;
                color: #5b61f6;
                border: 1px solid #e0e3ff;
                border-radius: 28px;
                font-size: 30px;
                font-weight: 600;
            }
        """)

        contador_layout.addWidget(
            circulo,
            alignment=Qt.AlignmentFlag.AlignCenter
        )

        self.label_contador = QLabel("0")
        self.label_contador.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_contador.setStyleSheet("""
            QLabel {
                color: #11163d;
                font-size: 24px;
                font-weight: 700;
            }
        """)

        contador_layout.addWidget(self.label_contador)

        lbl_itens = QLabel("itens cadastrados")
        lbl_itens.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_itens.setStyleSheet("""
            QLabel {
                color: #63739a;
                font-size: 11px;
                font-weight: 500;
            }
        """)

        contador_layout.addWidget(lbl_itens)
        contador_layout.addStretch()

        self.btn_toggle = QPushButton("⛶  Visão completa")
        self.btn_toggle.setObjectName("btnSecondary")
        self.btn_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle.setFixedSize(160, 44)
        self.btn_toggle.setCheckable(True)
        self.btn_toggle.clicked.connect(self._alternar_modo)

        self.btn_toggle.setStyleSheet("""
            QPushButton {
                background: white;
                color: #52648f;
                border: 1px solid #dce3ee;
                border-radius: 10px;
                font-size: 13px;
                font-weight: 500;
                padding: 0 14px;
            }

            QPushButton:hover {
                background: #f8faff;
                border-color: #bcc9e0;
            }

            QPushButton:pressed {
                background: #eef2ff;
            }
        """)

        coluna_direita_superior = QWidget()
        coluna_direita_superior.setFixedWidth(160)
        coluna_superior_layout = QVBoxLayout(coluna_direita_superior)
        coluna_superior_layout.setContentsMargins(0, 0, 0, 0)
        coluna_superior_layout.setSpacing(12)

        coluna_superior_layout.addWidget(contador_box)
        coluna_superior_layout.addWidget(self.btn_toggle)

        topo.addWidget(coluna_direita_superior)
        card_layout.addLayout(topo)

        # =====================================================
        # TABELA
        # =====================================================
        self.tabela = QTableWidget(0, len(self.COLUNAS))
        self.tabela.setHorizontalHeaderLabels(self.COLUNAS)

        self.tabela.setStyleSheet("""
            QTableWidget {
                background: white;
                color: #111827;
                border: 1px solid #dfe5ee;
                border-radius: 11px;
                gridline-color: #edf0f5;
                font-size: 11px;
                selection-background-color: #eef0ff;
                selection-color: #111827;
            }

            QTableWidget::item {
                padding: 4px 7px;
                border-bottom: 1px solid #eef1f5;
            }

            QTableWidget::item:selected {
                background: #eef0ff;
                color: #111827;
            }

            QScrollBar:vertical {
                background: transparent;
                width: 10px;
                margin: 4px;
            }

            QScrollBar::handle:vertical {
                background: #cbd2df;
                border-radius: 5px;
                min-height: 30px;
            }

            QScrollBar::handle:vertical:hover {
                background: #aeb8ca;
            }

            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0px;
            }

            QScrollBar:horizontal {
                background: transparent;
                height: 10px;
            }

            QScrollBar::handle:horizontal {
                background: #cbd2df;
                border-radius: 5px;
                min-width: 30px;
            }
        """)

        header = self.tabela.horizontalHeader()
        header.setStyleSheet("""
            QHeaderView::section {
                background-color: #fbfcfe;
                color: #63739a;
                font-size: 9px;
                font-weight: 700;
                padding: 12px 8px;
                border: none;
                border-bottom: 1px solid #dfe5ee;
            }
        """)

        header.setStretchLastSection(False)

        for c in range(self.tabela.columnCount()):
            header.setSectionResizeMode(
                c,
                QHeaderView.ResizeMode.Interactive
            )

            if c == 1:
                largura = 165
            elif c == 2:
                largura = 180
            elif c == 3:
                largura = 290
            elif c in (4, 6):
                largura = 125
            elif c in (5, 7):
                largura = 110
            elif c == 8:
                largura = 150
            elif c == 20:
                largura = 110
            elif c == 22:
                largura = 125
            else:
                largura = 120

            header.resizeSection(c, largura)

        self.tabela.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )

        self.tabela.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )

        self.tabela.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked
        )

        self.tabela.setAlternatingRowColors(False)
        self.tabela.verticalHeader().setDefaultSectionSize(36)
        self.tabela.verticalHeader().setMinimumSectionSize(32)
        self.tabela.verticalHeader().setVisible(False)

        self.tabela.setHorizontalScrollMode(
            QAbstractItemView.ScrollMode.ScrollPerPixel
        )

        self.tabela.setVerticalScrollMode(
            QAbstractItemView.ScrollMode.ScrollPerPixel
        )

        self.tabela.setItemDelegate(
            EditorDelegate(self.tabela)
        )

        self.tabela.itemSelectionChanged.connect(
            self._atualizar_detalhes
        )

        card_layout.addWidget(self.tabela, 1)

        card.setStyleSheet("""
            QWidget#pageCard {
                background: #ffffff;
                border: 1px solid #e2e7ef;
                border-radius: 16px;
            }
        """)

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
                texto = " ".join(
                    str(v) for v in item.values()
                ).lower()

                if filtro_texto not in texto:
                    continue

            row = self.tabela.rowCount()
            self.tabela.insertRow(row)

            for col, chave in enumerate(self.CHAVES):
                valor = str(item.get(chave, ""))

                cell = QTableWidgetItem(valor)

                cell.setFlags(
                    cell.flags() & ~Qt.ItemFlag.ItemIsEditable
                )

                self.tabela.setItem(row, col, cell)

        if self.modo_resumido:
            for c in range(len(self.COLUNAS)):
                self.tabela.setColumnHidden(
                    c,
                    c not in self.COLUNAS_RESUMIDAS
                )

            header = self.tabela.horizontalHeader()
            ordem = [
                self.COLUNAS.index(col)
                for col in self.HEADERS_RESUMIDOS
            ]

            for i, logico in enumerate(ordem):
                pos = header.visualIndex(logico)

                if pos != i:
                    header.moveSection(pos, i)
        else:
            for c in range(len(self.COLUNAS)):
                self.tabela.setColumnHidden(c, False)

        self.tabela.blockSignals(False)

        self.label_contador.setText(
            str(self.tabela.rowCount())
        )

        self._atualizar_detalhes()

    def _atualizar(self):
        modo_anterior = self.modo_resumido

        if self.modo_resumido:
            self.modo_resumido = False
            self.btn_toggle.setText("▣  Visão resumida")

        clipboard = QGuiApplication.clipboard()
        texto = clipboard.text()

        if not texto.strip():
            QMessageBox.warning(
                self,
                "Aviso",
                "A área de transferência está vazia."
            )

            self.modo_resumido = modo_anterior

            if modo_anterior:
                self.btn_toggle.setText("⛶  Visão completa")

            return

        linhas = [
            l.strip()
            for l in texto.replace("\r\n", "\n").split("\n")
            if l.strip()
        ]

        if not linhas:
            self.modo_resumido = modo_anterior

            if modo_anterior:
                self.btn_toggle.setText("⛶  Visão completa")

            return

        header, dados_linha = self._separar_cabecalho(linhas)

        if not dados_linha:
            QMessageBox.warning(
                self,
                "Aviso",
                "Não há dados válidos para atualizar."
            )

            self.modo_resumido = modo_anterior

            if modo_anterior:
                self.btn_toggle.setText("⛶  Visão completa")

            return

        colunas = len(dados_linha[0].split("\t"))

        if colunas == 40:
            resposta = QMessageBox.question(
                self,
                "Confirmação",
                "Atualizar completamente o estoque?",
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )

            if resposta != QMessageBox.StandardButton.Yes:
                self.modo_resumido = modo_anterior

                if modo_anterior:
                    self.btn_toggle.setText("⛶  Visão completa")

                return

            self._fazer_atualizacao_completa(
                dados_linha
            )

        elif colunas == 24:
            self._fazer_atualizacao_parcial(
                dados_linha,
                header
            )

        else:
            QMessageBox.warning(
                self,
                "Formato inválido",
                "A tabela copiada deve ter 40 ou 24 colunas."
            )

            self.modo_resumido = modo_anterior

            if modo_anterior:
                self.btn_toggle.setText("⛶  Visão completa")

            return

        self.modo_resumido = modo_anterior

        if modo_anterior:
            self.btn_toggle.setText(
                "⛶  Visão completa"
            )
        else:
            self.btn_toggle.setText(
                "▣  Visão resumida"
            )

        self._popular_tabela()

        # Sincronizar itens com estoque zero
        main_win = self.window()

        if main_win and hasattr(main_win, "pages"):
            itens_zero_page = main_win.pages.get(
                "itens_zero"
            )

            if itens_zero_page:
                itens_zero_page._sincronizar()

        QMessageBox.information(
            self,
            "Sucesso",
            "Estoque atualizado com sucesso!"
        )

    def _fazer_atualizacao_completa(self, linhas):
        novos_por_kardex = {}

        for linha in linhas:
            partes = linha.split("\t")

            if len(partes) < 2:
                continue

            item = {}

            for col, chave in enumerate(self.CHAVES):
                if col < len(partes):
                    item[chave] = partes[col].strip()

            chave_kardex = str(
                item.get("Kardex", "")
            ).strip()

            if chave_kardex:
                novos_por_kardex[
                    chave_kardex
                ] = item

        existentes_por_kardex = {
            str(item.get("Kardex", "")).strip(): item
            for item in self.dados
            if str(item.get("Kardex", "")).strip()
        }

        for kardex, item_novo in (
            novos_por_kardex.items()
        ):
            item_atual = (
                existentes_por_kardex.get(kardex)
            )

            if item_atual is not None:
                item_atual.update(item_novo)
            else:
                self.dados.append(item_novo)

        self._salvar_json()
        self._popular_tabela()

    def _fazer_atualizacao_parcial(self, linhas, header):
        kardex_idx = 0
        qtde_novo_idx = 6
        qtde_retorno_idx = 4
        consumo_medio_idx = 18
        loc_novo_idx = 5
        loc_retorno_idx = 3

        dph_idx = -1
        qad_idx = -1

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

            if "QtdeDPH" in mapa:
                dph_idx = mapa["QtdeDPH"]

            if "Qtde QAD" in mapa:
                qad_idx = mapa["Qtde QAD"]

        max_idx = max(
            kardex_idx,
            qtde_novo_idx,
            qtde_retorno_idx,
            consumo_medio_idx,
            loc_novo_idx,
            loc_retorno_idx
        )

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

            item = dados_por_kardex.get(
                chave_kardex
            )

            if not item:
                continue

            item["Qtde novo"] = (
                partes[qtde_novo_idx].strip()
            )

            item["Qtde retorno"] = (
                partes[qtde_retorno_idx].strip()
            )

            item["Consumo médio"] = (
                partes[consumo_medio_idx].strip()
            )

            item["Loc novo"] = (
                partes[loc_novo_idx].strip()
            )

            item["Loc retorno"] = (
                partes[loc_retorno_idx].strip()
            )

            if dph_idx >= 0 and len(partes) > dph_idx:
                item["QtdeDPH"] = (
                    partes[dph_idx].strip()
                )

            if qad_idx >= 0 and len(partes) > qad_idx:
                item["Qtde QAD"] = (
                    partes[qad_idx].strip()
                )

            atualizou = True

        if atualizou:
            self._salvar_json()
            self._popular_tabela()

    def _separar_cabecalho(self, linhas):
        if not linhas:
            return None, []

        primeiras_partes = linhas[0].split("\t")

        if self._eh_linha_cabecalho(
            primeiras_partes
        ):
            return (
                [
                    p.strip()
                    for p in primeiras_partes
                ],
                linhas[1:]
            )

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
            texto = texto.replace(
                original,
                substituicao
            )

        return "".join(
            ch for ch in texto
            if ch.isalnum()
        )

    def _eh_linha_cabecalho(self, partes):
        if not partes:
            return False

        nome_normalizado = self._normalizar_coluna(
            partes[0]
        )

        return nome_normalizado in {
            "id",
            "kardex",
            "codigo",
            "descricao",
        }

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

            "qtedph": "QtdeDPH",
            "qtdedph": "QtdeDPH",
            "qtdph": "QtdeDPH",

            "qtdeqad": "Qtde QAD",
            "qtdqad": "Qtde QAD",
        }

        for indice, coluna in enumerate(header):
            chave = self._normalizar_coluna(
                coluna
            )

            if chave in mapeamento_nomes:
                mapa[
                    mapeamento_nomes[chave]
                ] = indice

        return mapa

    def _aplicar_filtro(self):
        self._popular_tabela()

    def _atualizar_detalhes(self):
        kardex = ""

        row = self.tabela.currentRow()

        if row >= 0:
            cell = self.tabela.item(
                row,
                self.COLUNAS.index("Kardex")
            )

            if cell:
                kardex = cell.text().strip()

        item = None

        if kardex:
            item = next(
                (
                    d for d in self.dados
                    if str(
                        d.get("Kardex", "")
                    ).strip() == kardex
                ),
                None,
            )

        for chave, lbl in self._labels_valores.items():
            valor = (
                str(item.get(chave, "")).strip()
                if item
                else ""
            )

            lbl.setText(
                valor if valor else "-"
            )

    def _alternar_modo(self):
        self.modo_resumido = (
            not self.modo_resumido
        )

        if self.modo_resumido:
            self.btn_toggle.setText(
                "⛶  Visão completa"
            )
        else:
            self.btn_toggle.setText(
                "▣  Visão resumida"
            )

        self._popular_tabela()

    def _salvar_json(self):
        caminho = _caminho_json()

        if not caminho:
            import config
            config.avisar_sem_pasta(self)
            return

        try:
            os.makedirs(
                os.path.dirname(caminho),
                exist_ok=True
            )

            with open(
                caminho,
                "w",
                encoding="utf-8"
            ) as f:
                json.dump(
                    self.dados,
                    f,
                    ensure_ascii=False,
                    indent=2
                )

        except OSError:
            pass