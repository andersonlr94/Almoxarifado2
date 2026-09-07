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
    COLS_NUMERICAS = {0, 1, 2, 5, 11, 13, 15}
    COL_STATUS = 14

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
        if index.column() == self.COL_STATUS:
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


class SolicitacoesSaPage(QWidget):
    COLUNAS = [
        "Qtde\nN",
        "Qtde\nR",
        "Qtde\nP",
        "Kardex",
        "Código",
        "Qtde",
        "Nº Req",
        "Destino",
        "Local entrega",
        "Data\nnecessidade",
        "Locação\nNovo",
        "Estoque\nnovo",
        "Locação\nretorno",
        "Estoque\nretorno",
        "Status",
        "Custo total\nestimado",
        "Observações",
        "Conta",
    ]
    CHAVES = [
        "qtde_n",
        "qtde_r",
        "qtde_p",
        "kardex",
        "codigo",
        "qtde",
        "numero_req",
        "destino",
        "local_entrega",
        "data_necessidade",
        "locacao_novo",
        "estoque_novo",
        "locacao_retorno",
        "estoque_retorno",
        "status",
        "custo_total_estimado",
        "observacoes",
        "conta",
    ]

    IDX_STATUS = 14
    IDX_KARDEX = 3
    IDX_CODIGO = 4
    IDX_NUM_REQ = 6

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

        # Header
        header_layout = QHBoxLayout()
        header_texts = QVBoxLayout()
        header_texts.setSpacing(4)
        titulo = QLabel("Solicitações SA")
        titulo.setObjectName("pageTitle")
        header_texts.addWidget(titulo)
        subtitulo = QLabel("Filtre por SA, status, solicitante, Kardex, requisição, destino, conta e projeto")
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

        # 1) Nº de SA
        self.filtro_sa = QLineEdit()
        self.filtro_sa.setPlaceholderText("Ex: SA123...")
        self.filtro_sa.returnPressed.connect(self._aplicar_filtro)
        add_field_h("Nº de SA", self.filtro_sa)

        # 2) Status
        self.filtro_status = QComboBox()
        for label, valor in zip(STATUS_FILTRO_LABELS, STATUS_OPCOES):
            self.filtro_status.addItem(label, valor)
        self.filtro_status.setCurrentIndex(0)
        add_field_h("Status", self.filtro_status)

        # 3) Solicitante
        self.filtro_solicitante = QComboBox()
        self.filtro_solicitante.setEditable(True)
        self.filtro_solicitante.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.filtro_solicitante.addItem("Vazio", "")
        self.filtro_solicitante.setCurrentIndex(0)
        self.filtro_solicitante.setPlaceholderText("Selecione...")
        if self.filtro_solicitante.lineEdit():
            self.filtro_solicitante.lineEdit().setPlaceholderText("Selecione...")
        add_field_h("Solicitante", self.filtro_solicitante)

        # 4) Kardex
        self.filtro_kardex = QLineEdit()
        self.filtro_kardex.setPlaceholderText("Kardex...")
        self.filtro_kardex.returnPressed.connect(self._aplicar_filtro)
        add_field_h("Kardex", self.filtro_kardex)

        # 5) Requisição
        self.filtro_requisicao = QLineEdit()
        self.filtro_requisicao.setPlaceholderText("Nº Req...")
        self.filtro_requisicao.returnPressed.connect(self._aplicar_filtro)
        add_field_h("Requisição", self.filtro_requisicao)

        # 6) Destino
        self.filtro_destino = QLineEdit()
        self.filtro_destino.setPlaceholderText("Destino...")
        self.filtro_destino.returnPressed.connect(self._aplicar_filtro)
        add_field_h("Destino", self.filtro_destino)

        # 7) Conta
        self.filtro_conta = QLineEdit()
        self.filtro_conta.setPlaceholderText("Conta...")
        self.filtro_conta.returnPressed.connect(self._aplicar_filtro)
        add_field_h("Conta", self.filtro_conta)

        # 8) Projeto de destino
        self.filtro_projeto = QComboBox()
        self.filtro_projeto.setEditable(True)
        self.filtro_projeto.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.filtro_projeto.addItem("Vazio", "")
        self.filtro_projeto.setCurrentIndex(0)
        self.filtro_projeto.setPlaceholderText("Selecione...")
        if self.filtro_projeto.lineEdit():
            self.filtro_projeto.lineEdit().setPlaceholderText("Selecione...")
        add_field_h("Projeto de destino", self.filtro_projeto)

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

        # Linha 1: SA em quadro + 6 campos + quadro interno à direita com botões
        linha_sa = QHBoxLayout()
        linha_sa.setSpacing(12)
        # quadro para o número da SA (mesmo estilo dos botões)
        self.quadro_sa_numero = QFrame()
        self.quadro_sa_numero.setObjectName("quadroSaNumero")
        self.quadro_sa_numero.setFrameShape(QFrame.Shape.StyledPanel)
        self.quadro_sa_numero.setStyleSheet("""
            QFrame#quadroSaNumero {
                background-color: #f8fafc;
                border: 1px solid #e2e8f0;
                border-radius: 10px;
            }
        """)
        self.quadro_sa_numero.setFixedWidth(110)
        self.quadro_sa_numero.setFixedHeight(62)
        lay_sa_num = QVBoxLayout(self.quadro_sa_numero)
        lay_sa_num.setContentsMargins(6, 6, 6, 6)
        lay_sa_num.setSpacing(0)
        lay_sa_num.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_sa_numero = QLabel("SA99102")
        self.label_sa_numero.setObjectName("labelSA")
        self.label_sa_numero.setStyleSheet("color:#1e293b; font-size:17px; font-weight:800; letter-spacing:0.5px; background:transparent; border:none;")
        self.label_sa_numero.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay_sa_num.addWidget(self.label_sa_numero)
        linha_sa.addWidget(self.quadro_sa_numero)

        # helper para campo com label dentro do quadro — label e campo próximos
        def criar_campo_quadro(placeholder, label_text):
            w = QWidget()
            w.setMaximumWidth(135)
            w.setMinimumWidth(105)
            v = QVBoxLayout(w)
            v.setContentsMargins(0, 0, 0, 0)
            v.setSpacing(1)
            lbl = QLabel(label_text)
            lbl.setStyleSheet("color:#64748b; font-size:9px; font-weight:600; padding:0px; margin:0px;")
            lbl.setMaximumWidth(135)
            lbl.setFixedHeight(12)
            v.addWidget(lbl)
            edit = QLineEdit()
            edit.setPlaceholderText(placeholder)
            edit.setFixedHeight(26)
            edit.setMaximumWidth(135)
            edit.setMinimumWidth(105)
            edit.setStyleSheet("background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:2px 6px; font-size:11px; margin:0px;")
            v.addWidget(edit)
            return w, edit

        # todos em UMA ÚNICA LINHA (6 campos lado a lado) — agora DENTRO DE QUADRO central
        self.quadro_sa_campos = QFrame()
        self.quadro_sa_campos.setObjectName("quadroSaCampos")
        self.quadro_sa_campos.setFrameShape(QFrame.Shape.StyledPanel)
        self.quadro_sa_campos.setStyleSheet("""
            QFrame#quadroSaCampos {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 10px;
            }
        """)
        # quadro central com 2 linhas: linha1 (6 campos) + linha2 (Entregar/Entregue/Data)
        quadro_campos_v = QVBoxLayout(self.quadro_sa_campos)
        quadro_campos_v.setSpacing(6)
        quadro_campos_v.setContentsMargins(8, 8, 8, 8)

        grid_sa = QHBoxLayout()
        grid_sa.setSpacing(8)
        grid_sa.setContentsMargins(0, 0, 0, 0)

        w_solic, self.campo_sa_solicitante = criar_campo_quadro("Nome...", "Solicitante")
        w_tel, self.campo_sa_telefone = criar_campo_quadro("(00) 0000-0000", "Telefone")
        w_dep, self.campo_sa_departamento = criar_campo_quadro("Depto...", "Departamento")
        w_planta, self.campo_sa_planta = criar_campo_quadro("Planta...", "Planta")
        w_proj, self.campo_sa_projeto_debito = criar_campo_quadro("Projeto...", "Projeto débito")
        w_conta, self.campo_sa_conta_debito = criar_campo_quadro("Conta...", "Conta débito")

        for w in [w_solic, w_tel, w_dep, w_planta, w_proj, w_conta]:
            grid_sa.addWidget(w)
        grid_sa.addStretch()
        quadro_campos_v.addLayout(grid_sa)

        # segunda linha DENTRO do quadro solicitante: Entregar para / Entregue para / Data
        def campo_entrega_compacto(label_text, placeholder):
            w = QWidget()
            w.setMaximumWidth(135)
            w.setMinimumWidth(105)
            v = QVBoxLayout(w)
            v.setContentsMargins(0, 0, 0, 0)
            v.setSpacing(1)
            lbl = QLabel(label_text)
            lbl.setStyleSheet("color:#64748b; font-size:9px; font-weight:600; padding:0px; margin:0px;")
            lbl.setMaximumWidth(135)
            lbl.setFixedHeight(12)
            v.addWidget(lbl)
            edit = QLineEdit()
            edit.setPlaceholderText(placeholder)
            edit.setFixedHeight(26)
            edit.setMaximumWidth(135)
            edit.setMinimumWidth(105)
            edit.setStyleSheet("background:#ffffff; border:1px solid #e2e8f0; border-radius:8px; padding:2px 6px; font-size:11px; margin:0px;")
            v.addWidget(edit)
            return w, edit

        linha_sa_segunda = QHBoxLayout()
        linha_sa_segunda.setSpacing(8)
        linha_sa_segunda.setContentsMargins(0, 0, 0, 0)
        w_entregar, self.campo_sa_entregar_para = campo_entrega_compacto("Entregar para", "Nome / local...")
        w_entregue, self.campo_sa_entregue_para = campo_entrega_compacto("Entregue para", "Nome / local...")
        linha_sa_segunda.addWidget(w_entregar)
        linha_sa_segunda.addWidget(w_entregue)

        w_data = QWidget()
        w_data.setMaximumWidth(135)
        w_data.setMinimumWidth(110)
        v_data = QVBoxLayout(w_data)
        v_data.setContentsMargins(0, 0, 0, 0)
        v_data.setSpacing(1)
        lbl_data = QLabel("Data de entrega")
        lbl_data.setStyleSheet("color:#64748b; font-size:9px; font-weight:600; padding:0px; margin:0px;")
        lbl_data.setMaximumWidth(135)
        lbl_data.setFixedHeight(12)
        v_data.addWidget(lbl_data)
        self.campo_sa_data_entrega = QDateEdit()
        self.campo_sa_data_entrega.setCalendarPopup(True)
        self.campo_sa_data_entrega.setDisplayFormat("dd/MM/yyyy")
        self.campo_sa_data_entrega.setDate(QDate.currentDate())
        self.campo_sa_data_entrega.setFixedHeight(26)
        self.campo_sa_data_entrega.setMaximumWidth(135)
        self.campo_sa_data_entrega.setMinimumWidth(110)
        self.campo_sa_data_entrega.setStyleSheet("background:#ffffff; border:1px solid #e2e8f0; border-radius:8px; padding:2px 6px; font-size:11px; margin:0px;")
        v_data.addWidget(self.campo_sa_data_entrega)
        linha_sa_segunda.addWidget(w_data)
        linha_sa_segunda.addStretch()
        quadro_campos_v.addLayout(linha_sa_segunda)

        linha_sa.addWidget(self.quadro_sa_campos, 1)

        # quadro interno à direita (dentro do quadro principal) com 2 botões
        self.quadro_sa_botoes = QFrame()
        self.quadro_sa_botoes.setObjectName("quadroSaBotoes")
        self.quadro_sa_botoes.setFrameShape(QFrame.Shape.StyledPanel)
        self.quadro_sa_botoes.setStyleSheet("""
            QFrame#quadroSaBotoes {
                background-color: #f8fafc;
                border: 1px solid #e2e8f0;
                border-radius: 10px;
            }
        """)
        self.quadro_sa_botoes.setFixedWidth(150)
        inner_lay = QVBoxLayout(self.quadro_sa_botoes)
        inner_lay.setContentsMargins(8, 8, 8, 8)
        inner_lay.setSpacing(6)
        self.btn_imprimir_sa = QPushButton(qtawesome.icon('fa6s.print', color='#ffffff'), "  Imprimir SA")
        self.btn_imprimir_sa.setObjectName("btnPrimary")
        self.btn_imprimir_sa.setFixedHeight(32)
        self.btn_imprimir_sa.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_imprimir_sa.clicked.connect(self._imprimir_sa)
        inner_lay.addWidget(self.btn_imprimir_sa)
        self.btn_devolver_sa = QPushButton(qtawesome.icon('fa6s.rotate-left', color='#ffffff'), "  Devolver SA")
        self.btn_devolver_sa.setObjectName("btnGradientRose")
        self.btn_devolver_sa.setFixedHeight(32)
        self.btn_devolver_sa.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_devolver_sa.clicked.connect(self._devolver_sa)
        inner_lay.addWidget(self.btn_devolver_sa)
        linha_sa.addWidget(self.quadro_sa_botoes)

        quadro_layout.addLayout(linha_sa)

        # Linha 2 do quadro principal: 5 radios + contador à direita
        self.label_contador = QLabel("0 solicitações")
        self.label_contador.setObjectName("statusLabel")
        self.label_contador.setStyleSheet("color:#64748b; font-size:11px; font-weight:600;")
        self.label_contador.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        linha_radios = QHBoxLayout()
        linha_radios.setSpacing(10)
        linha_radios.setContentsMargins(0, 2, 0, 2)
        lbl_status = QLabel("Status:")
        lbl_status.setStyleSheet("color:#475569; font-size:11px; font-weight:700;")
        linha_radios.addWidget(lbl_status)
        self.grupo_sa_status = QButtonGroup(self)
        self.radio_sa_cancelado = QRadioButton("Cancelado")
        self.radio_sa_devolvido = QRadioButton("Devolvido")
        self.radio_sa_pendente = QRadioButton("Pendente")
        self.radio_sa_pendente.setChecked(True)
        self.radio_sa_programado = QRadioButton("Programado")
        self.radio_sa_todos = QRadioButton("Todos")
        for rb in [self.radio_sa_cancelado, self.radio_sa_devolvido, self.radio_sa_pendente, self.radio_sa_programado, self.radio_sa_todos]:
            rb.setStyleSheet("font-size:11px; color:#334155;")
            self.grupo_sa_status.addButton(rb)
            linha_radios.addWidget(rb)
        linha_radios.addStretch()
        linha_radios.addWidget(self.label_contador)
        quadro_layout.addLayout(linha_radios)

        # ── Layout inferior: quadro esquerdo + (quadro_sa + tabela) à direita ──
        # O quadro esquerdo terá width igual ao conjunto quadro_sa + tabela (lado direito)
        conteudo_inferior = QWidget()
        conteudo_inferior_lay = QHBoxLayout(conteudo_inferior)
        conteudo_inferior_lay.setContentsMargins(0, 0, 0, 0)
        conteudo_inferior_lay.setSpacing(12)

        # Quadro à esquerda — Lista de SAs, 100px width, lista arquivos em Almox/SA
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
        lbl_esq_titulo = QLabel("Lista de SAs")
        lbl_esq_titulo.setStyleSheet("color:#1e293b; font-size:9px; font-weight:700;")
        lbl_esq_titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_esq_titulo.setWordWrap(True)
        lay_esq.addWidget(lbl_esq_titulo)
        # lista de arquivos SA
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
            0: 38,
            1: 38,
            2: 38,
            3: 110,
            4: 110,
            5: 75,
            6: 95,
            7: 120,
            8: 130,
            9: 120,
            10: 115,
            11: 105,
            12: 125,
            13: 115,
            14: 120,
            15: 135,
            16: 180,
            17: 110,
        }
        for c, w in larguras.items():
            header.setSectionResizeMode(c, QHeaderView.ResizeMode.Fixed)
            header.resizeSection(c, w)
        header.setSectionResizeMode(16, QHeaderView.ResizeMode.Interactive)
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
        """Retorna pasta Almox/SA, tentando config e fallbacks locais."""
        candidatos = []
        try:
            import config
            base = config.obter_caminho_jsons()
            if base and os.path.isdir(base):
                candidatos.append(os.path.normpath(os.path.join(base, "Almox", "SA")))
        except Exception:
            pass
        # fallbacks locais
        candidatos.extend([
            os.path.normpath(os.path.join(os.getcwd(), "Almox", "SA")),
            os.path.normpath(r"C:\Users\ander\Documents\AntiGravity\Almoxarifado2\Almox\SA"),
            os.path.normpath(r"C:\Users\ander\Documents\AntiGravity\AlmoxarifadoConf\Almox\SA"),
            os.path.normpath(r"C:\Almox\SA"),
        ])
        for p in candidatos:
            if os.path.isdir(p):
                return p
        # retorna primeiro candidato mesmo se não existir (para criar)
        return candidatos[0] if candidatos else ""

    def _atualizar_lista_sas(self):
        if not hasattr(self, "lista_sas"):
            return
        self.lista_sas.blockSignals(True)
        self.lista_sas.clear()
        pastas = []
        # coleta de todas as pastas candidatas (evita duplicar)
        vistos = set()
        candidatos = []
        try:
            import config
            base = config.obter_caminho_jsons()
            if base:
                candidatos.append(os.path.normpath(os.path.join(base, "Almox", "SA")))
        except Exception:
            pass
        candidatos.extend([
            os.path.normpath(os.path.join(os.getcwd(), "Almox", "SA")),
            os.path.normpath(r"C:\Users\ander\Documents\AntiGravity\Almoxarifado2\Almox\SA"),
            os.path.normpath(r"C:\Users\ander\Documents\AntiGravity\AlmoxarifadoConf\Almox\SA"),
            os.path.normpath(r"C:\Almox\SA"),
        ])
        arquivos = {}
        for pasta in candidatos:
            if not pasta or not os.path.isdir(pasta):
                continue
            try:
                for nome in os.listdir(pasta):
                    if nome.lower().endswith(".json"):
                        chave = nome.lower()
                        if chave not in arquivos:
                            arquivos[chave] = os.path.join(pasta, nome)
            except Exception:
                continue
        # ordena por nome
        for nome in sorted(arquivos.keys()):
            caminho = arquivos[nome]
            sa_nome = os.path.splitext(os.path.basename(caminho))[0]  # ex: 120320
            from PySide6.QtWidgets import QListWidgetItem
            item = QListWidgetItem(sa_nome)
            item.setData(Qt.ItemDataRole.UserRole, caminho)
            item.setToolTip(caminho)
            self.lista_sas.addItem(item)
        self.lista_sas.blockSignals(False)
        # atualiza contador do quadro esquerdo via tooltip
        if self.lista_sas.count() == 0:
            from PySide6.QtWidgets import QListWidgetItem
            it = QListWidgetItem("(vazio)")
            it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEnabled)
            it.setForeground(QBrush(QColor("#94a3b8")))
            self.lista_sas.addItem(it)

    def _on_sa_selecionada(self, item):
        if not item:
            return
        caminho = item.data(Qt.ItemDataRole.UserRole)
        if not caminho or not os.path.isfile(caminho):
            return
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                dados_sa = json.load(f)
            if not isinstance(dados_sa, list):
                dados_sa = []
        except Exception as e:
            self._mostrar_toast(f"Erro ao ler {os.path.basename(caminho)}: {e}", erro=True)
            return
        # atualiza header SA
        sa_nome = os.path.splitext(os.path.basename(caminho))[0]
        if hasattr(self, "label_sa_numero"):
            self.label_sa_numero.setText(f"SA{sa_nome}" if not sa_nome.upper().startswith("SA") else sa_nome)
        # carrega itens da SA na tabela (substitui dados atuais)
        # preserva backup do solicitante header se existir nos itens
        # normaliza chaves
        for d in dados_sa:
            if isinstance(d, dict):
                for ch in self.CHAVES:
                    d.setdefault(ch, "")
                d.setdefault("solicitante", "")
                d.setdefault("projeto_destino", "")
        self.dados = dados_sa
        self._popular_tabela()
        self._mostrar_toast(f"SA {sa_nome} carregada ({len(dados_sa)} itens).", erro=False)

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
        self._popular_tabela()

    def _limpar_filtros(self):
        # bloqueia sinais para não disparar _popular_tabela a cada clear
        for w in [self.filtro_sa, self.filtro_kardex, self.filtro_requisicao, self.filtro_destino, self.filtro_conta]:
            w.blockSignals(True)
            w.clear()
            w.blockSignals(False)
        self.filtro_status.blockSignals(True)
        self.filtro_status.setCurrentIndex(0)
        self.filtro_status.blockSignals(False)
        # solicitante e projeto são editáveis: limpar texto
        for combo in [self.filtro_solicitante, self.filtro_projeto]:
            combo.blockSignals(True)
            combo.setCurrentIndex(0)
            if combo.lineEdit():
                combo.lineEdit().clear()
            combo.blockSignals(False)
        self._popular_tabela()

    def _filtros_ativos(self):
        """Retorna dict com valores atuais dos 8 filtros."""
        def combo_valor(combo):
            # para combos editáveis, prioriza texto digitado
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
            "sa": self.filtro_sa.text().strip(),
            "status": combo_valor(self.filtro_status),
            "solicitante": combo_valor(self.filtro_solicitante),
            "kardex": self.filtro_kardex.text().strip(),
            "requisicao": self.filtro_requisicao.text().strip(),
            "destino": self.filtro_destino.text().strip(),
            "conta": self.filtro_conta.text().strip(),
            "projeto": combo_valor(self.filtro_projeto),
        }

    def _item_pass_filtro(self, item, f):
        # SA -> filtra em numero_req (Nº Req) — contém
        if f["sa"]:
            if f["sa"].lower() not in str(item.get("numero_req", "")).lower():
                # também tenta conta/kardex como fallback para SA
                if f["sa"].lower() not in str(item.get("conta", "")).lower():
                    return False
        # Status -> exato (vazio = ignora)
        if f["status"]:
            # filtro_status "" = Vazio = ignora filtro
            if f["status"] != "":
                if str(item.get("status", "")).strip() != f["status"]:
                    return False
        # Solicitante -> como não há coluna dedicada, filtra em observacoes/destino/conta/texto geral
        if f["solicitante"]:
            texto_geral = " ".join(str(v) for v in item.values()).lower()
            if f["solicitante"].lower() not in texto_geral:
                # também checa chave solicitante se existir
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
            # projeto_destino ainda vazio no schema — filtra em destino/local_entrega/observacoes
            if "projeto_destino" in item and str(item.get("projeto_destino", "")).strip():
                if f["projeto"].lower() not in str(item.get("projeto_destino", "")).lower():
                    return False
            else:
                texto_geral = " ".join(str(v) for v in item.values()).lower()
                if f["projeto"].lower() not in texto_geral:
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
                valor = str(item.get(chave, ""))
                cell = QTableWidgetItem(valor)
                cell.setFlags(cell.flags() | Qt.ItemFlag.ItemIsEditable)

                if chave == "status":
                    cor_bg = CORES_STATUS.get(valor, "")
                    if cor_bg:
                        cell.setData(Qt.BackgroundRole, QBrush(QColor(cor_bg)))
                        cor_txt = TEXTO_STATUS.get(valor, "#1e1b4b")
                        cell.setData(Qt.ForegroundRole, QBrush(QColor(cor_txt)))
                    cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                elif chave in ("qtde_n", "qtde_r", "qtde_p", "qtde", "estoque_novo", "estoque_retorno", "custo_total_estimado"):
                    cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    if chave == "custo_total_estimado" and valor:
                        cell.setToolTip(f"R$ {valor}")
                elif chave == "data_necessidade":
                    cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                elif chave in ("kardex", "codigo", "numero_req", "conta"):
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
            cell = QTableWidgetItem("")
            if col == self.IDX_STATUS:
                cell.setText("")
                cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            cell.setFlags(cell.flags() | Qt.ItemFlag.ItemIsEditable)
            if col == self.IDX_KARDEX:
                cell.setToolTip("Digite o Kardex para criar...")
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
        self.tabela.setCurrentCell(last, self.IDX_KARDEX)
        self.tabela.setFocus()
        item = self.tabela.item(last, self.IDX_KARDEX)
        if item:
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
            tem_conteudo = False
            for c in range(len(self.COLUNAS)):
                cel = self.tabela.item(row, c)
                if cel and cel.text().strip():
                    if c == self.IDX_STATUS and cel.text().strip() == "":
                        continue
                    tem_conteudo = True
                    break
            if not tem_conteudo:
                return

            novo_item = {}
            for c, ch in enumerate(self.CHAVES):
                cel = self.tabela.item(row, c)
                valor = cel.text().strip() if cel else ""
                if ch in ("kardex", "codigo", "conta"):
                    valor = valor.strip().upper()
                novo_item[ch] = valor

            for campo in ("qtde_n", "qtde_r", "qtde_p", "qtde", "estoque_novo", "estoque_retorno"):
                ok, msg = self._validar_qtde(novo_item.get(campo, ""))
                if not ok:
                    self.tabela.blockSignals(True)
                    idx_col = self.CHAVES.index(campo)
                    cel_err = self.tabela.item(row, idx_col)
                    if cel_err:
                        cel_err.setText("")
                    self.tabela.blockSignals(False)
                    self._mostrar_toast(msg, erro=True)
                    return

            ok, msg = self._validar_custo(novo_item.get("custo_total_estimado", ""))
            if not ok:
                self.tabela.blockSignals(True)
                cel_err = self.tabela.item(row, self.CHAVES.index("custo_total_estimado"))
                if cel_err:
                    cel_err.setText("")
                self.tabela.blockSignals(False)
                self._mostrar_toast(msg, erro=True)
                return

            # Regra 1: Qtde N/R/P não pode ser 0
            for campo in ("qtde_n", "qtde_r", "qtde_p"):
                v = str(novo_item.get(campo, "")).strip()
                if v:
                    p = self._parse_qtde(v)
                    if p is not None and p == 0:
                        self.tabela.blockSignals(True)
                        cel_err = self.tabela.item(row, self.CHAVES.index(campo))
                        if cel_err:
                            cel_err.setText("")
                        self.tabela.blockSignals(False)
                        self._mostrar_toast(f"{campo.replace('qtde_','Qtde ').upper()} não pode ser 0.", erro=True)
                        return
            # Regra 2 (soma N+R+P == Qtde) agora é validada apenas ao SAIR da linha,
            # para permitir preenchimento parcial (ex: Qtde=5, digita N=3 depois R=2).
            # Ver _ao_mudar_celula / _validar_soma_linha.

            if not (novo_item.get("kardex") or novo_item.get("codigo") or novo_item.get("numero_req")):
                self._mostrar_toast("Preencha ao menos Kardex, Código ou Nº Req.", erro=True)
                return

            self.dados.append(novo_item)
            # persiste também chaves extras de filtro para busca futura
            # guarda solicitante/projeto se preenchidos nos filtros? não, só tabela
            self._salvar_json()
            self._popular_tabela()
            QTimer.singleShot(0, self._adicionar_linha)
            ident = novo_item.get("numero_req") or novo_item.get("kardex") or novo_item.get("codigo") or "nova"
            self._mostrar_toast(f"Solicitação \"{ident}\" adicionada.", erro=False)
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

        # Regra 2 (soma N+R+P == Qtde) não é validada aqui para permitir
        # preenchimento parcial. Será validada ao sair da linha
        # em _ao_mudar_celula / _validar_soma_linha.
        # Ex: Qtde=5, usuário digita N=3 e depois R=2 sem erro intermediário.

        if self.dados[idx].get(chave, "") == novo_valor:
            return

        self.dados[idx][chave] = novo_valor
        # guarda filtros extras se existirem
        self._salvar_json()
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
                # limpa modelo e view
                self.dados[idx]["qtde_n"] = ""
                self.dados[idx]["qtde_r"] = ""
                self.dados[idx]["qtde_p"] = ""
                self._salvar_json()
                self.tabela.blockSignals(True)
                for col in (0, 1, 2):
                    it = self.tabela.item(row, col)
                    if it:
                        it.setText("")
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
        submenu_status = menu.addMenu("Alterar Status")
        for label, valor in zip(STATUS_FILTRO_LABELS, STATUS_OPCOES):
            if valor == "" :
                continue
            act = submenu_status.addAction(label)
            pix = QPixmap(12, 12)
            pix.fill(QColor(CORES_STATUS.get(valor, "#ffffff")))
            act.setIcon(QIcon(pix))
            act.triggered.connect(lambda checked=False, s=valor, i=idx: self._alterar_status(i, s))
        # opção Vazio
        act_vazio = submenu_status.addAction("Vazio")
        act_vazio.triggered.connect(lambda checked=False, i=idx: self._alterar_status(i, ""))
        menu.addSeparator()
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
