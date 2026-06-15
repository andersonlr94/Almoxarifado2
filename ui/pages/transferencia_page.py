import json
import os

import pyautogui
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit,
    QPushButton, QRadioButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QButtonGroup, QMessageBox,
)
from ui.regras_automacao import esperar_inicio, digitar_texto, enter


def _caminho_json():
    import config
    base = config.obter_caminho_jsons()
    if not base:
        base = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "jsons")
    return os.path.normpath(os.path.join(base, "Almox", "Transferencias", "transferencias.json"))


class TransferenciaPage(QWidget):
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

        titulo = QLabel("Transferência de itens")
        titulo.setObjectName("pageTitle")
        card_layout.addWidget(titulo)

        grid = QGridLayout()
        grid.setHorizontalSpacing(4)
        grid.setVerticalSpacing(0)
        grid.setContentsMargins(0, 0, 0, 0)

        self.campo_de_local = QLineEdit("10912")
        self.campo_de_local.setPlaceholderText("De Local")
        self.campo_de_local.setFixedWidth(163)
        grid.addWidget(self.campo_de_local, 0, 0)

        self.campo_de_lugar = QLineEdit("ZCENTRAL")
        self.campo_de_lugar.setPlaceholderText("De lugar")
        self.campo_de_lugar.setFixedWidth(163)
        grid.addWidget(self.campo_de_lugar, 1, 0)

        self.campo_de_lote = QLineEdit()
        self.campo_de_lote.setPlaceholderText("De lote")
        self.campo_de_lote.setFixedWidth(163)
        grid.addWidget(self.campo_de_lote, 2, 0)

        self.campo_para_local = QLineEdit("10912")
        self.campo_para_local.setPlaceholderText("Para Local")
        self.campo_para_local.setFixedWidth(163)
        grid.addWidget(self.campo_para_local, 0, 1)

        self.campo_para_lugar = QLineEdit("ZCENTRAL")
        self.campo_para_lugar.setPlaceholderText("Para lugar")
        self.campo_para_lugar.setFixedWidth(163)
        grid.addWidget(self.campo_para_lugar, 1, 1)

        self.campo_para_lote = QLineEdit()
        self.campo_para_lote.setPlaceholderText("Para Lote")
        self.campo_para_lote.setFixedWidth(163)
        grid.addWidget(self.campo_para_lote, 2, 1)

        self.grupo_radio = QButtonGroup(self)
        self.radio_formulario = QRadioButton("Usar formulario")
        self.radio_lote_inicial = QRadioButton("Usar lote inicial")
        self.radio_lote_destino = QRadioButton("Usar lote destino")
        self.radio_formulario.setChecked(True)
        self.grupo_radio.addButton(self.radio_formulario)
        self.grupo_radio.addButton(self.radio_lote_inicial)
        self.grupo_radio.addButton(self.radio_lote_destino)
        grid.addWidget(self.radio_formulario, 0, 2)
        grid.addWidget(self.radio_lote_inicial, 1, 2)
        grid.addWidget(self.radio_lote_destino, 2, 2)

        self.btn_colar = QPushButton("Colar")
        self.btn_colar.setObjectName("btnSecondary")
        self.btn_colar.setFixedWidth(130)
        self.btn_colar.clicked.connect(self._colar)
        grid.addWidget(self.btn_colar, 0, 3)

        self.btn_executar = QPushButton("Executar")
        self.btn_executar.setObjectName("btnPrimary")
        self.btn_executar.setFixedWidth(130)
        self.btn_executar.clicked.connect(self._executar)
        grid.addWidget(self.btn_executar, 1, 3)

        self.btn_limpar = QPushButton("Limpar")
        self.btn_limpar.setObjectName("btnDanger")
        self.btn_limpar.setFixedWidth(130)
        self.btn_limpar.clicked.connect(self._limpar)
        grid.addWidget(self.btn_limpar, 2, 3)

        card_layout.addLayout(grid)

        info_linha = QHBoxLayout()
        info_linha.setSpacing(16)
        info_linha.addStretch()
        self.label_contador = QLabel("0 itens")
        self.label_contador.setObjectName("statusLabel")
        info_linha.addWidget(self.label_contador)
        card_layout.addLayout(info_linha)

        self.tabela = QTableWidget(0, 3)
        self.tabela.setHorizontalHeaderLabels(
            ["Item", "Qtde", "Lote"]
        )
        header = self.tabela.horizontalHeader()
        header.setStretchLastSection(True)
        for c in range(self.tabela.columnCount()):
            header.setSectionResizeMode(c, QHeaderView.ResizeMode.Stretch)
        self.tabela.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabela.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabela.setAlternatingRowColors(True)
        self.tabela.verticalHeader().setDefaultSectionSize(36)
        self.tabela.verticalHeader().setMinimumSectionSize(28)
        self.tabela.verticalHeader().setVisible(False)
        card_layout.addWidget(self.tabela)

        layout.addWidget(card)

        self.radio_formulario.toggled.connect(self._atualizar_bloqueio_lotes)
        self.radio_lote_inicial.toggled.connect(self._atualizar_bloqueio_lotes)
        self.radio_lote_destino.toggled.connect(self._atualizar_bloqueio_lotes)

    def _atualizar_bloqueio_lotes(self):
        if self.radio_lote_inicial.isChecked():
            self.campo_de_lote.setEnabled(False)
            self.campo_para_lote.setEnabled(True)
        elif self.radio_lote_destino.isChecked():
            self.campo_para_lote.setEnabled(False)
            self.campo_de_lote.setEnabled(True)
        else:
            self.campo_de_lote.setEnabled(True)
            self.campo_para_lote.setEnabled(True)

    def _carregar_dados(self):
        try:
            with open(_caminho_json(), "r", encoding="utf-8") as f:
                self.dados = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.dados = []
        self._popular_tabela()

    def _popular_tabela(self):
        self.tabela.setRowCount(0)
        for registro in self.dados:
            row = self.tabela.rowCount()
            self.tabela.insertRow(row)
            self.tabela.setItem(row, 0, QTableWidgetItem(str(registro.get("item", ""))))
            self.tabela.setItem(row, 1, QTableWidgetItem(str(registro.get("qtde", ""))))
            self.tabela.setItem(row, 2, QTableWidgetItem(str(registro.get("lote", ""))))
        self._atualizar_contador()

    def _atualizar_contador(self):
        self.label_contador.setText(f"{self.tabela.rowCount()} itens")

    def _colar(self):
        from PySide6.QtGui import QGuiApplication
        texto = QGuiApplication.clipboard().text()
        if not texto:
            return
        linhas = texto.strip().splitlines()
        if not linhas:
            return

        for linha in linhas:
            partes = [p.strip() for p in linha.split("\t") if p.strip()]
            if not partes:
                continue
            item = partes[0].upper()
            qtde = partes[1].upper() if len(partes) > 1 else ""
            lote = partes[2].upper() if len(partes) > 2 else ""
            self.dados.append({"item": item, "qtde": qtde, "lote": lote})
        self._salvar_json()
        self._popular_tabela()

    def _executar(self):
        if self.tabela.rowCount() == 0:
            QMessageBox.information(self, "Executar", "Nenhum item na tabela.")
            return

        de_local = self.campo_de_local.text().strip().upper()
        de_lugar = self.campo_de_lugar.text().strip().upper()
        de_lote = self.campo_de_lote.text().strip().upper()
        para_local = self.campo_para_local.text().strip().upper()
        para_lugar = self.campo_para_lugar.text().strip().upper()
        para_lote = self.campo_para_lote.text().strip().upper()

        esperar_inicio()

        for row in range(self.tabela.rowCount()):
            kardex = self.tabela.item(row, 0).text().upper() if self.tabela.item(row, 0) else ""
            qtde = self.tabela.item(row, 1).text().upper() if self.tabela.item(row, 1) else ""
            lote_tabela = self.tabela.item(row, 2).text().upper() if self.tabela.item(row, 2) else ""

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

            pyautogui.press("f4")

    def _limpar(self):
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
        try:
            os.makedirs(os.path.dirname(_caminho_json()), exist_ok=True)
            with open(_caminho_json(), "w", encoding="utf-8") as f:
                json.dump(self.dados, f, ensure_ascii=False, indent=2)
        except OSError:
            pass
