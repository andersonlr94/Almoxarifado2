import json
import os
import re
import unicodedata

import pandas as pd
import qtawesome as qta
from PySide6.QtCore import Qt, QSize, QTimer, QThread, Signal
from PySide6.QtGui import QGuiApplication, QKeySequence, QShortcut, QColor, QBrush, QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QStyledItemDelegate, QMessageBox, QFrame,
    QFileDialog
)

import config


class EditorDelegate(QStyledItemDelegate):
    def sizeHint(self, option, index):
        base = super().sizeHint(option, index)
        return QSize(base.width(), max(base.height(), 32))

    def createEditor(self, parent, option, index):
        editor = super().createEditor(parent, option, index)
        if isinstance(editor, QLineEdit):
            editor.setMinimumHeight(32)
            editor.setStyleSheet("padding: 2px 6px;")
        return editor


def _caminho_json():
    base = config.obter_caminho_jsons()
    if not base:
        return ""
    return os.path.normpath(
        os.path.join(
            base,
            "Almox",
            "AnaliseEstoque",
            "AnaliseEstoque.json"
        )
    )


def obter_pasta_documentos():
    """Retorna o caminho da pasta Documentos do usuário no Windows (local ou OneDrive)."""
    import sys
    if sys.platform == "win32":
        try:
            import ctypes.wintypes
            CSIDL_PERSONAL = 5  # My Documents
            SHGFP_TYPE_CURRENT = 0
            buf = ctypes.create_unicode_buffer(ctypes.wintypes.MAX_PATH)
            ctypes.windll.shell32.SHGetFolderPathW(None, CSIDL_PERSONAL, None, SHGFP_TYPE_CURRENT, buf)
            caminho = buf.value
            if caminho and os.path.isdir(caminho):
                return os.path.normpath(caminho)
        except Exception:
            pass

    userprofile = os.environ.get("USERPROFILE", "")
    onedrive = os.environ.get("OneDrive", "")
    onedrive_com = os.environ.get("OneDriveCommercial", "")

    candidatos = [
        os.path.join(userprofile, "OneDrive - Versigent", "Documentos"),
        os.path.join(onedrive_com, "Documentos"),
        os.path.join(onedrive, "Documentos"),
        os.path.join(userprofile, "Documents"),
        os.path.join(userprofile, "Documentos"),
        os.path.expanduser("~/Documents"),
        os.path.expanduser("~/Documentos"),
    ]
    for c in candidatos:
        if c and os.path.isdir(c):
            return os.path.normpath(c)

    return os.path.expanduser("~")


class CarregarAnaliseEstoqueThread(QThread):
    dados_carregados = Signal(list)
    erro = Signal(str)

    def run(self):
        try:
            caminho = _caminho_json()
            if not caminho or not os.path.exists(caminho):
                self.dados_carregados.emit([])
                return
            with open(caminho, "r", encoding="utf-8") as f:
                dados = json.load(f)
            self.dados_carregados.emit(dados if isinstance(dados, list) else [])
        except (FileNotFoundError, json.JSONDecodeError):
            self.dados_carregados.emit([])
        except Exception as e:
            self.erro.emit(str(e))


class AnaliseEstoquePage(QWidget):
    COLUNAS = [
        "SA",
        "Destino",
        "Requisição",
        "Kardex",
        "Código",
        "Qtde solicitada",
        "Qtde pendente",
        "Custo unitário",
        "Custo total pendente",
        "Local",
        "Fornecedor",
        "Estoque total",
        "Qtde novo",
        "Qtde retorno",
        "Conta",
        "Projeto Conta",
        "Projeto uso",
        "Status",
    ]

    COLUNAS_PENDENTES = [
        "SA",
        "Destino",
        "Requisição",
        "Kardex",
        "Código",
        "Qtde pendente",
        "Qtde estoque",
        "Qte programado",
        "Saldo",
    ]

    LARGURAS_COMPLETAS = {
        "SA": 80,
        "Destino": 110,
        "Requisição": 95,
        "Kardex": 90,
        "Código": 120,
        "Qtde solicitada": 95,
        "Qtde pendente": 95,
        "Custo unitário": 100,
        "Custo total pendente": 125,
        "Local": 85,
        "Fornecedor": 150,
        "Estoque total": 95,
        "Qtde novo": 85,
        "Qtde retorno": 85,
        "Conta": 80,
        "Projeto Conta": 105,
        "Projeto uso": 105,
        "Status": 95,
    }

    LARGURAS_PENDENTES = {
        "SA": 70,
        "Destino": 140,
        "Requisição": 70,
        "Kardex": 140,
        "Código": 140,
        "Qtde pendente": 115,
        "Qtde estoque": 115,
        "Qte programado": 125,
        "Saldo": 110,
    }

    CHAVES = COLUNAS

    MAPA_NORMALIZACAO_COLUNAS = {
        "sa": "SA",
        "solicitacaodoalmoxarifado": "SA",
        "nsa": "SA",
        "destino": "Destino",
        "requisicao": "Requisição",
        "req": "Requisição",
        "nrequisicao": "Requisição",
        "kardex": "Kardex",
        "codkardex": "Kardex",
        "codigo": "Código",
        "cocigo": "Código",
        "codigodoitem": "Código",
        "coditem": "Código",
        "cod": "Código",
        "qtdesolicitada": "Qtde solicitada",
        "quantidadesolicitada": "Qtde solicitada",
        "solicitada": "Qtde solicitada",
        "qtdsolicitada": "Qtde solicitada",
        "qtdependente": "Qtde pendente",
        "quantidadependente": "Qtde pendente",
        "pendente": "Qtde pendente",
        "qtdpendente": "Qtde pendente",
        "custounitario": "Custo unitário",
        "custounit": "Custo unitário",
        "custo": "Custo unitário",
        "unitario": "Custo unitário",
        "custototalpendente": "Custo total pendente",
        "custototal": "Custo total pendente",
        "totalpendente": "Custo total pendente",
        "local": "Local",
        "loc": "Local",
        "localizacao": "Local",
        "fornecedor": "Fornecedor",
        "fornec": "Fornecedor",
        "estoquetotal": "Estoque total",
        "totalestoque": "Estoque total",
        "estoque": "Estoque total",
        "qtdeestoque": "Qtde estoque",
        "qtdenovo": "Qtde novo",
        "quantidadenovo": "Qtde novo",
        "novo": "Qtde novo",
        "qtderetorno": "Qtde retorno",
        "quantidaderetorno": "Qtde retorno",
        "retorno": "Qtde retorno",
        "ret": "Qtde retorno",
        "conta": "Conta",
        "projetoconta": "Projeto Conta",
        "projconta": "Projeto Conta",
        "projetouso": "Projeto uso",
        "projuso": "Projeto uso",
        "status": "Status",
        "situacao": "Status",
        "qteprogramado": "Qte programado",
        "qtdeprogramado": "Qte programado",
        "quantidadeprogramado": "Qte programado",
        "programado": "Qte programado",
        "saldo": "Saldo",
    }

    def __init__(self):
        super().__init__()
        self.dados = []
        self._texto_filtro_cache = []
        self.modo_pendentes = False
        self.modo_agrupado = False
        self._ordem_saldo_asc = True
        self._filtro_apenas_pendentes = False
        self._linhas_filtradas_atuais = []
        self._mapa_itens_almox = None
        self._mapa_pedidos_prog = None

        self._thread_carregar = CarregarAnaliseEstoqueThread()
        self._thread_carregar.dados_carregados.connect(self._on_dados_carregados)

        self._setup_ui()
        self._carregar_dados()

    def showEvent(self, event):
        super().showEvent(event)
        self._carregar_dados()

    # -------------------------------------------------------------------------
    # UI SETUP
    # -------------------------------------------------------------------------
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 8, 32, 16)
        layout.setSpacing(0)

        card = QWidget()
        card.setObjectName("pageCard")

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(28, 16, 28, 16)
        card_layout.setSpacing(10)

        # =====================================================
        # TOPO (VISÃO GERAL + CONTADOR)
        # =====================================================
        topo = QHBoxLayout()
        topo.setSpacing(18)

        coluna_esquerda = QVBoxLayout()
        coluna_esquerda.setSpacing(10)

        # -----------------------------------------------------
        # BOTÕES DA BARRA DE CONTROLE
        # -----------------------------------------------------
        btn_recarregar = QPushButton()
        btn_recarregar.setIcon(qta.icon("fa6s.arrows-rotate", color="#4f46e5"))
        btn_recarregar.setIconSize(QSize(14, 14))
        btn_recarregar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_recarregar.setFixedSize(34, 34)
        btn_recarregar.setToolTip("Atualizar dados da análise")
        btn_recarregar.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                border: 1px solid #dce3ee;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #eef2ff;
                border-color: #c7d2fe;
            }
            QPushButton:pressed {
                background-color: #e0e7ff;
                border-color: #a5b4fc;
            }
        """)
        btn_recarregar.clicked.connect(self._carregar_dados)

        btn_inserir = QPushButton(" Inserir informações")
        btn_inserir.setIcon(qta.icon("fa6s.file-import", color="#ffffff"))
        btn_inserir.setIconSize(QSize(13, 13))
        btn_inserir.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_inserir.setFixedHeight(34)
        btn_inserir.setToolTip("Carregar o arquivo mais recente de 'Relatório SAs pendentes' (.xlsx) da pasta Documentos")
        btn_inserir.setStyleSheet("""
            QPushButton {
                background-color: #4f46e5;
                color: #ffffff;
                border: 1px solid #4338ca;
                border-radius: 8px;
                padding: 0 14px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #4338ca;
                border-color: #3730a3;
            }
            QPushButton:pressed {
                background-color: #3730a3;
            }
        """)
        btn_inserir.clicked.connect(self._inserir_dados)

        btn_exportar = QPushButton(" Exportar Excel")
        btn_exportar.setIcon(qta.icon("fa6s.file-excel", color="#ffffff"))
        btn_exportar.setIconSize(QSize(13, 13))
        btn_exportar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_exportar.setFixedHeight(34)
        btn_exportar.setToolTip("Exportar dados da listagem atual para planilha Excel (.xlsx)")
        btn_exportar.setStyleSheet("""
            QPushButton {
                background-color: #10b981;
                color: #ffffff;
                border: 1px solid #059669;
                border-radius: 8px;
                padding: 0 14px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #059669;
                border-color: #047857;
            }
            QPushButton:pressed {
                background-color: #047857;
            }
        """)
        btn_exportar.clicked.connect(self._exportar_excel)

        self.campo_filtro = QLineEdit()
        self.campo_filtro.setPlaceholderText("⌕   Pesquisar...")
        self.campo_filtro.setFixedHeight(34)
        self.campo_filtro.setFixedWidth(280)
        self._filtro_timer = QTimer(self)
        self._filtro_timer.setSingleShot(True)
        self._filtro_timer.setInterval(280)
        self._filtro_timer.timeout.connect(self._on_filtro_timeout)
        self.campo_filtro.textChanged.connect(self._on_filtro_text_changed)

        self.campo_filtro.setStyleSheet("""
            QLineEdit {
                background: #ffffff;
                color: #17203f;
                border: 1px solid #dce3ee;
                border-radius: 8px;
                padding-left: 12px;
                padding-right: 12px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1.5px solid #6366f1;
            }
        """)

        self.btn_limpar_filtro = QPushButton("✕")
        self.btn_limpar_filtro.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_limpar_filtro.setFixedSize(34, 34)
        self.btn_limpar_filtro.setToolTip("Limpar filtro")
        self.btn_limpar_filtro.clicked.connect(self._limpar_filtro)
        self.btn_limpar_filtro.setStyleSheet("""
            QPushButton {
                background: #ffffff;
                color: #9ca3af;
                border: 1px solid #dce3ee;
                border-radius: 8px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #fef2f2;
                color: #ef4444;
                border-color: #fca5a5;
            }
            QPushButton:pressed {
                background: #fee2e2;
                color: #dc2626;
            }
        """)

        # -----------------------------------------------------
        # CARD CENTRAL - ITEM SELECIONADO (VISÃO GERAL)
        # -----------------------------------------------------
        ALTURA_VISAO_GERAL = 120
        ALTURA_CONTADOR_BOX = 120
        ALTURA_BTN_TOGGLE = 34
        ESPACO_QUADROS = 10

        self.detalhes_box = QWidget()
        self.detalhes_box.setObjectName("detalhesBox")
        self.detalhes_box.setFixedHeight(ALTURA_VISAO_GERAL)
        self.detalhes_box.setMinimumWidth(670)

        self.detalhes_box.setStyleSheet("""
            QWidget#detalhesBox {
                background: #ffffff;
                border: 1px solid #dce3ee;
                border-radius: 12px;
            }
            QLabel {
                border: none;
                background: transparent;
            }
        """)

        detalhes_layout = QVBoxLayout(self.detalhes_box)
        detalhes_layout.setContentsMargins(14, 6, 14, 6)
        detalhes_layout.setSpacing(2)

        lbl_visao = QLabel("VISÃO GERAL DO ITEM SELECIONADO")
        lbl_visao.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        lbl_visao.setStyleSheet("""
            QLabel {
                color: #65769d;
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 0.5px;
                margin: 0;
                padding: 0;
            }
        """)
        detalhes_layout.addWidget(lbl_visao, 0, Qt.AlignmentFlag.AlignTop)

        self._labels_valores = {}

        def criar_linha(rotulo, chave, simbolo="", cor="#5f6cf5", largura_label=60, word_wrap=False):
            widget = QWidget()
            widget.setMinimumHeight(24)

            lay = QHBoxLayout(widget)
            lay.setContentsMargins(0, 0, 0, 0)
            lay.setSpacing(4)

            icone = QLabel(simbolo)
            icone.setFixedWidth(16)
            icone.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icone.setStyleSheet(f"""
                QLabel {{
                    color: {cor};
                    font-size: 15px;
                    font-weight: 700;
                }}
            """)

            lbl_nome = QLabel(rotulo.upper())
            lbl_nome.setMinimumWidth(largura_label)
            lbl_nome.setStyleSheet("""
                QLabel {
                    color: #7183aa;
                    font-size: 10px;
                    font-weight: 600;
                }
            """)

            lbl_valor = QLabel("-")
            lbl_valor.setWordWrap(word_wrap)
            lbl_valor.setStyleSheet("""
                QLabel {
                    color: #17203f;
                    font-size: 12px;
                    font-weight: 600;
                }
            """)
            lbl_valor.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            self._labels_valores[chave] = lbl_valor

            lay.addWidget(icone)
            lay.addWidget(lbl_nome)
            lay.addWidget(lbl_valor, 1)

            return widget

        def separador():
            linha = QFrame()
            linha.setFrameShape(QFrame.Shape.HLine)
            linha.setStyleSheet("""
                QFrame {
                    border: none;
                    background: #edf0f5;
                    max-height: 1px;
                }
            """)
            return linha

        def separador_vertical():
            linha = QFrame()
            linha.setFrameShape(QFrame.Shape.VLine)
            linha.setStyleSheet("""
                QFrame {
                    border: none;
                    background: #edf0f5;
                    max-width: 1px;
                }
            """)
            return linha

        # Linha 1: SA | Requisição | Kardex | Código | Status
        linha1 = QHBoxLayout()
        linha1.setSpacing(14)
        linha1.setContentsMargins(0, 0, 0, 0)
        linha1.addWidget(criar_linha("SA", "SA", "◇", "#5865f2", largura_label=25), 1)
        linha1.addWidget(separador_vertical())
        linha1.addWidget(criar_linha("Req", "Requisição", "▤", "#5865f2", largura_label=30), 1)
        linha1.addWidget(separador_vertical())
        linha1.addWidget(criar_linha("Kardex", "Kardex", "▤", "#5865f2", largura_label=48), 1)
        linha1.addWidget(separador_vertical())
        linha1.addWidget(criar_linha("Código", "Código", "◇", "#5865f2", largura_label=48), 1)
        linha1.addWidget(separador_vertical())
        linha1.addWidget(criar_linha("Status", "Status", "◉", "#10b981", largura_label=45), 1)

        linha1_widget = QWidget()
        linha1_widget.setLayout(linha1)
        detalhes_layout.addWidget(linha1_widget)
        detalhes_layout.addWidget(separador())

        # Linha 2: Destino | Local | Fornecedor | Conta | Projeto Conta
        linha2 = QHBoxLayout()
        linha2.setSpacing(14)
        linha2.setContentsMargins(0, 0, 0, 0)
        linha2.addWidget(criar_linha("Destino", "Destino", "⌖", "#5865f2", largura_label=48), 1)
        linha2.addWidget(separador_vertical())
        linha2.addWidget(criar_linha("Local", "Local", "⌖", "#5865f2", largura_label=36), 1)
        linha2.addWidget(separador_vertical())
        linha2.addWidget(criar_linha("Fornecedor", "Fornecedor", "▣", "#5865f2", largura_label=68), 2)
        linha2.addWidget(separador_vertical())
        linha2.addWidget(criar_linha("Conta", "Conta", "◪", "#5865f2", largura_label=38), 1)
        linha2.addWidget(separador_vertical())
        linha2.addWidget(criar_linha("Proj Conta", "Projeto Conta", "◪", "#5865f2", largura_label=64), 1)

        linha2_widget = QWidget()
        linha2_widget.setLayout(linha2)
        detalhes_layout.addWidget(linha2_widget)
        detalhes_layout.addWidget(separador())

        # Linha 3: Solicitada | Pendente | Est. Total | Qtde Novo | Qtde Retorno | Custo Unit | Custo Pendente
        linha3 = QHBoxLayout()
        linha3.setSpacing(10)
        linha3.setContentsMargins(0, 0, 0, 0)
        linha3.addWidget(criar_linha("Solicitada", "Qtde solicitada", "▣", "#5865f2", largura_label=55))
        linha3.addWidget(separador_vertical())
        linha3.addWidget(criar_linha("Pendente", "Qtde pendente", "▣", "#ff7a21", largura_label=55))
        linha3.addWidget(separador_vertical())
        linha3.addWidget(criar_linha("Est. Total", "Estoque total", "▣", "#16b86c", largura_label=55))
        linha3.addWidget(separador_vertical())
        linha3.addWidget(criar_linha("Novo", "Qtde novo", "▣", "#16b86c", largura_label=35))
        linha3.addWidget(separador_vertical())
        linha3.addWidget(criar_linha("Retorno", "Qtde retorno", "▣", "#ff7a21", largura_label=48))
        linha3.addWidget(separador_vertical())
        linha3.addWidget(criar_linha("Custo Unit", "Custo unitário", "＄", "#16b86c", largura_label=60))
        linha3.addWidget(separador_vertical())
        linha3.addWidget(criar_linha("Custo Pend", "Custo total pendente", "＄", "#e11d48", largura_label=65))
        linha3.addStretch(1)

        linha3_widget = QWidget()
        linha3_widget.setLayout(linha3)
        detalhes_layout.addWidget(linha3_widget)
        detalhes_layout.addStretch(1)

        coluna_esquerda.addWidget(self.detalhes_box)

        # -----------------------------------------------------
        # BOTÃO AGRUPAR POR ITEM E INDICADOR DE CUSTO
        # -----------------------------------------------------
        self.btn_agrupar = QPushButton(" Agrupar por item")
        self.btn_agrupar.setIcon(qta.icon("fa6s.layer-group", color="#4338ca"))
        self.btn_agrupar.setIconSize(QSize(13, 13))
        self.btn_agrupar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_agrupar.setFixedHeight(34)
        self.btn_agrupar.setCheckable(True)
        self.btn_agrupar.setToolTip("Agrupar linhas por Kardex somando as quantidades pendentes")
        self.btn_agrupar.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                color: #4338ca;
                border: 1px solid #c7d2fe;
                border-radius: 8px;
                padding: 0 14px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #eef2ff;
                border-color: #a5b4fc;
            }
            QPushButton:checked {
                background-color: #4f46e5;
                color: #ffffff;
                border: 1px solid #4338ca;
            }
            QPushButton:checked:hover {
                background-color: #4338ca;
            }
        """)
        self.btn_agrupar.clicked.connect(self._toggle_agrupamento)
        self.btn_agrupar.setVisible(False)

        self.btn_indicador_custo = QPushButton("Total Pendente: R$ 0,00")
        self.btn_indicador_custo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_indicador_custo.setFixedHeight(34)
        self.btn_indicador_custo.setIcon(qta.icon("fa6s.dollar-sign", color="#b45309"))
        self.btn_indicador_custo.setIconSize(QSize(12, 12))
        self.btn_indicador_custo.setStyleSheet("""
            QPushButton {
                background-color: #fffbeb;
                color: #b45309;
                border: 1px solid #fde68a;
                border-radius: 8px;
                padding: 0 14px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #fef3c7;
            }
        """)

        linha_filtro_botoes = QHBoxLayout()
        linha_filtro_botoes.setSpacing(10)
        linha_filtro_botoes.addWidget(self.campo_filtro)
        linha_filtro_botoes.addWidget(self.btn_limpar_filtro)
        linha_filtro_botoes.addWidget(btn_recarregar)
        linha_filtro_botoes.addWidget(btn_inserir)
        linha_filtro_botoes.addWidget(btn_exportar)
        linha_filtro_botoes.addStretch()
        linha_filtro_botoes.addWidget(self.btn_agrupar)
        linha_filtro_botoes.addWidget(self.btn_indicador_custo)

        coluna_esquerda.addLayout(linha_filtro_botoes)

        topo.addLayout(coluna_esquerda)

        # =====================================================
        # CARD CONTADOR (DIREITA SUPERIOR)
        # =====================================================
        contador_box = QWidget()
        contador_box.setFixedWidth(141)
        contador_box.setFixedHeight(ALTURA_CONTADOR_BOX)
        contador_box.setStyleSheet("""
            QWidget {
                background: white;
                border: 1px solid #dce3ee;
                border-radius: 12px;
            }
            QLabel {
                border: none;
                background: transparent;
            }
        """)

        contador_layout = QVBoxLayout(contador_box)
        contador_layout.setContentsMargins(8, 5, 8, 5)
        contador_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        contador_layout.setSpacing(2)

        circulo = QLabel("◇")
        circulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        circulo.setFixedSize(34, 34)
        circulo.setStyleSheet("""
            QLabel {
                background: #f0f1ff;
                color: #5b61f6;
                border: 1px solid #e0e3ff;
                border-radius: 17px;
                font-size: 20px;
                font-weight: 600;
            }
        """)
        contador_layout.addWidget(circulo, alignment=Qt.AlignmentFlag.AlignCenter)

        self.label_contador = QLabel("0")
        self.label_contador.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_contador.setStyleSheet("""
            QLabel {
                color: #11163d;
                font-size: 20px;
                font-weight: 700;
            }
        """)
        contador_layout.addWidget(self.label_contador)

        lbl_itens = QLabel("itens analisados")
        lbl_itens.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_itens.setStyleSheet("""
            QLabel {
                color: #63739a;
                font-size: 11px;
                font-weight: 500;
            }
        """)
        contador_layout.addWidget(lbl_itens)
        contador_layout.addStretch()

        self.btn_toggle = QPushButton("⚡  SAs Pendentes")
        self.btn_toggle.setObjectName("btnSecondary")
        self.btn_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle.setFixedSize(141, ALTURA_BTN_TOGGLE)
        self.btn_toggle.setCheckable(True)
        self.btn_toggle.clicked.connect(self._toggle_filtro_pendentes)
        self.btn_toggle.setStyleSheet("""
            QPushButton {
                background: white;
                color: #52648f;
                border: 1px solid #dce3ee;
                border-radius: 10px;
                font-size: 12px;
                font-weight: 500;
                padding: 0 10px;
            }
            QPushButton:hover {
                background: #f8faff;
                border-color: #bcc9e0;
            }
            QPushButton:checked {
                background: #fee2e2;
                color: #dc2626;
                border: 1px solid #fca5a5;
                font-weight: 600;
            }
        """)

        coluna_direita_superior = QWidget()
        coluna_direita_superior.setFixedWidth(141)
        coluna_direita_superior.setFixedHeight(ALTURA_CONTADOR_BOX + ESPACO_QUADROS + ALTURA_BTN_TOGGLE)
        coluna_superior_layout = QVBoxLayout(coluna_direita_superior)
        coluna_superior_layout.setContentsMargins(0, 0, 0, 0)
        coluna_superior_layout.setSpacing(ESPACO_QUADROS)
        coluna_superior_layout.addWidget(contador_box)
        coluna_superior_layout.addWidget(self.btn_toggle)

        topo.addWidget(coluna_direita_superior)
        card_layout.addLayout(topo)

        # =====================================================
        # TABELA
        # =====================================================
        self.tabela = QTableWidget(0, len(self.COLUNAS))
        self.tabela.setHorizontalHeaderLabels(self.COLUNAS)
        self.tabela.setItemDelegate(EditorDelegate(self.tabela))
        self.tabela.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabela.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tabela.setAlternatingRowColors(True)
        self.tabela.verticalHeader().setVisible(False)

        self.tabela.setStyleSheet("""
            QTableWidget {
                background: white;
                color: #111827;
                border: 1px solid #dfe5ee;
                border-radius: 11px;
                gridline-color: #edf0f5;
                font-size: 11px;
                selection-background-color: #eef0ff;
                selection-color: #111827;
            }
            QHeaderView::section {
                background-color: #ffffff;
                color: #5b657a;
                font-size: 11px;
                font-weight: 700;
                border: none;
                border-bottom: 2px solid #e5e9f0;
                border-right: 1px solid #edf0f5;
                padding: 7px 6px;
            }
            QTableWidget::item {
                border-bottom: 1px solid #edf0f5;
                padding-left: 6px;
                padding-right: 6px;
            }
            QTableWidget::item:selected {
                background-color: #eef0ff;
                color: #111827;
            }
        """)

        header = self.tabela.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setDefaultSectionSize(110)
        header.sectionClicked.connect(self._on_header_section_clicked)

        self._aplicar_colunas_e_larguras()

        self.tabela.itemSelectionChanged.connect(self._atualizar_detalhes)
        self.tabela.cellClicked.connect(self._atualizar_detalhes)

        # Atalho Ctrl+C na tabela
        self._atalho_copiar = QShortcut(QKeySequence.StandardKey.Copy, self.tabela)
        self._atalho_copiar.activated.connect(self._copiar_selecao)

        card_layout.addWidget(self.tabela, 1)
        layout.addWidget(card)

        self._atualizar_indicadores(0, 0.0)

    # -------------------------------------------------------------------------
    # TABELA E MODO DE EXIBIÇÃO
    # -------------------------------------------------------------------------
    def _aplicar_colunas_e_larguras(self):
        if self.modo_pendentes:
            indicador_ordem = " ▲" if getattr(self, "_ordem_saldo_asc", True) else " ▼"
            colunas_rotulos = [
                f"Saldo{indicador_ordem}" if c == "Saldo" else c
                for c in self.COLUNAS_PENDENTES
            ]
        else:
            colunas_rotulos = self.COLUNAS

        self.tabela.setColumnCount(len(colunas_rotulos))
        self.tabela.setHorizontalHeaderLabels(colunas_rotulos)

        larguras = self.LARGURAS_PENDENTES if self.modo_pendentes else self.LARGURAS_COMPLETAS
        colunas_base = self.COLUNAS_PENDENTES if self.modo_pendentes else self.COLUNAS
        for idx, col_name in enumerate(colunas_base):
            if col_name in larguras:
                self.tabela.setColumnWidth(idx, larguras[col_name])

        if self.modo_pendentes:
            for idx, c in enumerate(self.COLUNAS_PENDENTES):
                if c == "Saldo":
                    header_item = self.tabela.horizontalHeaderItem(idx)
                    if header_item:
                        ordem_texto = "menor para o maior" if getattr(self, "_ordem_saldo_asc", True) else "maior para o menor"
                        header_item.setToolTip(f"Saldo ordenado do {ordem_texto}. Clique para alternar.")

    def _on_header_section_clicked(self, logical_index):
        if not self.modo_pendentes:
            return
        if logical_index < len(self.COLUNAS_PENDENTES) and self.COLUNAS_PENDENTES[logical_index] == "Saldo":
            self._ordem_saldo_asc = not getattr(self, "_ordem_saldo_asc", True)
            self._popular_tabela()

    # -------------------------------------------------------------------------
    # CARREGAMENTO E DADOS
    # -------------------------------------------------------------------------
    def _carregar_dados(self):
        if self._thread_carregar.isRunning():
            return
        self._mapa_itens_almox = None
        self._mapa_pedidos_prog = None
        self.tabela.setRowCount(0)
        self._thread_carregar.start()

    def _corrigir_dados_deslocados(self, dados_lista):
        if not dados_lista or len(dados_lista) < 2:
            return dados_lista
        # Se os primeiros valores da coluna 'SA' forem inteiros sequenciais (1, 2, 3...)
        primeiros_sa = [str(d.get("SA", "")).strip() for d in dados_lista[:5]]
        if all(v.isdigit() for v in primeiros_sa) and primeiros_sa == [str(i) for i in range(1, len(primeiros_sa) + 1)]:
            novos = []
            for d in dados_lista:
                valores_ordenados = [d.get(col, "") for col in self.COLUNAS]
                item_corrigido = {}
                for idx, col in enumerate(self.COLUNAS):
                    idx_origem = idx + 1
                    item_corrigido[col] = valores_ordenados[idx_origem] if idx_origem < len(valores_ordenados) else ""
                novos.append(item_corrigido)
            return novos
        return dados_lista

    def _on_dados_carregados(self, dados):
        dados_corrigidos = self._corrigir_dados_deslocados(dados)
        if dados_corrigidos != dados:
            self.dados = dados_corrigidos
            self._salvar_json()
        else:
            self.dados = dados
        self._rebuild_cache_filtro()
        self._popular_tabela()

    def _rebuild_cache_filtro(self):
        self._texto_filtro_cache = [
            " ".join(str(v) for v in item.values()).lower()
            for item in self.dados
        ]

    def _parse_numero(self, valor):
        if valor is None:
            return 0.0
        val_str = str(valor).strip().replace("R$", "").replace(" ", "")
        if not val_str or val_str == "-":
            return 0.0
        if "," in val_str:
            val_str = val_str.replace(".", "").replace(",", ".")
        try:
            return float(val_str)
        except ValueError:
            return 0.0

    def _formatar_numero_exibicao(self, num):
        if num is None:
            return "0"
        if isinstance(num, (int, float)):
            if num == int(num):
                return str(int(num))
            return f"{num:.2f}".rstrip("0").rstrip(".")
        s = str(num).strip()
        return s if s else "0"

    def _carregar_mapa_itens_almoxarifado(self):
        """Carrega dados de ItensAlmoxarifado.json indexados por Kardex e Código."""
        try:
            base = config.obter_caminho_jsons()
            if not base:
                return {}, {}
            caminho = os.path.normpath(os.path.join(base, "Almox", "ItensAlmoxarifado", "ItensAlmoxarifado.json"))
            if not os.path.exists(caminho):
                return {}, {}
            with open(caminho, "r", encoding="utf-8") as f:
                dados_almox = json.load(f)
            if not isinstance(dados_almox, list):
                return {}, {}
            por_kardex = {}
            por_codigo = {}
            for item in dados_almox:
                k = str(item.get("Kardex", "") or "").strip()
                c = str(item.get("Código", "") or "").strip().upper()
                if k:
                    por_kardex[k] = item
                    if k.isdigit():
                        por_kardex[str(int(k))] = item
                if c:
                    por_codigo[c] = item
            return por_kardex, por_codigo
        except Exception:
            return {}, {}

    def _carregar_mapa_pedidos_programados(self):
        """Carrega totais pendentes/programados de pedidos de compra indexados por Kardex e Código."""
        try:
            base = config.obter_caminho_jsons()
            if not base:
                return {}, {}
            caminho = os.path.normpath(os.path.join(base, "Almox", "ControlePedidos", "PedidosPendentes", "PedidosPendentes.json"))
            if not os.path.exists(caminho):
                return {}, {}
            with open(caminho, "r", encoding="utf-8") as f:
                pedidos = json.load(f)
            if not isinstance(pedidos, list):
                return {}, {}
            totais_kardex = {}
            totais_codigo = {}
            for ped in pedidos:
                status = str(ped.get("Status", "") or "").strip().lower()
                if "entregue" in status or "cancelad" in status:
                    continue
                qtde = self._parse_numero(ped.get("Qtde pendente", ped.get("Qtde programada", 0)))
                if qtde <= 0:
                    continue
                k = str(ped.get("Kardex", "") or "").strip()
                c = str(ped.get("Código", "") or "").strip().upper()
                if k:
                    totais_kardex[k] = totais_kardex.get(k, 0.0) + qtde
                    if k.isdigit():
                        k_int = str(int(k))
                        if k_int != k:
                            totais_kardex[k_int] = totais_kardex.get(k_int, 0.0) + qtde
                if c:
                    totais_codigo[c] = totais_codigo.get(c, 0.0) + qtde
            return totais_kardex, totais_codigo
        except Exception:
            return {}, {}

    def _obter_dados_linha_pendentes(self, item, mapa_k_almox, mapa_c_almox, mapa_k_ped, mapa_c_ped):
        """
        Retorna os dados correspondentes às 9 colunas de SAs Pendentes.
        Os valores de 'Qtde estoque' e 'Qte programado' são obtidos
        EXCLUSIVAMENTE do sistema (ItensAlmoxarifado.json e PedidosPendentes.json),
        nunca da planilha importada.
        """
        kardex = str(item.get("Kardex", "") or "").strip()
        codigo = str(item.get("Código", "") or "").strip().upper()
        k_int = str(int(kardex)) if kardex.isdigit() else kardex

        # 1. Qtde estoque - EXCLUSIVAMENTE NO SISTEMA (ItensAlmoxarifado.json: Qtde novo + Qtde retorno)
        item_almox = (
            mapa_k_almox.get(kardex)
            or (mapa_k_almox.get(k_int) if kardex.isdigit() else None)
            or mapa_c_almox.get(codigo)
        )
        if item_almox:
            novo = self._parse_numero(item_almox.get("Qtde novo", 0))
            retorno = self._parse_numero(item_almox.get("Qtde retorno", 0))
            val_estoque_num = novo + retorno
        else:
            val_estoque_num = 0.0

        # 2. Qte programado - EXCLUSIVAMENTE NO SISTEMA (PedidosPendentes.json e ItensAlmoxarifado.json)
        ped_prog = (
            mapa_k_ped.get(kardex)
            or (mapa_k_ped.get(k_int) if kardex.isdigit() else None)
            or mapa_c_ped.get(codigo)
        )
        if ped_prog is not None and ped_prog > 0:
            val_programado_num = ped_prog
        elif item_almox and ("Pend. entrega compras" in item_almox or "Qtde comprada" in item_almox):
            val_programado_num = self._parse_numero(item_almox.get("Pend. entrega compras", item_almox.get("Qtde comprada", 0)))
        else:
            val_programado_num = 0.0

        # 3. Qtde pendente (da SA)
        val_pendente_num = self._parse_numero(item.get("Qtde pendente", 0))

        # 4. Saldo: (Estoque do sistema + Programado do sistema) - Pendente da SA
        val_saldo_num = (val_estoque_num + val_programado_num) - val_pendente_num

        return {
            "SA": str(item.get("SA", "") or ""),
            "Destino": str(item.get("Destino", "") or ""),
            "Requisição": str(item.get("Requisição", "") or ""),
            "Kardex": str(item.get("Kardex", "") or ""),
            "Código": str(item.get("Código", "") or ""),
            "Qtde pendente": self._formatar_numero_exibicao(val_pendente_num),
            "Qtde estoque": self._formatar_numero_exibicao(val_estoque_num),
            "Qte programado": self._formatar_numero_exibicao(val_programado_num),
            "Saldo": self._formatar_numero_exibicao(val_saldo_num),
            "_saldo_num": val_saldo_num,
            "_estoque_num": val_estoque_num,
            "_programado_num": val_programado_num,
        }

    def _toggle_agrupamento(self):
        self.modo_agrupado = not self.modo_agrupado
        self.btn_agrupar.setChecked(self.modo_agrupado)
        if self.modo_agrupado:
            self.btn_agrupar.setText(" Desagrupar")
            self.btn_agrupar.setIcon(qta.icon("fa6s.object-ungroup", color="#ffffff"))
            self.btn_agrupar.setToolTip("Clique para desagrupar e exibir todas as SAs individualmente")
        else:
            self.btn_agrupar.setText(" Agrupar por item")
            self.btn_agrupar.setIcon(qta.icon("fa6s.layer-group", color="#4338ca"))
            self.btn_agrupar.setToolTip("Agrupar linhas por Kardex somando as quantidades pendentes")
        self._popular_tabela()

    def _agrupar_por_kardex(self, lista_itens):
        grupos = {}
        for item in lista_itens:
            kardex = str(item.get("Kardex", "") or "").strip()
            chave = kardex if kardex else str(item.get("Código", "") or "").strip().upper()
            if not chave:
                chave = f"__sem_kardex_{id(item)}"
            if chave not in grupos:
                grupos[chave] = []
            grupos[chave].append(item)

        itens_agrupados = []
        for chave, grupo in grupos.items():
            primeiro = grupo[0]
            item_agr = dict(primeiro)

            # As colunas SA, Destino, Requisição devem ficar em branco ao agrupar
            item_agr["SA"] = ""
            item_agr["Destino"] = ""
            item_agr["Requisição"] = ""

            # Soma das quantidades pendentes de todas as SAs do grupo
            soma_pendente = sum(self._parse_numero(it.get("Qtde pendente", 0)) for it in grupo)
            item_agr["Qtde pendente"] = self._formatar_numero_exibicao(soma_pendente)

            # Soma de quantidade solicitada
            soma_solicitada = sum(self._parse_numero(it.get("Qtde solicitada", 0)) for it in grupo)
            item_agr["Qtde solicitada"] = self._formatar_numero_exibicao(soma_solicitada)

            # Soma do custo total pendente
            soma_custo_pendente = sum(self._parse_numero(it.get("Custo total pendente", 0)) for it in grupo)
            if soma_custo_pendente > 0:
                item_agr["Custo total pendente"] = f"{soma_custo_pendente:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

            item_agr["_itens_originais"] = grupo
            item_agr["_qtd_itens_agrupados"] = len(grupo)
            itens_agrupados.append(item_agr)

        return itens_agrupados

    def _popular_tabela(self):
        if len(self._texto_filtro_cache) != len(self.dados):
            self._rebuild_cache_filtro()

        self.tabela.setUpdatesEnabled(False)
        self.tabela.blockSignals(True)

        self._aplicar_colunas_e_larguras()

        filtro_texto = self.campo_filtro.text().strip().lower()
        filtrados = []
        cache = self._texto_filtro_cache

        total_pendentes = 0
        total_custo_pendente = 0.0

        for idx, item in enumerate(self.dados):
            qtde_pend = self._parse_numero(item.get("Qtde pendente", 0))
            custo_pend = self._parse_numero(item.get("Custo total pendente", 0))

            if qtde_pend > 0:
                total_pendentes += 1
                total_custo_pendente += custo_pend

            if (self.modo_pendentes or self._filtro_apenas_pendentes) and qtde_pend <= 0:
                continue

            if filtro_texto:
                texto = cache[idx] if idx < len(cache) else " ".join(str(v) for v in item.values()).lower()
                if filtro_texto not in texto:
                    continue

            filtrados.append(item)

        # Se o modo agrupado estiver ativo, agrupa por Kardex somando as quantidades pendentes
        if self.modo_agrupado:
            linhas_exibicao = self._agrupar_por_kardex(filtrados)
        else:
            linhas_exibicao = filtrados

        if self.modo_pendentes:
            if self._mapa_itens_almox is None:
                self._mapa_itens_almox = self._carregar_mapa_itens_almoxarifado()
            if self._mapa_pedidos_prog is None:
                self._mapa_pedidos_prog = self._carregar_mapa_pedidos_programados()
            mapa_k_almox, mapa_c_almox = self._mapa_itens_almox
            mapa_k_ped, mapa_c_ped = self._mapa_pedidos_prog

            # Prepara os dados das 9 colunas e calcula o Saldo numérico para ordenação
            itens_com_dados = [
                (item, self._obter_dados_linha_pendentes(item, mapa_k_almox, mapa_c_almox, mapa_k_ped, mapa_c_ped))
                for item in linhas_exibicao
            ]

            # Ordena por Saldo numérico (padrão menor para maior: _ordem_saldo_asc = True)
            ordem_asc = getattr(self, "_ordem_saldo_asc", True)
            itens_com_dados.sort(key=lambda x: x[1].get("_saldo_num", 0.0), reverse=not ordem_asc)

            self._linhas_filtradas_atuais = [x[0] for x in itens_com_dados]
            self.tabela.setRowCount(len(itens_com_dados))

            for row, (item, dados_linha) in enumerate(itens_com_dados):
                for col, chave in enumerate(self.COLUNAS_PENDENTES):
                    valor = str(dados_linha.get(chave, ""))
                    cell = QTableWidgetItem(valor)
                    cell.setFlags(cell.flags() & ~Qt.ItemFlag.ItemIsEditable)

                    if col == 0:
                        cell.setData(Qt.ItemDataRole.UserRole, item)

                    # Alinhamento e estilizações no modo SAs Pendentes
                    if chave in ("SA", "Requisição", "Kardex", "Qtde estoque", "Qte programado"):
                        cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                        if chave == "Qtde estoque":
                            est_num = dados_linha.get("_estoque_num", 0.0)
                            if est_num <= 0:
                                cell.setForeground(QBrush(QColor("#dc2626")))
                            else:
                                cell.setForeground(QBrush(QColor("#15803d")))
                        elif chave == "Qte programado":
                            prog_num = dados_linha.get("_programado_num", 0.0)
                            if prog_num > 0:
                                cell.setForeground(QBrush(QColor("#2563eb")))
                    elif chave == "Qtde pendente":
                        cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                        font = cell.font()
                        font.setBold(True)
                        cell.setFont(font)
                        cell.setForeground(QBrush(QColor("#ea580c")))
                    elif chave == "Saldo":
                        cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                        saldo_num = dados_linha.get("_saldo_num", 0.0)
                        font = cell.font()
                        font.setBold(True)
                        cell.setFont(font)
                        if saldo_num < 0:
                            cell.setForeground(QBrush(QColor("#dc2626")))
                            cell.setBackground(QBrush(QColor("#fef2f2")))
                        elif saldo_num > 0:
                            cell.setForeground(QBrush(QColor("#16a34a")))
                        else:
                            cell.setForeground(QBrush(QColor("#4b5563")))
                    else:
                        cell.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

                    self.tabela.setItem(row, col, cell)
        else:
            self._linhas_filtradas_atuais = linhas_exibicao
            self.tabela.setRowCount(len(linhas_exibicao))

            for row, item in enumerate(linhas_exibicao):
                for col, chave in enumerate(self.CHAVES):
                    valor = str(item.get(chave, "") if item.get(chave) is not None else "")
                    cell = QTableWidgetItem(valor)
                    cell.setFlags(cell.flags() & ~Qt.ItemFlag.ItemIsEditable)

                    if col == 0:
                        cell.setData(Qt.ItemDataRole.UserRole, item)

                    # Alinhamento numérico para colunas específicas
                    if chave in ("Qtde solicitada", "Qtde pendente", "Estoque total", "Qtde novo", "Qtde retorno"):
                        cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    elif chave in ("Custo unitário", "Custo total pendente"):
                        cell.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

                    self.tabela.setItem(row, col, cell)

        self.tabela.blockSignals(False)
        self.tabela.setUpdatesEnabled(True)

        self.label_contador.setText(str(len(self._linhas_filtradas_atuais)))
        self._atualizar_indicadores(total_pendentes, total_custo_pendente)

        if len(self._linhas_filtradas_atuais) > 0:
            self.tabela.selectRow(0)
            self._atualizar_detalhes()
        else:
            self._limpar_detalhes()

    def _atualizar_indicadores(self, total_pendentes, total_custo_pendente):
        self.btn_indicador_custo.setText(f"Total Pendente: R$ {total_custo_pendente:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

    def _toggle_filtro_pendentes(self):
        self.modo_pendentes = not self.modo_pendentes
        self._filtro_apenas_pendentes = self.modo_pendentes
        self.btn_toggle.setChecked(self.modo_pendentes)
        self.btn_toggle.setText("▣  Relatório" if self.modo_pendentes else "⚡  SAs Pendentes")
        self.btn_toggle.setToolTip(
            "Clique para voltar ao Relatório (18 colunas)"
            if self.modo_pendentes
            else "Alternar para tabela de SAs Pendentes (9 colunas)"
        )
        # O botão agrupar/desagrupar aparece apenas na tabela de SAs Pendentes
        self.btn_agrupar.setVisible(self.modo_pendentes)
        if not self.modo_pendentes:
            self.modo_agrupado = False
            self.btn_agrupar.setChecked(False)
            self.btn_agrupar.setText(" Agrupar por item")
            self.btn_agrupar.setIcon(qta.icon("fa6s.layer-group", color="#4338ca"))
            self.btn_agrupar.setToolTip("Agrupar linhas por Kardex somando as quantidades pendentes")
        self._popular_tabela()

    def _atualizar_detalhes(self):
        row = self.tabela.currentRow()
        if row < 0 or row >= self.tabela.rowCount():
            self._limpar_detalhes()
            return

        item = None
        cell_0 = self.tabela.item(row, 0)
        if cell_0:
            item = cell_0.data(Qt.ItemDataRole.UserRole)
        if not item and hasattr(self, "_linhas_filtradas_atuais") and 0 <= row < len(self._linhas_filtradas_atuais):
            item = self._linhas_filtradas_atuais[row]

        if not item:
            self._limpar_detalhes()
            return

        for chave, lbl in self._labels_valores.items():
            val = str(item.get(chave, "") if item.get(chave) is not None else "").strip()
            lbl.setText(val if val else "-")

        # Se for item agrupado por Kardex, sinaliza no campo SA da visão geral
        if item.get("_qtd_itens_agrupados", 1) > 1:
            if "SA" in self._labels_valores and not item.get("SA"):
                qtd = item.get("_qtd_itens_agrupados")
                self._labels_valores["SA"].setText(f"({qtd} SAs agrupadas)")

        # No modo SAs pendentes, garante que o quadro superior exiba os valores oficiais de estoque do próprio sistema
        if self.modo_pendentes and self._mapa_itens_almox:
            mapa_k_almox, mapa_c_almox = self._mapa_itens_almox
            kardex = str(item.get("Kardex", "") or "").strip()
            codigo = str(item.get("Código", "") or "").strip().upper()
            k_int = str(int(kardex)) if kardex.isdigit() else kardex
            item_almox = (
                mapa_k_almox.get(kardex)
                or (mapa_k_almox.get(k_int) if kardex.isdigit() else None)
                or mapa_c_almox.get(codigo)
            )
            if item_almox:
                novo = self._parse_numero(item_almox.get("Qtde novo", 0))
                retorno = self._parse_numero(item_almox.get("Qtde retorno", 0))
                total = novo + retorno
                if "Qtde novo" in self._labels_valores:
                    self._labels_valores["Qtde novo"].setText(self._formatar_numero_exibicao(novo))
                if "Qtde retorno" in self._labels_valores:
                    self._labels_valores["Qtde retorno"].setText(self._formatar_numero_exibicao(retorno))
                if "Estoque total" in self._labels_valores:
                    self._labels_valores["Estoque total"].setText(self._formatar_numero_exibicao(total))

    def _limpar_detalhes(self):
        for lbl in self._labels_valores.values():
            lbl.setText("-")

    # -------------------------------------------------------------------------
    # FILTRO E PESQUISA
    # -------------------------------------------------------------------------
    def _on_filtro_text_changed(self, texto):
        self._filtro_timer.start()

    def _on_filtro_timeout(self):
        self._popular_tabela()

    def _limpar_filtro(self):
        try:
            self._filtro_timer.stop()
        except Exception:
            pass
        self.modo_pendentes = False
        self.modo_agrupado = False
        self._ordem_saldo_asc = True
        self._filtro_apenas_pendentes = False
        self.btn_toggle.setChecked(False)
        self.btn_toggle.setText("⚡  SAs Pendentes")
        self.btn_toggle.setToolTip("Alternar para tabela de SAs Pendentes (9 colunas)")
        self.btn_agrupar.setVisible(False)
        self.btn_agrupar.setChecked(False)
        self.btn_agrupar.setText(" Agrupar por item")
        self.btn_agrupar.setIcon(qta.icon("fa6s.layer-group", color="#4338ca"))
        self.btn_agrupar.setToolTip("Agrupar linhas por Kardex somando as quantidades pendentes")
        self.campo_filtro.clear()
        self.campo_filtro.setFocus()
        self._popular_tabela()

    def _copiar_selecao(self):
        itens_selecionados = self.tabela.selectedItems()
        if not itens_selecionados:
            return
        texto = "\t".join(it.text() for it in itens_selecionados)
        QGuiApplication.clipboard().setText(texto)

    # -------------------------------------------------------------------------
    # IMPORTAÇÃO AUTOMÁTICA DE ARQUIVO EXCEL (RELATÓRIO SAS PENDENTES)
    # -------------------------------------------------------------------------
    def _normalizar_str(self, texto):
        texto = unicodedata.normalize("NFKD", str(texto))
        texto = "".join(c for c in texto if not unicodedata.combining(c))
        return re.sub(r"[^a-zA-Z0-9]", "", texto).lower()

    def _localizar_arquivo_relatorio(self, pasta_docs):
        if not pasta_docs or not os.path.isdir(pasta_docs):
            return None

        arquivos_xlsx = []
        try:
            for f in os.listdir(pasta_docs):
                if f.lower().endswith((".xlsx", ".xls")) and not f.startswith("~$"):
                    caminho_completo = os.path.join(pasta_docs, f)
                    if os.path.isfile(caminho_completo):
                        try:
                            mtime = os.path.getmtime(caminho_completo)
                            arquivos_xlsx.append((caminho_completo, mtime, f))
                        except OSError:
                            pass
        except Exception:
            pass

        if not arquivos_xlsx:
            return None

        # 1. Filtra primeiro por arquivos com "Relatório SAs pendentes" no nome
        arquivos_especificos = []
        for caminho, mtime, nome in arquivos_xlsx:
            norm = self._normalizar_str(nome)
            if "relatorio" in norm and "pendente" in norm:
                arquivos_especificos.append((caminho, mtime, nome))
            elif "sa" in norm and "pendente" in norm:
                arquivos_especificos.append((caminho, mtime, nome))

        if arquivos_especificos:
            # Pega o mais recente dentre os que batem com o nome
            arquivos_especificos.sort(key=lambda x: x[1], reverse=True)
            return arquivos_especificos[0][0]

        # 2. Se nenhum arquivo tiver nome correspondente, pega o .xlsx mais recente da pasta
        arquivos_xlsx.sort(key=lambda x: x[1], reverse=True)
        return arquivos_xlsx[0][0]

    def _inserir_dados(self):
        pasta_docs = obter_pasta_documentos()
        arquivo_alvo = self._localizar_arquivo_relatorio(pasta_docs)

        if not arquivo_alvo:
            resposta = QMessageBox.question(
                self,
                "Arquivo não encontrado",
                f"Nenhum arquivo .xlsx foi encontrado automaticamente na pasta Documentos:\n"
                f"{pasta_docs}\n\n"
                "Deseja selecionar o arquivo de relatório manualmente?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            if resposta == QMessageBox.StandardButton.Yes:
                arquivo_alvo, _ = QFileDialog.getOpenFileName(
                    self,
                    "Selecionar Relatório SAs pendentes",
                    pasta_docs,
                    "Arquivos Excel (*.xlsx *.xls)"
                )
            if not arquivo_alvo:
                return

        try:
            excel_file = pd.ExcelFile(arquivo_alvo)
            sheet_names = excel_file.sheet_names

            aba_alvo = None
            for s in sheet_names:
                norm_s = self._normalizar_str(s)
                if "relatorio" in norm_s and "pendente" in norm_s:
                    aba_alvo = s
                    break
                elif "sa" in norm_s and "pendente" in norm_s:
                    aba_alvo = s
                    break

            if not aba_alvo:
                aba_alvo = sheet_names[0]

            df_bruto = pd.read_excel(excel_file, sheet_name=aba_alvo, header=None, dtype=str)
        except Exception as e:
            QMessageBox.critical(
                self,
                "Erro ao abrir arquivo",
                f"Falha ao ler a planilha Excel:\n{arquivo_alvo}\n\nErro: {str(e)}"
            )
            return

        if df_bruto.empty:
            QMessageBox.warning(self, "Aviso", f"A planilha '{aba_alvo}' está vazia.")
            return

        # Localiza linha do cabeçalho
        linha_cabecalho = 0
        mapa_colunas = {}
        colunas_numeracao_excel = {"", "#", "item", "seq", "sequencia", "no", "n", "num", "numero", "linha", "row", "id", "ordem"}

        for r in range(min(15, len(df_bruto))):
            linha_valores = [str(v) if pd.notna(v) else "" for v in df_bruto.iloc[r]]
            mapa_temp = {}
            for idx_col, val in enumerate(linha_valores):
                norm = self._normalizar_str(val)
                # Ignora colunas que representem numeração/índice do Excel
                if norm in colunas_numeracao_excel:
                    continue
                if norm in self.MAPA_NORMALIZACAO_COLUNAS:
                    chave_oficial = self.MAPA_NORMALIZACAO_COLUNAS[norm]
                    mapa_temp[chave_oficial] = idx_col
            if len(mapa_temp) >= 3:
                linha_cabecalho = r
                mapa_colunas = mapa_temp
                break

        df_dados = df_bruto.iloc[linha_cabecalho + 1:] if mapa_colunas else df_bruto

        # Verifica se a primeira coluna é apenas a numeração do Excel (1, 2, 3...)
        offset_posicional = 0
        if not mapa_colunas:
            if len(df_dados) > 0 and len(df_dados.columns) > len(self.COLUNAS):
                offset_posicional = 1
            elif len(df_dados) >= 2:
                valores_col0 = [str(df_dados.iloc[i, 0]).strip() for i in range(min(5, len(df_dados)))]
                if all(v.isdigit() for v in valores_col0) and valores_col0 == [str(i) for i in range(1, len(valores_col0) + 1)]:
                    offset_posicional = 1
        elif "SA" in mapa_colunas and mapa_colunas["SA"] == 0:
            valores_col0 = [str(df_dados.iloc[i, 0]).strip() for i in range(min(5, len(df_dados)))]
            if len(valores_col0) >= 2 and all(v.isdigit() for v in valores_col0) and valores_col0 == [str(i) for i in range(1, len(valores_col0) + 1)]:
                mapa_colunas["SA"] = 1

        nome_arquivo = os.path.basename(arquivo_alvo)
        resposta = QMessageBox.question(
            self,
            "Confirmar Importação",
            f"Arquivo localizado:\n{nome_arquivo}\n\n"
            f"Aba: '{aba_alvo}'\n"
            f"Linhas para importar: {len(df_dados)}\n\n"
            "Deseja atualizar a tabela da Análise de Estoque com estas informações?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )
        if resposta != QMessageBox.StandardButton.Yes:
            return

        def _limpar_valor(val):
            if val is None or pd.isna(val):
                return ""
            v_str = str(val).strip()
            if v_str.lower() in ("nan", "none", "null"):
                return ""
            if v_str.endswith(".0"):
                p_int = v_str[:-2]
                if p_int.replace("-", "").isdigit():
                    return p_int
            return v_str

        novos_dados = []
        for r_idx in range(len(df_dados)):
            linha_series = df_dados.iloc[r_idx]
            item = {}

            if mapa_colunas:
                for chave in self.COLUNAS:
                    idx_col = mapa_colunas.get(chave)
                    if idx_col is not None and idx_col < len(linha_series):
                        item[chave] = _limpar_valor(linha_series.iloc[idx_col])
                    else:
                        item[chave] = ""
                for col_extra in ("Qtde estoque", "Qte programado", "Saldo"):
                    idx_extra = mapa_colunas.get(col_extra)
                    if idx_extra is not None and idx_extra < len(linha_series):
                        item[col_extra] = _limpar_valor(linha_series.iloc[idx_extra])
            else:
                for idx_col, chave in enumerate(self.COLUNAS):
                    orig_col = idx_col + offset_posicional
                    if orig_col < len(linha_series):
                        item[chave] = _limpar_valor(linha_series.iloc[orig_col])
                    else:
                        item[chave] = ""

            if any(item.values()):
                novos_dados.append(item)

        self.dados = self._corrigir_dados_deslocados(novos_dados)
        self._salvar_json()
        self._rebuild_cache_filtro()
        self._popular_tabela()

        QMessageBox.information(
            self,
            "Sucesso",
            f"Análise de Estoque atualizada com sucesso!\n\n"
            f"Arquivo: {nome_arquivo}\n"
            f"Aba: {aba_alvo}\n"
            f"Total de itens importados: {len(novos_dados)}"
        )

    # -------------------------------------------------------------------------
    # PERSISTÊNCIA E EXPORTAÇÃO
    # -------------------------------------------------------------------------
    def _salvar_json(self):
        caminho = _caminho_json()
        if not caminho:
            config.avisar_sem_pasta(self)
            return

        try:
            os.makedirs(os.path.dirname(caminho), exist_ok=True)
            with open(caminho, "w", encoding="utf-8") as f:
                json.dump(self.dados, f, ensure_ascii=False, indent=2)
        except Exception as e:
            QMessageBox.critical(self, "Erro ao salvar", f"Não foi possível salvar os dados:\n{str(e)}")

    def _exportar_excel(self):
        if not self.dados:
            QMessageBox.warning(self, "Aviso", "Não existem dados para exportar.")
            return

        sufixo = "_sas_pendentes" if self.modo_pendentes else "_relatorio"
        arquivo, _ = QFileDialog.getSaveFileName(
            self,
            "Salvar Análise de Estoque",
            f"analise_estoque{sufixo}.xlsx",
            "Arquivos Excel (*.xlsx)"
        )
        if not arquivo:
            return

        try:
            colunas_atuais = self.COLUNAS_PENDENTES if self.modo_pendentes else self.COLUNAS
            dados_exportacao = []
            for row in range(self.tabela.rowCount()):
                linha = {}
                for col in range(self.tabela.columnCount()):
                    if self.tabela.isColumnHidden(col):
                        continue
                    header_item = self.tabela.horizontalHeaderItem(col)
                    cabecalho = colunas_atuais[col] if col < len(colunas_atuais) else (header_item.text() if header_item else f"Col {col}")
                    item = self.tabela.item(row, col)
                    linha[cabecalho] = item.text() if item else ""
                dados_exportacao.append(linha)

            df = pd.DataFrame(dados_exportacao)
            df.to_excel(arquivo, index=False, engine="openpyxl")

            QMessageBox.information(
                self,
                "Sucesso",
                f"Arquivo exportado com sucesso:\n{arquivo}"
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Erro",
                f"Falha ao exportar:\n{str(e)}"
            )

