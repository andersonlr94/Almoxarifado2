import json
import os

import pyautogui
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QMessageBox,
)
from ui.regras_automacao import esperar_inicio, digitar_texto, enter


def _caminho_json():
    import config
    base = config.obter_caminho_jsons()
    if not base:
        base = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "jsons")
    return os.path.normpath(os.path.join(base, "Almox", "RemoveLocDuplicadas", "remove_loc_duplicadas.json"))


class RemoveLocDuplicadasPage(QWidget):
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

        titulo = QLabel("Remove Loc Duplicadas")
        titulo.setObjectName("pageTitle")
        card_layout.addWidget(titulo)

        grid_botoes = QHBoxLayout()
        grid_botoes.setSpacing(8)
        grid_botoes.setContentsMargins(0, 0, 0, 0)

        self.btn_colar = QPushButton("Colar")
        self.btn_colar.setObjectName("btnSecondary")
        self.btn_colar.setFixedWidth(130)
        self.btn_colar.clicked.connect(self._colar)
        grid_botoes.addWidget(self.btn_colar)

        self.btn_executar = QPushButton("Executar")
        self.btn_executar.setObjectName("btnPrimary")
        self.btn_executar.setFixedWidth(130)
        self.btn_executar.clicked.connect(self._executar)
        grid_botoes.addWidget(self.btn_executar)

        self.btn_voltar_loc = QPushButton("Voltar Loc")
        self.btn_voltar_loc.setObjectName("btnPrimary")
        self.btn_voltar_loc.setFixedWidth(130)
        self.btn_voltar_loc.clicked.connect(self._voltar_loc)
        grid_botoes.addWidget(self.btn_voltar_loc)

        self.btn_limpar = QPushButton("Limpar")
        self.btn_limpar.setObjectName("btnDanger")
        self.btn_limpar.setFixedWidth(130)
        self.btn_limpar.clicked.connect(self._limpar)
        grid_botoes.addWidget(self.btn_limpar)

        grid_botoes.addStretch()

        self.label_contador = QLabel("0 itens")
        self.label_contador.setObjectName("statusLabel")
        grid_botoes.addWidget(self.label_contador)

        card_layout.addLayout(grid_botoes)

        self.tabela = QTableWidget(0, 4)
        self.tabela.setHorizontalHeaderLabels(
            ["Item", "Referência", "UM", "Qde em mãos"]
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
            self.tabela.setItem(row, 1, QTableWidgetItem(str(registro.get("referencia", ""))))
            self.tabela.setItem(row, 2, QTableWidgetItem(str(registro.get("um", ""))))
            self.tabela.setItem(row, 3, QTableWidgetItem(str(registro.get("qde_em_maos", ""))))
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
            referencia = partes[1].upper() if len(partes) > 1 else ""
            um = partes[2].upper() if len(partes) > 2 else ""
            qde_em_maos = partes[3].upper() if len(partes) > 3 else ""
            self.dados.append({
                "item": item,
                "referencia": referencia,
                "um": um,
                "qde_em_maos": qde_em_maos
            })
        self._salvar_json()
        self._popular_tabela()

    def _executar(self):
        if self.tabela.rowCount() == 0:
            QMessageBox.information(self, "Executar", "Nenhum item na tabela.")
            return

        # Agrupar itens por Kardex (item)
        grouped = {}
        for registro in self.dados:
            item_id = registro.get("item", "").strip().upper()
            if not item_id:
                continue
            if item_id not in grouped:
                grouped[item_id] = []
            grouped[item_id].append(registro)

        transferencias_para_fazer = []
        for item_id, records in grouped.items():
            rec_recebe = None
            rec_outra = None
            for r in records:
                ref = r.get("referencia", "").strip().upper()
                if ref == "RECEBE":
                    rec_recebe = r
                else:
                    rec_outra = r
            
            if rec_recebe and rec_outra:
                qtde = rec_recebe.get("qde_em_maos", "").strip()
                para_lote = rec_outra.get("referencia", "").strip().upper()
                
                transferencias_para_fazer.append({
                    "kardex": item_id,
                    "qtde": qtde,
                    "de_local": "10912",
                    "de_lugar": "ZCENTRAL",
                    "de_lote": "RECEBE",
                    "para_local": "10912",
                    "para_lugar": "ZCENTRAL",
                    "para_lote": para_lote
                })

        if not transferencias_para_fazer:
            QMessageBox.warning(
                self, 
                "Executar", 
                "Nenhum par de itens correspondentes (RECEBE + Outra Loc) encontrado para execução."
            )
            return

        esperar_inicio()

        for t in transferencias_para_fazer:
            kardex = t["kardex"]
            qtde = t["qtde"]
            de_local = t["de_local"]
            de_lugar = t["de_lugar"]
            de_lote = t["de_lote"]
            para_local = t["para_local"]
            para_lugar = t["para_lugar"]
            para_lote = t["para_lote"]

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

            digitar_texto(de_lote)
            enter(2)

            digitar_texto(para_local)
            enter()

            digitar_texto(para_lugar)
            enter()

            digitar_texto(para_lote)
            enter(3)

            pyautogui.press("f4")

    def _voltar_loc(self):
        if self.tabela.rowCount() == 0:
            QMessageBox.information(self, "Voltar Loc", "Nenhum item na tabela.")
            return

        # Agrupar itens por Kardex (item)
        grouped = {}
        for registro in self.dados:
            item_id = registro.get("item", "").strip().upper()
            if not item_id:
                continue
            if item_id not in grouped:
                grouped[item_id] = []
            grouped[item_id].append(registro)

        transferencias_para_fazer = []
        for item_id, records in grouped.items():
            rec_recebe = None
            rec_outra = None
            for r in records:
                ref = r.get("referencia", "").strip().upper()
                if ref == "RECEBE":
                    rec_recebe = r
                else:
                    rec_outra = r
            
            if rec_recebe and rec_outra:
                qtde = rec_recebe.get("qde_em_maos", "").strip()
                de_lote = rec_outra.get("referencia", "").strip().upper()
                
                transferencias_para_fazer.append({
                    "kardex": item_id,
                    "qtde": qtde,
                    "de_local": "10912",
                    "de_lugar": "ZCENTRAL",
                    "de_lote": de_lote,
                    "para_local": "10912",
                    "para_lugar": "ZCENTRAL",
                    "para_lote": "RECEBE"
                })

        if not transferencias_para_fazer:
            QMessageBox.warning(
                self, 
                "Voltar Loc", 
                "Nenhum par de itens correspondentes (RECEBE + Outra Loc) encontrado para execução."
            )
            return

        esperar_inicio()

        for t in transferencias_para_fazer:
            kardex = t["kardex"]
            qtde = t["qtde"]
            de_local = t["de_local"]
            de_lugar = t["de_lugar"]
            de_lote = t["de_lote"]
            para_local = t["para_local"]
            para_lugar = t["para_lugar"]
            para_lote = t["para_lote"]

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

            digitar_texto(de_lote)
            enter(2)

            digitar_texto(para_local)
            enter()

            digitar_texto(para_lugar)
            enter()

            digitar_texto(para_lote)
            enter(3)

            pyautogui.press("f4")

    def _limpar(self):
        self.dados.clear()
        self._salvar_json()
        self._popular_tabela()

    def _salvar_json(self):
        try:
            os.makedirs(os.path.dirname(_caminho_json()), exist_ok=True)
            with open(_caminho_json(), "w", encoding="utf-8") as f:
                json.dump(self.dados, f, ensure_ascii=False, indent=2)
        except OSError:
            pass
