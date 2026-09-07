import json
import os
import re

import qtawesome
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QFrame,
    QAbstractItemView, QDateEdit, QDialog, QGridLayout, QComboBox, QDialogButtonBox,
    QMessageBox, QMenu, QStyledItemDelegate,
)
from PySide6.QtCore import Qt, QDate, QTimer, QSize, QEvent
from PySide6.QtGui import QColor, QBrush, QDoubleValidator, QCursor, QIcon, QPixmap


# ── Cores por status (mesmo de SAs emitidas) ─────────────────────────────
CORES_STATUS = {
    "Pendente": "#fef9c3",
    "Programado": "#e0f2fe",
    "Entregue": "#dcfce7",
    "Programado/Entregue": "#d1fae5",
    "Cancelado": "#fee2e2",
    "Devolvido": "#ffedd5",
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

STATUS_OPCOES = ["", "Pendente", "Programado", "Entregue", "Programado/Entregue", "Cancelado", "Devolvido"]
STATUS_LABELS = ["Vazio", "Pendente", "Programado", "Entregue", "Programado/Entregue", "Cancelado", "Devolvido"]


def _caminho_itens_almoxarifado_json():
    import config
    base = config.obter_caminho_jsons()
    if not base:
        return ""
    return os.path.normpath(os.path.join(base, "Almox", "ItensAlmoxarifado", "ItensAlmoxarifado.json"))


# ── Delegate para coluna Qtde sem padding (célula e campo de texto) ─────
class DelegateQtdeSemPadding(QStyledItemDelegate):
    """Remove padding da célula e do QLineEdit da coluna Qtde (col 0)."""
    def paint(self, painter, option, index):
        if index.column() == 0:
            self.initStyleOption(option, index)
            # Fundo (inclui seleção e cor amarela de qtde)
            bg = index.data(Qt.ItemDataRole.BackgroundRole)
            if bg is not None:
                painter.save()
                brush = bg if isinstance(bg, QBrush) else QBrush(bg)
                painter.fillRect(option.rect, brush)
                painter.restore()
            elif option.state & QStyledItemDelegate.StateFlag.State_Selected:
                painter.save()
                painter.fillRect(option.rect, option.palette.highlight())
                painter.restore()
            else:
                # mantém fundo padrão (branco/alternado) — não preenche, deixa tabela desenhar
                pass
            # Texto sem padding, centralizado, ocupando todo o rect
            text = index.data(Qt.ItemDataRole.DisplayRole) or ""
            painter.save()
            # cor do texto
            fg = index.data(Qt.ItemDataRole.ForegroundRole)
            if fg is not None:
                brush_fg = fg if isinstance(fg, QBrush) else QBrush(fg)
                painter.setPen(brush_fg.color())
            else:
                painter.setPen(option.palette.color(option.palette.ColorRole.Text))
            painter.drawText(option.rect, int(Qt.AlignmentFlag.AlignCenter), str(text))
            painter.restore()
            return
        super().paint(painter, option, index)

    def sizeHint(self, option, index):
        base = super().sizeHint(option, index)
        if index.column() == 0:
            # altura mínima sem padding extra
            return QSize(base.width(), max(base.height(), 22))
        return base

    def createEditor(self, parent, option, index):
        if index.column() == 0:
            editor = QLineEdit(parent)
            editor.setContentsMargins(0, 0, 0, 0)
            editor.setStyleSheet("QLineEdit { padding:0px; margin:0px; border:none; border-bottom:1.5px solid #6366f1; border-radius:0px; background:#ffffff; font-size:12px; }")
            editor.setAlignment(Qt.AlignmentFlag.AlignCenter)
            return editor
        return super().createEditor(parent, option, index)

    def updateEditorGeometry(self, editor, option, index):
        if index.column() == 0:
            # ocupa toda a célula, sem padding
            editor.setGeometry(option.rect)
            return
        super().updateEditorGeometry(editor, option, index)


# ── Janela para inserir itens a partir de ItensAlmoxarifado ──────────────
class DialogInserirItens(QDialog):
    """Janela que carrega todos os itens de ItensAlmoxarifado em tabela.

    Colunas: Qtde (editável, vazio), Kardex, Item (Código), Descrição, Custo unit.
    Usuário preenche Qtde e confirma para adicionar à SA.
    """
    COLUNAS = ["Qtde", "Kardex", "Item", "Descrição", "Custo unit."]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Inserir itens - ItensAlmoxarifado")
        self.setModal(True)
        self.resize(980, 620)
        self._todos_itens = []
        self._filtrados = []
        self._texto_filtro_cache = []
        self._qtde_por_chave = {}  # chave (kardex|codigo) -> texto qtde
        self._setup_ui()
        self._carregar_itens()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        # Título + filtro
        header = QHBoxLayout()
        titulo = QLabel("Selecione os itens")
        titulo.setStyleSheet("color:#1e293b; font-size:14px; font-weight:700;")
        header.addWidget(titulo)
        header.addStretch()

        lbl_filtro = QLabel("Pesquisar:")
        lbl_filtro.setStyleSheet("color:#64748b; font-size:11px; font-weight:600;")
        header.addWidget(lbl_filtro)

        self.campo_filtro = QLineEdit()
        self.campo_filtro.setPlaceholderText("Kardex, código ou descrição...")
        self.campo_filtro.setFixedHeight(32)
        self.campo_filtro.setMinimumWidth(280)
        self.campo_filtro.setMaximumWidth(360)
        self.campo_filtro.setStyleSheet("background:#ffffff; border:1px solid #e2e8f0; border-radius:8px; padding:4px 10px; font-size:12px;")
        self.campo_filtro.textChanged.connect(self._on_filtro_text_changed)
        header.addWidget(self.campo_filtro)

        self.btn_limpar_filtro = QPushButton(qtawesome.icon('fa6s.xmark', color='#64748b'), "")
        self.btn_limpar_filtro.setFixedSize(28, 28)
        self.btn_limpar_filtro.setToolTip("Limpar filtro")
        self.btn_limpar_filtro.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_limpar_filtro.setObjectName("btnGhost")
        self.btn_limpar_filtro.clicked.connect(lambda: self.campo_filtro.clear())
        header.addWidget(self.btn_limpar_filtro)

        layout.addLayout(header)

        subtitulo = QLabel("Preencha a coluna Qtde (vazia) para os itens desejados. Apenas itens com Qtde preenchida serão adicionados.")
        subtitulo.setStyleSheet("color:#94a3b8; font-size:11px;")
        subtitulo.setWordWrap(True)
        layout.addWidget(subtitulo)

        # Tabela
        self.tabela = QTableWidget(0, len(self.COLUNAS))
        self.tabela.setObjectName("tabelaInserirItens")
        self.tabela.setStyleSheet("""
            QTableWidget#tabelaInserirItens {
                background-color: #ffffff;
                border: 1px solid #eef1f6;
                border-radius: 12px;
                gridline-color: transparent;
                selection-background-color: #eef2ff;
                selection-color: #1e1b4b;
                font-size: 12px;
                outline: none;
            }
            QTableWidget#tabelaInserirItens::item {
                padding: 4px 8px;
                border-bottom: 1px solid #f3f4f6;
            }
            QTableWidget#tabelaInserirItens::item:selected {
                background-color: #eef2ff;
                color: #1e1b4b;
            }
        """)
        # delegate sem padding para coluna Qtde (célula e campo de texto)
        self.tabela.setItemDelegate(DelegateQtdeSemPadding(self.tabela))
        self.tabela.setHorizontalHeaderLabels(self.COLUNAS)
        hdr = self.tabela.horizontalHeader()
        hdr.setStretchLastSection(True)
        # Qtde pequena, descrição estica
        larguras = {0: 80, 1: 130, 2: 130, 4: 110}
        for c, w in larguras.items():
            hdr.setSectionResizeMode(c, QHeaderView.ResizeMode.Fixed)
            hdr.resizeSection(c, w)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        hdr.setStyleSheet(
            "QHeaderView::section {"
            "  font-size: 8.5px; font-weight: 700;"
            "  background-color: #f8fafc; color: #64748b;"
            "  text-transform: uppercase; letter-spacing: 0.3px;"
            "  padding: 6px 8px; margin: 0px; border: none; border-bottom: 2px solid #e2e8f0;"
            "}"
        )
        self.tabela.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabela.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tabela.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked
            | QAbstractItemView.EditTrigger.EditKeyPressed
            | QAbstractItemView.EditTrigger.AnyKeyPressed
        )
        self.tabela.setAlternatingRowColors(True)
        self.tabela.verticalHeader().setDefaultSectionSize(28)
        self.tabela.verticalHeader().setMinimumSectionSize(26)
        self.tabela.verticalHeader().setVisible(False)
        self.tabela.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.tabela.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.tabela.itemChanged.connect(self._on_item_changed)
        self.tabela.cellDoubleClicked.connect(self._on_cell_double_clicked)

        layout.addWidget(self.tabela, 1)

        # Rodapé: contador + botões
        rodape = QHBoxLayout()
        self.label_contador = QLabel("0 itens")
        self.label_contador.setStyleSheet("color:#64748b; font-size:11px; font-weight:600;")
        rodape.addWidget(self.label_contador)
        self.label_selecionados = QLabel("0 com Qtde")
        self.label_selecionados.setStyleSheet("color:#6366f1; font-size:11px; font-weight:700;")
        rodape.addWidget(self.label_selecionados)
        rodape.addStretch()

        self.btn_adicionar = QPushButton(qtawesome.icon('fa6s.check', color='#ffffff'), "  Adicionar selecionados")
        self.btn_adicionar.setObjectName("btnPrimary")
        self.btn_adicionar.setFixedHeight(34)
        self.btn_adicionar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_adicionar.clicked.connect(self.accept)
        rodape.addWidget(self.btn_adicionar)

        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setObjectName("btnSecondary")
        btn_cancelar.setFixedHeight(34)
        btn_cancelar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancelar.clicked.connect(self.reject)
        rodape.addWidget(btn_cancelar)

        layout.addLayout(rodape)

        # Timer debounce filtro
        self._filtro_timer = QTimer(self)
        self._filtro_timer.setSingleShot(True)
        self._filtro_timer.setInterval(220)
        self._filtro_timer.timeout.connect(self._aplicar_filtro)

    def _chave_item(self, item):
        return f"{str(item.get('Kardex','')).strip()}|{str(item.get('Código','')).strip()}"

    def _carregar_itens(self):
        caminho = _caminho_itens_almoxarifado_json()
        dados = []
        # tenta múltiplos fallbacks como em outras páginas
        candidatos = []
        if caminho:
            candidatos.append(caminho)
        try:
            import config
            base = config.obter_caminho_jsons()
            if base:
                candidatos.append(os.path.normpath(os.path.join(base, "Almox", "ItensAlmoxarifado", "ItensAlmoxarifado.json")))
        except Exception:
            pass
        candidatos.extend([
            os.path.normpath(r"C:\Users\ander\Documents\AntiGravity\AlmoxarifadoConf\Almox\ItensAlmoxarifado\ItensAlmoxarifado.json"),
            os.path.normpath(r"C:\Users\ander\Documents\AntiGravity\Almoxarifado2\Almox\ItensAlmoxarifado\ItensAlmoxarifado.json"),
            os.path.normpath(os.path.join(os.getcwd(), "Almox", "ItensAlmoxarifado", "ItensAlmoxarifado.json")),
        ])
        for cand in candidatos:
            if cand and os.path.isfile(cand):
                try:
                    with open(cand, "r", encoding="utf-8") as f:
                        dados = json.load(f)
                        if isinstance(dados, list):
                            caminho = cand
                            break
                except Exception:
                    continue
        if not isinstance(dados, list):
            dados = []
        self._todos_itens = dados
        # cache para filtro
        self._texto_filtro_cache = []
        for it in self._todos_itens:
            # junta campos relevantes para busca
            txt = " ".join([
                str(it.get("Kardex", "")),
                str(it.get("Código", "")),
                str(it.get("Descrição", "")),
                str(it.get("Custo", "")),
            ]).lower()
            self._texto_filtro_cache.append(txt)
        self._filtrados = list(self._todos_itens)
        self._popular_tabela()

    def _on_filtro_text_changed(self, _texto):
        self._filtro_timer.stop()
        self._filtro_timer.start(220)

    def _aplicar_filtro(self):
        # persiste qtde editadas antes de filtrar
        self._salvar_qtde_visivel_no_mapa()
        filtro = self.campo_filtro.text().strip().lower()
        if not filtro:
            self._filtrados = list(self._todos_itens)
        else:
            self._filtrados = []
            for idx, item in enumerate(self._todos_itens):
                txt = self._texto_filtro_cache[idx] if idx < len(self._texto_filtro_cache) else ""
                if filtro in txt:
                    self._filtrados.append(item)
        self._popular_tabela()

    def _salvar_qtde_visivel_no_mapa(self):
        # salva qtde da tabela visível no dict persistente
        for row in range(self.tabela.rowCount()):
            it_qtde = self.tabela.item(row, 0)
            if it_qtde is None:
                continue
            chave = it_qtde.data(Qt.ItemDataRole.UserRole)
            if not chave:
                # fallback: usa kardex|codigo da linha
                kardex_it = self.tabela.item(row, 1)
                codigo_it = self.tabela.item(row, 2)
                chave = f"{kardex_it.text().strip() if kardex_it else ''}|{codigo_it.text().strip() if codigo_it else ''}"
            txt = it_qtde.text().strip()
            if txt:
                self._qtde_por_chave[chave] = txt
            else:
                self._qtde_por_chave.pop(chave, None)

    def _popular_tabela(self):
        self.tabela.blockSignals(True)
        self.tabela.setRowCount(0)
        for item in self._filtrados:
            row = self.tabela.rowCount()
            self.tabela.insertRow(row)
            kardex = str(item.get("Kardex", "")).strip()
            codigo = str(item.get("Código", "")).strip()
            descricao = str(item.get("Descrição", "")).strip()
            custo_raw = str(item.get("Custo", "")).strip()
            # custo já vem como "R$ 0,17" — mantém como está para exibir
            custo = custo_raw if custo_raw else ""
            chave = f"{kardex}|{codigo}"
            qtde_texto = self._qtde_por_chave.get(chave, "")

            # Qtde — editável, vazio
            cell_qtde = QTableWidgetItem(qtde_texto)
            cell_qtde.setFlags(cell_qtde.flags() | Qt.ItemFlag.ItemIsEditable)
            cell_qtde.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            cell_qtde.setData(Qt.ItemDataRole.UserRole, chave)
            cell_qtde.setToolTip("Digite a quantidade e pressione Enter")
            if qtde_texto:
                cell_qtde.setBackground(QBrush(QColor("#fef9c3")))
            self.tabela.setItem(row, 0, cell_qtde)

            # Kardex — somente leitura
            cell_kardex = QTableWidgetItem(kardex)
            cell_kardex.setFlags(cell_kardex.flags() & ~Qt.ItemFlag.ItemIsEditable)
            cell_kardex.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if kardex:
                cell_kardex.setToolTip(kardex)
            self.tabela.setItem(row, 1, cell_kardex)

            # Item (Código) — somente leitura
            cell_codigo = QTableWidgetItem(codigo)
            cell_codigo.setFlags(cell_codigo.flags() & ~Qt.ItemFlag.ItemIsEditable)
            cell_codigo.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if codigo:
                cell_codigo.setToolTip(codigo)
            self.tabela.setItem(row, 2, cell_codigo)

            # Descrição — somente leitura
            cell_desc = QTableWidgetItem(descricao)
            cell_desc.setFlags(cell_desc.flags() & ~Qt.ItemFlag.ItemIsEditable)
            if descricao:
                cell_desc.setToolTip(descricao)
            self.tabela.setItem(row, 3, cell_desc)

            # Custo unit — somente leitura, centralizado
            cell_custo = QTableWidgetItem(custo)
            cell_custo.setFlags(cell_custo.flags() & ~Qt.ItemFlag.ItemIsEditable)
            cell_custo.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if custo:
                cell_custo.setToolTip(custo)
            self.tabela.setItem(row, 4, cell_custo)

        self.tabela.blockSignals(False)
        self._atualizar_contadores()
        # restaurar seleção se houver qtde
        # não força seleção

    def _on_item_changed(self, item):
        if item.column() != 0:
            return
        # valida numérico e atualiza mapa + cor
        texto = item.text().strip()
        chave = item.data(Qt.ItemDataRole.UserRole)
        if texto == "":
            item.setBackground(QBrush(QColor("#ffffff")))
            if chave:
                self._qtde_por_chave.pop(chave, None)
        else:
            # valida: aceita 1.000,00 / 10 / 10,5
            t_norm = texto.replace(".", "").replace(",", ".") if "," in texto else texto
            try:
                v = float(t_norm)
                if v < 0:
                    raise ValueError
                # ok — pinta amarelo claro
                item.setBackground(QBrush(QColor("#fef9c3")))
                if chave:
                    self._qtde_por_chave[chave] = texto
            except ValueError:
                # inválido — limpa
                self.tabela.blockSignals(True)
                item.setText("")
                item.setBackground(QBrush(QColor("#ffffff")))
                self.tabela.blockSignals(False)
                if chave:
                    self._qtde_por_chave.pop(chave, None)
        self._atualizar_contadores()

    def _on_cell_double_clicked(self, row, col):
        if col == 0:
            # foca edição
            it = self.tabela.item(row, 0)
            if it:
                self.tabela.editItem(it)

    def _atualizar_contadores(self):
        total = len(self._filtrados)
        total_geral = len(self._todos_itens)
        if total != total_geral:
            self.label_contador.setText(f"{total} de {total_geral} itens")
        else:
            self.label_contador.setText(f"{total_geral} itens")
        qtdes = len(self._qtde_por_chave)
        self.label_selecionados.setText(f"{qtdes} com Qtde")
        self.btn_adicionar.setEnabled(qtdes > 0)
        self.btn_adicionar.setText(f"  Adicionar ({qtdes})" if qtdes else "  Adicionar selecionados")

    def _parse_qtde(self, texto):
        t = texto.strip().replace(".", "").replace(",", ".") if "," in texto else texto.strip()
        try:
            return float(t)
        except ValueError:
            return None

    def _parse_custo_para_float(self, texto):
        # "R$ 0,17" -> 0.17
        t = re.sub(r"[R$\s]", "", texto or "")
        t = t.replace(".", "").replace(",", ".") if "," in t else t
        try:
            return float(t) if t else 0.0
        except ValueError:
            return 0.0

    def obter_itens_selecionados(self):
        # garante que qtde visível está salva
        self._salvar_qtde_visivel_no_mapa()
        selecionados = []
        # percorre todos os itens (não só filtrados) usando o mapa persistente
        for item in self._todos_itens:
            chave = self._chave_item(item)
            qtde_txt = self._qtde_por_chave.get(chave, "").strip()
            if not qtde_txt:
                continue
            qtde_val = self._parse_qtde(qtde_txt)
            if qtde_val is None or qtde_val <= 0:
                continue
            kardex = str(item.get("Kardex", "")).strip()
            codigo = str(item.get("Código", "")).strip()
            descricao = str(item.get("Descrição", "")).strip()
            custo_raw = str(item.get("Custo", "")).strip()
            # custo unit sem "R$" para tabela principal? mantém número formatado
            # extrai só valor para cálculo, mas exibe como veio sem R$? Na tabela nova pede "custo unit" — usaremos valor limpo
            custo_unit_limpo = re.sub(r"^\s*R\$\s*", "", custo_raw).strip() if custo_raw else ""
            if not custo_unit_limpo:
                custo_unit_limpo = "0,00"
            # custo total = qtde * custo_unit
            custo_float = self._parse_custo_para_float(custo_raw)
            total_float = (qtde_val or 0) * custo_float
            total_txt = f"{total_float:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            selecionados.append({
                "kardex": kardex,
                "codigo": codigo,
                "descricao": descricao,
                "qtde": qtde_txt,
                "custo_unit": custo_unit_limpo,
                "custo_total": total_txt,
                "status": "Pendente",
                "qtde_programada": "",
                "qtde_entregue": "",
            })
        return selecionados

    def accept(self):
        itens = self.obter_itens_selecionados()
        if not itens:
            QMessageBox.warning(self, "Atenção", "Preencha a Qtde de ao menos um item.")
            return
        super().accept()


# ── Página principal ─────────────────────────────────────────────────────
class SolicitacaoSaPage(QWidget):
    COLUNAS = [
        "Kardex",
        "Código",
        "Descrição",
        "Qtde",
        "Custo unit.",
        "Custo total",
        "Status",
        "Qtde\nprogramada",
        "Qtde\nentregue",
    ]
    CHAVES = [
        "kardex",
        "codigo",
        "descricao",
        "qtde",
        "custo_unit",
        "custo_total",
        "status",
        "qtde_programada",
        "qtde_entregue",
    ]

    def _obter_proximo_numero_sa(self):
        """Retorna próximo número sequencial baseado nos arquivos em Almox/SA.
        Ex: se existe 19525.json -> retorna '19526'. Considera prefixo SA opcional.
        """
        try:
            import config
            base = config.obter_caminho_jsons()
            pasta = os.path.normpath(os.path.join(base, "Almox", "SA")) if base else ""
        except Exception:
            pasta = ""
        # fallbacks se pasta base não existir ainda
        candidatos = []
        if pasta:
            candidatos.append(pasta)
        candidatos.extend([
            os.path.normpath(os.path.join(os.getcwd(), "Almox", "SA")),
            os.path.normpath(r"C:\Users\ander\Documents\AntiGravity\AlmoxarifadoConf\Almox\SA"),
            os.path.normpath(r"C:\Users\ander\Documents\AntiGravity\Almoxarifado2\Almox\SA"),
        ])
        # usa primeira pasta existente com .json, senão usa pasta principal para calcular
        pasta_uso = ""
        for cand in candidatos:
            if cand and os.path.isdir(cand):
                pasta_uso = cand
                break
        if not pasta_uso:
            pasta_uso = pasta or candidatos[0]
        max_num = 0
        try:
            if pasta_uso and os.path.isdir(pasta_uso):
                for nome in os.listdir(pasta_uso):
                    if not nome.lower().endswith(".json"):
                        continue
                    stem = os.path.splitext(nome)[0].strip()
                    if stem.upper().startswith("SA"):
                        stem = stem[2:].strip()
                    # só considera stems puramente numéricos ou com prefixo numérico
                    m = re.match(r"^(\d+)$", stem)
                    if m:
                        try:
                            v = int(m.group(1))
                            if v > max_num:
                                max_num = v
                        except Exception:
                            continue
                    else:
                        m2 = re.match(r"^(\d+)", stem)
                        if m2:
                            try:
                                v = int(m2.group(1))
                                if v > max_num:
                                    max_num = v
                            except Exception:
                                continue
        except Exception:
            pass
        if max_num > 0:
            return str(max_num + 1)
        # sem arquivos: começa em 1 (exemplo do usuário: 19525 -> 19526 seria max+1)
        return "1"

    def _atualizar_preview_num_req(self):
        # Deprecated: Nº de requisição e Nº da SA são diferentes.
        # O campo deve permanecer vazio/editável; a SA é gerada só no Cadastrar SA.
        # Mantido por compatibilidade, não deve ser chamado.
        return

    def __init__(self):
        super().__init__()
        self.itens = []
        self._setup_ui()
        # Nº de requisição e Nº da SA são coisas diferentes:
        # o campo deve começar vazio para o usuário digitar a requisição.
        # O nº da SA é gerado automaticamente apenas no Cadastrar SA (nome do arquivo).
        try:
            self.campo_num_req.clear()
            self.campo_num_req.setPlaceholderText("")
        except Exception:
            pass

    # ── UI ────────────────────────────────────────────────────────────────
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Header — mesmo estilo de SAs emitidas
        header_layout = QHBoxLayout()
        header_texts = QVBoxLayout()
        header_texts.setSpacing(4)
        titulo = QLabel("Solicitação de SA")
        titulo.setObjectName("pageTitle")
        header_texts.addWidget(titulo)
        subtitulo = QLabel("Preencha os dados da SA e insira os itens na tabela abaixo")
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

        # ── QUADRO SUPERIOR (mesmo estilo do quadroSA de SAs emitidas) ──
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

        # Linha principal: quadro central com campos + quadro botão à direita
        linha_sa = QHBoxLayout()
        linha_sa.setSpacing(12)

        # helper para campo com label — idêntico ao de SAs emitidas
        def criar_campo_quadro(placeholder, label_text, max_w=135, min_w=105):
            w = QWidget()
            w.setMaximumWidth(max_w)
            w.setMinimumWidth(min_w)
            v = QVBoxLayout(w)
            v.setContentsMargins(0, 0, 0, 0)
            v.setSpacing(1)
            lbl = QLabel(label_text)
            lbl.setStyleSheet("color:#64748b; font-size:9px; font-weight:600; padding:0px; margin:0px;")
            lbl.setMaximumWidth(max_w)
            lbl.setFixedHeight(12)
            v.addWidget(lbl)
            edit = QLineEdit()
            edit.setPlaceholderText(placeholder)
            edit.setFixedHeight(26)
            edit.setMaximumWidth(max_w)
            edit.setMinimumWidth(min_w)
            edit.setStyleSheet("background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:2px 6px; font-size:11px; margin:0px;")
            v.addWidget(edit)
            return w, edit

        # Quadro central com 2 linhas de campos (4 + 4)
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
        quadro_campos_v = QVBoxLayout(self.quadro_sa_campos)
        quadro_campos_v.setSpacing(6)
        quadro_campos_v.setContentsMargins(8, 8, 8, 8)

        # Linha 1: 4 campos
        linha1 = QHBoxLayout()
        linha1.setSpacing(8)
        linha1.setContentsMargins(0, 0, 0, 0)
        w_nome, self.campo_nome_emissor = criar_campo_quadro("Nome completo...", "Nome do emissor")
        w_req, self.campo_num_req = criar_campo_quadro("", "Nº de requisição")
        self.campo_num_req.setReadOnly(False)
        self.campo_num_req.clear()
        self.campo_num_req.setPlaceholderText("")
        self.campo_num_req.setStyleSheet("background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:2px 6px; font-size:11px; margin:0px; color:#1e293b;")
        self.campo_num_req.setToolTip("Nº de requisição — informe o número da requisição (diferente do nº da SA, que é gerado automaticamente).")
        w_proj, self.campo_projeto_debito = criar_campo_quadro("Projeto...", "Projeto p/ débito")
        w_conta, self.campo_conta_debito = criar_campo_quadro("Conta...", "Conta p/ débito")
        for w in [w_nome, w_req, w_proj, w_conta]:
            linha1.addWidget(w)
        linha1.addStretch()
        quadro_campos_v.addLayout(linha1)

        # Linha 2: 4 campos
        linha2 = QHBoxLayout()
        linha2.setSpacing(8)
        linha2.setContentsMargins(0, 0, 0, 0)
        w_destino, self.campo_destino = criar_campo_quadro("Destino...", "Destino")
        w_local, self.campo_local_entrega = criar_campo_quadro("Local...", "Local para entrega")
        w_entregar, self.campo_entregar_para = criar_campo_quadro("Nome / local...", "Entregar para")
        # Data necessidade — QDateEdit no mesmo estilo compacto
        w_data = QWidget()
        w_data.setMaximumWidth(135)
        w_data.setMinimumWidth(110)
        v_data = QVBoxLayout(w_data)
        v_data.setContentsMargins(0, 0, 0, 0)
        v_data.setSpacing(1)
        lbl_data = QLabel("Data da necessidade")
        lbl_data.setStyleSheet("color:#64748b; font-size:9px; font-weight:600; padding:0px; margin:0px;")
        lbl_data.setMaximumWidth(135)
        lbl_data.setFixedHeight(12)
        v_data.addWidget(lbl_data)
        self.campo_data_necessidade = QDateEdit()
        self.campo_data_necessidade.setCalendarPopup(True)
        self.campo_data_necessidade.setDisplayFormat("dd/MM/yyyy")
        self.campo_data_necessidade.setDate(QDate.currentDate())
        self.campo_data_necessidade.setFixedHeight(26)
        self.campo_data_necessidade.setMaximumWidth(135)
        self.campo_data_necessidade.setMinimumWidth(110)
        self.campo_data_necessidade.setStyleSheet("background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:2px 6px; font-size:11px; margin:0px;")
        v_data.addWidget(self.campo_data_necessidade)

        for w in [w_destino, w_local, w_entregar]:
            linha2.addWidget(w)
        linha2.addWidget(w_data)
        linha2.addStretch()
        quadro_campos_v.addLayout(linha2)

        linha_sa.addWidget(self.quadro_sa_campos, 1)

        # Quadro à direita com botão Inserir itens — mesmo estilo do quadroSaBotoes original
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
        self.quadro_sa_botoes.setFixedWidth(160)
        inner_lay = QVBoxLayout(self.quadro_sa_botoes)
        inner_lay.setContentsMargins(8, 8, 8, 8)
        inner_lay.setSpacing(6)
        # espaçador para centralizar verticalmente
        inner_lay.addStretch()
        self.btn_cadastrar_sa = QPushButton(qtawesome.icon('fa6s.check', color='#ffffff'), "  Cadastrar SA")
        self.btn_cadastrar_sa.setObjectName("btnPrimary")
        self.btn_cadastrar_sa.setFixedHeight(36)
        self.btn_cadastrar_sa.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cadastrar_sa.clicked.connect(self._cadastrar_sa)
        inner_lay.addWidget(self.btn_cadastrar_sa)
        self.btn_cancelar_sa = QPushButton(qtawesome.icon('fa6s.xmark', color='#64748b'), "  Cancelar")
        self.btn_cancelar_sa.setObjectName("btnSecondary")
        self.btn_cancelar_sa.setFixedHeight(32)
        self.btn_cancelar_sa.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancelar_sa.clicked.connect(self._cancelar_sa)
        inner_lay.addWidget(self.btn_cancelar_sa)
        inner_lay.addStretch()
        linha_sa.addWidget(self.quadro_sa_botoes)

        quadro_layout.addLayout(linha_sa)

        # Linha inferior do quadro: contador com Inserir itens + Limpar à esquerda
        self.label_contador = QLabel("0 itens")
        self.label_contador.setObjectName("statusLabel")
        self.label_contador.setStyleSheet("color:#64748b; font-size:11px; font-weight:600;")
        self.label_contador.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        linha_contador = QHBoxLayout()
        linha_contador.setContentsMargins(0, 2, 0, 2)
        linha_contador.setSpacing(8)
        self.btn_inserir_itens = QPushButton(qtawesome.icon('fa6s.plus', color='#ffffff'), "  Inserir itens")
        self.btn_inserir_itens.setObjectName("btnPrimary")
        self.btn_inserir_itens.setFixedHeight(30)
        self.btn_inserir_itens.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_inserir_itens.clicked.connect(self._abrir_dialog_inserir)
        linha_contador.addWidget(self.btn_inserir_itens)
        self.btn_limpar_sa = QPushButton(qtawesome.icon('fa6s.broom', color='#64748b'), "  Limpar")
        self.btn_limpar_sa.setObjectName("btnSecondary")
        self.btn_limpar_sa.setFixedHeight(30)
        self.btn_limpar_sa.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_limpar_sa.clicked.connect(self._limpar_formulario)
        linha_contador.addWidget(self.btn_limpar_sa)
        linha_contador.addStretch()
        linha_contador.addWidget(self.label_contador)
        quadro_layout.addLayout(linha_contador)

        card_layout.addWidget(self.quadro_sa)

        # ── TABELA (read-only, mesmo estilo visual) ──
        self.tabela = QTableWidget(0, len(self.COLUNAS))
        self.tabela.setObjectName("tabelaSolicitacaoSA")
        self.tabela.setStyleSheet("""
            QTableWidget#tabelaSolicitacaoSA {
                background-color: #ffffff;
                border: 1px solid #eef1f6;
                border-radius: 12px;
                gridline-color: transparent;
                selection-background-color: #eef2ff;
                selection-color: #1e1b4b;
                font-size: 12px;
                outline: none;
            }
            QTableWidget#tabelaSolicitacaoSA::item {
                padding: 4px 8px;
                border-bottom: 1px solid #f3f4f6;
            }
            QTableWidget#tabelaSolicitacaoSA::item:selected {
                background-color: #eef2ff;
                color: #1e1b4b;
            }
            QTableWidget#tabelaSolicitacaoSA::item:hover {
                background-color: #f5f3ff;
            }
        """)
        self.tabela.setHorizontalHeaderLabels(self.COLUNAS)
        header = self.tabela.horizontalHeader()
        header.setStretchLastSection(True)
        # larguras fixas — descrição estica
        larguras = {
            0: 110,  # Kardex
            1: 110,  # Código
            # 2 Descrição fica stretch
            3: 70,   # Qtde
            4: 100,  # Custo unit
            5: 110,  # Custo total
            6: 130,  # Status
            7: 90,   # Qtde programada
            8: 90,   # Qtde entregue
        }
        for c, w in larguras.items():
            header.setSectionResizeMode(c, QHeaderView.ResizeMode.Fixed)
            header.resizeSection(c, w)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setStyleSheet(
            "QHeaderView::section {"
            "  font-size: 8.5px; font-weight: 700;"
            "  background-color: #f8fafc; color: #64748b;"
            "  text-transform: uppercase; letter-spacing: 0.3px;"
            "  padding: 0px; margin: 0px; border: none; border-bottom: 2px solid #e2e8f0;"
            "}"
        )
        self.tabela.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabela.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tabela.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabela.setAlternatingRowColors(True)
        self.tabela.verticalHeader().setDefaultSectionSize(32)
        self.tabela.verticalHeader().setMinimumSectionSize(28)
        self.tabela.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.tabela.verticalHeader().setVisible(False)
        self.tabela.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.tabela.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.tabela.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tabela.customContextMenuRequested.connect(self._context_menu)

        card_layout.addWidget(self.tabela, 1)
        layout.addWidget(card, 1)

    # ── Ações ─────────────────────────────────────────────────────────────
    def _abrir_dialog_inserir(self):
        dlg = DialogInserirItens(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            novos = dlg.obter_itens_selecionados()
            if not novos:
                self._mostrar_toast("Nenhum item com Qtde preenchida.", erro=True)
                return
            # evita duplicatas por kardex|codigo — atualiza qtde se já existe
            existentes = {f"{it.get('kardex','')}|{it.get('codigo','')}": idx for idx, it in enumerate(self.itens)}
            adicionados = 0
            atualizados = 0
            for novo in novos:
                chave = f"{novo.get('kardex','')}|{novo.get('codigo','')}"
                if chave in existentes:
                    idx = existentes[chave]
                    # soma qtde? por enquanto substitui e recalcula total
                    try:
                        # soma qtde existente + nova
                        q_antigo = self._parse_qtde(self.itens[idx].get("qtde", "0"))
                        q_novo = self._parse_qtde(novo.get("qtde", "0"))
                        q_total = (q_antigo or 0) + (q_novo or 0)
                        # mantém formato original com vírgula se houver
                        # formata com no-máximo 2 casas removendo zeros desnecessários?
                        # usa texto original somado: se ambos inteiros, mantém inteiro
                        if q_total == int(q_total):
                            novo_qtde_txt = str(int(q_total))
                        else:
                            novo_qtde_txt = f"{q_total:.2f}".replace(".", ",")
                        self.itens[idx]["qtde"] = novo_qtde_txt
                        # recalcula total
                        custo_f = self._parse_custo(novo.get("custo_unit", "0"))
                        total_f = (q_total or 0) * (custo_f or 0)
                        self.itens[idx]["custo_total"] = f"{total_f:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                    except Exception:
                        self.itens[idx] = novo
                    atualizados += 1
                else:
                    self.itens.append(novo)
                    adicionados += 1
            self._popular_tabela()
            if adicionados and atualizados:
                self._mostrar_toast(f"{adicionados} item(ns) adicionado(s), {atualizados} atualizado(s).", erro=False)
            elif adicionados:
                self._mostrar_toast(f"{adicionados} item(ns) adicionado(s).", erro=False)
            else:
                self._mostrar_toast(f"{atualizados} item(ns) atualizado(s) (qtde somada).", erro=False)

    def _parse_qtde(self, texto):
        t = str(texto).strip().replace(".", "").replace(",", ".") if "," in str(texto) else str(texto).strip()
        try:
            return float(t) if t else 0.0
        except ValueError:
            return 0.0

    def _parse_custo(self, texto):
        t = re.sub(r"[R$\s]", "", str(texto or ""))
        t = t.replace(".", "").replace(",", ".") if "," in t else t
        try:
            return float(t) if t else 0.0
        except ValueError:
            return 0.0

    def _popular_tabela(self):
        self.tabela.setRowCount(0)
        for item in self.itens:
            row = self.tabela.rowCount()
            self.tabela.insertRow(row)
            for col, chave in enumerate(self.CHAVES):
                valor = str(item.get(chave, ""))
                cell = QTableWidgetItem(valor)
                # read-only: sem flag Editable
                cell.setFlags(cell.flags() & ~Qt.ItemFlag.ItemIsEditable)
                # cores de status
                if chave == "status":
                    cor_bg = CORES_STATUS.get(valor, "")
                    if cor_bg:
                        cell.setData(Qt.BackgroundRole, QBrush(QColor(cor_bg)))
                        cor_txt = TEXTO_STATUS.get(valor, "#1e1b4b")
                        cell.setData(Qt.ForegroundRole, QBrush(QColor(cor_txt)))
                    cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                elif chave in ("qtde", "custo_unit", "custo_total", "qtde_programada", "qtde_entregue"):
                    cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    if chave == "custo_total" and valor:
                        cell.setToolTip(f"R$ {valor}")
                    if chave == "custo_unit" and valor:
                        cell.setToolTip(f"R$ {valor}")
                elif chave in ("kardex", "codigo"):
                    if valor:
                        cell.setToolTip(valor)
                    cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.tabela.setItem(row, col, cell)
        self._atualizar_contador()

    def _atualizar_contador(self):
        total = len(self.itens)
        if total == 1:
            self.label_contador.setText("1 item")
        else:
            self.label_contador.setText(f"{total} itens")

    def _limpar_formulario(self):
        resp = QMessageBox.question(
            self, "Limpar", "Limpar cabeçalho e todos os itens da tabela?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if resp != QMessageBox.StandardButton.Yes:
            return
        for campo in [self.campo_nome_emissor, self.campo_projeto_debito,
                      self.campo_conta_debito, self.campo_destino, self.campo_local_entrega,
                      self.campo_entregar_para]:
            campo.clear()
        self.campo_num_req.clear()
        self.campo_data_necessidade.setDate(QDate.currentDate())
        self.itens.clear()
        self._popular_tabela()
        self._mostrar_toast("Formulário limpo.", erro=False)

    def _cancelar_sa(self):
        # Cancela e limpa sem confirmação extra? Mantém confirmação para evitar perda
        resp = QMessageBox.question(
            self, "Cancelar", "Cancelar solicitação? Todos os dados serão perdidos.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if resp != QMessageBox.StandardButton.Yes:
            return
        for campo in [self.campo_nome_emissor, self.campo_projeto_debito,
                      self.campo_conta_debito, self.campo_destino, self.campo_local_entrega,
                      self.campo_entregar_para]:
            campo.clear()
        self.campo_num_req.clear()
        self.campo_data_necessidade.setDate(QDate.currentDate())
        self.itens.clear()
        self._popular_tabela()
        self._mostrar_toast("Solicitação cancelada.", erro=False)

    def _cadastrar_sa(self):
        # Validações mínimas
        nome = self.campo_nome_emissor.text().strip()
        if not nome:
            self._mostrar_toast("Informe o Nome do emissor.", erro=True)
            self.campo_nome_emissor.setFocus()
            return
        if not self.itens:
            self._mostrar_toast("Insira ao menos um item na tabela.", erro=True)
            return
        # Nº de requisição e Nº da SA são diferentes:
        # - campo Nº de requisição = digitado pelo usuário (começa vazio, permanece editável)
        # - nº da SA = gerado automaticamente sequencialmente (nome do arquivo)
        numero_req_usuario = self.campo_num_req.text().strip()
        proximo_num = self._obter_proximo_numero_sa()
        # garante que arquivo não existe (evita colisão se pasta tiver gaps ou concorrência)
        try:
            import config
            base = config.obter_caminho_jsons()
            pasta_tmp = os.path.normpath(os.path.join(base, "Almox", "SA")) if base else ""
        except Exception:
            pasta_tmp = ""
        if pasta_tmp:
            # verifica colisão e avança se necessário
            try:
                os.makedirs(pasta_tmp, exist_ok=True)
                cand = os.path.join(pasta_tmp, f"{proximo_num}.json")
                tentativas = 0
                while os.path.exists(cand) and tentativas < 5000:
                    try:
                        proximo_num = str(int(proximo_num) + 1)
                    except Exception:
                        proximo_num = f"{proximo_num}_1"
                        break
                    cand = os.path.join(pasta_tmp, f"{proximo_num}.json")
                    tentativas += 1
            except Exception:
                pass
        # Monta payload da SA — numero_req é o digitado pelo usuário, numero_sa é o gerado
        sa_dados = {
            "nome_emissor": nome,
            "numero_req": numero_req_usuario,
            "numero_sa": proximo_num,
            "projeto_debito": self.campo_projeto_debito.text().strip(),
            "conta_debito": self.campo_conta_debito.text().strip(),
            "destino": self.campo_destino.text().strip(),
            "local_entrega": self.campo_local_entrega.text().strip(),
            "entregar_para": self.campo_entregar_para.text().strip(),
            "data_necessidade": self.campo_data_necessidade.date().toString("dd/MM/yyyy"),
            "itens": list(self.itens),
        }
        # Tenta persistir em Almox/SA ou exibe toast
        try:
            import config
            base = config.obter_caminho_jsons()
            if base:
                pasta = os.path.normpath(os.path.join(base, "Almox", "SA"))
                os.makedirs(pasta, exist_ok=True)
                caminho = os.path.join(pasta, f"{proximo_num}.json")
                # evita sobrescrever: loop já garantiu, mas confere novamente
                cnt = 0
                while os.path.exists(caminho) and cnt < 5000:
                    try:
                        proximo_num = str(int(proximo_num) + 1)
                    except Exception:
                        break
                    sa_dados["numero_sa"] = proximo_num
                    caminho = os.path.join(pasta, f"{proximo_num}.json")
                    cnt += 1
                with open(caminho, "w", encoding="utf-8") as f:
                    json.dump(sa_dados, f, ensure_ascii=False, indent=2)
                self._mostrar_toast(f"SA {proximo_num} cadastrada com {len(self.itens)} item(ns).", erro=False)
                # Limpa todos os campos (Nº de requisição volta a ficar vazio, é diferente da SA)
                for campo in [self.campo_nome_emissor, self.campo_num_req, self.campo_projeto_debito,
                              self.campo_conta_debito, self.campo_destino, self.campo_local_entrega,
                              self.campo_entregar_para]:
                    campo.clear()
                self.campo_data_necessidade.setDate(QDate.currentDate())
                self.itens.clear()
                self._popular_tabela()
                return
        except Exception as e:
            self._mostrar_toast(f"Erro ao salvar SA: {e}", erro=True)
            return
        # fallback sem pasta configurada — apenas simula
        qtd = len(self.itens)
        self._mostrar_toast(f"SA {proximo_num} cadastrada (simulação) — {qtd} item(ns).", erro=False)
        for campo in [self.campo_nome_emissor, self.campo_num_req, self.campo_projeto_debito,
                      self.campo_conta_debito, self.campo_destino, self.campo_local_entrega,
                      self.campo_entregar_para]:
            campo.clear()
        self.campo_data_necessidade.setDate(QDate.currentDate())
        self.itens.clear()
        self._popular_tabela()

    def _context_menu(self, pos):
        item = self.tabela.itemAt(pos)
        if item is None:
            return
        row = item.row()
        menu = QMenu(self)
        act_remover = menu.addAction(qtawesome.icon('fa6s.trash', color='#ef4444'), "Remover item")
        act = menu.exec(QCursor.pos())
        if act == act_remover:
            if 0 <= row < len(self.itens):
                ident = self.itens[row].get("codigo") or self.itens[row].get("kardex") or f"linha {row+1}"
                confirm = QMessageBox.question(self, "Remover", f"Remover \"{ident}\" da tabela?",
                                               QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                if confirm == QMessageBox.StandardButton.Yes:
                    self.itens.pop(row)
                    self._popular_tabela()
                    self._mostrar_toast(f"\"{ident}\" removido.", erro=False)

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
