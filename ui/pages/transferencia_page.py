import json
import os

import pyautogui
import qtawesome
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QRadioButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QButtonGroup, QMessageBox, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt
from ui.regras_automacao import esperar_inicio, digitar_texto, enter


def _caminho_json():
    import config
    base = config.obter_caminho_jsons()
    if not base:
        return ""
    return os.path.normpath(os.path.join(base, "Almox", "Transferencias", "transferencias.json"))


class TransferenciaPage(QWidget):
    def __init__(self):
        super().__init__()
        self.dados = []
        self._setup_ui()
        self._carregar_dados()

    def showEvent(self, event):
        super().showEvent(event)
        self._garantir_linha_vazia()

    # ── UI ──────────────────────────────────────────────────────────────
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        card = QWidget()
        card.setObjectName("pageCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(12, 12, 12, 12)
        card_layout.setSpacing(8)

        # ── Header ──
        header_layout = QHBoxLayout()
        header_texts = QVBoxLayout()
        header_texts.setSpacing(4)
        titulo = QLabel("Transferência de itens")
        titulo.setObjectName("pageTitle")
        header_texts.addWidget(titulo)
        subtitulo = QLabel("Movimentação entre locais, lugares e lotes — cole da planilha e execute")
        subtitulo.setObjectName("pageSubtitle")
        header_texts.addWidget(subtitulo)
        header_layout.addLayout(header_texts)
        header_layout.addStretch()
        
        card_layout.addLayout(header_layout)

        # ── Conteúdo principal: coluna esquerda (formulário) + coluna direita (tabela) ──
        main_content = QHBoxLayout()
        main_content.setSpacing(16)

        # Helper — campo apenas com placeholder (sem título)
        def _campo(placeholder, valor_padrao="", enabled=True):
            edit = QLineEdit(valor_padrao)
            edit.setPlaceholderText(placeholder)
            edit.setFixedHeight(34)
            edit.setEnabled(enabled)
            edit.setMinimumWidth(100)
            return edit

        # ── Coluna Esquerda: origem → destino → modo → botões ──
        left_widget = QWidget()
        left_widget.setFixedWidth(320)
        left_widget.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)

        # Origem box — sem seta entre os quadros
        origem_box = QWidget()
        origem_box.setObjectName("detalhesBox")
        origem_layout = QVBoxLayout(origem_box)
        origem_layout.setContentsMargins(14, 12, 14, 12)
        origem_layout.setSpacing(8)
        origem_titulo = QLabel("ORIGEM")
        origem_titulo.setObjectName("fieldLabel")
        origem_titulo.setStyleSheet("color:#6366f1; font-weight:700; letter-spacing:0.6px;")
        origem_layout.addWidget(origem_titulo)

        self.campo_de_local = _campo("De local", "10912")
        self.campo_de_lugar = _campo("De lugar", "ZCENTRAL")
        self.campo_de_lote = _campo("De lote", "")
        for campo in (self.campo_de_local, self.campo_de_lugar, self.campo_de_lote):
            origem_layout.addWidget(campo)

        # Destino box — abaixo do de origem (sem seta)
        destino_box = QWidget()
        destino_box.setObjectName("detalhesBox")
        destino_layout = QVBoxLayout(destino_box)
        destino_layout.setContentsMargins(14, 12, 14, 12)
        destino_layout.setSpacing(8)
        destino_titulo = QLabel("DESTINO")
        destino_titulo.setObjectName("fieldLabel")
        destino_titulo.setStyleSheet("color:#10b981; font-weight:700; letter-spacing:0.6px;")
        destino_layout.addWidget(destino_titulo)

        self.campo_para_local = _campo("Para local", "10912")
        self.campo_para_lugar = _campo("Para lugar", "ZCENTRAL")
        self.campo_para_lote = _campo("Para lote", "")
        for campo in (self.campo_para_local, self.campo_para_lugar, self.campo_para_lote):
            destino_layout.addWidget(campo)

        # Adiciona origem e destino lado a lado (origem à esquerda, destino à direita)
        origem_destino_row = QHBoxLayout()
        origem_destino_row.setSpacing(12)
        origem_destino_row.addWidget(origem_box)
        origem_destino_row.addWidget(destino_box)
        left_layout.addLayout(origem_destino_row)

        # Modo box — abaixo do destino
        modo_box = QWidget()
        modo_box.setObjectName("detalhesBox")
        modo_box_layout = QVBoxLayout(modo_box)
        modo_box_layout.setContentsMargins(14, 12, 14, 12)
        modo_box_layout.setSpacing(8)
        modo_label = QLabel("MODO DE LOTE")
        modo_label.setObjectName("fieldLabel")
        modo_label.setStyleSheet("color:#64748b;")
        modo_box_layout.addWidget(modo_label)

        self.grupo_radio = QButtonGroup(self)
        self.radio_formulario = QRadioButton("Usar formulário")
        self.radio_lote_inicial = QRadioButton("Usar lote como origem")
        self.radio_lote_destino = QRadioButton("Usar lote como destino")
        self.radio_formulario.setChecked(True)
        self.radio_formulario.setToolTip("Usa os lotes digitados nos campos acima")
        self.radio_lote_inicial.setToolTip("Usa o lote da coluna da tabela como origem")
        self.radio_lote_destino.setToolTip("Usa o lote da coluna da tabela como destino")
        for rb in (self.radio_formulario, self.radio_lote_inicial, self.radio_lote_destino):
            self.grupo_radio.addButton(rb)
            rb.setCursor(Qt.CursorShape.PointingHandCursor)
            modo_box_layout.addWidget(rb)
        left_layout.addWidget(modo_box)

        # Três botões abaixo do modo — coluna esquerda
        self.btn_colar = QPushButton(qtawesome.icon('fa6s.paste', color='#6b7280'), "  Colar da área de transferência")
        self.btn_colar.setObjectName("btnSecondary")
        self.btn_colar.setFixedHeight(36)
        self.btn_colar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_colar.setToolTip("Cola linhas tab-separated (Item \\t Qtde \\t Lote) da área de transferência")
        self.btn_colar.clicked.connect(self._colar)
        left_layout.addWidget(self.btn_colar)

        self.btn_executar = QPushButton(qtawesome.icon('fa6s.play', color='#ffffff'), "  Executar automação")
        self.btn_executar.setObjectName("btnPrimary")
        self.btn_executar.setFixedHeight(36)
        self.btn_executar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_executar.setToolTip("Inicia a automação no sistema (pyautogui)")
        self.btn_executar.clicked.connect(self._executar)
        left_layout.addWidget(self.btn_executar)

        self.btn_limpar = QPushButton(qtawesome.icon('fa6s.broom', color='#ffffff'), "  Limpar tabela")
        self.btn_limpar.setObjectName("btnGradientRose")
        self.btn_limpar.setFixedHeight(36)
        self.btn_limpar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_limpar.setToolTip("Remove todos os itens da tabela")
        self.btn_limpar.clicked.connect(self._limpar)
        left_layout.addWidget(self.btn_limpar)

        left_layout.addStretch()
        main_content.addWidget(left_widget, 0)

        # ── Coluna Direita: tabela ocupando altura total do quadro ──
        right_widget = QWidget()
        right_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)

        # Linha contador + ações da tabela
        info_linha = QHBoxLayout()
        info_linha.setSpacing(8)
        contador_wrap = QHBoxLayout()
        contador_wrap.setSpacing(6)
        try:
            icon_lbl = QLabel()
            icon_lbl.setPixmap(qtawesome.icon('fa6s.list', color='#94a3b8').pixmap(14, 14))
            contador_wrap.addWidget(icon_lbl)
        except Exception:
            pass
        self.label_contador = QLabel("0 itens")
        self.label_contador.setObjectName("statusLabel")
        contador_wrap.addWidget(self.label_contador)
        info_linha.addLayout(contador_wrap)
        info_linha.addStretch()
        self.btn_remover_sel = QPushButton(qtawesome.icon('fa6s.trash-can', color='#64748b'), "  Remover selecionados")
        self.btn_remover_sel.setObjectName("btnGhost")
        self.btn_remover_sel.setFixedHeight(30)
        self.btn_remover_sel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_remover_sel.setToolTip("Remove as linhas selecionadas")
        self.btn_remover_sel.clicked.connect(self._remover_selecionados)
        info_linha.addWidget(self.btn_remover_sel)
        right_layout.addLayout(info_linha)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Plain)
        sep.setStyleSheet("color:#f1f5f9; background-color:#f1f5f9; max-height:1px;")
        sep.setFixedHeight(1)
        right_layout.addWidget(sep)

        self.tabela = QTableWidget(0, 3)
        self.tabela.setObjectName("tabelaTransferencia")
        self.tabela.setStyleSheet("""
            QTableWidget#tabelaTransferencia {
                background-color: #ffffff;
                border: 1px solid #eef1f6;
                border-radius: 12px;
                gridline-color: transparent;
                selection-background-color: #eef2ff;
                selection-color: #1e1b4b;
                font-size: 13px;
                outline: none;
            }
            QTableWidget#tabelaTransferencia::item {
                border-bottom: 1px solid #f3f4f6;
            }
            QTableWidget#tabelaTransferencia::item:selected {
                background-color: #eef2ff;
                color: #1e1b4b;
            }
            QTableWidget#tabelaTransferencia::item:hover {
                background-color: #f5f3ff;
            }
            QTableWidget#tabelaTransferencia QLineEdit {
                padding: 0px;
                margin: 0px;
                border: none;
            }
        """)
        self.tabela.setHorizontalHeaderLabels(["Item", "Qtde", "Lote"])
        header = self.tabela.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(1, 90)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(2, 160)
        self.tabela.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabela.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.tabela.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked |
            QAbstractItemView.EditTrigger.SelectedClicked |
            QAbstractItemView.EditTrigger.EditKeyPressed |
            QAbstractItemView.EditTrigger.AnyKeyPressed
        )
        self.tabela.setAlternatingRowColors(True)
        self.tabela.verticalHeader().setDefaultSectionSize(32)
        self.tabela.verticalHeader().setMinimumSectionSize(26)
        self.tabela.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.tabela.verticalHeader().setVisible(False)
        self.tabela.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        # altura total do quadro — ocupa espaço restante
        right_layout.addWidget(self.tabela, 1)

        hint = QLabel("Dica: preencha diretamente na tabela (uma linha vazia sempre fica disponível) ou copie 3 colunas da planilha e use \"Colar\"")
        hint.setStyleSheet("color:#94a3b8; font-size:11px; padding-left:2px;")
        hint.setWordWrap(True)
        right_layout.addWidget(hint)

        main_content.addWidget(right_widget, 1)
        main_content.addStretch(1)
        card_layout.addLayout(main_content)
        layout.addWidget(card)

        # Conexões
        self.radio_formulario.toggled.connect(self._atualizar_bloqueio_lotes)
        self.radio_lote_inicial.toggled.connect(self._atualizar_bloqueio_lotes)
        self.radio_lote_destino.toggled.connect(self._atualizar_bloqueio_lotes)
        self.tabela.itemSelectionChanged.connect(self._atualizar_estado_botoes)
        self.tabela.itemChanged.connect(self._ao_editar_item)
        self._atualizar_bloqueio_lotes()
        self._atualizar_estado_botoes()

        try:
            from PySide6.QtGui import QShortcut, QKeySequence
            QShortcut(QKeySequence("Ctrl+V"), self, self._colar)
        except Exception:
            pass

    def _atualizar_bloqueio_lotes(self):
        if self.radio_lote_inicial.isChecked():
            self.campo_de_lote.setEnabled(False)
            self.campo_para_lote.setEnabled(True)
            self.campo_de_lote.setToolTip("Desativado — lote virá da tabela")
            self.campo_para_lote.setToolTip("")
        elif self.radio_lote_destino.isChecked():
            self.campo_para_lote.setEnabled(False)
            self.campo_de_lote.setEnabled(True)
            self.campo_para_lote.setToolTip("Desativado — lote virá da tabela")
            self.campo_de_lote.setToolTip("")
        else:
            self.campo_de_lote.setEnabled(True)
            self.campo_para_lote.setEnabled(True)
            self.campo_de_lote.setToolTip("")
            self.campo_para_lote.setToolTip("")

    def _atualizar_estado_botoes(self):
        tem_sel = bool(self.tabela.selectionModel().selectedRows())
        self.btn_remover_sel.setEnabled(tem_sel)
        self.btn_executar.setEnabled(len(self.dados) > 0)

    # ── Dados ─────────────────────────────────────────────────────────
    def _carregar_dados(self):
        try:
            with open(_caminho_json(), "r", encoding="utf-8") as f:
                brutos = json.load(f)
                if isinstance(brutos, list):
                    self.dados = [
                        d for d in brutos
                        if isinstance(d, dict) and (
                            str(d.get("item", "")).strip() or
                            str(d.get("qtde", "")).strip() or
                            str(d.get("lote", "")).strip()
                        )
                    ]
                else:
                    self.dados = []
        except (FileNotFoundError, json.JSONDecodeError):
            self.dados = []
        self._popular_tabela()

    def _inserir_linha_vazia(self, row):
        self.tabela.blockSignals(True)
        self.tabela.insertRow(row)

        it_item = QTableWidgetItem("")
        self.tabela.setItem(row, 0, it_item)

        it_qtde = QTableWidgetItem("")
        it_qtde.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.tabela.setItem(row, 1, it_qtde)

        it_lote = QTableWidgetItem("")
        it_lote.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.tabela.setItem(row, 2, it_lote)
        self.tabela.blockSignals(False)

    def _garantir_linha_vazia(self):
        total_linhas = self.tabela.rowCount()
        if total_linhas == 0:
            self._inserir_linha_vazia(0)
            return

        ultima_row = total_linhas - 1
        it_ult = self.tabela.item(ultima_row, 0).text().strip() if self.tabela.item(ultima_row, 0) else ""
        qt_ult = self.tabela.item(ultima_row, 1).text().strip() if self.tabela.item(ultima_row, 1) else ""
        lo_ult = self.tabela.item(ultima_row, 2).text().strip() if self.tabela.item(ultima_row, 2) else ""

        if it_ult or qt_ult or lo_ult:
            # A última linha foi preenchida! Adiciona nova linha vazia no fim
            self._inserir_linha_vazia(total_linhas)
        else:
            # Se a última linha já é vazia e a penúltima também for vazia, remove a excedente
            while self.tabela.rowCount() > 1:
                tot = self.tabela.rowCount()
                u_row = tot - 1
                pen_row = tot - 2

                u_it = self.tabela.item(u_row, 0).text().strip() if self.tabela.item(u_row, 0) else ""
                u_qt = self.tabela.item(u_row, 1).text().strip() if self.tabela.item(u_row, 1) else ""
                u_lo = self.tabela.item(u_row, 2).text().strip() if self.tabela.item(u_row, 2) else ""

                p_it = self.tabela.item(pen_row, 0).text().strip() if self.tabela.item(pen_row, 0) else ""
                p_qt = self.tabela.item(pen_row, 1).text().strip() if self.tabela.item(pen_row, 1) else ""
                p_lo = self.tabela.item(pen_row, 2).text().strip() if self.tabela.item(pen_row, 2) else ""

                if not (u_it or u_qt or u_lo) and not (p_it or p_qt or p_lo):
                    curr = self.tabela.currentRow()
                    self.tabela.blockSignals(True)
                    if curr == u_row:
                        self.tabela.removeRow(pen_row)
                    else:
                        self.tabela.removeRow(u_row)
                    self.tabela.blockSignals(False)
                else:
                    break

    def _sincronizar_dados_da_tabela(self):
        novos_dados = []
        for r in range(self.tabela.rowCount()):
            it = self.tabela.item(r, 0).text().strip().upper() if self.tabela.item(r, 0) else ""
            qt = self.tabela.item(r, 1).text().strip() if self.tabela.item(r, 1) else ""
            lo = self.tabela.item(r, 2).text().strip().upper() if self.tabela.item(r, 2) else ""
            if it or qt or lo:
                novos_dados.append({"item": it, "qtde": qt, "lote": lo})
        self.dados = novos_dados
        self._salvar_json()
        self._atualizar_contador()
        self._atualizar_estado_botoes()

    def _popular_tabela(self):
        self.tabela.blockSignals(True)
        self.tabela.setRowCount(0)
        for registro in self.dados:
            item_val = str(registro.get("item", "")).strip().upper()
            qtde_val = str(registro.get("qtde", "")).strip()
            lote_val = str(registro.get("lote", "")).strip().upper()
            if not (item_val or qtde_val or lote_val):
                continue

            row = self.tabela.rowCount()
            self.tabela.insertRow(row)

            it_item = QTableWidgetItem(item_val)
            it_item.setToolTip(item_val)
            self.tabela.setItem(row, 0, it_item)

            it_qtde = QTableWidgetItem(qtde_val)
            it_qtde.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tabela.setItem(row, 1, it_qtde)

            it_lote = QTableWidgetItem(lote_val)
            it_lote.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tabela.setItem(row, 2, it_lote)

        self.tabela.blockSignals(False)
        self._garantir_linha_vazia()
        self._atualizar_contador()
        self._atualizar_estado_botoes()
        if len(self.dados) == 0:
            self.tabela.setToolTip("Digite os dados diretamente na tabela ou cole da planilha")
        else:
            self.tabela.setToolTip("")

    def _ao_editar_item(self, item):
        if not item:
            return
        row = item.row()
        col = item.column()
        texto = item.text().strip()
        if col in (0, 2):
            texto = texto.upper()

        if item.text() != texto:
            self.tabela.blockSignals(True)
            item.setText(texto)
            if col == 0:
                item.setToolTip(texto)
            self.tabela.blockSignals(False)

        self._sincronizar_dados_da_tabela()
        self._garantir_linha_vazia()

    def _atualizar_contador(self):
        n = len(self.dados)
        if n == 1:
            self.label_contador.setText("1 item")
        else:
            self.label_contador.setText(f"{n} itens")

    def _colar(self):
        focus_w = QApplication.focusWidget()
        campos_form = (
            self.campo_de_local, self.campo_de_lugar, self.campo_de_lote,
            self.campo_para_local, self.campo_para_lugar, self.campo_para_lote
        )
        if isinstance(focus_w, QLineEdit) and focus_w not in campos_form:
            focus_w.paste()
            return

        from PySide6.QtGui import QGuiApplication
        texto = QGuiApplication.clipboard().text()
        if not texto or not texto.strip():
            QMessageBox.information(self, "Colar", "Área de transferência vazia.")
            return
        linhas = texto.strip().splitlines()
        if not linhas:
            return
        novos = 0
        for linha in linhas:
            if not linha.strip():
                continue
            partes = [p.strip() for p in linha.split("\t")]
            if len(partes) < 2 and "  " in linha:
                partes = [p.strip() for p in linha.split() if p.strip()]
            partes = [p for p in partes if p != ""]
            if not partes:
                continue
            item = partes[0].upper() if len(partes) > 0 else ""
            qtde = partes[1] if len(partes) > 1 else ""
            lote = partes[2].upper() if len(partes) > 2 else ""
            if not item:
                continue
            self.dados.append({"item": item, "qtde": qtde, "lote": lote})
            novos += 1
        if novos == 0:
            QMessageBox.warning(self, "Colar", "Nenhum item válido encontrado. Copie no formato: Item [TAB] Qtde [TAB] Lote")
            return
        self._salvar_json()
        self._popular_tabela()
        self.label_contador.setText(f"{len(self.dados)} itens  •  +{novos} colados")

    def _remover_selecionados(self):
        sel = self.tabela.selectionModel().selectedRows()
        if not sel:
            return
        rows = sorted(set(i.row() for i in sel), reverse=True)
        self.tabela.blockSignals(True)
        for r in rows:
            if 0 <= r < self.tabela.rowCount():
                self.tabela.removeRow(r)
        self.tabela.blockSignals(False)
        self._sincronizar_dados_da_tabela()
        self._garantir_linha_vazia()

    def _executar(self):
        linhas_execucao = []
        for row in range(self.tabela.rowCount()):
            it = self.tabela.item(row, 0)
            qt = self.tabela.item(row, 1)
            lo = self.tabela.item(row, 2)
            kardex = it.text().strip().upper() if it else ""
            qtde = qt.text().strip().upper() if qt else ""
            lote_tabela = lo.text().strip().upper() if lo else ""
            if kardex or qtde or lote_tabela:
                linhas_execucao.append((kardex, qtde, lote_tabela))

        if not linhas_execucao:
            QMessageBox.information(self, "Executar", "Nenhum item na tabela.")
            return

        de_local = self.campo_de_local.text().strip().upper()
        de_lugar = self.campo_de_lugar.text().strip().upper()
        de_lote = self.campo_de_lote.text().strip().upper()
        para_local = self.campo_para_local.text().strip().upper()
        para_lugar = self.campo_para_lugar.text().strip().upper()
        para_lote = self.campo_para_lote.text().strip().upper()
        if not de_local or not de_lugar or not para_local or not para_lugar:
            QMessageBox.warning(self, "Executar", "Preencha De local/lugar e Para local/lugar.")
            return
        if self.radio_formulario.isChecked() and (not de_lote or not para_lote):
            pass  # Prossegue diretamente mesmo se vazio
        
        esperar_inicio()
        for kardex, qtde, lote_tabela in linhas_execucao:
            digitar_texto(kardex)
            enter()
            digitar_texto(qtde)
            enter(5)
            digitar_texto("TRANSFI")
            enter(2)
            digitar_texto(de_local)
            enter()
            digitar_texto(de_lugar)
            enter()
            if self.radio_formulario.isChecked():
                digitar_texto(de_lote)
                enter(2)
                digitar_texto(para_local)
                enter()
                digitar_texto(para_lugar)
                enter()
                digitar_texto(para_lote)
                enter(3)
            elif self.radio_lote_inicial.isChecked():
                digitar_texto(lote_tabela)
                enter(2)
                digitar_texto(para_local)
                enter()
                digitar_texto(para_lugar)
                enter()
                digitar_texto(para_lote)
                enter(3)
            elif self.radio_lote_destino.isChecked():
                digitar_texto(de_lote)
                enter(2)
                digitar_texto(para_local)
                enter()
                digitar_texto(para_lugar)
                enter()
                digitar_texto(lote_tabela)
                enter(3)
            
            if de_local == "10012" and para_local == "10912":
                enter()
                
            pyautogui.press("f4")

    def _limpar(self):
        if len(self.dados) == 0 and self.tabela.rowCount() <= 1:
            return
        
        self.dados.clear()
        self._salvar_json()
        self._popular_tabela()

    def _limpar_campos(self):
        self.campo_de_local.clear()
        self.campo_de_lugar.clear()
        self.campo_de_lote.clear()
        self.campo_para_local.clear()
        self.campo_para_lugar.clear()
        self.campo_para_lote.clear()

    def _salvar_json(self):
        caminho = _caminho_json()
        if not caminho:
            import config
            config.avisar_sem_pasta(self)
            return
        try:
            os.makedirs(os.path.dirname(caminho), exist_ok=True)
            dados_para_salvar = [
                d for d in self.dados
                if str(d.get("item", "")).strip() or
                   str(d.get("qtde", "")).strip() or
                   str(d.get("lote", "")).strip()
            ]
            with open(caminho, "w", encoding="utf-8") as f:
                json.dump(dados_para_salvar, f, ensure_ascii=False, indent=2)
        except OSError:
            pass
