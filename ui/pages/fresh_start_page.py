import json
import os
import shutil
import subprocess
import time
from datetime import datetime
from urllib.parse import quote

import matplotlib
matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter

import qtawesome

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QStyledItemDelegate, QFileDialog, QMessageBox, QDialog,
    QComboBox, QCheckBox, QFrame, QSizePolicy,
)
from PySide6.QtCore import Qt, QSize, QRect
from PySide6.QtGui import QPainter, QColor
from ui.regras_automacao import digitar_texto, enter, esperar_inicio
from ui.pages.dpp_ativos_page import CredentialsDialog
import pyautogui

try:
    from openpyxl import Workbook
    from openpyxl.styles import Font
    OPENPYXL_DISPONIVEL = True
except ImportError:
    OPENPYXL_DISPONIVEL = False

import config


def _caminho_json():
    base = config.obter_caminho_jsons()
    if not base:
        return ""
    return os.path.normpath(os.path.join(base, "Almox", "FreshStart", "fresh_start.json"))


def _caminho_zcentral():
    base = config.obter_caminho_jsons()
    if not base:
        return ""
    return os.path.normpath(os.path.join(base, "Almox", "zCentral.prn"))


def _caminho_dados_fresh_start():
    base = config.obter_caminho_jsons()
    if not base:
        return ""
    return os.path.normpath(os.path.join(base, "Almox", "FreshStart", "DadosFreshStart", "DadosFreshStart.json"))


def _caminho_estoque():
    base = config.obter_caminho_jsons()
    if not base:
        return ""
    return os.path.normpath(os.path.join(base, "Almox", "ItensAlmoxarifado", "ItensAlmoxarifado.json"))


def _caminho_zcusto():
    base = config.obter_caminho_jsons()
    if not base:
        return ""
    return os.path.normpath(os.path.join(base, "Almox", "zCusto.prn"))


def _parse_numero(texto):
    texto = texto.strip()
    if not texto:
        return 0.0
    return float(texto.replace(".", "").replace(",", "."))


def _carregar_historico():
    caminho = _caminho_dados_fresh_start()
    if not caminho or not os.path.isfile(caminho):
        return []
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            conteudo = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []
    if not isinstance(conteudo, list):
        return []
    registros = []
    for item in conteudo:
        if not isinstance(item, str) or " - " not in item:
            continue
        data, _, valores = item.partition(" - ")
        partes = [v.strip() for v in valores.split(",")]
        if len(partes) != 3:
            continue
        try:
            numeros = tuple(float(v.replace(" ", "")) for v in partes)
        except ValueError:
            continue
        registros.append((data.strip(), *numeros))
    return registros


class EditorDelegate(QStyledItemDelegate):
    def sizeHint(self, option, index):
        base = super().sizeHint(option, index)
        return QSize(base.width(), max(base.height(), 34))


class ToggleSwitch(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setFixedSize(54, 26)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setText("QAD")
        self.toggled.connect(self.update)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect().adjusted(1, 1, -1, -1)
        checked = self.isChecked()
        track_color = QColor("#4f46e5") if checked else QColor("#e2e8f0")
        border_color = QColor("#cbd5e1") if not checked else QColor("#4338ca")

        painter.setPen(border_color)
        painter.setBrush(track_color)
        painter.drawRoundedRect(rect, 13, 13)

        knob_size = 18
        knob_margin = 4
        knob_x = knob_margin if not checked else self.width() - knob_size - knob_margin
        knob_rect = QRect(knob_x, 4, knob_size, self.height() - 8)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#ffffff"))
        painter.drawRoundedRect(knob_rect, 9, 9)

        text = "QAD" if checked else "SCI"
        painter.setPen(QColor("#ffffff") if checked else QColor("#334155"))
        font = self.font()
        font.setBold(True)
        font.setPointSizeF(7)
        painter.setFont(font)

        if checked:
            text_rect = QRect(8, 0, self.width() - 26, self.height())
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, text)
        else:
            text_rect = QRect(18, 0, self.width() - 26, self.height())
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, text)


class TabelaFreshStart(QTableWidget):
    """Tabela com sizeHint contido para evitar que o layout force expansão da janela."""
    def sizeHint(self):
        return QSize(600, 220)

    def minimumSizeHint(self):
        return QSize(300, 100)


class ChartCanvas(FigureCanvas):
    """Canvas com sizeHint contido para evitar que o matplotlib force expansão da janela."""
    def sizeHint(self):
        return QSize(600, 220)

    def minimumSizeHint(self):
        return QSize(300, 100)


class FreshStartPage(QWidget):
    COLUNAS = [
        "Transf", "Local", "Kardex", "Descrição", "Loc", "Qtde Qad", "Qtde Sci",
        "Compras", "Fornecedor", "Pedido", "Lugar transf", "Loc transf", "Data",
    ]
    CHAVES = [
        "transf", "local", "kardex", "descricao", "loc", "qtde_qad", "qtde_sci",
        "compras", "fornecedor", "pedido", "lugar_transferido", "loc_transf", "data",
    ]

    def sizeHint(self):
        return QSize(1000, 650)

    def minimumSizeHint(self):
        return QSize(600, 320)

    def __init__(self):
        super().__init__()
        self.dados = []
        self._credenciais = None
        self._estado_grafico = 1
        self._dados_grafico_atual = []
        self._annot = None
        self._ax = None
        self._setup_ui()
        self._carregar_dados()

    def showEvent(self, event):
        super().showEvent(event)
        self._carregar_dados()

    def _atualizar_zcusto(self):
        caminho = _caminho_zcusto()
        if not caminho:
            config.avisar_sem_pasta(self)
            return

        if not self._modo_busca_qad:
            origem = os.path.normpath(r"C:\SciTemp\zCusto.prn")
            if not os.path.isfile(origem):
                QMessageBox.warning(
                    self,
                    "zCusto não encontrado",
                    f"Não foi encontrado o arquivo zCusto.prn em:\n{origem}",
                )
                return
            try:
                os.makedirs(os.path.dirname(caminho), exist_ok=True)
                shutil.copy2(origem, caminho)
            except OSError as erro:
                QMessageBox.warning(
                    self,
                    "Erro ao copiar zCusto",
                    f"Não foi possível copiar o arquivo zCusto.prn.\n{erro}",
                )
                return
        else:
            try:
                time.sleep(5)
                digitar_texto("30.16.13.2")
                enter(10)
                digitar_texto("10912")
                enter()
                digitar_texto("10912")
                enter()
                digitar_texto("zcentral")
                enter()
                digitar_texto("zcentral")
                enter(11)
                digitar_texto("zCusto")
                enter(3)

                resposta = QMessageBox(self)
                resposta.setWindowTitle("Relatório")
                resposta.setText("Clicar em OK depois que o relatorio for gerado")
                resposta.setIcon(QMessageBox.Icon.Information)
                resposta.setStandardButtons(QMessageBox.StandardButton.Ok)
                resposta.exec()

                if self._credenciais is None:
                    usr, pwd = CredentialsDialog.get_credentials(self)
                    if usr is None:
                        return
                    self._credenciais = (usr, pwd)

                os.makedirs(os.path.dirname(caminho), exist_ok=True)
                self._baixar_zcusto_com_winscp(
                    self._credenciais[0], self._credenciais[1], caminho
                )
            except Exception as erro:
                QMessageBox.warning(
                    self,
                    "Erro na automação zCusto",
                    str(erro),
                )
                return

            if not os.path.isfile(caminho) or os.path.getsize(caminho) == 0:
                QMessageBox.warning(
                    self,
                    "zCusto não encontrado",
                    "Não foi encontrado o arquivo zCusto.prn na pasta Almox.",
                )
                return

        self._calcular_total_zcentral()
        self._calcular_total_dph()
        self._registrar_atualizacao()
        self._atualizar_grafico()
        QMessageBox.information(self, "zCusto", "zCusto OK")

    # ── UI ──
    def _setup_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(16)

        header_layout = QHBoxLayout()
        header_texts = QVBoxLayout()
        header_texts.setSpacing(4)
        titulo = QLabel("Fresh Start")
        titulo.setObjectName("pageTitle")
        header_texts.addWidget(titulo)
        subtitulo = QLabel("Itens para o novo início / transferência")
        subtitulo.setObjectName("pageSubtitle")
        header_texts.addWidget(subtitulo)
        header_layout.addLayout(header_texts)
        header_layout.addStretch()
        self.layout.addLayout(header_layout)

        self.table_card = QWidget()
        self.table_card.setObjectName("pageCard")
        table_card_layout = QVBoxLayout(self.table_card)
        table_card_layout.setContentsMargins(18, 14, 18, 14)
        table_card_layout.setSpacing(10)

        # ── Filtro ──
        self.filter_row = QHBoxLayout()
        self.filter_row.setSpacing(8)

        btn_zcentral = QPushButton(qtawesome.icon('fa6s.rotate', color='#ffffff'), "  zCentral")
        btn_zcentral.setObjectName("btnPrimary")
        btn_zcentral.setFixedHeight(32)
        btn_zcentral.clicked.connect(self._atualizar_do_prn)
        self.filter_row.addWidget(btn_zcentral)

        btn_zcusto = QPushButton(qtawesome.icon('fa6s.rotate', color='#ffffff'), "  zCusto")
        btn_zcusto.setObjectName("btnPrimary")
        btn_zcusto.setFixedHeight(32)
        btn_zcusto.clicked.connect(self._atualizar_zcusto)
        self.filter_row.addWidget(btn_zcusto)

        self._modo_busca_qad = True
        self.btn_busca = ToggleSwitch()
        self.btn_busca.setChecked(True)
        self.btn_busca.toggled.connect(self._alternar_busca)
        self._atualizar_texto_busca()
        self.filter_row.addWidget(self.btn_busca)

        self.campo_filtro = QLineEdit()
        self.campo_filtro.setPlaceholderText("Pesquisar...")
        self.campo_filtro.setFixedHeight(34)
        self.campo_filtro.setFixedWidth(220)
        self.campo_filtro.setStyleSheet("padding: 2px 8px;")
        self.campo_filtro.textChanged.connect(self._aplicar_filtro)
        self.filter_row.addWidget(self.campo_filtro)

        self.btn_transf = QPushButton(qtawesome.icon('fa6s.truck-fast', color='#ffffff'), "  Transf")
        self.btn_transf.setObjectName("btnPrimary")
        self.btn_transf.setFixedHeight(32)
        self.btn_transf.clicked.connect(self._executar_transferencia)
        self.filter_row.addWidget(self.btn_transf)

        self.filter_row.addStretch()

        self.label_contador = QLabel("0 itens")
        self.label_contador.setObjectName("statusLabel")
        self.filter_row.addWidget(self.label_contador)

        btn_exportar = QPushButton(qtawesome.icon('fa6s.file-excel', color='#ffffff'), "  Exportar Excel")
        btn_exportar.setObjectName("btnPrimary")
        btn_exportar.setFixedHeight(32)
        btn_exportar.clicked.connect(self._exportar_excel)
        self.filter_row.addWidget(btn_exportar)

        table_card_layout.addLayout(self.filter_row)

        self.tabela = TabelaFreshStart(0, len(self.COLUNAS))
        self.tabela.setObjectName("tabelaFreshStart")
        self.tabela.setSizeAdjustPolicy(QAbstractItemView.SizeAdjustPolicy.AdjustIgnored)
        self.tabela.setHorizontalHeaderLabels(self.COLUNAS)
        header = self.tabela.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        larguras = [50, 50, 140, 200, 100, 100, 100, 100, 150, 100, 120, 100]
        for c, largura in enumerate(larguras):
            header.resizeSection(c, largura)
        self.tabela.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabela.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked)
        self.tabela.setAlternatingRowColors(True)
        self.tabela.setWordWrap(False)
        self.tabela.verticalHeader().setDefaultSectionSize(34)
        self.tabela.verticalHeader().setVisible(False)
        self.tabela.setItemDelegate(EditorDelegate(self.tabela))
        self.tabela.itemChanged.connect(self._item_modificado)
        table_card_layout.addWidget(self.tabela)

        # Rótulos internos mantidos para compatibilidade com cálculo e histórico
        self.label_total_zcentral = QLabel("R$ 0,00")
        self.label_total_dph = QLabel("R$ 0,00")
        self.label_total_dph_dif = QLabel("R$ 0,00")

        self.layout.addWidget(self.table_card)

        # ── Gráfico de histórico ──
        self.chart_card = QWidget()
        self.chart_card.setObjectName("pageCard")
        self.chart_card_layout = QVBoxLayout(self.chart_card)
        self.chart_card_layout.setContentsMargins(18, 14, 18, 14)
        self.chart_card_layout.setSpacing(10)

        # Cabeçalho do Gráfico
        chart_header = QHBoxLayout()
        chart_header.setSpacing(8)

        chart_titulo = QLabel("Evolução dos valores")
        chart_titulo.setObjectName("pageSubtitle")
        chart_header.addWidget(chart_titulo)

        badge_sub = QLabel("Histórico Financeiro")
        badge_sub.setStyleSheet("""
            QLabel {
                background-color: #eef2ff;
                color: #4f46e5;
                font-size: 10px;
                font-weight: 700;
                padding: 2px 8px;
                border-radius: 6px;
                border: 1px solid #c7d2fe;
            }
        """)
        chart_header.addWidget(badge_sub)
        chart_header.addStretch()

        self.botao_recolher = QPushButton()
        self.botao_recolher.setObjectName("btnRecolherGrafico")
        self.botao_recolher.setIcon(qtawesome.icon('fa6s.chevron-down', color='#6366f1'))
        self.botao_recolher.setIconSize(QSize(12, 12))
        self.botao_recolher.setFixedSize(28, 28)
        self.botao_recolher.setCursor(Qt.CursorShape.PointingHandCursor)
        self.botao_recolher.setToolTip("Recolher gráfico")
        self.botao_recolher.setStyleSheet(
            "QPushButton#btnRecolherGrafico {"
            " background-color: #ffffff; border: 1px solid #e2e8f0;"
            " border-radius: 8px;"
            "}"
            "QPushButton#btnRecolherGrafico:hover {"
            " background-color: #eef2ff; border-color: #c7d2fe;"
            "}"
        )
        self.botao_recolher.clicked.connect(self._recolher_ou_expandir_grafico)
        chart_header.addWidget(self.botao_recolher)

        self.botao_grafico = QPushButton()
        self.botao_grafico.setObjectName("btnExpandirGrafico")
        self.botao_grafico.setIcon(qtawesome.icon('fa6s.up-right-and-down-left-from-center', color='#6366f1'))
        self.botao_grafico.setIconSize(QSize(12, 12))
        self.botao_grafico.setFixedSize(28, 28)
        self.botao_grafico.setCursor(Qt.CursorShape.PointingHandCursor)
        self.botao_grafico.setToolTip("Maximizar gráfico")
        self.botao_grafico.setStyleSheet(
            "QPushButton#btnExpandirGrafico {"
            " background-color: #ffffff; border: 1px solid #e2e8f0;"
            " border-radius: 8px;"
            "}"
            "QPushButton#btnExpandirGrafico:hover {"
            " background-color: #eef2ff; border-color: #c7d2fe;"
            "}"
        )
        self.botao_grafico.clicked.connect(self._maximizar_ou_restaurar_grafico)
        chart_header.addWidget(self.botao_grafico)

        self.chart_card_layout.addLayout(chart_header)

        # ── Cartões de Resumo KPI ──
        def _criar_card_kpi(titulo, cor_borda, cor_texto, icone_nome=""):
            card = QFrame()
            card.setObjectName("kpiCard")
            card.setStyleSheet(f"""
                QFrame#kpiCard {{
                    background-color: #ffffff;
                    border: 1px solid {cor_borda};
                    border-radius: 10px;
                }}
            """)
            lay = QVBoxLayout(card)
            lay.setContentsMargins(10, 6, 10, 6)
            lay.setSpacing(2)

            topo = QHBoxLayout()
            topo.setSpacing(6)
            if icone_nome:
                try:
                    ico = QLabel()
                    ico.setPixmap(qtawesome.icon(icone_nome, color=cor_texto).pixmap(12, 12))
                    topo.addWidget(ico)
                except Exception:
                    pass
            lbl_tit = QLabel(titulo.upper())
            lbl_tit.setStyleSheet("color: #64748b; font-size: 10px; font-weight: 700; letter-spacing: 0.5px;")
            topo.addWidget(lbl_tit)
            topo.addStretch()
            lay.addLayout(topo)

            lbl_val = QLabel("R$ 0,00")
            lbl_val.setStyleSheet(f"color: {cor_texto}; font-size: 14px; font-weight: 800;")
            lbl_val.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            lay.addWidget(lbl_val)

            return card, lbl_val

        self.kpi_widget = QWidget()
        kpi_lay = QHBoxLayout(self.kpi_widget)
        kpi_lay.setContentsMargins(0, 0, 0, 0)
        kpi_lay.setSpacing(10)

        card_zc, self.lbl_kpi_zcentral = _criar_card_kpi("zCentral Atual", "#c7d2fe", "#4338ca", "fa6s.warehouse")
        card_dp, self.lbl_kpi_dph = _criar_card_kpi("DPH Atual", "#a7f3d0", "#059669", "fa6s.boxes-stacked")
        card_df, self.lbl_kpi_dif = _criar_card_kpi("Diferença (zC - DPH)", "#fed7aa", "#d97706", "fa6s.scale-balanced")
        card_dt, self.lbl_kpi_data = _criar_card_kpi("Último Registro", "#e2e8f0", "#475569", "fa6s.calendar-day")
        self.lbl_kpi_data.setText("-")

        kpi_lay.addWidget(card_zc)
        kpi_lay.addWidget(card_dp)
        kpi_lay.addWidget(card_df)
        kpi_lay.addWidget(card_dt)
        self.chart_card_layout.addWidget(self.kpi_widget)

        # ── Barra de Controles do Gráfico ──
        self.controls_widget = QWidget()
        ctrl_lay = QHBoxLayout(self.controls_widget)
        ctrl_lay.setContentsMargins(0, 2, 0, 2)
        ctrl_lay.setSpacing(8)

        lbl_per = QLabel("Período:")
        lbl_per.setStyleSheet("color: #475569; font-size: 11px; font-weight: 700;")
        ctrl_lay.addWidget(lbl_per)

        self.combo_periodo = QComboBox()
        self.combo_periodo.addItems(["Todos os registros", "Últimos 30 dias", "Últimos 15 dias", "Últimos 7 dias"])
        self.combo_periodo.setStyleSheet("""
            QComboBox {
                background-color: #ffffff;
                border: 1px solid #dce3ee;
                border-radius: 8px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 600;
                color: #334155;
                min-height: 22px;
            }
            QComboBox:hover {
                border-color: #6366f1;
            }
        """)
        self.combo_periodo.currentIndexChanged.connect(self._atualizar_grafico)
        ctrl_lay.addWidget(self.combo_periodo)

        lbl_tipo = QLabel("Tipo:")
        lbl_tipo.setStyleSheet("color: #475569; font-size: 11px; font-weight: 700; margin-left: 4px;")
        ctrl_lay.addWidget(lbl_tipo)

        self.combo_tipo = QComboBox()
        self.combo_tipo.addItems(["Linhas com Área", "Linhas Simples", "Barras Agrupadas"])
        self.combo_tipo.setStyleSheet("""
            QComboBox {
                background-color: #ffffff;
                border: 1px solid #dce3ee;
                border-radius: 8px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 600;
                color: #334155;
                min-height: 22px;
            }
            QComboBox:hover {
                border-color: #6366f1;
            }
        """)
        self.combo_tipo.currentIndexChanged.connect(self._atualizar_grafico)
        ctrl_lay.addWidget(self.combo_tipo)

        def _separador():
            sep = QFrame()
            sep.setFrameShape(QFrame.Shape.VLine)
            sep.setStyleSheet("background-color: #e2e8f0; max-width: 1px; min-height: 18px;")
            return sep

        ctrl_lay.addWidget(_separador())

        lbl_ser = QLabel("Séries:")
        lbl_ser.setStyleSheet("color: #475569; font-size: 11px; font-weight: 700;")
        ctrl_lay.addWidget(lbl_ser)

        def _estilo_pill(cor_prim, cor_bg, cor_txt):
            return f"""
                QPushButton {{
                    background-color: #ffffff;
                    color: #64748b;
                    border: 1px solid #cbd5e1;
                    border-radius: 12px;
                    padding: 3px 10px;
                    font-size: 11px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background-color: #f8fafc;
                    border-color: {cor_prim};
                    color: {cor_txt};
                }}
                QPushButton:checked {{
                    background-color: {cor_bg};
                    color: {cor_txt};
                    border: 1.5px solid {cor_prim};
                    font-weight: 700;
                }}
            """

        self.btn_toggle_zcentral = QPushButton("●  zCentral")
        self.btn_toggle_zcentral.setCheckable(True)
        self.btn_toggle_zcentral.setChecked(True)
        self.btn_toggle_zcentral.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle_zcentral.setToolTip("Ligar/desligar exibição do zCentral")
        self.btn_toggle_zcentral.setStyleSheet(_estilo_pill("#6366f1", "#e0e7ff", "#4338ca"))
        self.btn_toggle_zcentral.clicked.connect(self._atualizar_grafico)
        ctrl_lay.addWidget(self.btn_toggle_zcentral)

        self.btn_toggle_dph = QPushButton("●  DPH")
        self.btn_toggle_dph.setCheckable(True)
        self.btn_toggle_dph.setChecked(True)
        self.btn_toggle_dph.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle_dph.setToolTip("Ligar/desligar exibição do DPH")
        self.btn_toggle_dph.setStyleSheet(_estilo_pill("#10b981", "#dcfce7", "#15803d"))
        self.btn_toggle_dph.clicked.connect(self._atualizar_grafico)
        ctrl_lay.addWidget(self.btn_toggle_dph)

        self.btn_toggle_dif = QPushButton("●  Diferença")
        self.btn_toggle_dif.setCheckable(True)
        self.btn_toggle_dif.setChecked(True)
        self.btn_toggle_dif.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle_dif.setToolTip("Ligar/desligar exibição da Diferença (zCentral - DPH)")
        self.btn_toggle_dif.setStyleSheet(_estilo_pill("#f97316", "#ffedd5", "#c2410c"))
        self.btn_toggle_dif.clicked.connect(self._atualizar_grafico)
        ctrl_lay.addWidget(self.btn_toggle_dif)

        ctrl_lay.addWidget(_separador())

        self.chk_valores = QCheckBox("Rótulos")
        self.chk_valores.setCursor(Qt.CursorShape.PointingHandCursor)
        self.chk_valores.setToolTip("Exibir os valores monetários sobre os pontos do gráfico")
        self.chk_valores.setStyleSheet("""
            QCheckBox {
                font-size: 11px;
                font-weight: 600;
                color: #475569;
                spacing: 5px;
            }
        """)
        self.chk_valores.toggled.connect(self._atualizar_grafico)
        ctrl_lay.addWidget(self.chk_valores)

        ctrl_lay.addStretch()

        btn_recarregar_grafico = QPushButton()
        btn_recarregar_grafico.setIcon(qtawesome.icon('fa6s.rotate', color='#6366f1'))
        btn_recarregar_grafico.setIconSize(QSize(12, 12))
        btn_recarregar_grafico.setFixedSize(28, 28)
        btn_recarregar_grafico.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_recarregar_grafico.setToolTip("Recarregar dados do gráfico")
        btn_recarregar_grafico.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                border: 1px solid #dce3ee;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #eef2ff;
                border-color: #c7d2fe;
            }
        """)
        btn_recarregar_grafico.clicked.connect(self._atualizar_grafico)
        ctrl_lay.addWidget(btn_recarregar_grafico)

        self.chart_card_layout.addWidget(self.controls_widget)

        # ── Canvas Matplotlib ──
        self.figure = Figure(figsize=(8, 3.2), facecolor="none")
        self.figure.subplots_adjust(left=0.08, right=0.98, top=0.92, bottom=0.18)
        self.canvas = ChartCanvas(self.figure)
        self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.canvas.mpl_connect("motion_notify_event", self._on_canvas_hover)
        self.canvas.mpl_connect("axes_leave_event", self._on_canvas_leave)
        self.chart_card_layout.addWidget(self.canvas)

        self.layout.addWidget(self.chart_card)
        self.layout.setStretch(0, 0)
        self.layout.setStretch(1, 1)
        self.layout.setStretch(2, 1)

        self._aplicar_estado_grafico()

        self._atualizar_grafico()

        self._inserir_linha_vazia()

    # ── Dados ──
    def _carregar_dados(self):
        caminho = _caminho_json()
        if not caminho:
            return
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                dados = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            dados = []
        self.dados = [
            {chave: str(item.get(chave, "")) for chave in self.CHAVES}
            for item in dados
        ]
        self._popular_tabela()
        self._calcular_total_zcentral()
        self._calcular_total_dph()
        self._atualizar_grafico()

    def _salvar_json(self):
        caminho = _caminho_json()
        if not caminho:
            config.avisar_sem_pasta(self)
            return
        try:
            os.makedirs(os.path.dirname(caminho), exist_ok=True)
            with open(caminho, "w", encoding="utf-8") as f:
                json.dump(self.dados, f, ensure_ascii=False, indent=2)
        except OSError:
            pass

    # ── Atualizar (zCentral.prn) ──
    def _atualizar_do_prn(self):
        caminho = _caminho_zcentral()
        if not caminho:
            config.avisar_sem_pasta(self)
            return

        if self._modo_busca_qad:
            try:
                time.sleep(5)
                for texto, quantidade in (
                    ("3.6.6", 5),
                    ("ZCENTRAL", 1),
                    ("ZCENTRAL", 1),
                    ("zCentral", 3),
                ):
                    digitar_texto(texto)
                    enter(quantidade)

                pyautogui.press("f4")

                usr, pwd = CredentialsDialog.get_credentials(self)
                if usr is None:
                    return

                os.makedirs(os.path.dirname(caminho), exist_ok=True)
                self._baixar_zcentral_com_winscp(
                    usr, pwd, caminho
                )
            except Exception as erro:
                QMessageBox.warning(self, "Erro ao baixar arquivo", str(erro))
                return
        else:
            origem = os.path.normpath(r"C:\SciTemp\zCentral.prn")
            if not os.path.exists(origem):
                QMessageBox.warning(
                    self,
                    "Arquivo não encontrado",
                    f"Não foi encontrado o arquivo zCentral.prn em:\n{origem}",
                )
                return
            try:
                os.makedirs(os.path.dirname(caminho), exist_ok=True)
                shutil.copy2(origem, caminho)
            except OSError:
                QMessageBox.warning(
                    self,
                    "Erro ao copiar arquivo",
                    "Não foi possível copiar o arquivo zCentral.prn da pasta SciTemp para a pasta Almox.",
                )
                return

        if not os.path.exists(caminho):
            config.avisar_sem_pasta(self)
            return

        novos = []
        with open(caminho, "r", encoding="latin-1") as f:
            for linha in f:
                linha = linha.rstrip("\n")
                if len(linha) < 80:
                    continue
                local = linha[0:9].strip()
                lugar_transf = linha[9:18].strip()
                kardex = linha[18:37].strip()
                loc = linha[37:56].strip()
                qtde_qad = linha[60:72].strip()
                data_prn = linha[72:82].strip()
                if local.isdigit() and kardex and loc and qtde_qad:
                    novos.append({
                        "local": local,
                        "kardex": kardex,
                        "loc": loc,
                        "qtde_qad": qtde_qad,
                        "lugar_transferido": lugar_transf,
                        "data": data_prn,
                    })

        if not novos:
            return

        self.dados = []

        estoque_por_kardex = {}
        caminho_estoque = _caminho_estoque()
        if caminho_estoque and os.path.exists(caminho_estoque):
            try:
                with open(caminho_estoque, "r", encoding="utf-8") as f:
                    for item in json.load(f):
                        k = str(item.get("Kardex", "")).strip().upper()
                        if k:
                            estoque_por_kardex[k] = item
            except (FileNotFoundError, json.JSONDecodeError):
                pass

        por_chave = {
            (item.get("local", ""), item.get("kardex", "").upper(), item.get("loc", "").upper()): item
            for item in self.dados
        }
        for item in novos:
            chave = (item["local"], item["kardex"].upper(), item["loc"].upper())
            existente = por_chave.get(chave)
            estoque = estoque_por_kardex.get(item["kardex"].upper())
            
            tem_descricao = False
            if estoque is not None:
                item["descricao"] = str(estoque.get("Descrição", ""))
                item["qtde_sci"] = str(estoque.get("Qtde novo", ""))
                item["fornecedor"] = str(estoque.get("Fornecedor", ""))
                if item["descricao"].strip():
                    tem_descricao = True

            if not tem_descricao:
                item["lugar_transferido"] = "ZMANUTE"

            if existente is not None:
                existente["loc"] = item["loc"]
                existente["qtde_qad"] = item["qtde_qad"]
                existente["lugar_transferido"] = item["lugar_transferido"]
                existente["data"] = item["data"]
                if estoque is not None:
                    existente["descricao"] = item["descricao"]
                    existente["qtde_sci"] = item["qtde_sci"]
                    existente["fornecedor"] = item["fornecedor"]
            else:
                novo_item = {chave: "" for chave in self.CHAVES}
                novo_item.update(item)
                self.dados.append(novo_item)
                por_chave[chave] = novo_item

        # Ordena a lista: itens sem descrição vão para o final
        self.dados.sort(key=lambda x: 1 if not str(x.get("descricao", "")).strip() else 0)

        self._salvar_json()
        self._popular_tabela()
        self._calcular_total_zcentral()
        self._calcular_total_dph()
        self._registrar_atualizacao()
        self._atualizar_grafico()

        # Atualiza a página de Estoque Zero
        main_win = self.window()
        if hasattr(main_win, "pages") and "itens_zero" in main_win.pages:
            main_win.pages["itens_zero"]._sincronizar()
            
        QMessageBox.information(self, "zCentral", "zCentral OK")

    def _baixar_zcentral_com_winscp(self, usuario, senha, destino_local):
        import sys
        base_dir = sys._MEIPASS if getattr(sys, 'frozen', False) else os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        caminhos = [
            os.path.join(base_dir, "recursos", "winscp", "WinSCP.com"),
            r"C:\Program Files (x86)\WinSCp-FTP\WinSCP.com",
            r"C:\Program Files (x86)\WinSCp-FTP\WinSCP\WinSCP.com",
        ]
        winscp = next((caminho for caminho in caminhos if os.path.exists(caminho)), None)
        if not winscp:
            raise Exception("WinSCP.com não encontrado.")

        comando = [
            winscp,
            #"/ini=nul",
            "/command",
            "option batch abort",
            "option confirm off",
            f"open sftp://{quote(usuario, safe='')}:{quote(senha, safe='')}@10.251.70.27/ ",
            f'get zCentral.prn "{destino_local}"',
            "exit",
        ]
        resultado = subprocess.run(
            comando, 
            capture_output=True, 
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        if resultado.returncode != 0:
            raise Exception(resultado.stderr or resultado.stdout)
        if not os.path.isfile(destino_local):
            retorno = resultado.stderr or resultado.stdout
            mensagem = "O WinSCP terminou, mas zCentral.prn não foi criado no destino."
            if retorno:
                mensagem += f"\n{retorno}"
            raise Exception(mensagem)

    def _baixar_zcusto_com_winscp(self, usuario, senha, destino_local):
        import sys
        base_dir = sys._MEIPASS if getattr(sys, 'frozen', False) else os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        caminhos = [
            os.path.join(base_dir, "recursos", "winscp", "WinSCP.com"),
            r"C:\Program Files (x86)\WinSCp-FTP\WinSCP.com",
            r"C:\Program Files (x86)\WinSCp-FTP\WinSCP\WinSCP.com",
        ]
        winscp = next((caminho for caminho in caminhos if os.path.exists(caminho)), None)
        if not winscp:
            raise Exception("WinSCP.com não encontrado.")

        comando = [
            winscp,
            #"/ini=nul",
            "/command",
            "option batch abort",
            "option confirm off",
            f"open sftp://{quote(usuario, safe='')}:{quote(senha, safe='')}@10.251.70.27:22/ ",
            f'get zCusto.prn "{destino_local}"',
            "exit",
        ]
        try:
            resultado = subprocess.run(
                comando,
                capture_output=True,
                text=True,
                timeout=60,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
        except subprocess.TimeoutExpired as erro:
            raise Exception("O WinSCP excedeu o limite de 60 segundos.") from erro

        if resultado.returncode != 0:
            raise Exception(resultado.stderr or resultado.stdout)
        if not os.path.isfile(destino_local) or os.path.getsize(destino_local) == 0:
            raise Exception("O WinSCP não criou o arquivo zCusto.prn no destino.")

    # ── Histórico de atualizações ──
    def _registrar_atualizacao(self):
        caminho = _caminho_dados_fresh_start()
        if not caminho:
            return

        zcentral = _parse_numero(
            self.label_total_zcentral.text().replace("R$", "").strip()
        )
        dph = _parse_numero(
            self.label_total_dph.text().replace("R$", "").strip()
        )
        valor = zcentral - dph

        hoje = datetime.now().strftime("%d/%m/%Y")
        registro = f"{hoje} - {zcentral}, {dph}, {valor}"

        try:
            with open(caminho, "r", encoding="utf-8") as f:
                dados = json.load(f)
                if not isinstance(dados, list):
                    dados = []
        except (FileNotFoundError, json.JSONDecodeError):
            dados = []

        # Atualiza o registro do dia, se já existir
        atualizado = False
        for i, item in enumerate(dados):
            if isinstance(item, str) and item.startswith(f"{hoje} - "):
                dados[i] = registro
                atualizado = True
                break

        # Se não existir, adiciona novo
        if not atualizado:
            dados.append(registro)

        try:
            os.makedirs(os.path.dirname(caminho), exist_ok=True)
            with open(caminho, "w", encoding="utf-8") as f:
                json.dump(dados, f, ensure_ascii=False, indent=2)
        except OSError:
            pass

    # ── Métodos de Formatação e Tooltips do Gráfico ──
    def _formatar_moeda(self, valor):
        return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    def _formatar_moeda_eixo(self, val, pos):
        if abs(val) >= 1_000_000:
            return f"R$ {val / 1_000_000:.1f}M".replace(".", ",")
        elif abs(val) >= 1_000:
            return f"R$ {val / 1_000:.0f}k"
        elif abs(val) == 0:
            return "R$ 0"
        else:
            return f"R$ {val:.0f}"

    def _formatar_moeda_ponto(self, val):
        if abs(val) >= 1_000_000:
            return f"{val / 1_000_000:.2f}M".replace(".", ",")
        elif abs(val) >= 1_000:
            return f"{val / 1_000:.0f}k"
        else:
            return f"{val:.0f}"

    def _on_canvas_leave(self, event):
        if hasattr(self, "_annot") and self._annot and self._annot.get_visible():
            self._annot.set_visible(False)
            self.canvas.draw_idle()

    def _on_canvas_hover(self, event):
        if not hasattr(self, "_annot") or not self._annot or not hasattr(self, "_dados_grafico_atual"):
            return
        if not hasattr(self, "_ax") or event.inaxes != self._ax or not self._dados_grafico_atual:
            if self._annot.get_visible():
                self._annot.set_visible(False)
                self.canvas.draw_idle()
            return

        x = event.xdata
        if x is None:
            return

        idx = int(round(x))
        if 0 <= idx < len(self._dados_grafico_atual):
            data_str, zc, dp, df = self._dados_grafico_atual[idx]

            linhas = [f"📅 {data_str}"]
            y_pts = []
            if self.btn_toggle_zcentral.isChecked():
                linhas.append(f"● zCentral: {self._formatar_moeda(zc)}")
                y_pts.append(zc)
            if self.btn_toggle_dph.isChecked():
                linhas.append(f"● DPH: {self._formatar_moeda(dp)}")
                y_pts.append(dp)
            if self.btn_toggle_dif.isChecked():
                linhas.append(f"● Diferença: {self._formatar_moeda(df)}")
                y_pts.append(df)

            texto = "\n".join(linhas)
            y_pos = max(y_pts) if y_pts else (event.ydata if event.ydata is not None else 0)

            self._annot.xy = (idx, y_pos)
            self._annot.set_text(texto)
            self._annot.set_visible(True)
            self.canvas.draw_idle()
        else:
            if self._annot.get_visible():
                self._annot.set_visible(False)
                self.canvas.draw_idle()

    # ── Gráfico ──
    def _atualizar_grafico(self):
        if not hasattr(self, "canvas") or not hasattr(self, "combo_periodo"):
            return

        self.figure.clear()
        registros = _carregar_historico()

        if not registros:
            ax = self.figure.add_subplot(111)
            self._ax = ax
            ax.set_facecolor("none")
            for spine in ax.spines.values():
                spine.set_visible(False)
            ax.tick_params(colors="#94a3b8", length=0, bottom=False, labelbottom=False, left=False, labelleft=False)
            ax.text(
                0.5, 0.5, "Nenhum histórico registrado ainda em DadosFreshStart.json",
                transform=ax.transAxes,
                ha="center", va="center",
                fontsize=11, color="#94a3b8", fontweight="600"
            )
            self.lbl_kpi_zcentral.setText("R$ 0,00")
            self.lbl_kpi_dph.setText("R$ 0,00")
            self.lbl_kpi_dif.setText("R$ 0,00")
            self.lbl_kpi_data.setText("Sem registros")
            self._dados_grafico_atual = []
            self.canvas.draw()
            return

        def _parse_data_str(d_str):
            try:
                return datetime.strptime(d_str, "%d/%m/%Y")
            except Exception:
                return datetime.min

        registros.sort(key=lambda r: _parse_data_str(r[0]))

        # Atualiza os cartões KPI com o registro mais recente
        ultimo = registros[-1]
        self.lbl_kpi_zcentral.setText(self._formatar_moeda(ultimo[1]))
        self.lbl_kpi_dph.setText(self._formatar_moeda(ultimo[2]))
        self.lbl_kpi_dif.setText(self._formatar_moeda(ultimo[3]))
        self.lbl_kpi_data.setText(f"{ultimo[0]} ({len(registros)} reg.)")

        # Filtra pelo período selecionado
        periodo = self.combo_periodo.currentText()
        if "7" in periodo:
            regs = registros[-7:]
        elif "15" in periodo:
            regs = registros[-15:]
        elif "30" in periodo:
            regs = registros[-30:]
        elif "90" in periodo:
            regs = registros[-90:]
        else:
            regs = list(registros)

        if not regs:
            regs = list(registros)

        # Filtra séries ativas
        mostrar_zc = self.btn_toggle_zcentral.isChecked()
        mostrar_dp = self.btn_toggle_dph.isChecked()
        mostrar_df = self.btn_toggle_dif.isChecked()

        series_ativas = []
        if mostrar_zc:
            series_ativas.append(([r[1] for r in regs], "zCentral", "#6366f1"))
        if mostrar_dp:
            series_ativas.append(([r[2] for r in regs], "DPH", "#10b981"))
        if mostrar_df:
            series_ativas.append(([r[3] for r in regs], "zCentral - DPH", "#f97316"))

        self.figure.subplots_adjust(left=0.08, right=0.98, top=0.92, bottom=0.18)
        ax = self.figure.add_subplot(111)
        self._ax = ax
        ax.set_facecolor("none")
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.tick_params(colors="#64748b", length=0, labelsize=9)
        ax.grid(axis="y", color="#e2e8f0", linewidth=0.8, linestyle="--", alpha=0.7)

        if not series_ativas:
            ax.tick_params(bottom=False, labelbottom=False, left=False, labelleft=False)
            ax.text(
                0.5, 0.5, "Nenhuma série selecionada. Ative ao menos uma série nos botões acima.",
                transform=ax.transAxes,
                ha="center", va="center",
                fontsize=11, color="#64748b", fontweight="600"
            )
            self._dados_grafico_atual = []
            self.canvas.draw()
            return

        datas = [r[0] for r in regs]
        n_pts = len(datas)
        xs = list(range(n_pts))

        tipo_grafico = self.combo_tipo.currentText()
        mostrar_rotulos = self.chk_valores.isChecked()

        if "Barra" in tipo_grafico:
            n_series = len(series_ativas)
            largura_total = 0.75
            largura_barra = largura_total / n_series

            for i, (valores, nome, cor) in enumerate(series_ativas):
                x_pos = [x - (largura_total / 2) + (i + 0.5) * largura_barra for x in xs]
                rects = ax.bar(x_pos, valores, width=largura_barra, label=nome, color=cor, alpha=0.88, zorder=3)
                if mostrar_rotulos:
                    for rect, val in zip(rects, valores):
                        y_val = rect.get_height()
                        ax.annotate(
                            self._formatar_moeda_ponto(val),
                            xy=(rect.get_x() + rect.get_width() / 2, y_val),
                            xytext=(0, 3),
                            textcoords="offset points",
                            ha="center", va="bottom",
                            fontsize=7, fontweight="700", color=cor
                        )
        else:
            com_area = "Área" in tipo_grafico
            for valores, nome, cor in series_ativas:
                ax.plot(
                    xs, valores,
                    label=nome, color=cor, linewidth=2.5, zorder=4,
                    marker="o", markersize=5 if n_pts <= 25 else 3,
                    markerfacecolor="#ffffff", markeredgecolor=cor, markeredgewidth=2,
                )
                if com_area:
                    ax.fill_between(xs, valores, color=cor, alpha=0.06, zorder=2)

                if mostrar_rotulos:
                    passo_rot = 1 if n_pts <= 15 else (2 if n_pts <= 30 else max(1, n_pts // 10))
                    for idx_pt in range(0, n_pts, passo_rot):
                        val_pt = valores[idx_pt]
                        ax.annotate(
                            self._formatar_moeda_ponto(val_pt),
                            xy=(xs[idx_pt], val_pt),
                            xytext=(0, 6),
                            textcoords="offset points",
                            ha="center", va="bottom",
                            fontsize=7.5, fontweight="600", color=cor,
                            bbox=dict(boxstyle="round,pad=0.2", fc="#ffffff", ec=cor, lw=0.8, alpha=0.85)
                        )
                    if (n_pts - 1) % passo_rot != 0 and n_pts > 0:
                        val_ult = valores[-1]
                        ax.annotate(
                            self._formatar_moeda_ponto(val_ult),
                            xy=(xs[-1], val_ult),
                            xytext=(0, 6),
                            textcoords="offset points",
                            ha="center", va="bottom",
                            fontsize=7.5, fontweight="700", color=cor,
                            bbox=dict(boxstyle="round,pad=0.2", fc="#ffffff", ec=cor, lw=1.0, alpha=0.9)
                        )

        # Configuração do Eixo X
        ax.set_xlim(-0.6, n_pts - 0.4)
        if n_pts <= 12:
            indices_ticks = xs
            rotulos_ticks = [datas[i][:5] if "/" in datas[i] else datas[i] for i in xs]
        elif n_pts <= 25:
            indices_ticks = xs[::2]
            if xs[-1] not in indices_ticks:
                indices_ticks.append(xs[-1])
            rotulos_ticks = [datas[i][:5] if "/" in datas[i] else datas[i] for i in indices_ticks]
        else:
            step = max(2, n_pts // 10)
            indices_ticks = xs[::step]
            if xs[-1] not in indices_ticks:
                indices_ticks.append(xs[-1])
            rotulos_ticks = [datas[i][:5] if "/" in datas[i] else datas[i] for i in indices_ticks]

        ax.set_xticks(indices_ticks)
        ax.set_xticklabels(rotulos_ticks, rotation=0, ha="center", fontsize=8.5, color="#64748b", fontweight="500")

        # Configuração do Eixo Y
        ax.yaxis.set_major_formatter(FuncFormatter(self._formatar_moeda_eixo))
        y_min, y_max = ax.get_ylim()
        margem = (y_max - y_min) * 0.12 if y_max > y_min else 1.0
        ax.set_ylim(max(0, y_min - margem * 0.2), y_max + margem)

        ax.legend(
            loc="upper left", frameon=True, facecolor="#ffffff", edgecolor="#e2e8f0",
            framealpha=0.92, fontsize=8.5, labelcolor="#334155"
        )

        self._dados_grafico_atual = [(r[0], r[1], r[2], r[3]) for r in regs]
        self._xs_grafico_atual = xs

        self._annot = ax.annotate(
            "",
            xy=(0, 0),
            xytext=(12, 12),
            textcoords="offset points",
            bbox=dict(boxstyle="round,pad=0.5", fc="#1e1b4b", ec="#4338ca", lw=1.2, alpha=0.94),
            color="#ffffff",
            fontsize=8.5,
            fontweight="600"
        )
        self._annot.set_visible(False)

        self.canvas.draw()

    def _recolher_ou_expandir_grafico(self):
        if self._estado_grafico == 0:
            self._estado_grafico = 1
        else:
            self._estado_grafico = 0
        self._aplicar_estado_grafico()

    def _maximizar_ou_restaurar_grafico(self):
        if self._estado_grafico == 2:
            self._estado_grafico = 1
        else:
            self._estado_grafico = 2
        self._aplicar_estado_grafico()

    def _alternar_grafico(self):
        self._estado_grafico = (self._estado_grafico + 1) % 3
        self._aplicar_estado_grafico()

    def _aplicar_estado_grafico(self):
        win = self.window()
        tam_antigo = win.size() if (win and hasattr(win, "size") and not win.isMaximized()) else None

        maximizado = self._estado_grafico == 2
        self.table_card.setVisible(not maximizado)

        if self._estado_grafico == 0:
            # Gráfico totalmente recolhido: exibe os cards KPI na parte inferior da tela
            self.kpi_widget.setVisible(True)
            self.controls_widget.setVisible(False)
            self.canvas.setVisible(False)
            self.canvas.setMinimumHeight(0)
            self.canvas.setMaximumHeight(0)
            self.chart_card.setMinimumHeight(0)
            self.chart_card.setMaximumHeight(16777215)
            self.chart_card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
            self.chart_card_layout.setContentsMargins(18, 10, 18, 10)
            self.chart_card_layout.setSpacing(8)
            self.layout.setStretch(1, 1)
            self.layout.setStretch(2, 0)
            if hasattr(self, "botao_recolher"):
                self.botao_recolher.setIcon(qtawesome.icon('fa6s.chevron-up', color='#6366f1'))
                self.botao_recolher.setToolTip("Expandir gráfico")
            self.botao_grafico.setIcon(qtawesome.icon('fa6s.up-right-and-down-left-from-center', color='#6366f1'))
            self.botao_grafico.setToolTip("Maximizar gráfico")
        elif self._estado_grafico == 1:
            # Estado normal: tabela em cima, gráfico com controles e cards embaixo
            self.kpi_widget.setVisible(True)
            self.controls_widget.setVisible(True)
            self.canvas.setVisible(True)
            self.chart_card.setMinimumHeight(0)
            self.chart_card.setMaximumHeight(16777215)
            self.chart_card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
            self.chart_card_layout.setContentsMargins(18, 12, 18, 12)
            self.chart_card_layout.setSpacing(8)
            self.canvas.setMinimumHeight(140)
            self.canvas.setMaximumHeight(16777215)
            self.layout.setStretch(1, 1)
            self.layout.setStretch(2, 1)
            if hasattr(self, "botao_recolher"):
                self.botao_recolher.setIcon(qtawesome.icon('fa6s.chevron-down', color='#6366f1'))
                self.botao_recolher.setToolTip("Recolher gráfico")
            self.botao_grafico.setIcon(qtawesome.icon('fa6s.up-right-and-down-left-from-center', color='#6366f1'))
            self.botao_grafico.setToolTip("Maximizar gráfico")
            self.canvas.draw_idle()
        else:
            # Maximizado: gráfico ocupa toda a tela, tabela oculta
            self.kpi_widget.setVisible(True)
            self.controls_widget.setVisible(True)
            self.canvas.setVisible(True)
            self.chart_card.setMinimumHeight(0)
            self.chart_card.setMaximumHeight(16777215)
            self.chart_card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
            self.chart_card_layout.setContentsMargins(18, 14, 18, 14)
            self.chart_card_layout.setSpacing(10)
            self.canvas.setMinimumHeight(200)
            self.canvas.setMaximumHeight(16777215)
            self.layout.setStretch(1, 0)
            self.layout.setStretch(2, 1)
            if hasattr(self, "botao_recolher"):
                self.botao_recolher.setIcon(qtawesome.icon('fa6s.chevron-down', color='#6366f1'))
                self.botao_recolher.setToolTip("Recolher gráfico")
            self.botao_grafico.setIcon(qtawesome.icon('fa6s.down-left-and-up-right-to-center', color='#6366f1'))
            self.botao_grafico.setToolTip("Restaurar tamanho normal")
            self.canvas.draw_idle()

        self.chart_card.updateGeometry()

        # Garante que a janela principal nunca se expanda além dos limites da tela ou do tamanho original
        if win and hasattr(win, "resize") and not win.isMaximized():
            from PySide6.QtGui import QGuiApplication
            tela = win.screen() or QGuiApplication.primaryScreen()
            if tela:
                geo = tela.availableGeometry()
                largura_ref = tam_antigo.width() if tam_antigo else win.width()
                altura_ref = tam_antigo.height() if tam_antigo else win.height()
                largura = max(800, min(largura_ref, geo.width()))
                altura = max(500, min(altura_ref, geo.height()))
                win.resize(largura, altura)

                pos = win.pos()
                novo_x = pos.x()
                novo_y = pos.y()
                if novo_x + largura > geo.right():
                    novo_x = max(geo.left(), geo.right() - largura)
                if novo_y + altura > geo.bottom():
                    novo_y = max(geo.top(), geo.bottom() - altura)
                if novo_x < geo.left():
                    novo_x = geo.left()
                if novo_y < geo.top():
                    novo_y = geo.top()
                if novo_x != pos.x() or novo_y != pos.y():
                    win.move(novo_x, novo_y)

    # ── Custo zCentral ──
    def _ler_custos_unitarios(self):
        caminho = _caminho_zcusto()
        if not caminho or not os.path.exists(caminho):
            return {}
        custos = {}
        with open(caminho, "r", encoding="latin-1") as f:
            for linha in f:
                linha = linha.rstrip("\n")
                if len(linha) < 120:
                    continue
                codigo = linha[1:19].strip()
                if not codigo:
                    continue
                if codigo.startswith("-") or not (codigo[0].isdigit() or codigo[0].isalpha()):
                    continue
                custo = linha[105:118].strip()
                if custo and custo != "0,00" and any(ch.isdigit() for ch in custo):
                    custos[codigo.upper()] = _parse_numero(custo)
        return custos

    def _calcular_total_zcentral(self):
        total = 0.0
        custos = self._ler_custos_unitarios()
        for item in self.dados:
            kardex = str(item.get("kardex", "")).strip()
            if not kardex:
                continue
            custo = custos.get(kardex.upper(), 0.0)
            qtde = _parse_numero(str(item.get("qtde_qad", "")))
            total += custo * qtde
        texto = f"R$ {total:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        self.label_total_zcentral.setText(texto)
        if hasattr(self, "lbl_kpi_zcentral"):
            self.lbl_kpi_zcentral.setText(texto)

    def _calcular_total_dph(self):
        total = 0.0
        custos = self._ler_custos_unitarios()
        caminho = _caminho_estoque()
        if caminho and os.path.exists(caminho):
            try:
                with open(caminho, "r", encoding="utf-8") as f:
                    for item in json.load(f):
                        kardex = str(item.get("Kardex", "")).strip()
                        if not kardex:
                            continue
                        qtde = _parse_numero(str(item.get("QtdeDPH", "0")))
                        if qtde <= 0:
                            continue
                        custo = custos.get(kardex.upper(), 0.0)
                        total += custo * qtde
            except (FileNotFoundError, json.JSONDecodeError):
                pass
        texto = f"R$ {total:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        self.label_total_dph.setText(texto)
        if hasattr(self, "lbl_kpi_dph"):
            self.lbl_kpi_dph.setText(texto)
        self._atualizar_total_central_dph()

    def _atualizar_total_central_dph(self):
        zcentral = _parse_numero(self.label_total_zcentral.text().replace("R$", "").strip())
        dph = _parse_numero(self.label_total_dph.text().replace("R$", "").strip())
        valor = zcentral - dph
        texto = f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        self.label_total_dph_dif.setText(texto)
        if hasattr(self, "lbl_kpi_dif"):
            self.lbl_kpi_dif.setText(texto)

    # ── Tabela ──
    def _popular_tabela(self):
        self.tabela.blockSignals(True)
        self.tabela.setRowCount(0)
        filtro = self.campo_filtro.text().strip().lower()
        campo_busca = "qtde_qad" if self._modo_busca_qad else "qtde_sci"
        for idx, item in enumerate(self.dados):
            if filtro:
                texto_total = " ".join(str(v) for v in item.values()).lower()
                texto_origem = str(item.get(campo_busca, "")).lower()
                if filtro not in texto_total and filtro not in texto_origem:
                    continue
            row = self.tabela.rowCount()
            self.tabela.insertRow(row)
            for col, chave in enumerate(self.CHAVES):
                cell = QTableWidgetItem()
                if chave == "transf":
                    cell.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                    valor = str(item.get(chave, ""))
                    estado = Qt.CheckState.Checked if valor.lower() in ("true", "1", "sim", "x") else Qt.CheckState.Unchecked
                    cell.setCheckState(estado)
                else:
                    cell.setText(str(item.get(chave, "")))
                    cell.setFlags(cell.flags() | Qt.ItemFlag.ItemIsEditable)
                self.tabela.setItem(row, col, cell)
            origem = self.tabela.item(row, 0)
            origem.setData(Qt.ItemDataRole.UserRole, idx)
        self._inserir_linha_vazia()
        self.tabela.blockSignals(False)
        self._atualizar_contador()

    def _inserir_linha_vazia(self):
        row = self.tabela.rowCount()
        self.tabela.insertRow(row)
        for col, chave in enumerate(self.CHAVES):
            cell = QTableWidgetItem()
            if chave == "transf":
                cell.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                cell.setCheckState(Qt.CheckState.Unchecked)
            else:
                cell.setText("")
                cell.setFlags(cell.flags() | Qt.ItemFlag.ItemIsEditable)
            self.tabela.setItem(row, col, cell)

    def _item_modificado(self, item):
        row = item.row()
        col = item.column()
        chave = self.CHAVES[col]

        idx = None
        celula_origem = self.tabela.item(row, 0)
        if celula_origem:
            origem = celula_origem.data(Qt.ItemDataRole.UserRole)
            if isinstance(origem, int):
                idx = origem

        if idx is None:
            if row != self.tabela.rowCount() - 1:
                return
            if chave != "transf" and item.text().strip():
                novo_item = {}
                for c, ch in enumerate(self.CHAVES):
                    celula = self.tabela.item(row, c)
                    if not celula:
                        novo_item[ch] = ""
                    elif ch == "transf":
                        novo_item[ch] = "True" if celula.checkState() == Qt.CheckState.Checked else "False"
                    else:
                        novo_item[ch] = celula.text().strip()
                self.dados.append(novo_item)
                celula_origem.setData(Qt.ItemDataRole.UserRole, len(self.dados) - 1)
                self._salvar_json()
                self._inserir_linha_vazia()
            return

        if chave == "transf":
            self.dados[idx][chave] = "True" if item.checkState() == Qt.CheckState.Checked else "False"
        else:
            self.dados[idx][chave] = item.text()
        self._salvar_json()
        if chave == "qtde_qad":
            self._calcular_total_zcentral()
            self._atualizar_total_central_dph()

    def _alternar_busca(self, ativado):
        self._modo_busca_qad = ativado
        self._atualizar_texto_busca()
        self._aplicar_filtro()

    def _atualizar_texto_busca(self):
        texto = "Buscando do QAD" if self._modo_busca_qad else "Buscando do SCI"
        self.btn_busca.setText("QAD" if self._modo_busca_qad else "SCI")
        self.btn_busca.setToolTip(texto)

    def _aplicar_filtro(self):
        self._popular_tabela()

    # ── Exportar Excel ──
    def _exportar_excel(self):
        if not OPENPYXL_DISPONIVEL:
            QMessageBox.warning(
                self, "Exportar Excel",
                "A biblioteca 'openpyxl' não está instalada.\n"
                "Instale com: pip install openpyxl",
            )
            return

        linhas = []
        for row in range(self.tabela.rowCount() - 1):
            linha = []
            for col in range(len(self.COLUNAS)):
                cell = self.tabela.item(row, col)
                linha.append(cell.text() if cell else "")
            linhas.append(linha)

        if not linhas:
            QMessageBox.information(self, "Exportar Excel", "Não há dados para exportar.")
            return

        caminho, _ = QFileDialog.getSaveFileName(
            self, "Exportar para Excel", "fresh_start.xlsx", "Arquivos Excel (*.xlsx)"
        )
        if not caminho:
            return
        if not caminho.lower().endswith(".xlsx"):
            caminho += ".xlsx"

        try:
            wb = Workbook()
            ws = wb.active
            ws.title = "Fresh Start"
            ws.append(list(self.COLUNAS))
            for celula in ws[1]:
                celula.font = Font(bold=True)
            for linha in linhas:
                ws.append(linha)
            for col, largura in enumerate([10, 15, 20, 35, 15, 15, 15, 15, 25, 15, 20, 15, 15], start=1):
                ws.column_dimensions[chr(64 + col)].width = max(largura, 8)
            wb.save(caminho)
        except OSError as erro:
            QMessageBox.critical(self, "Exportar Excel", f"Não foi possível salvar o arquivo.\n{erro}")
            return

        QMessageBox.information(self, "Exportar Excel", f"Tabela exportada com sucesso:\n{caminho}")

    def _atualizar_contador(self):
        total = max(0, self.tabela.rowCount() - 1)
        self.label_contador.setText(f"{total} itens")

    # ── Transferência ──
    def _executar_transferencia(self):
        linhas_para_transferir = []
        for row in range(self.tabela.rowCount()):
            cell_transf = self.tabela.item(row, 0)
            if cell_transf and cell_transf.checkState() == Qt.CheckState.Checked:
                linhas_para_transferir.append(row)

        if not linhas_para_transferir:
            QMessageBox.information(self, "Transferência", "Nenhum item selecionado para transferência.")
            return

        esperar_inicio()

        for row in linhas_para_transferir:
            cell_kardex = self.tabela.item(row, 2)
            cell_qtde = self.tabela.item(row, 5)
            cell_loc = self.tabela.item(row, 4)
            cell_lugar_transf = self.tabela.item(row, 10)
            cell_loc_transf = self.tabela.item(row, 11)

            kardex = cell_kardex.text().strip().upper() if cell_kardex else ""
            qtde = cell_qtde.text().strip() if cell_qtde else ""
            de_lote = cell_loc.text().strip().upper() if cell_loc else ""
            para_lugar = cell_lugar_transf.text().strip().upper() if cell_lugar_transf else ""
            para_lote = cell_loc_transf.text().strip().upper() if cell_loc_transf else ""
            
            if not para_lote:
                para_lote = "RECEBE"

            if not kardex or not qtde:
                continue

            de_local = "10912"
            para_local = "10912"
            de_lugar = "ZCENTRAL"

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

