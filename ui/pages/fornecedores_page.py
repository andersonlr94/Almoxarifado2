import json
import os
import re
from datetime import datetime

import qtawesome

from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QStyledItemDelegate, QInputDialog, QMessageBox
)
from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtGui import QColor, QBrush, QShortcut, QKeySequence


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class EditorDelegate(QStyledItemDelegate):
    def __init__(self, parent=None, edit_mode_getter=None):
        super().__init__(parent)
        self._edit_mode_getter = edit_mode_getter or (lambda: False)

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
        # Bloqueia edição se não estiver em modo edição
        if not self._edit_mode_getter():
            return None
        editor = super().createEditor(parent, option, index)
        try:
            from PySide6.QtWidgets import QLineEdit
            if isinstance(editor, QLineEdit):
                editor.setFixedHeight(option.rect.height() - 6)
                editor.setMaximumWidth(option.rect.width())
                editor.setContentsMargins(0, 0, 0, 0)
                editor.setStyleSheet(
                    "padding: 0px; margin: 0px; border: none; "
                    "border-bottom: 2px solid #6366f1; border-radius: 0px;"
                )
        except Exception:
            pass
        return editor


def _caminho_json():
    import config
    base = config.obter_caminho_jsons()
    if not base:
        return ""
    return os.path.normpath(os.path.join(base, "Almox", "Fornecedores", "fornecedores.json"))


class FornecedoresPage(QWidget):
    COLUNAS = ["Índice", "Fornecedor", "Email", "Telefone", "DUNS"]
    CHAVES = ["indice", "fornecedor", "email", "telefone", "duns"]

    def __init__(self):
        super().__init__()
        self.dados = []
        self._edit_mode = False  # edição só quando clicar em Editar
        self._setup_ui()
        self._setup_search_shortcuts()
        self._carregar_dados()

    # ── UI ────────────────────────────────────────────────────────────────
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Header
        header_layout = QHBoxLayout()
        header_texts = QVBoxLayout()
        header_texts.setSpacing(4)
        titulo = QLabel("Fornecedores")
        titulo.setObjectName("pageTitle")
        header_texts.addWidget(titulo)
        subtitulo = QLabel("Cadastro e gestão de fornecedores para pedidos e contatos")
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

        # Linha de ações + filtro
        linha_top = QHBoxLayout()
        linha_top.setSpacing(8)

        self.btn_adicionar = QPushButton(qtawesome.icon('fa6s.plus', color='#ffffff'), "  Adicionar")
        self.btn_adicionar.setObjectName("btnPrimary")
        self.btn_adicionar.setFixedHeight(34)
        self.btn_adicionar.setToolTip("Adicionar novo fornecedor (foca na última linha)")
        self.btn_adicionar.clicked.connect(self._adicionar_linha)
        linha_top.addWidget(self.btn_adicionar)

        self.btn_editar = QPushButton(qtawesome.icon('fa6s.pencil', color='#6b7280'), "  Editar")
        self.btn_editar.setObjectName("btnEditMode")
        self.btn_editar.setFixedHeight(34)
        self.btn_editar.setCheckable(True)
        self.btn_editar.setToolTip("Ativar/desativar modo edição — só edita quando ativado")
        self.btn_editar.clicked.connect(self._toggle_edicao)
        linha_top.addWidget(self.btn_editar)

        self.btn_excluir = QPushButton(qtawesome.icon('fa6s.trash', color='#ffffff'), "  Excluir")
        self.btn_excluir.setObjectName("btnGradientRose")
        self.btn_excluir.setFixedHeight(34)
        self.btn_excluir.setToolTip("Excluir fornecedor selecionado")
        self.btn_excluir.clicked.connect(self._remover_linha)
        linha_top.addWidget(self.btn_excluir)

        linha_top.addStretch()

        self.campo_busca = QLineEdit()
        self.campo_busca.setPlaceholderText("Pesquisar por nome, email, telefone ou DUNS...")
        self.campo_busca.setFixedHeight(32)
        self.campo_busca.setFixedWidth(260)
        self.campo_busca.textChanged.connect(self._aplicar_filtro)
        linha_top.addWidget(self.campo_busca)

        self.btn_limpar_filtro = QPushButton(qtawesome.icon('fa6s.xmark', color='#64748b'), "")
        self.btn_limpar_filtro.setObjectName("btnGhost")
        self.btn_limpar_filtro.setFixedSize(32, 32)
        self.btn_limpar_filtro.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_limpar_filtro.setToolTip("Limpar filtro (Esc)")
        self.btn_limpar_filtro.clicked.connect(self.campo_busca.clear)
        linha_top.addWidget(self.btn_limpar_filtro)

        self.label_contador = QLabel("0 fornecedores")
        self.label_contador.setObjectName("statusLabel")
        self.label_contador.setMinimumWidth(110)
        self.label_contador.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        linha_top.addWidget(self.label_contador)

        card_layout.addLayout(linha_top)

        # Tabela
        self.tabela = QTableWidget(0, len(self.COLUNAS))
        self.tabela.setObjectName("tabelaFornecedores")
        self.tabela.setStyleSheet("""
            QTableWidget#tabelaFornecedores {
                background-color: #ffffff;
                border: 1px solid #eef1f6;
                border-radius: 12px;
                gridline-color: transparent;
                selection-background-color: #eef2ff;
                selection-color: #1e1b4b;
                font-size: 13px;
                outline: none;
            }
            QTableWidget#tabelaFornecedores::item {
                padding: 4px 10px;
                border-bottom: 1px solid #f3f4f6;
            }
            QTableWidget#tabelaFornecedores::item:selected {
                background-color: #eef2ff;
                color: #1e1b4b;
            }
            QTableWidget#tabelaFornecedores::item:hover {
                background-color: #f5f3ff;
            }
            QTableWidget#tabelaFornecedores::item:focus {
                outline: none;
                border: 1.5px solid #6366f1;
                border-radius: 4px;
            }
        """)
        self.tabela.setHorizontalHeaderLabels(self.COLUNAS)
        header = self.tabela.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(0, 70)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(2, 240)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(3, 140)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(4, 110)

        self.tabela.setColumnHidden(0, True)

        self.tabela.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabela.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.tabela.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked | QAbstractItemView.EditTrigger.EditKeyPressed)
        self.tabela.setAlternatingRowColors(True)
        self.tabela.verticalHeader().setDefaultSectionSize(32)
        self.tabela.verticalHeader().setMinimumSectionSize(26)
        self.tabela.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.tabela.verticalHeader().setVisible(False)
        self.tabela.setItemDelegate(EditorDelegate(self.tabela, edit_mode_getter=lambda: self._edit_mode))
        self.tabela.itemChanged.connect(self._item_modificado)
        self.tabela.itemSelectionChanged.connect(self._atualizar_estado_botoes)
        self.tabela.setSortingEnabled(False)

        # duplo clique também inicia edição correta (col 1 se col 0 estiver oculta)
        self.tabela.cellDoubleClicked.connect(self._on_cell_double_clicked)

        card_layout.addWidget(self.tabela)
        layout.addWidget(card)

        self._atualizar_estado_botoes()

    def _setup_search_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+F"), self, self._buscar_item)
        QShortcut(QKeySequence("Ctrl+L"), self, self._buscar_item)
        QShortcut(QKeySequence("Ctrl+C"), self.tabela, self._copiar_selecao)
        # Esc limpa filtro quando campo tem foco
        sc_esc = QShortcut(QKeySequence("Escape"), self)
        sc_esc.activated.connect(self._esc_limpar_filtro)

    # ── Dados ─────────────────────────────────────────────────────────────
    def _carregar_dados(self):
        try:
            with open(_caminho_json(), "r", encoding="utf-8") as f:
                self.dados = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.dados = []
        # normaliza chaves ausentes e ordena
        for item in self.dados:
            for ch in self.CHAVES:
                item.setdefault(ch, "")
        self._ordenar_dados()
        self._popular_tabela()

    def _ordenar_dados(self):
        self.dados.sort(key=lambda x: x.get("fornecedor", "").strip().lower())

    def _aplicar_filtro(self):
        self._popular_tabela()

    def _popular_tabela(self):
        # preserva scroll / foco / seleção
        busca_focada = self.campo_busca.hasFocus()
        v_scroll = self.tabela.verticalScrollBar().value()
        h_scroll = self.tabela.horizontalScrollBar().value()
        curr_row = self.tabela.currentRow()
        curr_col = self.tabela.currentColumn()

        self.tabela.blockSignals(True)
        self.tabela.setRowCount(0)
        filtro = self.campo_busca.text().strip().lower()
        exibidos = 0
        for item in self.dados:
            if filtro:
                texto = " ".join(str(v) for v in item.values()).lower()
                if filtro not in texto:
                    continue
            row = self.tabela.rowCount()
            self.tabela.insertRow(row)
            for col, chave in enumerate(self.CHAVES):
                valor = str(item.get(chave, ""))
                cell = QTableWidgetItem(valor)
                if col == 0:
                    cell.setFlags(cell.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                else:
                    # Só editável em modo edição
                    if self._edit_mode:
                        cell.setFlags(cell.flags() | Qt.ItemFlag.ItemIsEditable)
                    else:
                        cell.setFlags(cell.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    if chave == "fornecedor":
                        cell.setToolTip(valor)
                    elif chave == "email" and valor and not EMAIL_RE.match(valor):
                        cell.setData(Qt.BackgroundRole, QBrush(QColor("#fef2f2")))
                        cell.setToolTip("Email em formato inválido")
                    elif chave == "email" and not valor:
                        cell.setToolTip("Sem email cadastrado")
                self.tabela.setItem(row, col, cell)
            # guarda referência ao índice real (mesma row, pois sem filtro extra)
            # para manter compatível com remoção por linha: usamos row direto quando sem filtro
            # mas quando filtrado, precisamos mapear. Guardamos o índice original em UserRole da col 0
            # Encontra índice real no self.dados (pode ser duplicado? usamos identidade por índice)
            # Busca linear pelo objeto
            try:
                idx_real = self.dados.index(item)
            except ValueError:
                idx_real = row
            c0 = self.tabela.item(row, 0)
            if c0:
                c0.setData(Qt.ItemDataRole.UserRole, idx_real)
            exibidos += 1

        self._inserir_linha_vazia()
        self.tabela.blockSignals(False)
        self._atualizar_contador(exibidos)

        # restaura seleção/foco se possível
        if not busca_focada and curr_row >= 0 and curr_row < self.tabela.rowCount() and curr_col >= 0:
            self.tabela.setCurrentCell(curr_row, curr_col)
        if busca_focada:
            self.campo_busca.setFocus()
        self.tabela.verticalScrollBar().setValue(v_scroll)
        self.tabela.horizontalScrollBar().setValue(h_scroll)
        self._atualizar_estado_botoes()

    def _inserir_linha_vazia(self):
        row = self.tabela.rowCount()
        self.tabela.insertRow(row)
        for col in range(len(self.COLUNAS)):
            # placeholder mais amigável na coluna Fornecedor
            if col == 1:
                cell = QTableWidgetItem("")
                if self._edit_mode:
                    cell.setFlags(cell.flags() | Qt.ItemFlag.ItemIsEditable)
                    cell.setToolTip("Digite para adicionar novo fornecedor...")
                else:
                    cell.setFlags(cell.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    cell.setToolTip("Ative o modo edição para adicionar fornecedores")
                cell.setData(Qt.ForegroundRole, QBrush(QColor("#94a3b8")))
            else:
                cell = QTableWidgetItem("")
                if col == 0:
                    cell.setFlags(cell.flags() & ~Qt.ItemFlag.ItemIsEditable)
                else:
                    if self._edit_mode:
                        cell.setFlags(cell.flags() | Qt.ItemFlag.ItemIsEditable)
                    else:
                        cell.setFlags(cell.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.tabela.setItem(row, col, cell)
        # marca linha vazia com UserRole = -1
        c0 = self.tabela.item(row, 0)
        if c0:
            c0.setData(Qt.ItemDataRole.UserRole, -1)

    def _atualizar_contador(self, exibidos=None):
        total = len(self.dados)
        if exibidos is None:
            exibidos = total
        filtro = self.campo_busca.text().strip()
        if filtro and exibidos != total:
            self.label_contador.setText(f"{exibidos} de {total} fornecedores")
        else:
            # plural correto
            if total == 1:
                self.label_contador.setText("1 fornecedor")
            else:
                self.label_contador.setText(f"{total} fornecedores")

    def _atualizar_estado_botoes(self):
        # Editar é toggle global — sempre habilitado
        self.btn_editar.setEnabled(True)
        # Adicionar só habilitado em modo edição (ou habilita modo ao clicar)
        self.btn_adicionar.setEnabled(True)
        tem_selecao = bool(self.tabela.selectionModel().selectedRows())
        if not tem_selecao:
            self.btn_excluir.setEnabled(False)
            return
        rows = [i.row() for i in self.tabela.selectionModel().selectedRows()]
        for r in rows:
            c0 = self.tabela.item(r, 0)
            if c0 and c0.data(Qt.ItemDataRole.UserRole) == -1:
                self.btn_excluir.setEnabled(False)
                return
        self.btn_excluir.setEnabled(True)

    # ── Ações ─────────────────────────────────────────────────────────────
    def _toggle_edicao(self):
        """Alterna modo edição global. Só permite editar células quando ativado."""
        self._edit_mode = self.btn_editar.isChecked()
        self.btn_editar.setChecked(self._edit_mode)
        self._popular_tabela()
        if self._edit_mode:
            self._mostrar_toast("Modo edição ativado — células liberadas para edição.", erro=False)
        else:
            self._mostrar_toast("Modo edição desativado.", erro=False)

    def _adicionar_linha(self):
        # Garante modo edição antes de adicionar
        if not self._edit_mode:
            self.btn_editar.setChecked(True)
            self._edit_mode = True
            self._popular_tabela()
        # foca na linha vazia, coluna Fornecedor
        last = self.tabela.rowCount() - 1
        self.tabela.scrollToBottom()
        self.tabela.setCurrentCell(last, 1)
        self.tabela.setFocus()
        item = self.tabela.item(last, 1)
        if item:
            self.tabela.editItem(item)

    def _on_cell_double_clicked(self, row, col):
        if not self._edit_mode:
            return
        # corrige clique na linha vazia: sempre edita Fornecedor (col 1)
        c0 = self.tabela.item(row, 0)
        if c0 and c0.data(Qt.ItemDataRole.UserRole) == -1 and col == 0:
            self.tabela.setCurrentCell(row, 1)

    def _editar_linha(self):
        # Mantido para compatibilidade — agora apenas garante modo edição e foca
        if not self._edit_mode:
            self.btn_editar.setChecked(True)
            self._edit_mode = True
            self._popular_tabela()
        selected = self.tabela.selectionModel().selectedRows()
        if not selected:
            # sem seleção, foca na primeira linha editável
            if self.tabela.rowCount() > 1:
                self.tabela.setCurrentCell(0, 1)
                item = self.tabela.item(0, 1)
                if item:
                    self.tabela.editItem(item)
            return
        row = selected[0].row()
        c0 = self.tabela.item(row, 0)
        if c0 and c0.data(Qt.ItemDataRole.UserRole) == -1:
            row = self.tabela.rowCount() - 1
        self.tabela.setCurrentCell(row, 1)
        item = self.tabela.item(row, 1)
        if item:
            self.tabela.editItem(item)

    def _remover_linha(self):
        selected = self.tabela.selectionModel().selectedRows()
        if not selected:
            return
        rows = sorted(set(i.row() for i in selected), reverse=True)
        # filtra linha vazia
        rows_validas = []
        nomes = []
        for r in rows:
            c0 = self.tabela.item(r, 0)
            if c0 and c0.data(Qt.ItemDataRole.UserRole) == -1:
                continue
            idx = self._indice_por_linha(r)
            if idx is not None:
                rows_validas.append((r, idx))
                nomes.append(self.dados[idx].get("fornecedor", "") or f"linha {r+1}")

        if not rows_validas:
            return

        if len(nomes) == 1:
            txt = f"Excluir o fornecedor <b>{nomes[0]}</b>?"
            detalhe = "Esta ação não pode ser desfeita."
        else:
            txt = f"Excluir {len(nomes)} fornecedores?"
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

        # remove do maior índice para o menor para não deslocar
        indices = sorted([idx for _, idx in rows_validas], reverse=True)
        for idx in indices:
            if 0 <= idx < len(self.dados):
                self.dados.pop(idx)
        self._salvar_json()
        self._popular_tabela()
        self._mostrar_toast(f"{len(indices)} fornecedor(es) removido(s).", erro=False)

    def _indice_por_linha(self, row):
        c0 = self.tabela.item(row, 0)
        if c0 is None:
            return None
        val = c0.data(Qt.ItemDataRole.UserRole)
        if isinstance(val, int) and 0 <= val < len(self.dados):
            return val
        # fallback: se não filtrado, row == índice
        if not self.campo_busca.text().strip() and 0 <= row < len(self.dados):
            return row
        return None

    # ── Validação / edição ──────────────────────────────────────────────
    def _validar_fornecedor(self, nome, row_idx_excluir=None):
        nome = nome.strip()
        if not nome:
            return False, "O nome do fornecedor não pode ficar em branco."
        # duplicado (case-insensitive)
        lower = nome.lower()
        for i, item in enumerate(self.dados):
            if row_idx_excluir is not None and i == row_idx_excluir:
                continue
            if item.get("fornecedor", "").strip().lower() == lower:
                return False, f"Fornecedor \"{nome}\" já cadastrado."
        return True, ""

    def _validar_email(self, email):
        email = email.strip()
        if not email:
            return True, ""  # email opcional
        if not EMAIL_RE.match(email):
            return False, f"Email \"{email}\" em formato inválido."
        return True, ""

    def _validar_duns(self, duns):
        duns = duns.strip()
        if not duns:
            return True, ""
        if not duns.isdigit():
            return False, "DUNS deve conter apenas números."
        if not (7 <= len(duns) <= 9):
            return False, "DUNS deve ter entre 7 e 9 dígitos."
        return True, ""

    def _item_modificado(self, item):
        # Bloqueia qualquer alteração fora do modo edição
        if not self._edit_mode:
            self.tabela.blockSignals(True)
            # desfaz a alteração visual
            c0_tmp = self.tabela.item(item.row(), 0)
            is_vazia_tmp = c0_tmp and c0_tmp.data(Qt.ItemDataRole.UserRole) == -1
            if is_vazia_tmp:
                item.setText("")
            else:
                idx_tmp = self._indice_por_linha(item.row())
                if idx_tmp is not None and 0 <= idx_tmp < len(self.dados):
                    chave_tmp = self.CHAVES[item.column()]
                    item.setText(str(self.dados[idx_tmp].get(chave_tmp, "")))
                else:
                    item.setText("")
            self.tabela.blockSignals(False)
            self._mostrar_toast("Ative o modo edição para alterar.", erro=True)
            return

        row = item.row()
        col = item.column()
        chave = self.CHAVES[col]

        # linha vazia -> criação de novo fornecedor
        c0 = self.tabela.item(row, 0)
        is_linha_vazia = c0 and c0.data(Qt.ItemDataRole.UserRole) == -1
        # fallback antigo (caso UserRole não esteja setado)
        if not is_linha_vazia and row == len(self.dados) and not self.campo_busca.text().strip():
            is_linha_vazia = True

        if is_linha_vazia:
            # só cria se o usuário preencheu algo (fornecedor é obrigatório)
            # verifica se alguma célula da linha tem conteúdo
            tem_conteudo = False
            for c in range(len(self.COLUNAS)):
                cel = self.tabela.item(row, c)
                if cel and cel.text().strip():
                    tem_conteudo = True
                    break
            if not tem_conteudo:
                return

            # coleta valores da linha
            novo_item = {}
            for c, ch in enumerate(self.CHAVES):
                cel = self.tabela.item(row, c)
                valor = cel.text().strip() if cel else ""
                # normalizações
                if ch == "fornecedor":
                    valor = valor.strip()
                elif ch == "email":
                    valor = valor.strip().lower()
                elif ch == "duns":
                    valor = valor.strip()
                novo_item[ch] = valor

            # validações
            ok, msg = self._validar_fornecedor(novo_item.get("fornecedor", ""))
            if not ok:
                self.tabela.blockSignals(True)
                item.setText("")
                self.tabela.blockSignals(False)
                self._mostrar_toast(msg, erro=True)
                return

            ok, msg = self._validar_email(novo_item.get("email", ""))
            if not ok:
                self.tabela.blockSignals(True)
                # limpa apenas email
                cel_email = self.tabela.item(row, 2)
                if cel_email:
                    cel_email.setText("")
                self.tabela.blockSignals(False)
                self._mostrar_toast(msg, erro=True)
                # mantém linha para corrigir, não cria
                return

            ok, msg = self._validar_duns(novo_item.get("duns", ""))
            if not ok:
                self.tabela.blockSignals(True)
                cel_duns = self.tabela.item(row, 4)
                if cel_duns:
                    cel_duns.setText("")
                self.tabela.blockSignals(False)
                self._mostrar_toast(msg, erro=True)
                return

            novo_item["indice"] = self._next_indice()
            self.dados.append(novo_item)
            self._ordenar_dados()
            self._salvar_json()
            self._popular_tabela()
            # foca na nova linha vazia
            QTimer.singleShot(0, self._adicionar_linha)
            self._mostrar_toast(f"Fornecedor \"{novo_item['fornecedor']}\" adicionado.", erro=False)
            return

        # edição de linha existente
        idx = self._indice_por_linha(row)
        if idx is None or not (0 <= idx < len(self.dados)):
            return

        novo_valor = item.text().strip()
        # normalização por coluna
        if chave == "email":
            novo_valor = novo_valor.lower()
            ok, msg = self._validar_email(novo_valor)
            if not ok:
                self.tabela.blockSignals(True)
                item.setText(self.dados[idx].get(chave, ""))
                self.tabela.blockSignals(False)
                self._mostrar_toast(msg, erro=True)
                return
        elif chave == "fornecedor":
            ok, msg = self._validar_fornecedor(novo_valor, row_idx_excluir=idx)
            if not ok:
                self.tabela.blockSignals(True)
                item.setText(self.dados[idx].get(chave, ""))
                self.tabela.blockSignals(False)
                self._mostrar_toast(msg, erro=True)
                return
            if not novo_valor:
                self.tabela.blockSignals(True)
                item.setText(self.dados[idx].get(chave, ""))
                self.tabela.blockSignals(False)
                self._mostrar_toast("Nome do fornecedor é obrigatório.", erro=True)
                return
        elif chave == "duns":
            ok, msg = self._validar_duns(novo_valor)
            if not ok:
                self.tabela.blockSignals(True)
                item.setText(self.dados[idx].get(chave, ""))
                self.tabela.blockSignals(False)
                self._mostrar_toast(msg, erro=True)
                return

        # telefone: apenas trim
        if self.dados[idx].get(chave, "") == novo_valor:
            return

        self.dados[idx][chave] = novo_valor
        # se alterou fornecedor, reordena
        if chave == "fornecedor":
            self._ordenar_dados()
            self._salvar_json()
            self._popular_tabela()
        else:
            self._salvar_json()
            # atualiza tooltip / background se email inválido
            if chave == "email":
                self._popular_tabela()

    # ── Busca / utilidades ───────────────────────────────────────────────
    def _esc_limpar_filtro(self):
        if self.campo_busca.text():
            self.campo_busca.clear()
        elif self.campo_busca.hasFocus():
            self.campo_busca.clearFocus()

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
        # centraliza no card/tabela
        parent_rect = self.tabela.geometry() if hasattr(self, 'tabela') else self.rect()
        # converte para global e posiciona
        global_pos = self.mapToGlobal(parent_rect.center())
        # ajusta para centralizar o label
        msg.move(global_pos.x() - msg.width() // 2, global_pos.y() - msg.height() // 2)
        msg.show()
        QTimer.singleShot(2200 if not erro else 3000, msg.close)

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

    def _next_indice(self):
        max_id = 0
        for d in self.dados:
            try:
                v = int(d.get("indice", 0) or 0)
                if v > max_id:
                    max_id = v
            except Exception:
                continue
        return max_id + 1
