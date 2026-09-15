import json
import os
import re
from datetime import datetime

import qtawesome

from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QGridLayout,
    QAbstractItemView, QStyledItemDelegate, QComboBox, QInputDialog, QMessageBox, QMenu,
    QRadioButton, QButtonGroup, QDateEdit, QFrame,
)
from PySide6.QtCore import Qt, QSize, QTimer, QDate, QEvent
from PySide6.QtGui import QColor, QBrush, QShortcut, QKeySequence, QCursor, QIcon, QPixmap, QDoubleValidator


# ── Cores por status (novos valores solicitados) ───────────────────────────
CORES_STATUS = {
    "Pendente": "#fef9c3",
    "Programado": "#e0f2fe",
    "Entregue": "#dcfce7",
    "Programado/Entregue": "#d1fae5",
    "Cancelado": "#fee2e2",
    "Devolvido": "#ffedd5",
    # compatibilidade com dados antigos
    "Em Análise": "#e0f2fe",
    "Aprovada": "#dcfce7",
    "Atendida": "#bbf7d0",
    "Parcial": "#ffedd5",
    "Rejeitada": "#fecaca",
}

TEXTO_STATUS = {
    "Pendente": "#92400e",
    "Programado": "#075985",
    "Entregue": "#166534",
    "Programado/Entregue": "#065f46",
    "Cancelado": "#991b1b",
    "Devolvido": "#9a3412",
    "Em Análise": "#075985",
    "Aprovada": "#166534",
    "Atendida": "#14532d",
    "Parcial": "#9a3412",
    "Rejeitada": "#7f1d1d",
}

# Valores do combobox de Status do filtro/tabela — conforme solicitado:
# Vazio, Pendente, Programado, Entregue, programado/entregue, cancelado, devolvido
STATUS_OPCOES = ["", "Pendente", "Programado", "Entregue", "Programado/Entregue", "Cancelado", "Devolvido"]
STATUS_FILTRO_LABELS = ["Vazio", "Pendente", "Programado", "Entregue", "Programado/Entregue", "Cancelado", "Devolvido"]


def _caminho_json():
    import config
    base = config.obter_caminho_jsons()
    if not base:
        return ""
    return os.path.normpath(os.path.join(base, "Almox", "SolicitacoesSA", "solicitacoes_sa.json"))


class EditorDelegate(QStyledItemDelegate):
    COLS_EDITAVEIS = {5}  # apenas Qtde Dph editável
    COLS_NUMERICAS = {5, 8, 9}
    COL_STATUS = 99

    def __init__(self, parent=None, edit_mode_getter=None):
        super().__init__(parent)
        self._edit_mode_getter = edit_mode_getter or (lambda: True)

    def paint(self, painter, option, index):
        self.initStyleOption(option, index)
        bg = index.data(Qt.BackgroundRole)
        if bg is not None:
            painter.save()
            painter.fillRect(option.rect, QBrush(bg) if not isinstance(bg, QBrush) else bg)
            painter.restore()
        super().paint(painter, option, index)

    def sizeHint(self, option, index):
        base = super().sizeHint(option, index)
        return QSize(base.width(), max(base.height(), 32))

    def createEditor(self, parent, option, index):
        if not self._edit_mode_getter():
            return None
        # Apenas Qtde N/R/P são editáveis
        if index.column() not in self.COLS_EDITAVEIS:
            return None
        if index.column() == self.COL_STATUS:
            # Status não é mais editável (mantido apenas por compatibilidade, mas bloqueado)
            return None
            editor = QComboBox(parent)
            editor.setEditable(False)
            # exibe "Vazio" para "" mas salva como ""
            for label, valor in zip(STATUS_FILTRO_LABELS, STATUS_OPCOES):
                editor.addItem(label, valor)
            editor.setContentsMargins(0, 0, 0, 0)
            editor.setStyleSheet("padding:0px; margin:0px; border:none; background:#ffffff;")
            editor.installEventFilter(self)
            return editor
        editor = super().createEditor(parent, option, index)
        try:
            if isinstance(editor, QLineEdit):
                editor.setContentsMargins(0, 0, 0, 0)
                editor.setStyleSheet(
                    "QLineEdit { padding:0px; margin:0px; border:none; border-bottom:2px solid #6366f1; border-radius:0px; background:#ffffff; }"
                )
                if index.column() in self.COLS_NUMERICAS:
                    validator = QDoubleValidator(-9999999, 999999999, 2, editor)
                    validator.setNotation(QDoubleValidator.Notation.StandardNotation)
                    editor.setValidator(validator)
                editor.installEventFilter(self)
        except Exception:
            pass
        return editor

    def updateEditorGeometry(self, editor, option, index):
        # sem padding — ocupa toda a célula
        editor.setGeometry(option.rect)

    def eventFilter(self, editor, event):
        if event.type() == QEvent.Type.KeyPress:
            key = event.key()
            # navegação por setas e Enter/Tab já com edição focada
            nav_keys = {
                Qt.Key.Key_Up: (-1, 0),
                Qt.Key.Key_Down: (1, 0),
                Qt.Key.Key_Left: (0, -1),
                Qt.Key.Key_Right: (0, 1),
                Qt.Key.Key_Tab: (0, 1),
                Qt.Key.Key_Enter: (1, 0),
                Qt.Key.Key_Return: (1, 0),
            }
            if key in nav_keys:
                # para QLineEdit, deixa Left/Right mover cursor se houver seleção/texto
                if isinstance(editor, QLineEdit) and key in (Qt.Key.Key_Left, Qt.Key.Key_Right):
                    # se cursor não está no extremo, deixa editar texto
                    txt = editor.text()
                    pos = editor.cursorPosition()
                    if key == Qt.Key.Key_Left and pos > 0:
                        return False
                    if key == Qt.Key.Key_Right and pos < len(txt):
                        return False
                # commit atual
                try:
                    table = self.parent()
                    if table is not None and isinstance(table, QTableWidget):
                        idx = table.currentIndex()
                        if idx.isValid():
                            # commit
                            self.commitData.emit(editor)
                            self.closeEditor.emit(editor, QStyledItemDelegate.EndEditHint.NoHint)
                            dr, dc = nav_keys[key]
                            # Shift+Tab volta
                            mods = event.modifiers()
                            if key == Qt.Key.Key_Tab and (mods & Qt.KeyboardModifier.ShiftModifier):
                                dc = -1
                                dr = 0
                            nr = idx.row() + dr
                            nc = idx.column() + dc
                            # clampa nos limites
                            nr = max(0, min(nr, table.rowCount() - 1))
                            nc = max(0, min(nc, table.columnCount() - 1))
                            table.setCurrentCell(nr, nc)
                            # foca e já abre edição na próxima (CurrentChanged cuidará, mas força)
                            nxt = table.item(nr, nc)
                            if nxt and (nxt.flags() & Qt.ItemFlag.ItemIsEditable):
                                table.editItem(nxt)
                            return True
                except Exception:
                    pass
        return super().eventFilter(editor, event)

    def setEditorData(self, editor, index):
        if isinstance(editor, QComboBox):
            valor = index.data(Qt.DisplayRole) or ""
            # mapeia valor -> índice pela userData
            idx = editor.findData(valor)
            if idx < 0:
                # compat: procura por texto
                idx = editor.findText(valor)
            if idx >= 0:
                editor.setCurrentIndex(idx)
            else:
                editor.setCurrentIndex(0)
        else:
            super().setEditorData(editor, index)

    def setModelData(self, editor, model, index):
        if isinstance(editor, QComboBox):
            data = editor.currentData()
            if data is None:
                data = editor.currentText()
                if data == "Vazio":
                    data = ""
            model.setData(index, data)
        else:
            super().setModelData(editor, model, index)


class DphPage(QWidget):
    COLUNAS = [
        "Req",
        "Req neces.",
        "Destino",
        "Kardex",
        "Código",
        "Qtde Dph",
        "Conta",
        "Entidade",
        "Custo unit",
        "Custo total",
        "DPH",
        "Proj/Cta",
        "Imprimir",
    ]
    CHAVES = [
        "req",
        "req_neces",
        "destino",
        "kardex",
        "codigo",
        "qtde_dph",
        "conta",
        "entidade",
        "custo_unit",
        "custo_total",
        "dph",
        "proj_cta",
        "imprimir",
    ]

    IDX_STATUS = 99
    IDX_KARDEX = 3
    IDX_CODIGO = 4
    IDX_NUM_REQ = 0

    def __init__(self):
        super().__init__()
        self.dados = []
        self._edit_mode = True  # edição sempre liberada agora que botões foram removidos
        self._setup_ui()
        self._setup_shortcuts()
        self._carregar_dados()

    # ── UI ────────────────────────────────────────────────────────────────────
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        card = QWidget()
        card.setObjectName("pageCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 16, 18, 16)
        card_layout.setSpacing(12)

        # ── FILTROS: 8 campos + 2 botões em UMA ÚNICA LINHA, width -60% ──
        filtro_container = QWidget()
        filtro_container.setObjectName("filtroContainer")
        # uma linha precisa ocupar toda a largura do card para caber 10 itens estreitos
        filtro_layout = QHBoxLayout(filtro_container)
        filtro_layout.setContentsMargins(0, 0, 0, 0)
        filtro_layout.setSpacing(8)

        def add_field_h(label_text, widget):
            widget.setFixedHeight(30)
            # -60% => 40% do original (~280 -> ~105)
            widget.setMaximumWidth(108)
            widget.setMinimumWidth(92)
            cont = QWidget()
            v = QVBoxLayout(cont)
            v.setContentsMargins(0, 0, 0, 0)
            v.setSpacing(3)
            lbl = QLabel(label_text)
            lbl.setObjectName("fieldLabel")
            lbl.setStyleSheet("color:#64748b; font-size:9px; font-weight:600;")
            lbl.setMaximumWidth(108)
            v.addWidget(lbl)
            v.addWidget(widget)
            cont.setMaximumWidth(112)
            filtro_layout.addWidget(cont)
            return cont

        # 1) Nº de DPH
        self.filtro_dph = QLineEdit()
        self.filtro_dph.setPlaceholderText("Ex: DPH123...")
        self.filtro_dph.returnPressed.connect(self._aplicar_filtro)
        add_field_h("Nº de DPH", self.filtro_dph)

        # 2) Nº de SA
        self.filtro_sa = QLineEdit()
        self.filtro_sa.setPlaceholderText("Ex: SA123...")
        self.filtro_sa.returnPressed.connect(self._aplicar_filtro)
        add_field_h("Nº de SA", self.filtro_sa)

        # 3) Kardex
        self.filtro_kardex = QLineEdit()
        self.filtro_kardex.setPlaceholderText("Kardex...")
        self.filtro_kardex.returnPressed.connect(self._aplicar_filtro)
        add_field_h("Kardex", self.filtro_kardex)

        # 4) Conta
        self.filtro_conta = QLineEdit()
        self.filtro_conta.setPlaceholderText("Conta...")
        self.filtro_conta.returnPressed.connect(self._aplicar_filtro)
        add_field_h("Conta", self.filtro_conta)

        # stubs para compatibilidade com lógica antiga (não exibidos)
        self.filtro_status = QComboBox()
        self.filtro_status.addItem("", "")
        self.filtro_status.setVisible(False)
        self.filtro_solicitante = QComboBox()
        self.filtro_solicitante.addItem("", "")
        self.filtro_solicitante.setVisible(False)
        self.filtro_requisicao = QLineEdit()
        self.filtro_requisicao.setVisible(False)
        self.filtro_destino = QLineEdit()
        self.filtro_destino.setVisible(False)
        self.filtro_projeto = QComboBox()
        self.filtro_projeto.addItem("", "")
        self.filtro_projeto.setVisible(False)

        # Botões na mesma linha
        self.btn_aplicar_filtro = QPushButton(qtawesome.icon('fa6s.filter', color='#ffffff'), "  Aplicar filtro")
        self.btn_aplicar_filtro.setObjectName("btnPrimary")
        self.btn_aplicar_filtro.setFixedHeight(30)
        self.btn_aplicar_filtro.setFixedWidth(118)
        self.btn_aplicar_filtro.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_aplicar_filtro.clicked.connect(self._aplicar_filtro)
        filtro_layout.addWidget(self.btn_aplicar_filtro, alignment=Qt.AlignmentFlag.AlignBottom)

        self.btn_limpar_filtro = QPushButton(qtawesome.icon('fa6s.xmark', color='#64748b'), "  Limpar filtro")
        self.btn_limpar_filtro.setObjectName("btnSecondary")
        self.btn_limpar_filtro.setFixedHeight(30)
        self.btn_limpar_filtro.setFixedWidth(112)
        self.btn_limpar_filtro.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_limpar_filtro.clicked.connect(self._limpar_filtros)
        filtro_layout.addWidget(self.btn_limpar_filtro, alignment=Qt.AlignmentFlag.AlignBottom)

        filtro_layout.addStretch()
        card_layout.addWidget(filtro_container)

        # ── QUADRO SA (abaixo dos filtros, acima da tabela) ──
        self.quadro_sa = QFrame()
        self.quadro_sa.setObjectName("quadroSA")
        self.quadro_sa.setFrameShape(QFrame.Shape.StyledPanel)
        self.quadro_sa.setStyleSheet("""
            QFrame#quadroSA {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 12px;
            }
        """)
        quadro_layout = QVBoxLayout(self.quadro_sa)
        quadro_layout.setContentsMargins(14, 12, 14, 12)
        quadro_layout.setSpacing(10)

        # ── QUADRO DPH: DPH Pendente Nº + 4 botões ──
        linha_dph = QHBoxLayout()
        linha_dph.setSpacing(10)
        linha_dph.setContentsMargins(0, 0, 0, 0)
        lbl_dph = QLabel("DPH Pendente Nº")
        lbl_dph.setStyleSheet("color:#1e293b; font-size:12px; font-weight:700;")
        linha_dph.addWidget(lbl_dph)
        self.campo_dph_pendente = QLineEdit()
        self.campo_dph_pendente.setPlaceholderText("Nº DPH...")
        self.campo_dph_pendente.setFixedHeight(30)
        self.campo_dph_pendente.setFixedWidth(160)
        self.campo_dph_pendente.setStyleSheet("background:#ffffff; border:1px solid #e2e8f0; border-radius:8px; padding:4px 10px; font-size:12px;")
        linha_dph.addWidget(self.campo_dph_pendente)
        self.btn_marcar_conta = QPushButton("Marcar conta imprimir")
        self.btn_marcar_conta.setObjectName("btnSecondary")
        self.btn_marcar_conta.setFixedHeight(30)
        self.btn_marcar_conta.setCursor(Qt.CursorShape.PointingHandCursor)
        linha_dph.addWidget(self.btn_marcar_conta)
        self.btn_visualizar_dph = QPushButton(qtawesome.icon('fa6s.eye', color='#ffffff'), "  visualizar DPH")
        self.btn_visualizar_dph.setObjectName("btnPrimary")
        self.btn_visualizar_dph.setFixedHeight(30)
        self.btn_visualizar_dph.setCursor(Qt.CursorShape.PointingHandCursor)
        linha_dph.addWidget(self.btn_visualizar_dph)
        self.btn_imprimir_dph = QPushButton(qtawesome.icon('fa6s.print', color='#ffffff'), "  Imprimir DPH")
        self.btn_imprimir_dph.setObjectName("btnPrimary")
        self.btn_imprimir_dph.setFixedHeight(30)
        self.btn_imprimir_dph.setCursor(Qt.CursorShape.PointingHandCursor)
        linha_dph.addWidget(self.btn_imprimir_dph)
        self.btn_saida_periodo = QPushButton("Saida por periodo")
        self.btn_saida_periodo.setObjectName("btnSecondary")
        self.btn_saida_periodo.setFixedHeight(30)
        self.btn_saida_periodo.setCursor(Qt.CursorShape.PointingHandCursor)
        linha_dph.addWidget(self.btn_saida_periodo)
        linha_dph.addStretch()
        quadro_layout.addLayout(linha_dph)

        # Label contador (mantido para tabela)
        self.label_contador = QLabel("0 solicitações")
        self.label_contador.setObjectName("statusLabel")
        self.label_contador.setStyleSheet("color:#64748b; font-size:11px; font-weight:600;")
        self.label_contador.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        # Filtro para tabela (embaixo do quadro)
        filtro_tabela_container = QWidget()
        filtro_tabela_layout = QHBoxLayout(filtro_tabela_container)
        filtro_tabela_layout.setContentsMargins(0, 6, 0, 0)
        filtro_tabela_layout.setSpacing(8)
        lbl_filtro = QLabel("Filtro tabela:")
        lbl_filtro.setStyleSheet("color:#475569; font-size:11px; font-weight:700;")
        filtro_tabela_layout.addWidget(lbl_filtro)
        self.campo_filtro_tabela = QLineEdit()
        self.campo_filtro_tabela.setPlaceholderText("Filtrar...")
        self.campo_filtro_tabela.setFixedHeight(30)
        self.campo_filtro_tabela.setMinimumWidth(240)
        self.campo_filtro_tabela.setStyleSheet("background:#ffffff; border:1px solid #e2e8f0; border-radius:8px; padding:4px 10px; font-size:12px;")
        self.campo_filtro_tabela.textChanged.connect(self._aplicar_filtro)
        filtro_tabela_layout.addWidget(self.campo_filtro_tabela)
        filtro_tabela_layout.addStretch()
        filtro_tabela_layout.addWidget(self.label_contador)
        quadro_layout.addWidget(filtro_tabela_container)

        # ── Layout inferior: quadro esquerdo + (quadro_sa + tabela) à direita ──
        # O quadro esquerdo terá width igual ao conjunto quadro_sa + tabela (lado direito)
        conteudo_inferior = QWidget()
        conteudo_inferior_lay = QHBoxLayout(conteudo_inferior)
        conteudo_inferior_lay.setContentsMargins(0, 0, 0, 0)
        conteudo_inferior_lay.setSpacing(12)

        # Quadro à esquerda — Lista de DPHs, 100px width
        self.quadro_esquerdo = QFrame()
        self.quadro_esquerdo.setObjectName("quadroEsquerdo")
        self.quadro_esquerdo.setFrameShape(QFrame.Shape.StyledPanel)
        self.quadro_esquerdo.setStyleSheet("""
            QFrame#quadroEsquerdo {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 12px;
            }
        """)
        self.quadro_esquerdo.setFixedWidth(100)
        self.quadro_esquerdo.setMinimumWidth(100)
        self.quadro_esquerdo.setMaximumWidth(100)
        lay_esq = QVBoxLayout(self.quadro_esquerdo)
        lay_esq.setContentsMargins(4, 6, 4, 6)
        lay_esq.setSpacing(4)
        lbl_esq_titulo = QLabel("Lista de DPHs")
        lbl_esq_titulo.setStyleSheet("color:#1e293b; font-size:9px; font-weight:700;")
        lbl_esq_titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_esq_titulo.setWordWrap(True)
        lay_esq.addWidget(lbl_esq_titulo)
        # lista de arquivos DPH (reutiliza SA)
        from PySide6.QtWidgets import QListWidget, QListWidgetItem
        self.lista_sas = QListWidget()
        self.lista_sas.setObjectName("listaSAs")
        self.lista_sas.setStyleSheet("""
            QListWidget#listaSAs {
                background-color: #f8fafc;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                font-size: 10px;
                outline: none;
            }
            QListWidget#listaSAs::item {
                padding: 6px 4px;
                border-bottom: 1px solid #f1f5f9;
                color: #334155;
            }
            QListWidget#listaSAs::item:selected {
                background-color: #eef2ff;
                color: #4f46e5;
                border-radius: 4px;
            }
            QListWidget#listaSAs::item:hover {
                background-color: #f1f5f9;
            }
        """)
        self.lista_sas.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.lista_sas.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.lista_sas.setWordWrap(False)
        self.lista_sas.itemClicked.connect(self._on_sa_selecionada)
        self.lista_sas.itemDoubleClicked.connect(self._on_sa_selecionada)
        lay_esq.addWidget(self.lista_sas, 1)
        # botão atualizar lista discreto
        self.btn_atualizar_lista_sa = QPushButton(qtawesome.icon('fa6s.rotate', color='#64748b'), "")
        self.btn_atualizar_lista_sa.setObjectName("btnGhost")
        self.btn_atualizar_lista_sa.setFixedSize(24, 24)
        self.btn_atualizar_lista_sa.setToolTip("Atualizar lista de SAs")
        self.btn_atualizar_lista_sa.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_atualizar_lista_sa.clicked.connect(self._atualizar_lista_sas)
        # coloca botão abaixo da lista, alinhado à direita
        wrap_btn = QWidget()
        hb = QHBoxLayout(wrap_btn)
        hb.setContentsMargins(0, 0, 0, 0)
        hb.addStretch()
        hb.addWidget(self.btn_atualizar_lista_sa)
        lay_esq.addWidget(wrap_btn)

        lado_direito = QWidget()
        lado_direito_lay = QVBoxLayout(lado_direito)
        lado_direito_lay.setContentsMargins(0, 0, 0, 0)
        lado_direito_lay.setSpacing(12)
        lado_direito_lay.addWidget(self.quadro_sa)

        # Tabela (inalterada) vai para o lado direito
        self.tabela = QTableWidget(0, len(self.COLUNAS))
        self.tabela.setObjectName("tabelaSolicitacoesSA")
        self.tabela.setStyleSheet("""
            QTableWidget#tabelaSolicitacoesSA {
                background-color: #ffffff;
                border: 1px solid #eef1f6;
                border-radius: 12px;
                gridline-color: transparent;
                selection-background-color: #eef2ff;
                selection-color: #1e1b4b;
                font-size: 12px;
                outline: none;
            }
            QTableWidget#tabelaSolicitacoesSA::item {
                padding: 4px 8px;
                border-bottom: 1px solid #f3f4f6;
            }
            QTableWidget#tabelaSolicitacoesSA::item:selected {
                background-color: #eef2ff;
                color: #1e1b4b;
            }
            QTableWidget#tabelaSolicitacoesSA::item:hover {
                background-color: #f5f3ff;
            }
            QTableWidget#tabelaSolicitacoesSA::item:focus {
                outline: none;
                border: 1.5px solid #6366f1;
                border-radius: 4px;
            }
        """)
        self.tabela.setHorizontalHeaderLabels(self.COLUNAS)
        header = self.tabela.horizontalHeader()
        header.setStretchLastSection(False)
        larguras = {
            0: 70,   # Req
            1: 85,   # Req neces.
            2: 110,  # Destino
            3: 110,  # Kardex
            4: 100,  # Código
            5: 80,   # Qtde Dph
            6: 85,   # Conta
            7: 110,  # Entidade
            8: 85,   # Custo unit
            9: 95,   # Custo total
            10: 95,  # Sphm status
            11: 95,  # Proj/Cta
            12: 80,  # Imprimir
        }
        for c, w in larguras.items():
            header.setSectionResizeMode(c, QHeaderView.ResizeMode.Fixed)
            header.resizeSection(c, w)
        header.setSectionResizeMode(12, QHeaderView.ResizeMode.Interactive)
        header.setStyleSheet(
            "QHeaderView::section {"
            "  font-size: 8.5px; font-weight: 700;"
            "  background-color: #f8fafc; color: #64748b;"
            "  text-transform: uppercase; letter-spacing: 0.3px;"
            "  padding: 0px; margin: 0px; border: none; border-bottom: 2px solid #e2e8f0;"
            "}"
        )

        self.tabela.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self.tabela.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.tabela.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked
            | QAbstractItemView.EditTrigger.EditKeyPressed
            | QAbstractItemView.EditTrigger.AnyKeyPressed
            | QAbstractItemView.EditTrigger.CurrentChanged
        )
        self.tabela.setAlternatingRowColors(True)
        self.tabela.verticalHeader().setDefaultSectionSize(30)
        self.tabela.verticalHeader().setMinimumSectionSize(26)
        self.tabela.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.tabela.verticalHeader().setVisible(False)
        self.tabela.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.tabela.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.tabela.setItemDelegate(EditorDelegate(self.tabela, edit_mode_getter=lambda: self._edit_mode))
        self.tabela.itemChanged.connect(self._item_modificado)
        self.tabela.currentCellChanged.connect(self._ao_mudar_celula)
        self.tabela.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tabela.customContextMenuRequested.connect(self._context_menu)
        self.tabela.cellDoubleClicked.connect(self._on_cell_double_clicked)
        self.tabela.cellClicked.connect(self._on_cell_clicked)

        lado_direito_lay.addWidget(self.tabela, 1)
        conteudo_inferior_lay.addWidget(self.quadro_esquerdo)
        conteudo_inferior_lay.addWidget(lado_direito, 1)
        card_layout.addWidget(conteudo_inferior, 1)
        layout.addWidget(card)

    def _setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+F"), self, self._buscar_item)
        QShortcut(QKeySequence("Ctrl+L"), self, self._buscar_item)
        QShortcut(QKeySequence("Ctrl+N"), self, self._adicionar_linha)
        QShortcut(QKeySequence("Ctrl+C"), self.tabela, self._copiar_selecao)
        sc_esc = QShortcut(QKeySequence("Escape"), self)
        sc_esc.activated.connect(self._limpar_filtros)
        QShortcut(QKeySequence("Delete"), self.tabela, self._remover_linha)

    # ── Dados ─────────────────────────────────────────────────────────────────
    def _carregar_dados(self):
        caminho = _caminho_json()
        try:
            if caminho and os.path.isfile(caminho):
                with open(caminho, "r", encoding="utf-8") as f:
                    self.dados = json.load(f)
                    if not isinstance(self.dados, list):
                        self.dados = []
            else:
                self.dados = []
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            self.dados = []
        for item in list(self.dados):
            if not isinstance(item, dict):
                continue
            if "numero_sa" in item and "numero_req" not in item:
                item["numero_req"] = item.pop("numero_sa")
            if "data" in item and "data_necessidade" not in item:
                if not item.get("data_necessidade"):
                    item["data_necessidade"] = item.pop("data")
                else:
                    item.pop("data", None)
            if "solicitante" in item:
                # preserva solicitante em observações se necessário, mas mantém chave para filtro
                # garante que não perde: cria chave solicitante se não existir
                if "solicitante" not in item:
                    pass
            if "setor" in item:
                item.pop("setor", None)
            if "descricao" in item and "observacoes" not in item:
                item["observacoes"] = item.pop("descricao")
            if "um" in item:
                item.pop("um", None)
            for ch in self.CHAVES:
                item.setdefault(ch, "")
            # normaliza status antigo vazio para ""
            if item.get("status") is None:
                item["status"] = ""
            # mantém solicitante/projeto_destino se vier do filtro antigo
            item.setdefault("solicitante", "")
            item.setdefault("projeto_destino", "")
            if not item.get("status"):
                # mantém "" como Vazio
                pass
        self._popular_tabela()
        # após carregar tabela, atualiza lista lateral de SAs
        try:
            self._atualizar_lista_sas()
        except Exception:
            pass

    def _caminho_sa_pasta(self):
        """Retorna pasta Almox/DPH, tentando config e fallbacks locais."""
        candidatos = []
        try:
            import config
            base = config.obter_caminho_jsons()
            if base and os.path.isdir(base):
                candidatos.append(os.path.normpath(os.path.join(base, "Almox", "DPH")))
        except Exception:
            pass
        # fallbacks locais
        candidatos.extend([
            os.path.normpath(os.path.join(os.getcwd(), "Almox", "DPH")),
            os.path.normpath(r"C:\Users\ander\Documents\AntiGravity\Almoxarifado2\Almox\DPH"),
            os.path.normpath(r"C:\Users\ander\Documents\AntiGravity\AlmoxarifadoConf\Almox\DPH"),
            os.path.normpath(r"C:\Almox\DPH"),
        ])
        for p in candidatos:
            if os.path.isdir(p):
                return p
        # retorna primeiro candidato mesmo se não existir (para criar)
        return candidatos[0] if candidatos else ""

    def _caminho_itens_almoxarifado_json(self):
        import config
        base = config.obter_caminho_jsons()
        if not base:
            return ""
        return os.path.normpath(os.path.join(base, "Almox", "ItensAlmoxarifado", "ItensAlmoxarifado.json"))

    def _mapa_itens_almoxarifado(self):
        caminho = self._caminho_itens_almoxarifado_json()
        if not caminho or not os.path.isfile(caminho):
            return {}
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                dados = json.load(f)
        except Exception:
            return {}
        mapa = {}
        for d in dados:
            if not isinstance(d, dict):
                continue
            k = str(d.get("Kardex", "")).strip()
            if k:
                mapa[k] = d
                # também indexa sem espaços para busca tolerante
                mapa[k.lower()] = d
        return mapa

    def _enriquecer_itens_com_estoque(self, itens):
        mapa = self._mapa_itens_almoxarifado()
        if not mapa:
            return itens
        for it in itens:
            kardex = str(it.get("kardex", "")).strip()
            if not kardex:
                continue
            estoque = mapa.get(kardex) or mapa.get(kardex.lower())
            if not estoque:
                continue
            try:
                it["locacao_novo"] = str(estoque.get("Loc novo", "") or estoque.get("locacao_novo", "") or "").strip()
                it["estoque_novo"] = str(estoque.get("Qtde novo", "") or estoque.get("estoque_novo", "") or "").strip()
                it["locacao_retorno"] = str(estoque.get("Loc retorno", "") or estoque.get("locacao_retorno", "") or "").strip()
                it["estoque_retorno"] = str(estoque.get("Qtde retorno", "") or estoque.get("estoque_retorno", "") or "").strip()
            except Exception:
                continue
        return itens

    def _atualizar_estoque_almoxarifado(self, kardex, delta_n=0, delta_r=0):
        caminho = self._caminho_itens_almoxarifado_json()
        if not caminho or not os.path.isfile(caminho):
            return None, None
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                dados = json.load(f)
        except Exception:
            return None, None
        novo_n_str = None
        novo_r_str = None
        for item in dados:
            if not isinstance(item, dict):
                continue
            k = str(item.get("Kardex", "")).strip()
            if k != kardex and k.lower() != kardex.lower():
                continue
            if delta_n != 0:
                atual = self._parse_qtde(str(item.get("Qtde novo", "") or "0")) or 0
                novo_val = atual - delta_n
                if novo_val < 0:
                    novo_val = 0
                # preserva formato brasileiro com 2 casas
                novo_n_str = f"{novo_val:.2f}".replace(".", ",")
                item["Qtde novo"] = novo_n_str
            if delta_r != 0:
                atual = self._parse_qtde(str(item.get("Qtde retorno", "") or "0")) or 0
                novo_val = atual - delta_r
                if novo_val < 0:
                    novo_val = 0
                novo_r_str = f"{novo_val:.2f}".replace(".", ",")
                item["Qtde retorno"] = novo_r_str
            break
        if novo_n_str is not None or novo_r_str is not None:
            try:
                os.makedirs(os.path.dirname(caminho), exist_ok=True)
                with open(caminho, "w", encoding="utf-8") as f:
                    json.dump(dados, f, ensure_ascii=False, indent=2)
            except Exception:
                pass
        return novo_n_str, novo_r_str

    def _atualizar_lista_sas(self):
        if not hasattr(self, "lista_sas"):
            return
        self.lista_sas.blockSignals(True)
        self.lista_sas.clear()
        # lista apenas "Pendente" -> DPHPendente.json em Almox/DPH
        import config
        base = config.obter_caminho_jsons()
        pasta = self._caminho_sa_pasta()
        caminho = os.path.join(pasta, "DPHPendente.json") if pasta else ""
        # garante pasta existe para tooltip, mas não cria arquivo
        from PySide6.QtWidgets import QListWidgetItem
        item = QListWidgetItem("Pendente")
        item.setData(Qt.ItemDataRole.UserRole, caminho)
        item.setToolTip(caminho)
        self.lista_sas.addItem(item)
        self.lista_sas.blockSignals(False)

    def _recarregar_dados_sa_pasta(self):
        """Recarrega self.dados a partir de Almox/DPH/DPHPendente.json apenas."""
        pasta = self._caminho_sa_pasta()
        caminho = os.path.join(pasta, "DPHPendente.json") if pasta else ""
        if not caminho or not os.path.isfile(caminho):
            # nenhum arquivo pendente — limpa dados
            self.dados = []
            try:
                self._atualizar_lista_sas()
            except Exception:
                pass
            return
        agregados = []
        for caminho in [caminho]:
            try:
                with open(caminho, "r", encoding="utf-8") as f:
                    dados_raw = json.load(f)
            except Exception:
                continue
            header = {}
            dados_sa = []
            if isinstance(dados_raw, dict):
                header = dict(dados_raw)
                itens = dados_raw.get("itens")
                if itens is None:
                    itens = dados_raw.get("Itens")
                if itens is None:
                    itens = dados_raw.get("items")
                if isinstance(itens, list):
                    dados_sa = itens
                else:
                    dados_sa = []
            elif isinstance(dados_raw, list):
                dados_sa = dados_raw
                if dados_sa and isinstance(dados_sa[0], dict):
                    header = dict(dados_sa[0])
                    try:
                        first_dest = str(header.get("destino", "")).strip()
                        if first_dest and all(str(d.get("destino", "")).strip() == first_dest for d in dados_sa if isinstance(d, dict)):
                            header["destino"] = first_dest
                    except Exception:
                        pass
            else:
                continue
            # normaliza cada item como em _on_sa_selecionada
            for d in dados_sa:
                if not isinstance(d, dict):
                    continue
                if "descricao" in d and "observacoes" not in d:
                    novo = {}
                    novo["kardex"] = str(d.get("kardex", "")).strip()
                    novo["codigo"] = str(d.get("codigo", "")).strip()
                    novo["qtde"] = str(d.get("qtde", "")).strip()
                    novo["status"] = str(d.get("status", "")).strip()
                    novo["qtde_p"] = str(d.get("qtde_programada", "")).strip()
                    novo["qtde_n"] = str(d.get("qtde_entregue", "")).strip()
                    novo["qtde_r"] = ""
                    novo["numero_req"] = str(header.get("numero_req", "") or header.get("numero_sa", "") or d.get("numero_req", "")).strip()
                    novo["destino"] = str(header.get("destino", "") or d.get("destino", "")).strip()
                    novo["local_entrega"] = str(header.get("local_entrega", "") or header.get("entregar_para", "") or d.get("local_entrega", "")).strip()
                    novo["data_necessidade"] = str(header.get("data_necessidade", "") or header.get("data_entrega", "") or d.get("data_necessidade", "")).strip()
                    novo["observacoes"] = str(d.get("descricao", "")).strip()
                    novo["custo_total_estimado"] = str(d.get("custo_total", "") or d.get("custo_total_estimado", "")).strip()
                    novo["conta"] = str(header.get("conta_debito", "") or header.get("conta", "") or d.get("conta", "")).strip()
                    for ch in self.CHAVES:
                        novo.setdefault(ch, "")
                    novo.setdefault("solicitante", str(header.get("nome_emissor", "") or header.get("solicitante", "")).strip())
                    novo.setdefault("projeto_destino", str(header.get("projeto_debito", "") or header.get("projeto_destino", "")).strip())
                    agregados.append(novo)
                else:
                    for ch in self.CHAVES:
                        d.setdefault(ch, "")
                    d.setdefault("solicitante", "")
                    d.setdefault("projeto_destino", "")
                    if not str(d.get("numero_req", "")).strip() and header.get("numero_req"):
                        d["numero_req"] = str(header.get("numero_req", "")).strip()
                    if not str(d.get("destino", "")).strip() and header.get("destino"):
                        d["destino"] = str(header.get("destino", "")).strip()
                    if not str(d.get("local_entrega", "")).strip() and (header.get("local_entrega") or header.get("entregar_para")):
                        d["local_entrega"] = str(header.get("local_entrega", "") or header.get("entregar_para", "")).strip()
                    if not str(d.get("data_necessidade", "")).strip() and (header.get("data_necessidade") or header.get("data_entrega")):
                        d["data_necessidade"] = str(header.get("data_necessidade", "") or header.get("data_entrega", "")).strip()
                    if not str(d.get("conta", "")).strip() and (header.get("conta_debito") or header.get("conta")):
                        d["conta"] = str(header.get("conta_debito", "") or header.get("conta", "")).strip()
                    agregados.append(d)
        # enriquecer com dados de estoque por kardex
        try:
            agregados = self._enriquecer_itens_com_estoque(agregados)
        except Exception:
            pass
        self.dados = agregados
        try:
            self._atualizar_lista_sas()
        except Exception:
            pass

    def _on_sa_selecionada(self, item):
        if not item:
            return
        caminho = item.data(Qt.ItemDataRole.UserRole)
        if not caminho or not os.path.isfile(caminho):
            return
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                dados_raw = json.load(f)
        except Exception as e:
            self._mostrar_toast(f"Erro ao ler {os.path.basename(caminho)}: {e}", erro=True)
            return
        # atualiza header SA
        sa_nome = os.path.splitext(os.path.basename(caminho))[0]
        if hasattr(self, "label_sa_numero"):
            self.label_sa_numero.setText(f"SA{sa_nome}" if not sa_nome.upper().startswith("SA") else sa_nome)

        # ── Determina formato: dict com header+itens vs lista direta ──
        header = {}
        dados_sa = []
        if isinstance(dados_raw, dict):
            # Formato novo da Solicitação de SA: {nome_emissor, numero_req, numero_sa, projeto_debito, ... , itens: [...]}
            header = dict(dados_raw)
            itens = dados_raw.get("itens")
            if itens is None:
                itens = dados_raw.get("Itens")
            if itens is None:
                itens = dados_raw.get("items")
            if isinstance(itens, list):
                dados_sa = itens
            else:
                # dict sem lista de itens — trata dict como único header sem itens
                dados_sa = []
                # mantém header para preencher campos
            # guarda numero_sa do header se existir, mas label já usa nome do arquivo
        elif isinstance(dados_raw, list):
            dados_sa = dados_raw
            # header será derivado do primeiro item (comum em arquivos antigos)
            if dados_sa and isinstance(dados_sa[0], dict):
                header = dict(dados_sa[0])
                # tenta agregar valores comuns (destino, local_entrega, etc.) se todos iguais
                # se todos os itens têm mesmo destino, usa esse destino no header
                try:
                    first_dest = str(header.get("destino", "")).strip()
                    if first_dest and all(str(d.get("destino","")).strip() == first_dest for d in dados_sa if isinstance(d, dict)):
                        header["destino"] = first_dest
                except Exception:
                    pass
        else:
            dados_sa = []
            header = {}

        # ── Preenche campos do quadro superior com informações da SA ──
        try:
            # bloqueia sinais para não disparar validações durante preenchimento
            campos_header = [
                getattr(self, "campo_sa_solicitante", None),
                getattr(self, "campo_sa_telefone", None),
                getattr(self, "campo_sa_departamento", None),
                getattr(self, "campo_sa_planta", None),
                getattr(self, "campo_sa_projeto_debito", None),
                getattr(self, "campo_sa_conta_debito", None),
                getattr(self, "campo_sa_entregar_para", None),
                getattr(self, "campo_sa_entregue_para", None),
            ]
            for c in campos_header:
                if c is not None:
                    c.blockSignals(True)

            # Mapeamento flexível: aceita várias chaves possíveis (compatibilidade dict novo x lista antiga)
            def _get_header_val(*keys, default=""):
                for k in keys:
                    if k in header and str(header.get(k, "")).strip():
                        return str(header.get(k, "")).strip()
                    # tenta variação case-insensitive
                    for hk in list(header.keys()):
                        if hk.lower() == k.lower() and str(header.get(hk, "")).strip():
                            return str(header.get(hk, "")).strip()
                return default

            # Solicitante <- nome_emissor / solicitante
            if hasattr(self, "campo_sa_solicitante"):
                val = _get_header_val("nome_emissor", "solicitante", "Solicitante", "nome", "Nome")
                self.campo_sa_solicitante.setText(val)
            if hasattr(self, "campo_sa_telefone"):
                val = _get_header_val("telefone", "Telefone", "tel", "fone")
                self.campo_sa_telefone.setText(val)
            if hasattr(self, "campo_sa_departamento"):
                val = _get_header_val("departamento", "Departamento", "depto", "setor")
                self.campo_sa_departamento.setText(val)
            if hasattr(self, "campo_sa_planta"):
                val = _get_header_val("planta", "Planta")
                self.campo_sa_planta.setText(val)
            if hasattr(self, "campo_sa_projeto_debito"):
                val = _get_header_val("projeto_debito", "projeto_destino", "projeto", "Projeto", "destino_projeto")
                self.campo_sa_projeto_debito.setText(val)
            if hasattr(self, "campo_sa_conta_debito"):
                val = _get_header_val("conta_debito", "conta", "Conta", "conta_destino")
                self.campo_sa_conta_debito.setText(val)
            if hasattr(self, "campo_sa_entregar_para"):
                val = _get_header_val("entregar_para", "entregarPara", "local_entrega", "LocalEntrega", "destino", "Destino")
                # Fallback extra: se ainda vazio, tenta extrair dos itens (mais comum local_entrega/destino)
                if not val and dados_sa:
                    try:
                        # tenta local_entrega mais comum
                        from collections import Counter
                        cands = []
                        for d in dados_sa:
                            if isinstance(d, dict):
                                for k in ("entregar_para", "local_entrega", "destino"):
                                    v = str(d.get(k, "")).strip()
                                    if v:
                                        cands.append(v)
                                        break
                                # também tenta header alternativo dentro do item
                                if not cands or cands[-1] != str(d.get("local_entrega","")).strip():
                                    pass
                        if cands:
                            # pega mais comum
                            val = Counter(cands).most_common(1)[0][0]
                        else:
                            # fallback direto: primeiro item com local_entrega/destino
                            for d in dados_sa:
                                if isinstance(d, dict):
                                    for k in ("local_entrega", "destino", "entregar_para"):
                                        v = str(d.get(k, "")).strip()
                                        if v:
                                            val = v
                                            break
                                if val:
                                    break
                    except Exception:
                        pass
                self.campo_sa_entregar_para.setText(val)
            if hasattr(self, "campo_sa_entregue_para"):
                val = _get_header_val("entregue_para", "entreguePara", "EntreguePara")
                if not val and dados_sa:
                    try:
                        for d in dados_sa:
                            if isinstance(d, dict):
                                for k in ("entregue_para", "entreguePara"):
                                    v = str(d.get(k, "")).strip()
                                    if v:
                                        val = v
                                        break
                            if val:
                                break
                    except Exception:
                        pass
                self.campo_sa_entregue_para.setText(val)

            # Data de entrega / necessidade
            if hasattr(self, "campo_sa_data_entrega"):
                data_str = _get_header_val("data_necessidade", "data_entrega", "dataEntrega", "Data", "data")
                if data_str:
                    qdate = None
                    # tenta dd/MM/yyyy
                    try:
                        # QDate.fromString com formato
                        q = QDate.fromString(data_str.strip(), "dd/MM/yyyy")
                        if q.isValid():
                            qdate = q
                        else:
                            # tenta yyyy-MM-dd
                            q2 = QDate.fromString(data_str.strip(), "yyyy-MM-dd")
                            if q2.isValid():
                                qdate = q2
                            else:
                                # tenta dd-MM-yyyy
                                q3 = QDate.fromString(data_str.strip(), "dd-MM-yyyy")
                                if q3.isValid():
                                    qdate = q3
                                else:
                                    # fallback: tenta parse manual
                                    partes = re.split(r"[/\-]", data_str.strip())
                                    if len(partes) == 3:
                                        try:
                                            d, m, y = int(partes[0]), int(partes[1]), int(partes[2])
                                            # se ano com 2 dígitos ou formato invertido
                                            if y < 100:
                                                y += 2000
                                            # se dia > 31 talvez seja yyyy-MM-dd
                                            if d > 31:
                                                y, m, d = d, m, y
                                            qtmp = QDate(y, m, d)
                                            if qtmp.isValid():
                                                qdate = qtmp
                                        except Exception:
                                            pass
                    except Exception:
                        pass
                    if qdate and qdate.isValid():
                        self.campo_sa_data_entrega.setDate(qdate)
                    else:
                        # mantém data atual se não conseguiu parsear
                        pass
                else:
                    # se header sem data, tenta usar data do primeiro item
                    pass

            # Status — marca radio correspondente (se houver status no header ou itens)
            status_val = _get_header_val("status", "Status")
            if not status_val and dados_sa:
                # tenta extrair status mais comum entre itens
                try:
                    from collections import Counter
                    statuses = [str(d.get("status","")).strip() for d in dados_sa if isinstance(d, dict) and str(d.get("status","")).strip()]
                    if statuses:
                        status_val = Counter(statuses).most_common(1)[0][0]
                except Exception:
                    pass
            if status_val:
                # normaliza
                sv = status_val.strip()
                # mapeia para radios existentes
                radios_map = {
                    "cancelado": getattr(self, "radio_sa_cancelado", None),
                    "devolvido": getattr(self, "radio_sa_devolvido", None),
                    "pendente": getattr(self, "radio_sa_pendente", None),
                    "programado": getattr(self, "radio_sa_programado", None),
                    "todos": getattr(self, "radio_sa_todos", None),
                }
                key = sv.lower()
                # trata variações
                if "programado/entregue" in key or "programado/entregue" in key.replace(" ", ""):
                    key = "programado"
                # desmarca todos primeiro? QButtonGroup gerencia
                target = radios_map.get(key)
                if target is not None:
                    target.setChecked(True)
                elif sv.lower() == "todos":
                    if radios_map["todos"]:
                        radios_map["todos"].setChecked(True)
        except Exception:
            pass
        finally:
            try:
                for c in campos_header:
                    if c is not None:
                        c.blockSignals(False)
            except Exception:
                pass

        # ── Normaliza itens para a tabela ──
        # Para formato novo (dict com itens de SolicitacaoSaPage), mapeia campos para CHAVES da tabela
        # solicitacao itens: kardex, codigo, descricao, qtde, custo_unit, custo_total, status, qtde_programada, qtde_entregue
        # sasEmitidas CHAVES: qtde_n, qtde_r, qtde_p, kardex, codigo, qtde, numero_req, destino, local_entrega, data_necessidade, locacao_novo, estoque_novo, locacao_retorno, estoque_retorno, status, custo_total_estimado, observacoes, conta
        itens_normalizados = []
        for d in dados_sa:
            if not isinstance(d, dict):
                continue
            # se já está no formato sasEmitidas (tem kardex/codigo/qtde etc.), mantém
            # detecta formato novo pela presença de 'descricao' e ausência de 'observacoes'
            if "descricao" in d and "observacoes" not in d:
                # mapeia
                novo = {}
                novo["kardex"] = str(d.get("kardex", "")).strip()
                novo["codigo"] = str(d.get("codigo", "")).strip()
                novo["qtde"] = str(d.get("qtde", "")).strip()
                novo["status"] = str(d.get("status", "")).strip()
                # qtde programada/entregue -> mapeia para qtde_p / qtde_n? mantém vazio por padrão, usa programada/entregue se existir
                novo["qtde_p"] = str(d.get("qtde_programada", "")).strip()
                # qtde_n usa entregue? deixa separado
                novo["qtde_n"] = str(d.get("qtde_entregue", "")).strip()
                novo["qtde_r"] = ""
                novo["numero_req"] = str(header.get("numero_req", "") or header.get("numero_sa", "") or d.get("numero_req", "")).strip()
                novo["destino"] = str(header.get("destino", "") or d.get("destino", "")).strip()
                novo["local_entrega"] = str(header.get("local_entrega", "") or header.get("entregar_para", "") or d.get("local_entrega", "")).strip()
                novo["data_necessidade"] = str(header.get("data_necessidade", "") or header.get("data_entrega", "") or d.get("data_necessidade", "")).strip()
                novo["observacoes"] = str(d.get("descricao", "")).strip()
                # custo
                novo["custo_total_estimado"] = str(d.get("custo_total", "") or d.get("custo_total_estimado", "")).strip()
                novo["conta"] = str(header.get("conta_debito", "") or header.get("conta", "") or d.get("conta", "")).strip()
                # campos restantes vazios
                for ch in self.CHAVES:
                    novo.setdefault(ch, "")
                # garante solicitante/projeto_destino
                novo.setdefault("solicitante", str(header.get("nome_emissor", "") or header.get("solicitante", "")).strip())
                novo.setdefault("projeto_destino", str(header.get("projeto_debito", "") or header.get("projeto_destino", "")).strip())
                itens_normalizados.append(novo)
            else:
                # formato antigo/lista — garante chaves
                for ch in self.CHAVES:
                    d.setdefault(ch, "")
                d.setdefault("solicitante", "")
                d.setdefault("projeto_destino", "")
                # se item não tem numero_req mas header tem, propaga
                if not str(d.get("numero_req","")).strip() and header.get("numero_req"):
                    d["numero_req"] = str(header.get("numero_req","")).strip()
                if not str(d.get("destino","")).strip() and header.get("destino"):
                    d["destino"] = str(header.get("destino","")).strip()
                if not str(d.get("local_entrega","")).strip() and (header.get("local_entrega") or header.get("entregar_para")):
                    d["local_entrega"] = str(header.get("local_entrega","") or header.get("entregar_para","")).strip()
                if not str(d.get("data_necessidade","")).strip() and (header.get("data_necessidade") or header.get("data_entrega")):
                    d["data_necessidade"] = str(header.get("data_necessidade","") or header.get("data_entrega","")).strip()
                if not str(d.get("conta","")).strip() and (header.get("conta_debito") or header.get("conta")):
                    d["conta"] = str(header.get("conta_debito","") or header.get("conta","")).strip()
                itens_normalizados.append(d)

        # enriquecer com dados de ItensAlmoxarifado por kardex
        try:
            if itens_normalizados:
                itens_normalizados = self._enriquecer_itens_com_estoque(itens_normalizados)
            elif isinstance(dados_sa, list):
                # enriquece dados_sa diretamente
                for d in dados_sa:
                    if isinstance(d, dict):
                        for ch in self.CHAVES:
                            d.setdefault(ch, "")
                dados_sa = self._enriquecer_itens_com_estoque(dados_sa)
        except Exception:
            pass
        self.dados = itens_normalizados if itens_normalizados else dados_sa
        # garante que mesmo se dados_sa era lista antiga sem normalização, ainda está em self.dados
        if not itens_normalizados and isinstance(dados_sa, list):
            for d in self.dados:
                if isinstance(d, dict):
                    for ch in self.CHAVES:
                        d.setdefault(ch, "")
                    d.setdefault("solicitante", "")
                    d.setdefault("projeto_destino", "")
        self._popular_tabela()
        self._mostrar_toast(f"SA {sa_nome} carregada ({len(self.dados)} itens).", erro=False)

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

    def _aplicar_filtro(self):
        try:
            self._recarregar_dados_sa_pasta()
        except Exception:
            pass
        self._popular_tabela()

    def _limpar_filtros(self):
        for w in [self.filtro_dph, self.filtro_sa, self.filtro_kardex, self.filtro_conta]:
            w.blockSignals(True)
            w.clear()
            w.blockSignals(False)
        for w in [self.filtro_requisicao, self.filtro_destino]:
            w.blockSignals(True)
            w.clear()
            w.blockSignals(False)
        self.filtro_status.blockSignals(True)
        self.filtro_status.setCurrentIndex(0)
        self.filtro_status.blockSignals(False)
        for combo in [self.filtro_solicitante, self.filtro_projeto]:
            combo.blockSignals(True)
            combo.setCurrentIndex(0)
            if combo.lineEdit():
                combo.lineEdit().clear()
            combo.blockSignals(False)
        if hasattr(self, "campo_filtro_tabela"):
            self.campo_filtro_tabela.blockSignals(True)
            self.campo_filtro_tabela.clear()
            self.campo_filtro_tabela.blockSignals(False)
        self._popular_tabela()

    def _filtros_ativos(self):
        """Retorna dict com valores atuais dos 4 filtros visíveis + stubs."""
        def combo_valor(combo):
            if combo.isEditable() and combo.lineEdit():
                txt_edit = combo.lineEdit().text().strip()
                if txt_edit:
                    if txt_edit.lower() == "vazio":
                        return ""
                    return txt_edit
            data = combo.currentData()
            if data is not None:
                val = str(data).strip()
                if val.lower() == "vazio":
                    return ""
                return val
            txt = combo.currentText().strip()
            if txt.lower() == "vazio":
                return ""
            return txt
        return {
            "dph": self.filtro_dph.text().strip() if hasattr(self, "filtro_dph") else "",
            "sa": self.filtro_sa.text().strip(),
            "status": combo_valor(self.filtro_status),
            "solicitante": combo_valor(self.filtro_solicitante),
            "kardex": self.filtro_kardex.text().strip(),
            "requisicao": self.filtro_requisicao.text().strip(),
            "destino": self.filtro_destino.text().strip(),
            "conta": self.filtro_conta.text().strip(),
            "projeto": combo_valor(self.filtro_projeto),
            "filtro_tabela": self.campo_filtro_tabela.text().strip() if hasattr(self, "campo_filtro_tabela") else "",
        }

    def _item_pass_filtro(self, item, f):
        if f.get("dph"):
            texto_geral = " ".join(str(v) for v in item.values()).lower()
            if f["dph"].lower() not in str(item.get("numero_req", "")).lower() and f["dph"].lower() not in texto_geral:
                return False
        if f["sa"]:
            if f["sa"].lower() not in str(item.get("numero_req", "")).lower():
                if f["sa"].lower() not in str(item.get("conta", "")).lower():
                    return False
        if f["status"]:
            if f["status"] != "":
                if str(item.get("status", "")).strip() != f["status"]:
                    return False
        if f["solicitante"]:
            texto_geral = " ".join(str(v) for v in item.values()).lower()
            if f["solicitante"].lower() not in texto_geral:
                if f["solicitante"].lower() not in str(item.get("solicitante", "")).lower():
                    return False
        if f["kardex"]:
            if f["kardex"].lower() not in str(item.get("kardex", "")).lower():
                return False
        if f["requisicao"]:
            if f["requisicao"].lower() not in str(item.get("numero_req", "")).lower():
                return False
        if f["destino"]:
            if f["destino"].lower() not in str(item.get("destino", "")).lower():
                return False
        if f["conta"]:
            if f["conta"].lower() not in str(item.get("conta", "")).lower():
                return False
        if f["projeto"]:
            if "projeto_destino" in item and str(item.get("projeto_destino", "")).strip():
                if f["projeto"].lower() not in str(item.get("projeto_destino", "")).lower():
                    return False
            else:
                texto_geral = " ".join(str(v) for v in item.values()).lower()
                if f["projeto"].lower() not in texto_geral:
                    return False
        if f.get("filtro_tabela"):
            texto_geral = " ".join(str(v) for v in item.values()).lower()
            if f["filtro_tabela"].lower() not in texto_geral:
                return False
        return True

    def _popular_tabela(self):
        # preserva scroll/seleção
        v_scroll = self.tabela.verticalScrollBar().value()
        h_scroll = self.tabela.horizontalScrollBar().value()
        curr_row = self.tabela.currentRow()
        curr_col = self.tabela.currentColumn()

        self.tabela.blockSignals(True)
        self.tabela.setRowCount(0)
        filtros = self._filtros_ativos()
        exibidos = 0

        for idx, item in enumerate(self.dados):
            if not isinstance(item, dict):
                continue
            if not self._item_pass_filtro(item, filtros):
                continue
            row = self.tabela.rowCount()
            self.tabela.insertRow(row)
            for col, chave in enumerate(self.CHAVES):
                if chave == "imprimir":
                    cell = QTableWidgetItem()
                    cell.setFlags(cell.flags() | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
                    val = item.get(chave, True)
                    is_true = True
                    if isinstance(val, bool):
                        is_true = val
                    elif isinstance(val, str):
                        vs = val.lower().strip()
                        if vs in ("false", "0", "unchecked", "off"):
                            is_true = False
                        elif vs in ("",):
                            is_true = True
                        elif vs in ("true", "1", "checked", "on"):
                            is_true = True
                    elif val is None:
                        is_true = True
                    elif isinstance(val, int):
                        is_true = bool(val)
                    cell.setCheckState(Qt.CheckState.Checked if is_true else Qt.CheckState.Unchecked)
                    cell.setText("")
                else:
                    valor = str(item.get(chave, ""))
                    cell = QTableWidgetItem(valor)
                    if col == 5:
                        cell.setFlags(cell.flags() | Qt.ItemFlag.ItemIsEditable)
                    else:
                        cell.setFlags(cell.flags() & ~Qt.ItemFlag.ItemIsEditable)

                if chave == "imprimir":
                    cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                elif chave in ("sphm_status", "status"):
                    cor_bg = CORES_STATUS.get(valor, "")
                    if cor_bg:
                        cell.setData(Qt.BackgroundRole, QBrush(QColor(cor_bg)))
                        cor_txt = TEXTO_STATUS.get(valor, "#1e1b4b")
                        cell.setData(Qt.ForegroundRole, QBrush(QColor(cor_txt)))
                    cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                elif chave in ("qtde_dph", "qtde_n", "qtde_r", "qtde_p", "qtde", "estoque_novo", "estoque_retorno", "custo_total", "custo_total_estimado", "custo_unit"):
                    cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    if chave in ("custo_total", "custo_total_estimado", "custo_unit") and valor:
                        cell.setToolTip(f"R$ {valor}")
                elif chave in ("req", "req_neces", "data_necessidade"):
                    cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                elif chave in ("kardex", "codigo", "numero_req", "conta", "req", "req_neces"):
                    if valor:
                        cell.setToolTip(valor)
                    cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                self.tabela.setItem(row, col, cell)

            c0 = self.tabela.item(row, 0)
            if c0:
                c0.setData(Qt.ItemDataRole.UserRole, idx)
            exibidos += 1

        self._inserir_linha_vazia()
        self.tabela.blockSignals(False)
        self._atualizar_contador(exibidos)
        # restaura seleção/scroll se ainda válido
        if curr_row >= 0 and curr_row < self.tabela.rowCount() and curr_col >= 0:
            self.tabela.setCurrentCell(curr_row, curr_col)
        self.tabela.verticalScrollBar().setValue(v_scroll)
        self.tabela.horizontalScrollBar().setValue(h_scroll)

    def _inserir_linha_vazia(self):
        row = self.tabela.rowCount()
        self.tabela.insertRow(row)
        for col in range(len(self.COLUNAS)):
            chave = self.CHAVES[col] if col < len(self.CHAVES) else ""
            if chave == "imprimir":
                cell = QTableWidgetItem()
                cell.setFlags(cell.flags() | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
                cell.setCheckState(Qt.CheckState.Checked)
                cell.setText("")
                cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            else:
                cell = QTableWidgetItem("")
                if col == self.IDX_STATUS:
                    cell.setText("")
                    cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if col == 5:
                    cell.setFlags(cell.flags() | Qt.ItemFlag.ItemIsEditable)
                    cell.setToolTip("Digite Qtde Dph...")
                else:
                    # já cobre imprimir acima, demais não editáveis
                    if chave != "imprimir":
                        cell.setFlags(cell.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.tabela.setItem(row, col, cell)
        c0 = self.tabela.item(row, 0)
        if c0:
            c0.setData(Qt.ItemDataRole.UserRole, -1)

    def _atualizar_contador(self, exibidos=None):
        total = len(self.dados)
        if exibidos is None:
            exibidos = total
        # se algum filtro ativo mostra "x de y"
        filtros = self._filtros_ativos()
        algum_filtro = any(v for v in filtros.values())
        if algum_filtro and exibidos != total:
            self.label_contador.setText(f"{exibidos} de {total} solicitações (filtrado)")
        else:
            if total == 1:
                self.label_contador.setText("1 solicitação")
            else:
                self.label_contador.setText(f"{total} solicitações")

    # ── Ações ─────────────────────────────────────────────────────────────────
    def _adicionar_linha(self):
        last = self.tabela.rowCount() - 1
        self.tabela.scrollToBottom()
        # Foca em Qtde Dph (col 5) para DPH
        self.tabela.setCurrentCell(last, 5)
        self.tabela.setFocus()
        item = self.tabela.item(last, 0)
        if item and (item.flags() & Qt.ItemFlag.ItemIsEditable):
            self.tabela.editItem(item)

    def _on_cell_double_clicked(self, row, col):
        pass

    def _on_cell_clicked(self, row, col):
        # Qtde N/R/P (cols 0,1,2) editáveis já no clique simples
        if col in (0, 1, 2):
            if not self._edit_mode:
                return
            item = self.tabela.item(row, col)
            if item and (item.flags() & Qt.ItemFlag.ItemIsEditable):
                # evita conflito com seleção de linha
                self.tabela.setCurrentCell(row, col)
                self.tabela.editItem(item)

    def _duplicar_linha(self):
        selected = self.tabela.selectionModel().selectedRows()
        if not selected:
            return
        rows = sorted(set(i.row() for i in selected))
        novos = []
        for r in rows:
            idx = self._indice_por_linha(r)
            if idx is None:
                continue
            clone = dict(self.dados[idx])
            base_req = clone.get("numero_req", "").strip()
            if base_req:
                clone["numero_req"] = f"{base_req}-CÓPIA"
            clone["status"] = "Pendente"
            novos.append(clone)
        if not novos:
            return
        for n in novos:
            self.dados.append(n)
        self._salvar_json()
        self._popular_tabela()
        self._mostrar_toast(f"{len(novos)} linha(s) duplicada(s).", erro=False)

    def _remover_linha(self):
        selected = self.tabela.selectionModel().selectedRows()
        if not selected:
            return
        rows = sorted(set(i.row() for i in selected), reverse=True)
        rows_validas = []
        nomes = []
        for r in rows:
            c0 = self.tabela.item(r, 0)
            if c0 and c0.data(Qt.ItemDataRole.UserRole) == -1:
                continue
            idx = self._indice_por_linha(r)
            if idx is not None:
                rows_validas.append((r, idx))
                nome = (
                    self.dados[idx].get("numero_req", "").strip()
                    or self.dados[idx].get("kardex", "").strip()
                    or self.dados[idx].get("codigo", "").strip()
                    or f"linha {r+1}"
                )
                nomes.append(nome)
        if not rows_validas:
            return
        if len(nomes) == 1:
            txt = f"Excluir a solicitação <b>{nomes[0]}</b>?"
            detalhe = "Esta ação não pode ser desfeita."
        else:
            txt = f"Excluir {len(nomes)} solicitações?"
            detalhe = ", ".join(nomes[:5]) + ("..." if len(nomes) > 5 else "")
        confirm = QMessageBox(self)
        confirm.setWindowTitle("Confirmar exclusão")
        confirm.setIcon(QMessageBox.Icon.Warning)
        confirm.setText(txt)
        confirm.setInformativeText(detalhe)
        btn_sim = confirm.addButton("Excluir", QMessageBox.ButtonRole.DestructiveRole)
        confirm.addButton("Cancelar", QMessageBox.ButtonRole.RejectRole)
        confirm.setDefaultButton(btn_sim)
        confirm.exec()
        if confirm.clickedButton() != btn_sim:
            return
        indices = sorted([idx for _, idx in rows_validas], reverse=True)
        for idx in indices:
            if 0 <= idx < len(self.dados):
                self.dados.pop(idx)
        self._salvar_json()
        self._popular_tabela()
        self._mostrar_toast(f"{len(indices)} solicitação(ões) removida(s).", erro=False)

    def _indice_por_linha(self, row):
        c0 = self.tabela.item(row, 0)
        if c0 is None:
            return None
        val = c0.data(Qt.ItemDataRole.UserRole)
        if isinstance(val, int) and 0 <= val < len(self.dados):
            return val
        # fallback sem filtro: row == índice quando não há filtro ativo
        filtros = self._filtros_ativos()
        algum = any(v for v in filtros.values())
        if not algum and 0 <= row < len(self.dados):
            return row
        return None

    # ── Validação ─────────────────────────────────────────────────────────────
    def _validar_qtde(self, valor):
        v = valor.strip()
        if not v:
            return True, ""
        v_norm = v.replace(".", "").replace(",", ".") if "," in v else v
        try:
            f = float(v_norm)
            if f < 0:
                return False, "Qtde não pode ser negativa."
        except ValueError:
            return False, f"Qtde \"{valor}\" inválida."
        return True, ""

    def _validar_custo(self, valor):
        v = valor.strip()
        if not v:
            return True, ""
        v_limpo = re.sub(r"[R$\s]", "", v)
        v_norm = v_limpo.replace(".", "").replace(",", ".") if "," in v_limpo else v_limpo
        v_norm = v_norm.replace(" ", "")
        try:
            f = float(v_norm)
            if f < 0:
                return False, "Custo não pode ser negativo."
        except ValueError:
            return False, f"Custo \"{valor}\" inválido."
        return True, ""

    def _parse_qtde(self, valor):
        v = str(valor).strip()
        if not v:
            return None
        v_norm = v.replace(".", "").replace(",", ".") if "," in v else v
        try:
            return float(v_norm)
        except ValueError:
            return None

    def _item_modificado(self, item):
        row = item.row()
        col = item.column()
        chave_tmp = self.CHAVES[col] if 0 <= col < len(self.CHAVES) else ""
        if chave_tmp == "imprimir":
            # checkbox toggle
            idx_tmp = self._indice_por_linha(row)
            is_checked = item.checkState() == Qt.CheckState.Checked
            if idx_tmp is not None and 0 <= idx_tmp < len(self.dados):
                self.dados[idx_tmp][chave_tmp] = is_checked
                self._salvar_json()
            return
        # Apenas Qtde Dph pode ser alterada (col 5)
        if col not in (5, 12):
            # reverte qualquer tentativa de edição em coluna não editável
            self.tabela.blockSignals(True)
            idx_tmp = self._indice_por_linha(row)
            if idx_tmp is not None and 0 <= idx_tmp < len(self.dados):
                item.setText(str(self.dados[idx_tmp].get(self.CHAVES[col], "")))
            else:
                # linha vazia não editável
                if item.text().strip():
                    item.setText("")
            self.tabela.blockSignals(False)
            return
        chave = self.CHAVES[col]

        c0 = self.tabela.item(row, 0)
        is_linha_vazia = c0 and c0.data(Qt.ItemDataRole.UserRole) == -1
        if not is_linha_vazia and row == len(self.dados):
            # sem filtro, última linha é vazia
            filtros = self._filtros_ativos()
            if not any(v for v in filtros.values()) and row == len(self.dados):
                is_linha_vazia = True
            elif any(v for v in filtros.values()):
                # com filtro, a linha vazia ainda é a última mas não corresponde a índice real
                # verifica se UserRole == -1
                is_linha_vazia = c0 and c0.data(Qt.ItemDataRole.UserRole) == -1

        if is_linha_vazia:
            # Apenas Qtde N/R/P são editáveis — não permite criar nova linha pela tabela
            # Novas SAs devem ser criadas em 'Solicitação de SA'
            attempted = item.text().strip() if hasattr(item, "text") else ""
            self.tabela.blockSignals(True)
            item.setText("")
            # garante que outras células N/R/P Vazias também fiquem limpas
            for c in (0, 1, 2):
                if c == col:
                    continue
                cel = self.tabela.item(row, c)
                if cel and not str(cel.text()).strip():
                    continue
            self.tabela.blockSignals(False)
            if attempted:
                self._mostrar_toast("Novas solicitações devem ser criadas em 'Solicitação de SA'.", erro=True)
            return

        idx = self._indice_por_linha(row)
        if idx is None or not (0 <= idx < len(self.dados)):
            return

        novo_valor = item.text().strip()
        if chave in ("kardex", "codigo", "conta"):
            novo_valor = novo_valor.upper()
        elif chave in ("qtde_n", "qtde_r", "qtde_p", "qtde", "estoque_novo", "estoque_retorno"):
            ok, msg = self._validar_qtde(novo_valor)
            if not ok:
                self.tabela.blockSignals(True)
                item.setText(str(self.dados[idx].get(chave, "")))
                self.tabela.blockSignals(False)
                self._mostrar_toast(msg, erro=True)
                return
        elif chave == "custo_total_estimado":
            ok, msg = self._validar_custo(novo_valor)
            if not ok:
                self.tabela.blockSignals(True)
                item.setText(str(self.dados[idx].get(chave, "")))
                self.tabela.blockSignals(False)
                self._mostrar_toast(msg, erro=True)
                return
            novo_valor = re.sub(r"^\s*R\$\s*", "", novo_valor)
        elif chave == "status":
            if novo_valor not in STATUS_OPCOES and novo_valor not in STATUS_FILTRO_LABELS:
                # permite vazio
                if novo_valor == "Vazio":
                    novo_valor = ""
                else:
                    # mantém valor mas normaliza: se digitado "programado/entregue" com barra
                    lower = novo_valor.lower()
                    mapping = {s.lower(): s for s in STATUS_OPCOES}
                    novo_valor = mapping.get(lower, "")

        # Regra 1: Qtde N/R/P não pode ser 0
        if chave in ("qtde_n", "qtde_r", "qtde_p"):
            p = self._parse_qtde(novo_valor)
            if p is not None and p == 0:
                self.tabela.blockSignals(True)
                item.setText(str(self.dados[idx].get(chave, "")))
                self.tabela.blockSignals(False)
                self._mostrar_toast("Qtde N/R/P não pode ser 0.", erro=True)
                return

        # Regra estoque: N <= estoque_novo, R <= estoque_retorno (P sem regra) — considera delta (estoque atual + qtde antiga)
        if chave == "qtde_n":
            estoque_str = str(self.dados[idx].get("estoque_novo", "")).strip()
            if estoque_str:
                estoque_val = self._parse_qtde(estoque_str)
                q_val = self._parse_qtde(novo_valor) or 0 if novo_valor.strip() else 0
                old_q = self._parse_qtde(str(self.dados[idx].get(chave, "") or "")) or 0
                if estoque_val is not None and q_val is not None:
                    disponivel = estoque_val + old_q
                    # se novo vazio, q_val=0 passa; se tem valor, compara com disponivel
                    if novo_valor.strip() and q_val > disponivel + 1e-9:
                        self.tabela.blockSignals(True)
                        item.setText(str(self.dados[idx].get(chave, "")))
                        self.tabela.blockSignals(False)
                        self._mostrar_toast("Quantidade inserida é maior do que existe em estoque novo", erro=True)
                        return
        elif chave == "qtde_r":
            estoque_str = str(self.dados[idx].get("estoque_retorno", "")).strip()
            if estoque_str:
                estoque_val = self._parse_qtde(estoque_str)
                q_val = self._parse_qtde(novo_valor) or 0 if novo_valor.strip() else 0
                old_q = self._parse_qtde(str(self.dados[idx].get(chave, "") or "")) or 0
                if estoque_val is not None and q_val is not None:
                    disponivel = estoque_val + old_q
                    if novo_valor.strip() and q_val > disponivel + 1e-9:
                        self.tabela.blockSignals(True)
                        item.setText(str(self.dados[idx].get(chave, "")))
                        self.tabela.blockSignals(False)
                        self._mostrar_toast("Quantidade inserida é maior do que existe em estoque de retorno", erro=True)
                        return

        # Regra 2 (soma N+R+P == Qtde) não é validada aqui para permitir
        # preenchimento parcial. Será validada ao sair da linha
        # em _ao_mudar_celula / _validar_soma_linha.
        # Ex: Qtde=5, usuário digita N=3 e depois R=2 sem erro intermediário.

        if self.dados[idx].get(chave, "") == novo_valor:
            return

        # calcula delta para desconto instantâneo no estoque
        old_val_str = str(self.dados[idx].get(chave, "") or "")
        old_q = self._parse_qtde(old_val_str) or 0
        new_q = self._parse_qtde(novo_valor) or 0 if novo_valor.strip() else 0
        delta = new_q - old_q

        self.dados[idx][chave] = novo_valor
        # guarda filtros extras se existirem
        self._salvar_json()
        # desconto instantâneo no ItensAlmoxarifado.json e atualização da linha
        if chave in ("qtde_n", "qtde_r") and delta != 0:
            kardex = str(self.dados[idx].get("kardex", "")).strip()
            if kardex:
                try:
                    if chave == "qtde_n":
                        novo_n, _ = self._atualizar_estoque_almoxarifado(kardex, delta_n=delta)
                        if novo_n is not None:
                            self.dados[idx]["estoque_novo"] = novo_n
                            self.tabela.blockSignals(True)
                            cell = self.tabela.item(row, 11)
                            if cell:
                                cell.setText(novo_n)
                            self.tabela.blockSignals(False)
                    else:
                        _, novo_r = self._atualizar_estoque_almoxarifado(kardex, delta_r=delta)
                        if novo_r is not None:
                            self.dados[idx]["estoque_retorno"] = novo_r
                            self.tabela.blockSignals(True)
                            cell = self.tabela.item(row, 13)
                            if cell:
                                cell.setText(novo_r)
                            self.tabela.blockSignals(False)
                except Exception:
                    pass
        if chave == "status":
            self._popular_tabela()
        else:
            if chave in ("kardex", "codigo", "numero_req", "conta"):
                item.setToolTip(novo_valor)
            if chave == "custo_total_estimado" and novo_valor:
                item.setToolTip(f"R$ {novo_valor}")

    # ── Validação diferida da soma N+R+P (Regra 4) ────────────────────────
    def _ao_mudar_celula(self, cur_row, cur_col, prev_row, prev_col):
        # só valida quando troca de LINHA (permite navegar entre N/R/P/Qtde na mesma linha)
        if prev_row < 0 or cur_row == prev_row:
            return
        # valida a linha que o usuário acabou de SAIR
        self._validar_soma_linha(prev_row)

    def _validar_soma_linha(self, row):
        """Valida se N+R+P == Qtde para o idx correspondente à linha. Se erro, limpa N/R/P. Retorna True se ok."""
        idx = self._indice_por_linha(row)
        # linha vazia (UserRole -1) ainda não tem dados - tenta validar pelo conteúdo da tabela
        if idx is None or idx == -1:
            # tenta ler diretamente da tabela (caso ainda não persistido)
            if 0 <= row < self.tabela.rowCount():
                vals = {}
                for k, col in [("qtde_n", 0), ("qtde_r", 1), ("qtde_p", 2), ("qtde", 5)]:
                    it = self.tabela.item(row, col)
                    vals[k] = it.text().strip() if it else ""
                if not vals["qtde"] or not any(vals[c] for c in ("qtde_n", "qtde_r", "qtde_p")):
                    return True
                parsed_qtde = self._parse_qtde(vals["qtde"])
                parsed_n = self._parse_qtde(vals["qtde_n"]) or 0
                parsed_r = self._parse_qtde(vals["qtde_r"]) or 0
                parsed_p = self._parse_qtde(vals["qtde_p"]) or 0
                if parsed_qtde is not None:
                    soma = parsed_n + parsed_r + parsed_p
                    if abs(soma - parsed_qtde) > 1e-6:
                        self._mostrar_toast(
                            f"Soma N({vals['qtde_n'] or 0})+R({vals['qtde_r'] or 0})+P({vals['qtde_p'] or 0})={soma:g} ≠ Qtde({vals['qtde']}) — campos N/R/P limpos.",
                            erro=True,
                        )
                        self.tabela.blockSignals(True)
                        for col in (0, 1, 2):
                            it = self.tabela.item(row, col)
                            if it:
                                it.setText("")
                        self.tabela.blockSignals(False)
                        return False
            return True

        if not (0 <= idx < len(self.dados)):
            return True
        vals = {k: str(self.dados[idx].get(k, "")).strip() for k in ("qtde_n", "qtde_r", "qtde_p", "qtde")}
        # só valida se Qtde e ao menos um de N/R/P preenchido
        if not vals["qtde"] or not any(vals[c] for c in ("qtde_n", "qtde_r", "qtde_p")):
            return True
        parsed_qtde = self._parse_qtde(vals["qtde"])
        parsed_n = self._parse_qtde(vals["qtde_n"]) or 0
        parsed_r = self._parse_qtde(vals["qtde_r"]) or 0
        parsed_p = self._parse_qtde(vals["qtde_p"]) or 0
        if parsed_qtde is not None:
            soma = parsed_n + parsed_r + parsed_p
            if abs(soma - parsed_qtde) > 1e-6:
                self._mostrar_toast(
                    f"Soma N({vals['qtde_n'] or 0})+R({vals['qtde_r'] or 0})+P({vals['qtde_p'] or 0})={soma:g} ≠ Qtde({vals['qtde']}) — campos N/R/P limpos.",
                    erro=True,
                )
                # antes de apagar, devolve ao ItensAlmoxarifado o que foi descontado instantaneamente
                try:
                    kardex = str(self.dados[idx].get("kardex", "")).strip()
                    if kardex:
                        if parsed_n:
                            novo_n, _ = self._atualizar_estoque_almoxarifado(kardex, delta_n=-parsed_n)
                            if novo_n is not None:
                                self.dados[idx]["estoque_novo"] = novo_n
                            else:
                                cur = self._parse_qtde(str(self.dados[idx].get("estoque_novo", "") or "0")) or 0
                                self.dados[idx]["estoque_novo"] = f"{cur + parsed_n:.2f}".replace(".", ",")
                        if parsed_r:
                            _, novo_r = self._atualizar_estoque_almoxarifado(kardex, delta_r=-parsed_r)
                            if novo_r is not None:
                                self.dados[idx]["estoque_retorno"] = novo_r
                            else:
                                cur = self._parse_qtde(str(self.dados[idx].get("estoque_retorno", "") or "0")) or 0
                                self.dados[idx]["estoque_retorno"] = f"{cur + parsed_r:.2f}".replace(".", ",")
                except Exception:
                    pass
                # limpa modelo e view (após restaurar estoque)
                self.dados[idx]["qtde_n"] = ""
                self.dados[idx]["qtde_r"] = ""
                self.dados[idx]["qtde_p"] = ""
                self._salvar_json()
                self.tabela.blockSignals(True)
                for col in (0, 1, 2):
                    it = self.tabela.item(row, col)
                    if it:
                        it.setText("")
                # atualiza células de estoque na linha para refletir estorno
                try:
                    if parsed_n:
                        cell_n = self.tabela.item(row, 11)
                        if cell_n:
                            cell_n.setText(str(self.dados[idx].get("estoque_novo", "")))
                    if parsed_r:
                        cell_r = self.tabela.item(row, 13)
                        if cell_r:
                            cell_r.setText(str(self.dados[idx].get("estoque_retorno", "")))
                except Exception:
                    pass
                self.tabela.blockSignals(False)
                return False
        return True

    # ── Context menu ──────────────────────────────────────────────────────────
    def _context_menu(self, pos):
        item = self.tabela.itemAt(pos)
        if not item:
            return
        row = item.row()
        idx = self._indice_por_linha(row)
        if idx is None:
            return
        menu = QMenu(self)
        # Apenas Qtde N/R/P são editáveis — menu de status removido
        act_duplicar = menu.addAction(qtawesome.icon('fa6s.copy', color='#64748b'), "Duplicar")
        act_duplicar.triggered.connect(self._duplicar_linha)
        act_excluir = menu.addAction(qtawesome.icon('fa6s.trash', color='#ef4444'), "Excluir")
        act_excluir.triggered.connect(self._remover_linha)
        menu.exec(QCursor.pos())

    def _alterar_status(self, idx, novo_status):
        if not (0 <= idx < len(self.dados)):
            return
        self.dados[idx]["status"] = novo_status
        self._salvar_json()
        self._popular_tabela()
        ident = self.dados[idx].get("numero_req") or self.dados[idx].get("kardex") or ""
        label = novo_status if novo_status else "Vazio"
        self._mostrar_toast(f"{ident} → {label}", erro=False)

    def _imprimir_sa(self):
        sa = self.label_sa_numero.text().strip() if hasattr(self, "label_sa_numero") else "SA"
        solicitante = self.campo_sa_solicitante.text().strip() if hasattr(self, "campo_sa_solicitante") else ""
        # coleta dados do quadro para impressão simples
        info = f"SA: {sa}\nSolicitante: {solicitante}\nTelefone: {self.campo_sa_telefone.text().strip()}\nDepartamento: {self.campo_sa_departamento.text().strip()}\nPlanta: {self.campo_sa_planta.text().strip()}\nProjeto débito: {self.campo_sa_projeto_debito.text().strip()}\nConta débito: {self.campo_sa_conta_debito.text().strip()}\nEntregar para: {self.campo_sa_entregar_para.text().strip()}\nEntregue para: {self.campo_sa_entregue_para.text().strip()}\nData entrega: {self.campo_sa_data_entrega.date().toString('dd/MM/yyyy')}"
        # por enquanto apenas toast + clipboard; impressão real pode ser integrada depois
        QApplication.clipboard().setText(info)
        self._mostrar_toast(f"{sa} copiado para impressão (clipboard).", erro=False)

    def _devolver_sa(self):
        sa = self.label_sa_numero.text().strip() if hasattr(self, "label_sa_numero") else "SA"
        resp = QMessageBox.question(self, "Devolver SA", f"Deseja devolver a {sa}?\nStatus será alterado para 'Devolvido'.", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if resp != QMessageBox.StandardButton.Yes:
            return
        # marca radio Devolvido
        if hasattr(self, "radio_sa_devolvido"):
            self.radio_sa_devolvido.setChecked(True)
        # se houver linha selecionada, atualiza status na tabela
        sel = self.tabela.selectionModel().selectedRows()
        if sel:
            for idx_row in sel:
                idx = self._indice_por_linha(idx_row.row())
                if idx is not None:
                    self.dados[idx]["status"] = "Devolvido"
            self._salvar_json()
            self._popular_tabela()
        self._mostrar_toast(f"{sa} devolvida.", erro=False)

    # ── Busca / utilidades ────────────────────────────────────────────────────
    def _buscar_item(self):
        texto, ok = QInputDialog.getText(self, "Pesquisar", "Digite o texto para buscar:")
        if not ok or not texto.strip():
            return
        busca = texto.strip().lower()
        for row in range(self.tabela.rowCount()):
            for col in range(self.tabela.columnCount()):
                it = self.tabela.item(row, col)
                if it and busca in it.text().lower():
                    self.tabela.selectRow(row)
                    self.tabela.scrollToItem(it)
                    return
        self._mostrar_toast("Texto não encontrado.", erro=True)

    def _copiar_selecao(self):
        item = self.tabela.currentItem()
        if item:
            QApplication.clipboard().setText(item.text())
        else:
            row = self.tabela.currentRow()
            col = self.tabela.currentColumn()
            if row >= 0 and col >= 0:
                cell = self.tabela.item(row, col)
                if cell:
                    QApplication.clipboard().setText(cell.text())

    def _mostrar_toast(self, texto, erro=False):
        msg = QLabel(texto, self)
        bg = "#fee2e2" if erro else "#dcfce7"
        fg = "#991b1b" if erro else "#166534"
        border = "#fecaca" if erro else "#bbf7d0"
        msg.setStyleSheet(f"background-color: {bg}; color: {fg}; border: 1px solid {border}; padding: 8px 16px; border-radius: 8px; font-size: 12px;")
        msg.setWordWrap(True)
        msg.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint)
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg.adjustSize()
        parent_rect = self.tabela.geometry() if hasattr(self, 'tabela') else self.rect()
        global_pos = self.mapToGlobal(parent_rect.center())
        msg.move(global_pos.x() - msg.width() // 2, global_pos.y() - msg.height() // 2)
        msg.show()
        QTimer.singleShot(2200 if not erro else 3000, msg.close)
