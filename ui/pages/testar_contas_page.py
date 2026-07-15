import json
import os

import pyautogui
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QMessageBox, QApplication,
    QStyledItemDelegate,
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor, QBrush, QPalette

from ui.regras_automacao import esperar_inicio, digitar_texto, enter


class RowHighlightDelegate(QStyledItemDelegate):
    """Delegate que pinta o fundo da célula a partir do BackgroundRole,
    ignorando o stylesheet global que sobrescreveria o setBackground()."""
    def paint(self, painter, option, index):
        bg = index.data(Qt.ItemDataRole.BackgroundRole)
        if bg is not None:
            brush = bg if isinstance(bg, QBrush) else QBrush(bg)
            painter.save()
            painter.fillRect(option.rect, brush)
            painter.restore()
            option.backgroundBrush = QBrush()  # evita que o pai pinte por cima
        super().paint(painter, option, index)


def _caminho_json():
    import config
    base = config.obter_caminho_jsons()
    if not base:
        base = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "jsons")
    return os.path.normpath(os.path.join(base, "Almox", "TestarContas", "testar_contas.json"))


HEADERS = ["Conta", "SubConta", "CC", "Projeto"]
CHAVES = ["conta", "subconta", "cc", "projeto"]

COR_LINHA_ATIVA = QColor("#3b82f6")  # azul claro


class TestarContasPage(QWidget):
    def __init__(self):
        super().__init__()
        self.dados = []
        self._setup_ui()
        self._carregar_dados()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        card = QWidget()
        card.setObjectName("pageCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(12, 12, 12, 12)
        card_layout.setSpacing(8)

        titulo = QLabel("Testar Contas")
        titulo.setObjectName("pageTitle")
        card_layout.addWidget(titulo)

        # ── Grid de campos + botões ──────────────────────────────────
        grid = QGridLayout()
        grid.setHorizontalSpacing(4)
        grid.setVerticalSpacing(4)
        grid.setContentsMargins(0, 0, 0, 0)

        lbl_kardex = QLabel("Kardex")
        lbl_kardex.setObjectName("fieldLabel")
        grid.addWidget(lbl_kardex, 0, 0)

        self.campo_kardex = QLineEdit("3ACD100120002964")
        self.campo_kardex.setPlaceholderText("Kardex")
        self.campo_kardex.setFixedWidth(200)
        grid.addWidget(self.campo_kardex, 1, 0)

        lbl_dph = QLabel("DPH")
        lbl_dph.setObjectName("fieldLabel")
        grid.addWidget(lbl_dph, 0, 1)

        self.campo_dph = QLineEdit()
        self.campo_dph.setPlaceholderText("DPH")
        self.campo_dph.setFixedWidth(160)
        grid.addWidget(self.campo_dph, 1, 1)

        self.btn_colar = QPushButton("Colar")
        self.btn_colar.setObjectName("btnSecondary")
        self.btn_colar.setFixedWidth(110)
        self.btn_colar.clicked.connect(self._colar)
        grid.addWidget(self.btn_colar, 1, 2)

        self.btn_limpar = QPushButton("Limpar")
        self.btn_limpar.setObjectName("btnDanger")
        self.btn_limpar.setFixedWidth(110)
        self.btn_limpar.clicked.connect(self._limpar)
        grid.addWidget(self.btn_limpar, 1, 3)

        self.btn_executar = QPushButton("Executar")
        self.btn_executar.setObjectName("btnPrimary")
        self.btn_executar.setFixedWidth(110)
        self.btn_executar.clicked.connect(self._executar)
        grid.addWidget(self.btn_executar, 1, 4)

        card_layout.addLayout(grid)

        # ── Contador ────────────────────────────────────────────────
        info_linha = QHBoxLayout()
        info_linha.setSpacing(16)
        info_linha.addStretch()
        self.label_contador = QLabel("0 itens")
        self.label_contador.setObjectName("statusLabel")
        info_linha.addWidget(self.label_contador)
        card_layout.addLayout(info_linha)

        # ── Tabela ──────────────────────────────────────────────────
        self.tabela = QTableWidget(0, len(HEADERS))
        self.tabela.setHorizontalHeaderLabels(HEADERS)
        header = self.tabela.horizontalHeader()
        header.setStretchLastSection(True)
        for c in range(self.tabela.columnCount()):
            header.setSectionResizeMode(c, QHeaderView.ResizeMode.Stretch)
        self.tabela.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabela.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabela.setAlternatingRowColors(False)
        self.tabela.verticalHeader().setDefaultSectionSize(28)
        self.tabela.verticalHeader().setMinimumSectionSize(22)
        self.tabela.verticalHeader().setVisible(False)
        self.tabela.setItemDelegate(RowHighlightDelegate(self.tabela))
        card_layout.addWidget(self.tabela)

        layout.addWidget(card)

    # ── Persistência ────────────────────────────────────────────────

    def _carregar_dados(self):
        try:
            with open(_caminho_json(), "r", encoding="utf-8") as f:
                self.dados = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.dados = []
        self._popular_tabela()

    def _salvar_json(self):
        try:
            os.makedirs(os.path.dirname(_caminho_json()), exist_ok=True)
            with open(_caminho_json(), "w", encoding="utf-8") as f:
                json.dump(self.dados, f, ensure_ascii=False, indent=2)
        except OSError:
            pass

    # ── Tabela helpers ──────────────────────────────────────────────

    def _popular_tabela(self, linha_ativa=-1):
        self.tabela.setRowCount(0)
        for idx, registro in enumerate(self.dados):
            row = self.tabela.rowCount()
            self.tabela.insertRow(row)
            for col, chave in enumerate(CHAVES):
                cell = QTableWidgetItem(str(registro.get(chave, "")))
                if idx == linha_ativa:
                    cell.setBackground(QBrush(COR_LINHA_ATIVA))
                    cell.setForeground(QBrush(QColor("#ffffff")))
                self.tabela.setItem(row, col, cell)
        self._atualizar_contador()

    def _atualizar_contador(self):
        self.label_contador.setText(f"{len(self.dados)} itens")

    def _destacar_linha(self, row_idx):
        """Pinta a linha ativa de azul e limpa as demais."""
        for row in range(self.tabela.rowCount()):
            eh_ativa = row == row_idx
            for col in range(self.tabela.columnCount()):
                cell = self.tabela.item(row, col)
                if cell is None:
                    continue
                if eh_ativa:
                    cell.setBackground(QBrush(COR_LINHA_ATIVA))
                    cell.setForeground(QBrush(QColor("#ffffff")))
                else:
                    cell.setBackground(QBrush(QColor("#ffffff")))
                    cell.setForeground(QBrush(QColor("#1e293b")))
        if row_idx >= 0:
            self.tabela.scrollToItem(self.tabela.item(row_idx, 0))

    # ── Slots dos botões ────────────────────────────────────────────

    def _colar(self):
        from PySide6.QtGui import QGuiApplication
        texto = QGuiApplication.clipboard().text()
        if not texto:
            return
        linhas = texto.strip().splitlines()
        for linha in linhas:
            partes = [p.strip() for p in linha.split("\t")]
            # Aceita linhas com 1 a 4 colunas
            conta    = partes[0].upper() if len(partes) > 0 else ""
            subconta = partes[1].upper() if len(partes) > 1 else ""
            cc       = partes[2].upper() if len(partes) > 2 else ""
            projeto  = partes[3].upper() if len(partes) > 3 else ""
            if not conta:
                continue
            self.dados.append({
                "conta": conta,
                "subconta": subconta,
                "cc": cc,
                "projeto": projeto,
            })
        self._salvar_json()
        self._popular_tabela()

    def _limpar(self):
        self.dados.clear()
        self._salvar_json()
        self._popular_tabela()

    def _executar(self):
        if not self.dados:
            QMessageBox.information(self, "Executar", "Nenhum item na tabela.")
            return

        kardex = self.campo_kardex.text().strip()
        dph    = self.campo_dph.text().strip()

        if not kardex:
            QMessageBox.warning(self, "Executar", "Preencha o campo Kardex.")
            return
        if not dph:
            QMessageBox.warning(self, "Executar", "Preencha o campo DPH.")
            return

        esperar_inicio()

        for idx, item in enumerate(self.dados):
            # Destaca a linha corrente em azul e força repaint
            self._destacar_linha(idx)
            QApplication.processEvents()

            conta    = item.get("conta", "")
            subconta = item.get("subconta", "")
            cc       = item.get("cc", "")
            projeto  = item.get("projeto", "")

            # 1 - digitar kardex
            digitar_texto(kardex)
            # 2 - enter
            enter()
            # 3 - digitar "1"
            digitar_texto("1")
            # 4 - enter 5 vezes
            enter(5)
            # 5 - F2
            pyautogui.press("f2")
            # 6 - enter 4 vezes
            enter(5)
            # 7 - digitar "sOutrasI"
            digitar_texto("sOutrasI")
            # 8 - enter
            enter()
            # 9 - digitar DPH
            digitar_texto(dph)
            # 10 - enter 6 vezes
            enter(6)
            # 11 - conta
            digitar_texto(conta)
            # 12 - enter
            enter()
            # 13 - subconta
            digitar_texto(subconta)
            # 14 - enter
            enter()
            # 15 - CC
            digitar_texto(cc)
            # 16 - enter
            enter()
            # 17 - Ctrl+Z para limpar campo, depois digitar projeto
            pyautogui.hotkey('ctrl', 'z')
            digitar_texto(projeto)
            # 18 - enter
            enter()           
            # 19 - F4 (delay de 1s antes de confirmar)
            import time; time.sleep(1)
            pyautogui.press("f4")
            # 20 - próximo item (loop continua)

        # Remove destaque ao finalizar
        self._popular_tabela()
