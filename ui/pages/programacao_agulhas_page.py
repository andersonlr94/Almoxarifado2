import json
import os
from datetime import datetime
from collections import Counter

import matplotlib
matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QStyledItemDelegate, QStyleOptionViewItem,
    QStyle, QDialog, QFrame, QDateEdit,
)
from PySide6.QtCore import Qt, QSize, QSizeF, QRect, Signal, QDate
from PySide6.QtGui import QPainter, QMouseEvent, QTextDocument, QPageSize
from PySide6.QtPrintSupport import QPrinter, QPrinterInfo
from PySide6.QtWidgets import QMessageBox
import socket


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


class CheckboxHeader(QHeaderView):
    toggleAll = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(Qt.Orientation.Horizontal, parent)
        self._checked = False
        self._partial = False
        self.setSectionsClickable(False)
        self.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)

    def paintSection(self, painter, rect, index):
        painter.save()
        super().paintSection(painter, rect, index)
        if index == 0:
            opt = QStyleOptionViewItem()
            cb_rect = QStyle.alignedRect(
                Qt.LayoutDirection.LeftToRight,
                Qt.AlignmentFlag.AlignCenter,
                QSize(16, 16),
                rect
            )
            opt.rect = cb_rect
            opt.state = QStyle.StateFlag.State_Enabled
            if self._partial:
                opt.state |= QStyle.StateFlag.State_NoChange
            elif self._checked:
                opt.state |= QStyle.StateFlag.State_On
            self.style().drawPrimitive(QStyle.PrimitiveElement.PE_IndicatorCheckBox, opt, painter, self)
        painter.restore()

    def mousePressEvent(self, event):
        index = self.logicalIndexAt(event.position().toPoint())
        if index == 0:
            self._checked = not self._checked
            self._partial = False
            self.toggleAll.emit(self._checked)
            self.updateSection(0)
        super().mousePressEvent(event)

    def setState(self, checked, partial=False):
        self._checked = checked
        self._partial = partial
        self.updateSection(0)


def _caminho_json():
    import config
    base = config.obter_caminho_jsons()
    if not base:
        base = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "jsons")
    return os.path.normpath(os.path.join(base, "Almox", "ProgramacaoAgulhasManutencao", "pedidos.json"))


def _caminho_entregues(ano):
    import config
    base = config.obter_caminho_jsons()
    if not base:
        base = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "jsons")
    return os.path.normpath(os.path.join(base, "Almox", "ProgramacaoAgulhasManutencao", f"{ano}-Entregues.json"))


def _caminho_itens():
    import config
    base = config.obter_caminho_jsons()
    if not base:
        base = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "jsons")
    return os.path.normpath(os.path.join(base, "Almox", "ItensAlmoxarifado", "ItensAlmoxarifado.json"))


def _chave_flexivel(item, *variacoes):
    for chave in variacoes:
        if chave in item:
            valor = item[chave]
            return str(valor) if valor is not None else ""
    return ""


def _buscar_item_por_codigo(codigo):
    try:
        with open(_caminho_itens(), "r", encoding="utf-8") as f:
            itens = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None

    chaves_codigo = ["codigo", "cod", "Código", "CODIGO", "Codigo", "COD"]

    def _extrair(item):
        if not isinstance(item, dict):
            return None
        cod = _chave_flexivel(item, *chaves_codigo)
        if cod and cod == codigo:
            return item
        return None

    if isinstance(itens, list):
        for item in itens:
            resultado = _extrair(item)
            if resultado:
                return resultado
    elif isinstance(itens, dict):
        for item in itens.values():
            resultado = _extrair(item)
            if resultado:
                return resultado
    return None


def _buscar_item_por_kardex(kardex):
    try:
        with open(_caminho_itens(), "r", encoding="utf-8") as f:
            itens = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None

    chaves_kardex = ["kardex", "Kardex", "KARDEX"]

    def _extrair(item):
        if not isinstance(item, dict):
            return None
        valor = _chave_flexivel(item, *chaves_kardex)
        if valor and valor == kardex:
            return item
        return None

    if isinstance(itens, list):
        for item in itens:
            resultado = _extrair(item)
            if resultado:
                return resultado
    elif isinstance(itens, dict):
        for item in itens.values():
            resultado = _extrair(item)
            if resultado:
                return resultado
    return None


class ProgramacaoAgulhasPage(QWidget):
    def __init__(self):
        super().__init__()
        self.dados = []
        self.dados_entregues = []
        self.filtro_status = "Pendentes"
        self.campo_data_por_filtro = {
            "Pendentes": "data_inserido",
            "Programados": "data_programado",
            "Separando": "data_separando",
            "Entregues": "data_entregue",
        }
        self._setup_ui()
        self._carregar_dados()

    def _lista_impressoras(self):
        try:
            disponiveis = QPrinterInfo.availablePrinters()
            return [printer.printerName() for printer in disponiveis]
        except Exception:
            return []

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        card = QWidget()
        card.setObjectName("pageCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(12)

        titulo = QLabel("Programação de agulhas para manutenção")
        titulo.setObjectName("pageTitle")
        card_layout.addWidget(titulo)

        secao_form = QLabel("Novo Pedido")
        secao_form.setObjectName("sectionTitle")
        card_layout.addWidget(secao_form)

        form_layout = QHBoxLayout()
        form_layout.setSpacing(8)

        self.campo_pedido = QLineEdit()
        self.campo_pedido.setPlaceholderText("Pedido")
        self.campo_codigo = QLineEdit()
        self.campo_codigo.setPlaceholderText("Código")
        self.campo_qtde = QLineEdit()
        self.campo_qtde.setPlaceholderText("Qtde")
        self.campo_requisitante = QLineEdit()
        self.campo_requisitante.setPlaceholderText("Requisitante (1, 2 ou 3)")
        self.campo_requisitante.textChanged.connect(self._mapear_requisitante)

        for campo in [self.campo_pedido, self.campo_codigo, self.campo_qtde, self.campo_requisitante]:
            campo.setFixedHeight(34)
            campo.returnPressed.connect(self._inserir)
            form_layout.addWidget(campo)

        btn_inserir = QPushButton("Inserir")
        btn_inserir.setObjectName("btnPrimary")
        btn_inserir.setFixedHeight(34)
        btn_inserir.setDefault(True)
        btn_inserir.clicked.connect(self._inserir)
        form_layout.addWidget(btn_inserir)
        card_layout.addLayout(form_layout)

        secao_filtros = QLabel("Filtrar por Status")
        secao_filtros.setObjectName("sectionTitle")
        card_layout.addWidget(secao_filtros)

        linha_top = QHBoxLayout()
        linha_top.setSpacing(8)

        botoes_status_layout = QHBoxLayout()
        botoes_status_layout.setSpacing(6)
        self.botoes_status = {}
        for status in ["Pendentes", "Programados", "Separando", "Entregues"]:
            btn = QPushButton(status)
            btn.setObjectName("segmented")
            btn.setCheckable(True)
            btn.setFixedHeight(30)
            btn.clicked.connect(lambda checked, s=status: self._filtrar_por_status(s))
            botoes_status_layout.addWidget(btn)
            self.botoes_status[status] = btn
        self.botoes_status["Pendentes"].setChecked(True)
        linha_top.addLayout(botoes_status_layout)

        self.campo_filtro = QLineEdit()
        self.campo_filtro.setPlaceholderText("Pesquisar...")
        self.campo_filtro.setFixedHeight(30)
        self.campo_filtro.setFixedWidth(140)
        self.campo_filtro.textChanged.connect(self._aplicar_filtro)
        linha_top.addWidget(self.campo_filtro)

        self.widget_filtro_data = QWidget()
        layout_filtro_data = QHBoxLayout()
        layout_filtro_data.setContentsMargins(0, 0, 0, 0)
        layout_filtro_data.setSpacing(4)

        lbl_data_ini = QLabel("De")
        lbl_data_ini.setFixedHeight(30)
        layout_filtro_data.addWidget(lbl_data_ini)

        self.data_inicio = QDateEdit()
        self.data_inicio.setCalendarPopup(True)
        self.data_inicio.setDisplayFormat("dd/MM/yyyy")
        self.data_inicio.setDate(QDate.currentDate().addMonths(-6))
        self.data_inicio.setFixedHeight(30)
        self.data_inicio.setFixedWidth(115)
        self.data_inicio.editingFinished.connect(self._aplicar_filtro)
        layout_filtro_data.addWidget(self.data_inicio)

        lbl_data_fim = QLabel("até")
        lbl_data_fim.setFixedHeight(30)
        layout_filtro_data.addWidget(lbl_data_fim)

        self.data_fim = QDateEdit()
        self.data_fim.setCalendarPopup(True)
        self.data_fim.setDisplayFormat("dd/MM/yyyy")
        self.data_fim.setDate(QDate.currentDate())
        self.data_fim.setFixedHeight(30)
        self.data_fim.setFixedWidth(115)
        self.data_fim.editingFinished.connect(self._aplicar_filtro)
        layout_filtro_data.addWidget(self.data_fim)

        self.btn_limpar_filtro_data = QPushButton("✕")
        self.btn_limpar_filtro_data.setObjectName("btnClear")
        self.btn_limpar_filtro_data.setFixedSize(30, 30)
        self.btn_limpar_filtro_data.setToolTip("Limpar filtro de período")
        self.btn_limpar_filtro_data.clicked.connect(self._limpar_filtro_data)
        layout_filtro_data.addWidget(self.btn_limpar_filtro_data)

        self.btn_grafico = QPushButton("Gráfico")
        self.btn_grafico.setFixedHeight(30)
        self.btn_grafico.setObjectName("btnPrimary")
        self.btn_grafico.clicked.connect(self._abrir_grafico)
        layout_filtro_data.addWidget(self.btn_grafico)

        self.widget_filtro_data.setLayout(layout_filtro_data)
        self.widget_filtro_data.setVisible(False)
        linha_top.addWidget(self.widget_filtro_data)

        linha_top.addStretch()

        self.btn_mover_programado = QPushButton("Programar")
        self.btn_mover_programado.setObjectName("btnPrimary")
        self.btn_mover_programado.setFixedHeight(30)
        self.btn_mover_programado.clicked.connect(self._mover_programado)
        self.btn_mover_separando = QPushButton("Separar")
        self.btn_mover_separando.setObjectName("btnPrimary")
        self.btn_mover_separando.setFixedHeight(30)
        self.btn_mover_separando.clicked.connect(self._mover_separando)
        self.btn_entregar = QPushButton("Entregar")
        self.btn_entregar.setObjectName("btnPrimary")
        self.btn_entregar.setFixedHeight(30)
        self.btn_entregar.clicked.connect(self._entregar)
        self.btn_excluir = QPushButton("Excluir")
        self.btn_excluir.setObjectName("btnDanger")
        self.btn_excluir.setFixedHeight(30)
        self.btn_excluir.clicked.connect(self._excluir)
        self.btn_dividir = QPushButton("Dividir")
        self.btn_dividir.setObjectName("btnPrimary")
        self.btn_dividir.setFixedHeight(30)
        self.btn_dividir.clicked.connect(self._dividir)

        self.combo_impressoras = QComboBox()
        self.combo_impressoras.setFixedHeight(30)
        self.combo_impressoras.setFixedWidth(160)
        self.combo_impressoras.setToolTip("Selecione a impressora Zebra para impressão")
        self.combo_impressoras.setVisible(False)

        self.btn_imprimir = QPushButton("Imprimir")
        self.btn_imprimir.setObjectName("btnPrimary")
        self.btn_imprimir.setFixedHeight(30)
        self.btn_imprimir.clicked.connect(self._imprimir_zebra)
        self.btn_imprimir.setVisible(False)

        linha_top.addWidget(self.btn_mover_programado)
        linha_top.addWidget(self.btn_mover_separando)
        linha_top.addWidget(self.btn_excluir)
        linha_top.addWidget(self.btn_dividir)
        linha_top.addWidget(self.btn_entregar)
        linha_top.addWidget(self.combo_impressoras)
        linha_top.addWidget(self.btn_imprimir)

        card_layout.addLayout(linha_top)

        info_linha = QHBoxLayout()
        info_linha.setSpacing(16)

        def lbl_info(texto):
            label = QLabel(texto)
            label.setObjectName("statusLabel")
            return label

        info_linha.addWidget(lbl_info("QTDE NOVO:"))
        self.label_qtde_novo = lbl_info("0")
        info_linha.addWidget(self.label_qtde_novo)
        info_linha.addWidget(lbl_info("QTDE RETORNO:"))
        self.label_qtde_retorno = lbl_info("0")
        info_linha.addWidget(self.label_qtde_retorno)
        info_linha.addWidget(lbl_info("CONSUMO MÉDIO:"))
        self.label_consumo_medio = lbl_info("0")
        info_linha.addWidget(self.label_consumo_medio)

        info_linha.addStretch()
        self.label_contador = QLabel("0 itens")
        self.label_contador.setObjectName("statusLabel")
        info_linha.addWidget(self.label_contador)
        card_layout.addLayout(info_linha)

        self.tabela = QTableWidget(0, 8)
        self.tabela.setHorizontalHeaderLabels(
            ["", "Pedido", "Kardex", "Código", "Qtde", "Fornecedor", "Requisitante", "Data"]
        )
        header = CheckboxHeader(self.tabela)
        header.toggleAll.connect(self._toggle_todos)
        self.tabela.setHorizontalHeader(header)
        header.setStretchLastSection(True)
        for c in range(self.tabela.columnCount()):
            header.setSectionResizeMode(c, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.tabela.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabela.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked)
        self.tabela.setAlternatingRowColors(True)
        self.tabela.setWordWrap(False)
        self.tabela.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.tabela.verticalHeader().setDefaultSectionSize(36)
        self.tabela.verticalHeader().setMinimumSectionSize(28)
        self.tabela.verticalHeader().setVisible(False)
        self.tabela.setItemDelegate(EditorDelegate(self.tabela))
        self.tabela.itemChanged.connect(self._item_modificado)
        self.tabela.cellClicked.connect(self._linha_clicada)
        card_layout.addWidget(self.tabela)

        self._preencher_impressoras()
        layout.addWidget(card)

    def _proximo_id(self):
        max_id = 0
        for d in self.dados:
            try:
                max_id = max(max_id, int(d.get("id", 0)))
            except (ValueError, TypeError):
                pass
        return max_id + 1

    def _carregar_dados(self):
        try:
            with open(_caminho_json(), "r", encoding="utf-8") as f:
                todos = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            todos = []
        self.dados = [d for d in todos if d.get("status") != "Entregue"]
        entregues = [d for d in todos if d.get("status") == "Entregue"]
        if entregues:
            ano_atual = datetime.now().strftime("%Y")
            try:
                with open(_caminho_entregues(ano_atual), "r", encoding="utf-8") as f:
                    existentes = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                existentes = []
            existentes.extend(entregues)
            os.makedirs(os.path.dirname(_caminho_entregues(ano_atual)), exist_ok=True)
            with open(_caminho_entregues(ano_atual), "w", encoding="utf-8") as f:
                json.dump(existentes, f, ensure_ascii=False, indent=2)
        for d in self.dados:
            if "id" not in d or not d["id"]:
                d["id"] = self._proximo_id()
        self._popular_tabela()

    def _popular_tabela(self):
        self.tabela.blockSignals(True)
        self.tabela.setRowCount(0)

        fonte = self._fonte_dados()

        filtro_texto = self.campo_filtro.text().strip().lower()
        dados_filtrados = []
        for item in fonte:
            status_item = item.get("status", "")
            if self.filtro_status == "Pendentes" and status_item != "Pendente":
                continue
            if self.filtro_status == "Programados" and "Programado" not in status_item:
                continue
            if self.filtro_status == "Separando" and "Separando" not in status_item:
                continue
            if self.filtro_status == "Entregues" and "Entregue" not in status_item:
                continue
            if filtro_texto:
                texto = " ".join(str(v) for v in item.values()).lower()
                if filtro_texto not in texto:
                    continue
            chave_data = self.campo_data_por_filtro.get(self.filtro_status, "status")
            valor_data = item.get(chave_data, "")
            if valor_data:
                try:
                    data_item = datetime.strptime(valor_data, "%d/%m/%Y").date()
                    data_ini = self.data_inicio.date().toPython()
                    data_fim = self.data_fim.date().toPython()
                    if not (data_ini <= data_item <= data_fim):
                        continue
                except ValueError:
                    pass
            dados_filtrados.append(item)

        for item in dados_filtrados:
            row = self.tabela.rowCount()
            self.tabela.insertRow(row)

            chk = QTableWidgetItem()
            chk.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            chk.setCheckState(Qt.CheckState.Unchecked if not item.get("selecionado") else Qt.CheckState.Checked)
            self.tabela.setItem(row, 0, chk)

            editavel = self.filtro_status != "Entregues"
            for col, chave in enumerate(["pedido", "kardex", "codigo", "qtde", "fornecedor", "requisitante"], 1):
                valor = str(item.get(chave, ""))
                if chave == "fornecedor":
                    valor_exibido = valor if len(valor) <= 20 else valor[:20] + "..."
                    cell = QTableWidgetItem(valor_exibido)
                    cell.setToolTip(valor)
                    cell.setData(Qt.EditRole, valor)
                else:
                    cell = QTableWidgetItem(valor)
                if editavel:
                    cell.setFlags(cell.flags() | Qt.ItemFlag.ItemIsEditable)
                self.tabela.setItem(row, col, cell)

            chave_data = self.campo_data_por_filtro.get(self.filtro_status, "status")
            valor_data = str(item.get(chave_data, ""))
            cell_data = QTableWidgetItem(valor_data)
            if editavel:
                cell_data.setFlags(cell_data.flags() | Qt.ItemFlag.ItemIsEditable)
            self.tabela.setItem(row, 7, cell_data)

        self.tabela.blockSignals(False)
        self._atualizar_header_checkbox()
        self._atualizar_contador()
        self._atualizar_botoes_acao()

    def _atualizar_botoes_acao(self):
        self.btn_mover_programado.setVisible(False)
        self.btn_mover_separando.setVisible(False)
        self.btn_entregar.setVisible(False)
        self.btn_excluir.setVisible(False)
        self.btn_dividir.setVisible(False)
        self.combo_impressoras.setVisible(False)
        self.btn_imprimir.setVisible(False)
        if self.filtro_status == "Pendentes":
            self.btn_mover_programado.setVisible(True)
            self.btn_mover_separando.setVisible(True)
            self.btn_excluir.setVisible(True)
            self.btn_dividir.setVisible(True)
        elif self.filtro_status == "Programados":
            self.btn_mover_separando.setVisible(True)
            self.btn_dividir.setVisible(True)
        elif self.filtro_status == "Separando":
            self.btn_entregar.setVisible(True)
            self.combo_impressoras.setVisible(True)
            self.btn_imprimir.setVisible(True)

    def _atualizar_contador(self):
        total = self.tabela.rowCount()
        selecionados = 0
        for row in range(total):
            chk = self.tabela.item(row, 0)
            if chk and chk.checkState() == Qt.CheckState.Checked:
                selecionados += 1
        self.label_contador.setText(f"{selecionados} itens selecionados de {total}")

    def _mover_status(self, novo_status):
        hoje = datetime.now().strftime("%d/%m/%Y")
        campo_data = {
            "Programado": "data_programado",
            "Separando": "data_separando",
            "Entregue": "data_entregue",
        }.get(novo_status)
        if novo_status == "Entregue":
            entregues = []
            restantes = []
            for d in self.dados:
                if d.get("selecionado"):
                    d["status"] = "Entregue"
                    if campo_data:
                        d[campo_data] = hoje
                    d["selecionado"] = False
                    entregues.append(d)
                else:
                    restantes.append(d)
            self.dados = restantes
            if entregues:
                ano = datetime.now().strftime("%Y")
                caminho = _caminho_entregues(ano)
                os.makedirs(os.path.dirname(caminho), exist_ok=True)
                try:
                    with open(caminho, "r", encoding="utf-8") as f:
                        existentes = json.load(f)
                except (FileNotFoundError, json.JSONDecodeError):
                    existentes = []
                existentes.extend(entregues)
                with open(caminho, "w", encoding="utf-8") as f:
                    json.dump(existentes, f, ensure_ascii=False, indent=2)
            self._salvar_json()
            self._filtrar_por_status(self.filtro_status)
            return
        for dado in self.dados:
            if dado.get("selecionado"):
                dado["status"] = novo_status
                if campo_data:
                    dado[campo_data] = hoje
                dado["selecionado"] = False
        self._salvar_json()
        self._filtrar_por_status(self.filtro_status)

    def _mover_programado(self):
        self._mover_status("Programado")

    def _mover_separando(self):
        self._mover_status("Separando")

    def _entregar(self):
        self._mover_status("Entregue")

    def _excluir(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Excluir")
        dialog.setFixedSize(400, 160)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 16)
        layout.setSpacing(16)

        msg = QLabel("Tem certeza que deseja excluir os itens selecionados?")
        msg.setStyleSheet("font-size: 13px; color: #1e293b;")
        msg.setWordWrap(True)
        layout.addWidget(msg)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setStyleSheet("color: #e2e8f0;")
        layout.addWidget(line)

        btn_ok = QPushButton("Sim")
        btn_ok.setObjectName("btnDanger")
        btn_ok.setFixedHeight(30)
        btn_ok.clicked.connect(dialog.accept)
        btn_ok.setDefault(True)
        btn_cancel = QPushButton("Não")
        btn_cancel.setObjectName("btnSecondary")
        btn_cancel.setFixedHeight(30)
        btn_cancel.clicked.connect(dialog.reject)
        botoes = QHBoxLayout()
        botoes.addStretch()
        botoes.addWidget(btn_cancel)
        botoes.addWidget(btn_ok)
        layout.addLayout(botoes)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.dados = [
            d for d in self.dados
            if not d.get("selecionado")
        ]
        self._salvar_json()
        self._filtrar_por_status(self.filtro_status)

    def _dividir(self):
        selecionados = [d for d in self.dados if d.get("selecionado")]
        if len(selecionados) == 0:
            QMessageBox.information(self, "Dividir", "Selecione um item para dividir.")
            return
        if len(selecionados) > 1:
            QMessageBox.information(self, "Dividir", "Selecione apenas um item para dividir.")
            return
        dado = selecionados[0]
        pedido_original = dado.get("pedido", "")
        codigo = dado.get("codigo", "")
        qtde_atual = dado.get("qtde", "1")
        try:
            qtde_int = int(qtde_atual)
        except ValueError:
            QMessageBox.information(self, "Dividir", "Quantidade inválida para divisão.")
            return
        if qtde_int <= 1:
            QMessageBox.information(self, "Dividir", "Quantidade deve ser maior que 1 para dividir.")
            return
        qtde_a = (qtde_int // 2) + (qtde_int % 2)
        qtde_b = qtde_int // 2

        dialog = QDialog(self)
        dialog.setWindowTitle("Dividir Pedido")
        dialog.setFixedSize(500, 200)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(14)

        grid = QGridLayout()
        grid.setSpacing(8)
        grid.setContentsMargins(4, 0, 4, 0)

        grid.addWidget(QLabel(""), 0, 0)
        lbl_pedido = QLabel("Pedido")
        lbl_pedido.setFixedWidth(160)
        lbl_pedido.setStyleSheet("font-size: 11px; font-weight: 600; color: #64748b;")
        grid.addWidget(lbl_pedido, 0, 1)
        lbl_qtde = QLabel("Qtde")
        lbl_qtde.setFixedWidth(60)
        lbl_qtde.setStyleSheet("font-size: 11px; font-weight: 600; color: #64748b;")
        grid.addWidget(lbl_qtde, 0, 2)
        lbl_item = QLabel("Código")
        lbl_item.setStyleSheet("font-size: 11px; font-weight: 600; color: #64748b;")
        grid.addWidget(lbl_item, 0, 3)

        grid.addWidget(QLabel("1"), 1, 0)
        pedido_a = QLineEdit(f"{pedido_original}-A")
        pedido_a.setFixedWidth(160)
        qtde_a_edit = QLineEdit(str(qtde_a))
        qtde_a_edit.setFixedWidth(60)
        qtde_a_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        codigo_edit = QLineEdit(codigo)
        codigo_edit.setReadOnly(True)
        grid.addWidget(pedido_a, 1, 1)
        grid.addWidget(qtde_a_edit, 1, 2)
        grid.addWidget(codigo_edit, 1, 3)

        grid.addWidget(QLabel("2"), 2, 0)
        pedido_b = QLineEdit(f"{pedido_original}-B")
        pedido_b.setFixedWidth(160)
        qtde_b_edit = QLineEdit(str(qtde_b))
        qtde_b_edit.setFixedWidth(60)
        qtde_b_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        codigo_b_edit = QLineEdit(codigo)
        codigo_b_edit.setReadOnly(True)
        grid.addWidget(pedido_b, 2, 1)
        grid.addWidget(qtde_b_edit, 2, 2)
        grid.addWidget(codigo_b_edit, 2, 3)

        layout.addLayout(grid)

        def _recalcular(origem):
            try:
                val = int(origem.text())
            except ValueError:
                return
            outro = qtde_b_edit if origem is qtde_a_edit else qtde_a_edit
            resto = qtde_int - val
            if resto < 0:
                resto = 0
            outro.setText(str(resto))

        qtde_a_edit.editingFinished.connect(lambda: _recalcular(qtde_a_edit))
        qtde_b_edit.editingFinished.connect(lambda: _recalcular(qtde_b_edit))

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setStyleSheet("color: #e2e8f0;")
        layout.addWidget(line)

        btn_ok = QPushButton("Confirmar")
        btn_ok.setObjectName("btnPrimary")
        btn_ok.setFixedHeight(30)
        btn_ok.clicked.connect(dialog.accept)
        btn_ok.setDefault(True)
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setObjectName("btnSecondary")
        btn_cancel.setFixedHeight(30)
        btn_cancel.clicked.connect(dialog.reject)
        botoes = QHBoxLayout()
        botoes.addStretch()
        botoes.addWidget(btn_cancel)
        botoes.addWidget(btn_ok)
        layout.addLayout(botoes)

        qtde_a_edit.setFocus()
        qtde_a_edit.selectAll()

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        dado["pedido"] = pedido_a.text().strip()
        dado["qtde"] = qtde_a_edit.text().strip()

        novo = dict(dado)
        novo["id"] = self._proximo_id()
        novo["pedido"] = pedido_b.text().strip()
        novo["qtde"] = qtde_b_edit.text().strip()
        novo["selecionado"] = False
        idx = self.dados.index(dado) + 1
        self.dados.insert(idx, novo)
        self._salvar_json()
        self._filtrar_por_status(self.filtro_status)

    def _filtrar_por_status(self, status):
        for s, btn in self.botoes_status.items():
            btn.setChecked(s == status)
        self.filtro_status = status
        self.widget_filtro_data.setVisible(status == "Entregues")
        for d in self.dados:
            d["selecionado"] = False
        self._popular_tabela()

    def _aplicar_filtro(self):
        self._popular_tabela()
        self._atualizar_botoes_acao()

    def _limpar_filtro_data(self):
        self.data_inicio.setDate(QDate.currentDate().addMonths(-6))
        self.data_fim.setDate(QDate.currentDate())
        self._aplicar_filtro()

    def _abrir_grafico(self):
        chave_data = self.campo_data_por_filtro.get(self.filtro_status, "status")
        dados_validos = []
        for item in self._fonte_dados():
            status_item = item.get("status", "")
            if self.filtro_status == "Pendentes" and status_item != "Pendente":
                continue
            if self.filtro_status == "Programados" and "Programado" not in status_item:
                continue
            if self.filtro_status == "Separando" and "Separando" not in status_item:
                continue
            if self.filtro_status == "Entregues" and "Entregue" not in status_item:
                continue
            filtro_texto = self.campo_filtro.text().strip().lower()
            if filtro_texto:
                texto = " ".join(str(v) for v in item.values()).lower()
                if filtro_texto not in texto:
                    continue
            valor_data = item.get(chave_data, "")
            if valor_data:
                try:
                    data_item = datetime.strptime(valor_data, "%d/%m/%Y").date()
                    data_ini = self.data_inicio.date().toPython()
                    data_fim = self.data_fim.date().toPython()
                    if not (data_ini <= data_item <= data_fim):
                        continue
                except ValueError:
                    continue
            dados_validos.append(item)

        meses = Counter()
        for item in dados_validos:
            valor_data = item.get(chave_data, "")
            if valor_data:
                try:
                    dt = datetime.strptime(valor_data, "%d/%m/%Y")
                    chave = dt.strftime("%Y-%m")
                    meses[chave] += 1
                except ValueError:
                    pass

        if not meses:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Information)
            msg.setWindowTitle("Gráfico")
            msg.setText("Nenhum dado encontrado no período.")
            msg.exec()
            return

        sorted_meses = sorted(meses.keys())
        valores = [meses[m] for m in sorted_meses]
        rotulos = [datetime.strptime(m, "%Y-%m").strftime("%b/%Y") for m in sorted_meses]

        dialog = QDialog(self)
        dialog.setWindowTitle("Itens por Mês")
        dialog.resize(700, 450)

        layout = QVBoxLayout(dialog)
        canvas = FigureCanvas(Figure(figsize=(7, 4)))
        layout.addWidget(canvas)

        ax = canvas.figure.subplots()
        ax.bar(range(len(rotulos)), valores, color="#4A90D9")
        ax.set_xticks(range(len(rotulos)))
        ax.set_xticklabels(rotulos, rotation=45, ha="right")
        ax.set_ylabel("Quantidade de Itens")
        ax.set_title(f"Itens por Mês - {self.filtro_status}")
        ax.margins(y=0.1)
        canvas.figure.tight_layout()

        dialog.exec()

    def _fonte_dados(self):
        if self.filtro_status == "Entregues":
            ano = datetime.now().strftime("%Y")
            try:
                with open(_caminho_entregues(ano), "r", encoding="utf-8") as f:
                    return json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                return []
        return self.dados

    def _mapear_requisitante(self, texto):
        mapa = {"1": "Almoxarifado PARAISO", "2": "PLANTA DE OUROS", "3": "PLANTA DE ITAJUBA"}
        if texto in mapa:
            self.campo_requisitante.blockSignals(True)
            self.campo_requisitante.setText(mapa[texto])
            self.campo_requisitante.blockSignals(False)

    def _inserir(self):
        pedido = self.campo_pedido.text().strip().upper()
        codigo = self.campo_codigo.text().strip().upper()
        qtde = self.campo_qtde.text().strip()
        requisitante = self.campo_requisitante.text().strip().upper()
        if not pedido:
            return

        item_encontrado = _buscar_item_por_codigo(codigo)
        kardex = ""
        fornecedor = ""
        if item_encontrado:
            kardex = _chave_flexivel(item_encontrado, "kardex", "Kardex", "KARDEX")
            fornecedor = _chave_flexivel(item_encontrado, "fornecedor", "Fornecedor", "FORNECEDOR", "forn")

        hoje = datetime.now().strftime("%d/%m/%Y")
        novo = {
            "id": self._proximo_id(),
            "pedido": pedido,
            "codigo": codigo,
            "kardex": kardex.upper() if kardex else kardex,
            "qtde": qtde or "1",
            "fornecedor": fornecedor.upper() if fornecedor else fornecedor,
            "requisitante": requisitante,
            "status": "Pendente",
            "selecionado": False,
            "data_inserido": hoje,
            "data_programado": "",
            "data_separando": "",
            "data_entregue": "",
        }
        self.dados.append(novo)
        self._salvar_json()
        self.campo_codigo.setText("PIN".upper())
        self.campo_qtde.clear()
        self.campo_requisitante.clear()
        self.campo_codigo.setFocus()
        self._popular_tabela()

    def _toggle_todos(self, checked):
        self.tabela.blockSignals(True)
        for row in range(self.tabela.rowCount()):
            item = self.tabela.item(row, 0)
            if item:
                item.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
        self.tabela.blockSignals(False)
        for dado in self.dados:
            dado["selecionado"] = False
        if checked:
            for row in range(self.tabela.rowCount()):
                pedido = self.tabela.item(row, 1)
                codigo = self.tabela.item(row, 3)
                if pedido and codigo:
                    indices = [i for i, d in enumerate(self.dados)
                               if d.get("pedido") == pedido.text()
                               and d.get("codigo") == codigo.text()]
                    if indices:
                        self.dados[indices[0]]["selecionado"] = True
        self._atualizar_contador()
        self._atualizar_header_checkbox()
        self._salvar_json()

    def _item_modificado(self, item):
        row = item.row()
        col = item.column()
        if col == 0:
            checked = item.checkState() == Qt.CheckState.Checked
            pedido = self.tabela.item(row, 1)
            codigo = self.tabela.item(row, 3)
            if pedido and codigo:
                indices = [i for i, d in enumerate(self.dados)
                           if d.get("pedido") == pedido.text()
                           and d.get("codigo") == codigo.text()]
                if indices:
                    self.dados[indices[0]]["selecionado"] = checked
                    self._salvar_json()
            self._atualizar_header_checkbox()
            self._atualizar_contador()
            return
        chaves = ["", "pedido", "kardex", "codigo", "qtde", "fornecedor", "requisitante"]
        if col < len(chaves):
            chave = chaves[col]
            if not chave:
                return
        elif col == 7:
            chave = self.campo_data_por_filtro.get(self.filtro_status)
            if not chave:
                return
        else:
            return
        pedido = self.tabela.item(row, 1)
        codigo = self.tabela.item(row, 3)
        if pedido and codigo:
            indices = [i for i, d in enumerate(self.dados)
                       if d.get("pedido") == pedido.text()
                       and d.get("codigo") == codigo.text()]
            if indices:
                self.dados[indices[0]][chave] = item.text()
                self._salvar_json()

    def _atualizar_header_checkbox(self):
        total = self.tabela.rowCount()
        if total == 0:
            self.tabela.horizontalHeader().setState(False, False)
            return
        checked = 0
        for row in range(total):
            chk = self.tabela.item(row, 0)
            if chk and chk.checkState() == Qt.CheckState.Checked:
                checked += 1
        if checked == total:
            self.tabela.horizontalHeader().setState(True, False)
        elif checked > 0:
            self.tabela.horizontalHeader().setState(True, True)
        else:
            self.tabela.horizontalHeader().setState(False, False)

    def _preencher_impressoras(self):
        self.combo_impressoras.clear()
        impressoras = self._lista_impressoras()
        if impressoras:
            self.combo_impressoras.addItems(impressoras)
        else:
            self.combo_impressoras.addItem("Nenhuma impressora encontrada")
            self.combo_impressoras.setEnabled(False)

    def _imprimir_zebra(self):
        impressora = self.combo_impressoras.currentText().strip()
        if not impressora or impressora == "Nenhuma impressora encontrada":
            return
        # Helper: convert millimeters to printer dots (assuming 203 dpi)
        def mm_to_dots(mm, dpi=203):
            return int(mm * dpi / 25.4)

        zpl_jobs = []
        for row in range(self.tabela.rowCount()):
            chk = self.tabela.item(row, 0)
            if chk and chk.checkState() == Qt.CheckState.Checked:
                pedido = self.tabela.item(row, 1).text() if self.tabela.item(row, 1) else ""
                kardex = self.tabela.item(row, 2).text() if self.tabela.item(row, 2) else ""
                codigo = self.tabela.item(row, 3).text() if self.tabela.item(row, 3) else ""
                qtde = self.tabela.item(row, 4).text() if self.tabela.item(row, 4) else ""
                requisitante = self.tabela.item(row, 6).text() if self.tabela.item(row, 6) else ""

                item_interno = _buscar_item_por_kardex(kardex)
                loc_novo = _chave_flexivel(item_interno, "Loc novo") if item_interno else ""
                loc_display = loc_novo or ""

                dpi = 203
                width = mm_to_dots(100, dpi)
                height = mm_to_dots(40, dpi)

                zpl = [
                    "^XA",
                    "^PON",
                    f"^PW{width}",
                    f"^LL{height}",
                    "^LH0,0",
                    f"^FO{mm_to_dots(2, dpi)},{mm_to_dots(2, dpi)}^GB{width - mm_to_dots(4, dpi)},{height - mm_to_dots(4, dpi)},2^FS",
                    f"^FO{mm_to_dots(5, dpi)},{mm_to_dots(5, dpi)}^A0N,40,40^FD{codigo}^FS",
                    f"^FO{mm_to_dots(5, dpi)},{mm_to_dots(12, dpi)}^A0N,30,30^FD{kardex}^FS",
                    f"^FO{mm_to_dots(5, dpi)},{mm_to_dots(20, dpi)}^A0N,25,25^FDPed: {pedido}^FS",
                    f"^FO{mm_to_dots(50, dpi)},{mm_to_dots(20, dpi)}^A0N,25,25^FDReq: {requisitante}^FS",
                    f"^FO{mm_to_dots(5, dpi)},{mm_to_dots(30, dpi)}^A0N,30,30^FDQtde: {qtde}^FS",
                    f"^FO{mm_to_dots(50, dpi)},{mm_to_dots(30, dpi)}^A0N,30,30^FDLOC: {loc_display}^FS",
                    "^PQ1",
                    "^XZ",
                ]
                zpl_jobs.append("\n".join(zpl))

        if not zpl_jobs:
            return

        # Send ZPL to printer using Windows API (pywin32). If not available, prompt user.
        def _send_zpl_to_printer(printer_name, zpl_data):
            try:
                import win32print
                import win32api
            except Exception:
                QMessageBox.warning(self, "Impressão Zebra", "Envio direto de ZPL requer a biblioteca pywin32 (win32print). Instale-a e tente novamente.")
                return False

            try:
                hPrinter = win32print.OpenPrinter(printer_name)
                try:
                    # Start a raw print job
                    hJob = win32print.StartDocPrinter(hPrinter, 1, ("ZPL Print", None, "RAW"))
                    try:
                        win32print.StartPagePrinter(hPrinter)
                        win32print.WritePrinter(hPrinter, zpl_data.encode('utf-8'))
                        win32print.EndPagePrinter(hPrinter)
                    finally:
                        win32print.EndDocPrinter(hPrinter)
                finally:
                    win32print.ClosePrinter(hPrinter)
                return True
            except Exception as e:
                QMessageBox.critical(self, "Erro de Impressão", f"Falha ao enviar ZPL para a impressora: {e}")
                return False

        # Send each ZPL job
        for zpl in zpl_jobs:
            ok = _send_zpl_to_printer(impressora, zpl)
            if not ok:
                break

    def _linha_clicada(self, row, col):
        item_codigo = self.tabela.item(row, 3)
        if not item_codigo:
            return
        codigo = item_codigo.text().strip()
        item = _buscar_item_por_codigo(codigo)
        if item:
            self.label_qtde_novo.setText(_chave_flexivel(item, "Qtde novo", "Qtde Novo", "QTDE NOVO", "qtde_novo", "qtdeNovo", "qtdenovo"))
            self.label_qtde_retorno.setText(_chave_flexivel(item, "Qtde retorno", "Qtde Retorno", "QTDE RETORNO", "qtde_retorno", "qtdeRetorno", "qtderetorno"))
            valor = _chave_flexivel(item, "Consumo médio", "Consumo Medio", "CONSUMO MÉDIO", "CONSUMO MEDIO", "consumo_medio", "consumoMedio")
            try:
                valor = f"{float(valor):.2f}"
            except ValueError:
                pass
            self.label_consumo_medio.setText(valor)
        else:
            self.label_qtde_novo.setText("0")
            self.label_qtde_retorno.setText("0")
            self.label_consumo_medio.setText("0")

    def _salvar_json(self):
        try:
            os.makedirs(os.path.dirname(_caminho_json()), exist_ok=True)
            ativos = [d for d in self.dados if d.get("status") != "Entregue"]
            with open(_caminho_json(), "w", encoding="utf-8") as f:
                json.dump(ativos, f, ensure_ascii=False, indent=2)
        except OSError:
            pass
