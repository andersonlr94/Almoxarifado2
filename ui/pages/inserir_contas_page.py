import os
import json
from datetime import datetime
import qtawesome
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QFrame, QAbstractItemView
)
from PySide6.QtCore import Qt

class InserirContasPage(QWidget):
    COLUNAS = [
        "Req origem/projeto",
        "Requisição",
        "Emissão",
        "Solicitante",
        "Custo total",
        "Entidade",
        "Conta",
    ]

    def __init__(self):
        super().__init__()
        self._setup_ui()
        self._carregar_dados()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        card = QWidget()
        card.setObjectName("pageCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 16, 18, 16)
        card_layout.setSpacing(12)

        # ── Filtros (Topo) ──
        filtro_container = QWidget()
        filtro_container.setObjectName("filtroContainer")
        filtro_layout = QHBoxLayout(filtro_container)
        filtro_layout.setContentsMargins(0, 0, 0, 0)
        filtro_layout.setSpacing(8)

        # Campo Requisição
        lbl_req = QLabel("Requisição")
        lbl_req.setStyleSheet("color:#1e293b; font-size:12px; font-weight:700;")
        filtro_layout.addWidget(lbl_req)

        self.campo_requisicao = QLineEdit()
        self.campo_requisicao.setPlaceholderText("Digite a requisição...")
        self.campo_requisicao.setFixedHeight(30)
        self.campo_requisicao.setFixedWidth(220)
        self.campo_requisicao.setStyleSheet("background:#ffffff; border:1px solid #e2e8f0; border-radius:8px; padding:4px 8px; font-size:12px;")
        filtro_layout.addWidget(self.campo_requisicao)

        # Botão Buscar
        self.btn_buscar = QPushButton(qtawesome.icon('fa6s.magnifying-glass', color='#ffffff'), "  Buscar")
        self.btn_buscar.setObjectName("btnPrimary")
        self.btn_buscar.setFixedHeight(30)
        self.btn_buscar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_buscar.clicked.connect(self._carregar_dados)
        filtro_layout.addWidget(self.btn_buscar)

        filtro_layout.addStretch()
        card_layout.addWidget(filtro_container)

        # ── Tabela ──
        self.tabela = QTableWidget()
        self.tabela.setColumnCount(len(self.COLUNAS))
        self.tabela.setHorizontalHeaderLabels(self.COLUNAS)
        self.tabela.setObjectName("tabelaSa")
        self.tabela.setStyleSheet("""
            QTableWidget {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                gridline-color: #f1f5f9;
                font-size: 11px;
                color: #334155;
            }
            QTableWidget::item {
                padding: 4px;
                border-bottom: 1px solid #f1f5f9;
            }
            QTableWidget::item:selected {
                background-color: #e0f2fe;
                color: #0f172a;
            }
        """)

        header = self.tabela.horizontalHeader()
        header.setStretchLastSection(True)
        header.setStyleSheet(
            "QHeaderView::section {"
            "  font-size: 10px; font-weight: 700;"
            "  background-color: #f8fafc; color: #64748b;"
            "  text-transform: uppercase; letter-spacing: 0.3px;"
            "  padding: 4px; border: none; border-bottom: 2px solid #e2e8f0;"
            "}"
        )
        
        self.tabela.setAlternatingRowColors(True)
        self.tabela.verticalHeader().setVisible(False)
        self.tabela.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabela.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tabela.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        # Configurar larguras específicas
        self.tabela.setColumnWidth(0, 200) # Coluna 1 (Req origem/projeto)
        self.tabela.setColumnWidth(3, 200) # Coluna 4 (Solicitante)

        # Container para limitar largura da tabela a 70%
        table_layout = QHBoxLayout()
        table_layout.setContentsMargins(0, 0, 0, 0)
        table_layout.addWidget(self.tabela, 7) # 70% do espaço
        table_layout.addStretch(3)             # 30% vazio

        card_layout.addLayout(table_layout, 1)
        layout.addWidget(card)

    def showEvent(self, event):
        super().showEvent(event)
        self._carregar_dados()

    def _carregar_dados(self):
        self.tabela.setRowCount(0)
        try:
            import config
            base = config.obter_caminho_jsons()
            pasta = os.path.normpath(os.path.join(base, "Almox", "SA")) if base else ""
        except Exception:
            pasta = os.path.normpath(os.path.join(os.getcwd(), "Almox", "SA"))

        if not pasta or not os.path.isdir(pasta):
            return

        sas_pendentes = []
        for nome_arquivo in os.listdir(pasta):
            if not nome_arquivo.lower().endswith(".json"):
                continue
            caminho = os.path.join(pasta, nome_arquivo)
            try:
                with open(caminho, "r", encoding="utf-8") as f:
                    dados = json.load(f)
                    
                    # Filtra: Projeto = "Despesas" e Conta = "email"
                    proj = str(dados.get("projeto_debito", "")).strip().lower()
                    conta = str(dados.get("conta_debito", "")).strip().lower()
                    
                    if proj == "despesas" and conta == "email":
                        # Se o usuário digitou algo na busca, filtra também pela requisição
                        filtro_req = self.campo_requisicao.text().strip().lower()
                        num_sa = str(dados.get("numero_sa", "")).strip().lower()
                        
                        if filtro_req and filtro_req not in num_sa and filtro_req not in f"sa {num_sa}":
                            continue

                        # Salva o caminho para poder ler data de criação se necessário
                        dados["_caminho_arquivo"] = caminho
                        sas_pendentes.append(dados)
            except Exception:
                continue

        for sa in sas_pendentes:
            row = self.tabela.rowCount()
            self.tabela.insertRow(row)

            # Coluna 0: Req origem/projeto (vazio)
            item_req_origem = QTableWidgetItem("")
            
            # Coluna 1: Requisição (SA)
            num_sa = "SA " + str(sa.get("numero_sa", ""))
            item_req = QTableWidgetItem(num_sa)
            item_req.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            
            # Coluna 2: Emissão (data da criação)
            emissao = sa.get("emissao", "")
            if not emissao:
                # Usa a data de modificação/criação do arquivo
                timestamp = os.path.getctime(sa["_caminho_arquivo"])
                emissao = datetime.fromtimestamp(timestamp).strftime("%d/%m/%Y")
            item_emissao = QTableWidgetItem(emissao)
            item_emissao.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            
            # Coluna 3: Solicitante
            solicitante = str(sa.get("nome_emissor", ""))
            item_solicitante = QTableWidgetItem(solicitante)

            # Coluna 4: Custo total da SA
            custo_total = 0.0
            for it in sa.get("itens", []):
                ct_str = str(it.get("custo_total", "0"))
                # Limpa o "R$" caso venha, e formata para float
                ct_str = ct_str.replace("R$", "").strip()
                ct_str = ct_str.replace(".", "").replace(",", ".") if "," in ct_str else ct_str
                try:
                    custo_total += float(ct_str)
                except Exception:
                    pass
            custo_str = f"R$ {custo_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            item_custo = QTableWidgetItem(custo_str)
            item_custo.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            # Coluna 5: Entidade (vazio)
            item_entidade = QTableWidgetItem("")

            # Coluna 6: Conta (conta para débito)
            item_conta = QTableWidgetItem(str(sa.get("conta_debito", "")))
            
            self.tabela.setItem(row, 0, item_req_origem)
            self.tabela.setItem(row, 1, item_req)
            self.tabela.setItem(row, 2, item_emissao)
            self.tabela.setItem(row, 3, item_solicitante)
            self.tabela.setItem(row, 4, item_custo)
            self.tabela.setItem(row, 5, item_entidade)
            self.tabela.setItem(row, 6, item_conta)

