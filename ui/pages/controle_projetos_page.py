import json
import os
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QTabWidget, QApplication, QListWidget,
)
from PySide6.QtCore import Qt


HEADERS_DPH = [
    "Req", "Req necessidade", "Destino", "Kardex", "Código",
    "Qtde DPH", "conta", "Entidade", "Custo uni", "Custo total",
    "DPH", "Status Proj/Cta", "Imprimir",
]

TABLE_STYLE = """
QTableWidget {
    font-size: 11px;
    padding: 0px;
}
QTableWidget::item {
    padding: 2px 4px;
}
QHeaderView::section {
    font-size: 10px;
    padding: 2px 4px;
}
"""


def _caminho_pasta_dph():
    import config
    base = config.obter_caminho_jsons()
    if not base:
        base = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "jsons")
    return os.path.normpath(os.path.join(base, "Almox", "DPH"))


class ControleProjetosPage(QWidget):
    def __init__(self):
        super().__init__()
        self.dados_dph = []
        self._setup_ui()
        self._carregar_dados_dph()
        self._carregar_projetos()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(16)

        tabs = QTabWidget()
        tabs.addTab(self._aba_controle_projetos(), "Controle de Projetos")
        tabs.addTab(self._aba_inserir_dph(), "Inserir DPH")
        layout.addWidget(tabs)

    def _aba_controle_projetos(self):
        pag = QWidget()
        pag_layout = QVBoxLayout(pag)
        pag_layout.setContentsMargins(0, 0, 0, 0)
        pag_layout.setSpacing(16)

        linha = QHBoxLayout()
        linha.setSpacing(16)

        for titulo_texto in ("Projeto", "Requisições", "SA"):
            card = QWidget()
            card.setObjectName("pageCard")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(28, 28, 28, 28)
            card_layout.setSpacing(12)

            if titulo_texto == "SA":
                self.label_sa_titulo = QLabel("SA")
                self.label_sa_titulo.setObjectName("pageTitle")
                card_layout.addWidget(self.label_sa_titulo)
            else:
                titulo = QLabel(titulo_texto)
                titulo.setObjectName("pageTitle")
                card_layout.addWidget(titulo)

            if titulo_texto == "Projeto":
                self.lista_projetos = QListWidget()
                self.lista_projetos.setStyleSheet("font-size: 12px; border: none;")
                self.lista_projetos.currentTextChanged.connect(self._filtrar_requisicoes)
                card_layout.addWidget(self.lista_projetos)
            elif titulo_texto == "Requisições":
                self.lista_requisicoes = QListWidget()
                self.lista_requisicoes.setStyleSheet("font-size: 12px; border: none;")
                self.lista_requisicoes.currentTextChanged.connect(self._filtrar_sa)
                card_layout.addWidget(self.lista_requisicoes)
            else:

                self.tabela_sa = QTableWidget(0, 2)
                self.tabela_sa.setHorizontalHeaderLabels(["Código", "Qtde"])
                self.tabela_sa.setStyleSheet(TABLE_STYLE)
                header_sa = self.tabela_sa.horizontalHeader()
                header_sa.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
                header_sa.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
                header_sa.resizeSection(1, 80)
                self.tabela_sa.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
                self.tabela_sa.setAlternatingRowColors(True)
                self.tabela_sa.verticalHeader().setDefaultSectionSize(24)
                self.tabela_sa.verticalHeader().setVisible(False)
                card_layout.addWidget(self.tabela_sa)

            linha.addWidget(card)

        pag_layout.addLayout(linha)
        return pag

    def _aba_inserir_dph(self):
        pag = QWidget()
        pag_layout = QVBoxLayout(pag)
        pag_layout.setContentsMargins(0, 0, 0, 0)
        pag_layout.setSpacing(16)

        card = QWidget()
        card.setObjectName("pageCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(28, 28, 28, 28)
        card_layout.setSpacing(16)

        titulo = QLabel("Inserir DPH")
        titulo.setObjectName("pageTitle")
        card_layout.addWidget(titulo)

        linha_botoes = QHBoxLayout()
        linha_botoes.setSpacing(8)

        btn_colar = QPushButton("Colar")
        btn_colar.setObjectName("btnPrimary")
        btn_colar.setFixedHeight(34)
        btn_colar.clicked.connect(self._colar_dph)
        linha_botoes.addWidget(btn_colar)

        linha_botoes.addStretch()
        card_layout.addLayout(linha_botoes)

        self.tabela_dph = QTableWidget(0, len(HEADERS_DPH))
        self.tabela_dph.setHorizontalHeaderLabels(HEADERS_DPH)
        self.tabela_dph.setStyleSheet(TABLE_STYLE)
        header = self.tabela_dph.horizontalHeader()
        for c in range(self.tabela_dph.columnCount()):
            header.setSectionResizeMode(c, QHeaderView.ResizeMode.Stretch)
        self.tabela_dph.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabela_dph.setAlternatingRowColors(True)
        self.tabela_dph.verticalHeader().setDefaultSectionSize(24)
        self.tabela_dph.verticalHeader().setVisible(False)
        card_layout.addWidget(self.tabela_dph)

        pag_layout.addWidget(card)
        return pag

    def _colar_dph(self):
        clipboard = QApplication.clipboard()
        texto = clipboard.text()
        if not texto:
            return
        linhas = [l.strip() for l in texto.strip().split("\n") if l.strip()]
        if not linhas:
            return

        dados_novos = []
        for linha in linhas:
            partes = linha.split("\t")
            dados_novos.append(partes)

        self.tabela_dph.blockSignals(True)
        for partes in dados_novos:
            row = self.tabela_dph.rowCount()
            self.tabela_dph.insertRow(row)
            for col in range(min(len(partes), len(HEADERS_DPH))):
                self.tabela_dph.setItem(row, col, QTableWidgetItem(partes[col].strip()))
        self.tabela_dph.blockSignals(False)

        self._salvar_dph_json(dados_novos)
        self._carregar_projetos()

    def _carregar_dados_dph(self):
        self.dados_dph = []
        pasta = _caminho_pasta_dph()
        try:
            for nome in os.listdir(pasta):
                if not nome.endswith(".json"):
                    continue
                caminho = os.path.join(pasta, nome)
                try:
                    with open(caminho, "r", encoding="utf-8") as f:
                        dados = json.load(f)
                    if isinstance(dados, list):
                        self.dados_dph.extend(dados)
                except (json.JSONDecodeError, OSError):
                    pass
        except FileNotFoundError:
            pass

    def _filtrar_requisicoes(self, conta):
        self.lista_requisicoes.clear()
        if not conta:
            return
        itens = set()
        for registro in self.dados_dph:
            if registro.get("conta", "").strip() == conta:
                req_nec = registro.get("Req necessidade", "").strip()
                req = registro.get("Req", "").strip()
                if req_nec:
                    itens.add(f"{req_nec} - {req}" if req else req_nec)
        for item in sorted(itens):
            self.lista_requisicoes.addItem(item)

    def _filtrar_sa(self, texto):
        self.tabela_sa.setRowCount(0)
        if not texto or " - " not in texto:
            self.label_sa_titulo.setText("SA")
            return
        req = texto.split(" - ", 1)[1].strip()
        self.label_sa_titulo.setText(f"SA{req}")
        for registro in self.dados_dph:
            if registro.get("Req", "").strip() == req:
                row = self.tabela_sa.rowCount()
                self.tabela_sa.insertRow(row)
                self.tabela_sa.setItem(row, 0, QTableWidgetItem(registro.get("Código", "").strip()))
                self.tabela_sa.setItem(row, 1, QTableWidgetItem(registro.get("Qtde DPH", "").strip()))

    def _salvar_dph_json(self, dados_novos):
        pasta = _caminho_pasta_dph()
        os.makedirs(pasta, exist_ok=True)
        data_str = datetime.now().strftime("%d-%m-%Y")
        caminho = os.path.join(pasta, f"{data_str}.json")

        registros = []
        for partes in dados_novos:
            registro = {}
            for col in range(min(len(partes), len(HEADERS_DPH))):
                registro[HEADERS_DPH[col]] = partes[col].strip()
            registros.append(registro)

        if os.path.exists(caminho):
            try:
                with open(caminho, "r", encoding="utf-8") as f:
                    existentes = json.load(f)
                if not isinstance(existentes, list):
                    existentes = []
            except (json.JSONDecodeError, OSError):
                existentes = []
            existentes.extend(registros)
            registros = existentes

        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(registros, f, ensure_ascii=False, indent=2)

    def _carregar_projetos(self):
        pasta = _caminho_pasta_dph()
        os.makedirs(pasta, exist_ok=True)
        projetos = set()
        try:
            for nome in os.listdir(pasta):
                if not nome.endswith(".json"):
                    continue
                caminho = os.path.join(pasta, nome)
                try:
                    with open(caminho, "r", encoding="utf-8") as f:
                        dados = json.load(f)
                    if isinstance(dados, list):
                        for registro in dados:
                            conta = registro.get("conta", "").strip()
                            if conta:
                                projetos.add(conta)
                except (json.JSONDecodeError, OSError):
                    pass
        except FileNotFoundError:
            pass

        self.lista_projetos.clear()
        for proj in sorted(projetos):
            self.lista_projetos.addItem(proj)
