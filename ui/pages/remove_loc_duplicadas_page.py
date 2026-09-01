import json
import os

import pyautogui
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QMessageBox, QApplication,
)
from PySide6.QtCore import Qt

import matplotlib
matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from ui.regras_automacao import esperar_inicio, digitar_texto, enter


def _caminho_json():
    import config
    base = config.obter_caminho_jsons()
    if not base:
        return ""
    return os.path.normpath(os.path.join(base, "Almox", "RemoveLocDuplicadas", "remove_loc_duplicadas.json"))


class RemoveLocDuplicadasPage(QWidget):
    def __init__(self):
        super().__init__()
        self.dados = []
        self._total_transferencias = 0
        self._transferencias_concluidas = 0
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

        # ── Linha de conteúdo: tabela à esquerda, gráfico à direita ──
        conteudo_row = QHBoxLayout()
        conteudo_row.setSpacing(16)

        # Painel esquerdo (Tabela)
        painel_tabela = QWidget()
        painel_tabela_layout = QVBoxLayout(painel_tabela)
        painel_tabela_layout.setContentsMargins(0, 0, 0, 0)
        painel_tabela_layout.setSpacing(8)

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
        painel_tabela_layout.addWidget(self.tabela)

        conteudo_row.addWidget(painel_tabela, stretch=1)

        # ── Card do gráfico de progresso (à direita) ──
        grafico_card = QWidget()
        grafico_card.setObjectName("statCard")
        grafico_card.setFixedWidth(320)
        grafico_card_layout = QVBoxLayout(grafico_card)
        grafico_card_layout.setContentsMargins(16, 14, 16, 14)
        grafico_card_layout.setSpacing(8)

        grafico_header = QHBoxLayout()
        self.grafico_titulo = QLabel("Progresso das Transferências")
        self.grafico_titulo.setObjectName("sectionTitle")
        grafico_header.addWidget(self.grafico_titulo)
        grafico_header.addStretch()
        grafico_card_layout.addLayout(grafico_header)

        self.canvas_grafico = FigureCanvas(Figure(figsize=(2.6, 2.6)))
        self.canvas_grafico.setMinimumHeight(260)
        self.canvas_grafico.setMinimumWidth(260)
        self.canvas_grafico.setParent(self)
        grafico_card_layout.addWidget(self.canvas_grafico)

        self.grafico_subtitulo = QLabel("")
        self.grafico_subtitulo.setObjectName("pageSubtitle")
        self.grafico_subtitulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        grafico_card_layout.addWidget(self.grafico_subtitulo)

        grafico_card_layout.addStretch()
        conteudo_row.addWidget(grafico_card)

        card_layout.addLayout(conteudo_row)

        layout.addWidget(card)
        self._atualizar_grafico()

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

    def _calcular_total_transferencias(self):
        grouped = {}
        for registro in self.dados:
            item_id = registro.get("item", "").strip().upper()
            if not item_id:
                continue
            if item_id not in grouped:
                grouped[item_id] = []
            grouped[item_id].append(registro)

        total = 0
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
                total += 1
        return total

    def _atualizar_grafico(self):
        pct = (self._transferencias_concluidas / self._total_transferencias * 100) if self._total_transferencias else 0

        self.grafico_subtitulo.setText(
            f"{self._transferencias_concluidas} de {self._total_transferencias} transferências" if self._total_transferencias else "Nenhuma transferência para realizar"
        )

        fig = self.canvas_grafico.figure
        fig.clear()
        ax = fig.add_subplot(111)

        if self._total_transferencias == 0:
            ax.text(0.5, 0.5, "Sem transferências", ha="center", va="center",
                    fontsize=12, color="#94a3b8")
            ax.axis("off")
        else:
            ax.pie(
                [self._transferencias_concluidas, self._total_transferencias - self._transferencias_concluidas],
                colors=["#10b981", "#e5e7eb"],
                startangle=90,
                counterclock=False,
                wedgeprops={"width": 0.28, "edgecolor": "white", "linewidth": 2},
            )
            ax.text(0.5, 0.52, f"{pct:.0f}%", ha="center", va="center",
                    fontsize=26, fontweight="bold", color="#1e1b4b")
            ax.text(0.5, 0.36, "concluído", ha="center", va="center",
                    fontsize=11, color="#94a3b8")
            ax.axis("equal")

        fig.tight_layout()
        self.canvas_grafico.draw()

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
        self._total_transferencias = self._calcular_total_transferencias()
        self._transferencias_concluidas = 0
        self._atualizar_grafico()

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

        self._total_transferencias = len(transferencias_para_fazer)
        self._transferencias_concluidas = 0
        self._atualizar_grafico()

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

            self._transferencias_concluidas += 1
            self._atualizar_grafico()
            QApplication.processEvents()

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

        self._total_transferencias = len(transferencias_para_fazer)
        self._transferencias_concluidas = 0
        self._atualizar_grafico()

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

            self._transferencias_concluidas += 1
            self._atualizar_grafico()
            QApplication.processEvents()

    def _limpar(self):
        self.dados.clear()
        self._salvar_json()
        self._popular_tabela()
        self._total_transferencias = 0
        self._transferencias_concluidas = 0
        self._atualizar_grafico()

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
