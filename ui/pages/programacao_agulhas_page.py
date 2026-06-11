import json
import os
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QStyledItemDelegate, QStyleOptionViewItem,
    QStyle,
)
from PySide6.QtCore import Qt, QSize, QSizeF, QRect, Signal
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
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(16)

        card = QWidget()
        card.setObjectName("pageCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(28, 28, 28, 28)
        card_layout.setSpacing(16)

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
        self.campo_filtro.setFixedWidth(200)
        self.campo_filtro.textChanged.connect(self._aplicar_filtro)
        linha_top.addWidget(self.campo_filtro)

        linha_top.addStretch()

        self.btn_mover_programado = QPushButton("Mover para Programado")
        self.btn_mover_programado.setObjectName("btnPrimary")
        self.btn_mover_programado.setFixedHeight(30)
        self.btn_mover_programado.clicked.connect(self._mover_programado)
        self.btn_mover_separando = QPushButton("Mover para Separando")
        self.btn_mover_separando.setObjectName("btnPrimary")
        self.btn_mover_separando.setFixedHeight(30)
        self.btn_mover_separando.clicked.connect(self._mover_separando)
        self.btn_entregar = QPushButton("Entregar")
        self.btn_entregar.setObjectName("btnPrimary")
        self.btn_entregar.setFixedHeight(30)
        self.btn_entregar.clicked.connect(self._entregar)

        self.combo_impressoras = QComboBox()
        self.combo_impressoras.setFixedHeight(30)
        self.combo_impressoras.setFixedWidth(220)
        self.combo_impressoras.setToolTip("Selecione a impressora Zebra para impressão")
        self.combo_impressoras.setVisible(False)

        self.btn_imprimir = QPushButton("Imprimir")
        self.btn_imprimir.setObjectName("btnPrimary")
        self.btn_imprimir.setFixedHeight(30)
        self.btn_imprimir.clicked.connect(self._imprimir_zebra)
        self.btn_imprimir.setVisible(False)

        linha_top.addWidget(self.btn_mover_programado)
        linha_top.addWidget(self.btn_mover_separando)
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
        self.tabela.verticalHeader().setDefaultSectionSize(36)
        self.tabela.verticalHeader().setMinimumSectionSize(28)
        self.tabela.verticalHeader().setVisible(False)
        self.tabela.setItemDelegate(EditorDelegate(self.tabela))
        self.tabela.itemChanged.connect(self._item_modificado)
        self.tabela.cellClicked.connect(self._linha_clicada)
        card_layout.addWidget(self.tabela)

        self._preencher_impressoras()
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
        dados_filtrados = []
        for item in self.dados:
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
            dados_filtrados.append(item)

        for item in dados_filtrados:
            row = self.tabela.rowCount()
            self.tabela.insertRow(row)

            chk = QTableWidgetItem()
            chk.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            chk.setCheckState(Qt.CheckState.Unchecked if not item.get("selecionado") else Qt.CheckState.Checked)
            self.tabela.setItem(row, 0, chk)

            for col, chave in enumerate(["pedido", "kardex", "codigo", "qtde", "fornecedor", "requisitante"], 1):
                valor = str(item.get(chave, ""))
                cell = QTableWidgetItem(valor)
                cell.setFlags(cell.flags() | Qt.ItemFlag.ItemIsEditable)
                self.tabela.setItem(row, col, cell)

            chave_data = self.campo_data_por_filtro.get(self.filtro_status, "status")
            valor_data = str(item.get(chave_data, ""))
            cell_data = QTableWidgetItem(valor_data)
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
        self.combo_impressoras.setVisible(False)
        self.btn_imprimir.setVisible(False)
        if self.filtro_status == "Pendentes":
            self.btn_mover_programado.setVisible(True)
            self.btn_mover_separando.setVisible(True)
        elif self.filtro_status == "Programados":
            self.btn_mover_separando.setVisible(True)
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

    def _filtrar_por_status(self, status):
        for s, btn in self.botoes_status.items():
            btn.setChecked(s == status)
        self.filtro_status = status
        self._popular_tabela()

    def _aplicar_filtro(self):
        self._popular_tabela()
        self._atualizar_botoes_acao()

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
            with open(_caminho_json(), "w", encoding="utf-8") as f:
                json.dump(self.dados, f, ensure_ascii=False, indent=2)
        except OSError:
            pass
