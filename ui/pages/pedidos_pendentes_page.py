import json
import os

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QStyledItemDelegate, QMessageBox,
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QGuiApplication


class EditorDelegate(QStyledItemDelegate):
    def sizeHint(self, option, index):
        base = super().sizeHint(option, index)
        return QSize(base.width(), max(base.height(), 34))

    def createEditor(self, parent, option, index):
        editor = super().createEditor(parent, option, index)
        if isinstance(editor, QLineEdit):
            editor.setMinimumHeight(34)
            editor.setStyleSheet("padding: 4px 8px;")
        return editor


class PedidosPendentesPage(QWidget):
    COLUNAS = [
        "N do pedido", "Kardex", "Código", "Fornecedor",
        "Data prog", "Semana prog", "Qtde programada", "Data entrega",
        "N de AR", "Entrada", "Qtde entregue", "Qtde pendente",
        "Requisitante", "Destino", "Status", "Observação",
    ]

    def __init__(self):
        super().__init__()
        self.dados = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(16)

        card = QWidget()
        card.setObjectName("pageCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(28, 28, 28, 28)
        card_layout.setSpacing(16)

        titulo = QLabel("Pedidos Pendentes")
        titulo.setObjectName("pageTitle")
        card_layout.addWidget(titulo)

        linha_top = QHBoxLayout()
        linha_top.setSpacing(8)

        btn_atualizar = QPushButton("Atualizar")
        btn_atualizar.setObjectName("btnPrimary")
        btn_atualizar.setFixedHeight(34)
        btn_atualizar.clicked.connect(self._atualizar)
        linha_top.addWidget(btn_atualizar)

        self.campo_filtro = QLineEdit()
        self.campo_filtro.setPlaceholderText("Pesquisar...")
        self.campo_filtro.setFixedHeight(30)
        self.campo_filtro.setFixedWidth(200)
        self.campo_filtro.textChanged.connect(self._aplicar_filtro)
        linha_top.addWidget(self.campo_filtro)

        self.label_contador = QLabel("0 itens")
        self.label_contador.setObjectName("statusLabel")
        linha_top.addWidget(self.label_contador)

        linha_top.addStretch()
        card_layout.addLayout(linha_top)

        self.tabela = QTableWidget(0, len(self.COLUNAS))
        self.tabela.setHorizontalHeaderLabels(self.COLUNAS)
        header = self.tabela.horizontalHeader()
        header.setStyleSheet(
            "QHeaderView::section {"
            "  font-size: 9px;"
            "  font-weight: 600;"
            "  background-color: #f8fafc;"
            "  color: #64748b;"
            "  text-transform: uppercase;"
            "  letter-spacing: 0.5px;"
            "  padding: 8px 12px;"
            "  border: none;"
            "  border-bottom: 2px solid #e2e8f0;"
            "}"
        )
        header.setStretchLastSection(False)
        for c in range(self.tabela.columnCount()):
            header.setSectionResizeMode(c, QHeaderView.ResizeMode.Interactive)
            largura = 150 if c == 1 else 180 if c in (2, 3) else 100
            header.resizeSection(c, largura)
        self.tabela.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self.tabela.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked)
        self.tabela.setAlternatingRowColors(False)
        self.tabela.verticalHeader().setDefaultSectionSize(28)
        self.tabela.verticalHeader().setMinimumSectionSize(24)
        self.tabela.verticalHeader().setVisible(False)
        self.tabela.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.tabela.setItemDelegate(EditorDelegate(self.tabela))
        card_layout.addWidget(self.tabela)

        layout.addWidget(card)

    def _popular_tabela(self):
        self.tabela.blockSignals(True)
        self.tabela.setRowCount(0)
        filtro_texto = self.campo_filtro.text().strip().lower()
        for item in self.dados:
            if filtro_texto:
                texto = " ".join(str(v) for v in item.values()).lower()
                if filtro_texto not in texto:
                    continue
            row = self.tabela.rowCount()
            self.tabela.insertRow(row)
            for col, chave in enumerate(self.COLUNAS):
                valor = str(item.get(chave, ""))
                cell = QTableWidgetItem(valor)
                cell.setFlags(cell.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.tabela.setItem(row, col, cell)
        self.tabela.blockSignals(False)
        self.label_contador.setText(f"{self.tabela.rowCount()} itens")

    def _atualizar(self):
        clipboard = QGuiApplication.clipboard()
        texto = clipboard.text()
        if not texto.strip():
            QMessageBox.warning(self, "Aviso", "A área de transferência está vazia.")
            return

        linhas = [l.strip() for l in texto.replace("\r\n", "\n").split("\n") if l.strip()]
        if not linhas:
            return

        header, dados_linha = self._separar_cabecalho(linhas)
        if not dados_linha:
            QMessageBox.warning(self, "Aviso", "Não há dados válidos para atualizar.")
            return

        colunas = len(dados_linha[0].split("\t"))

        if colunas != len(self.COLUNAS):
            QMessageBox.warning(
                self,
                "Formato inválido",
                f"A tabela copiada deve ter {len(self.COLUNAS)} colunas."
            )
            return

        self.dados.clear()
        for linha in dados_linha:
            partes = linha.split("\t")
            if len(partes) < 2:
                continue
            item = {}
            for col, chave in enumerate(self.COLUNAS):
                item[chave] = partes[col].strip() if col < len(partes) else ""
            self.dados.append(item)

        self._popular_tabela()

        QMessageBox.information(
            self,
            "Sucesso",
            "Pedidos atualizados com sucesso!"
        )

    def _separar_cabecalho(self, linhas):
        if not linhas:
            return None, []

        primeiras_partes = linhas[0].split("\t")
        if self._eh_linha_cabecalho(primeiras_partes):
            return [p.strip() for p in primeiras_partes], linhas[1:]

        return None, linhas

    def _normalizar_coluna(self, texto):
        texto = texto.strip().lower()
        for original, substituicao in {
            "á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u",
            "ã": "a", "õ": "o", "â": "a", "ê": "e", "ô": "o",
            "ç": "c",
        }.items():
            texto = texto.replace(original, substituicao)
        return "".join(ch for ch in texto if ch.isalnum())

    def _eh_linha_cabecalho(self, partes):
        if not partes:
            return False
        nome_normalizado = self._normalizar_coluna(partes[0])
        return nome_normalizado in {"npedido", "ndopedido", "pedido", "kardex", "codigo", "fornecedor"}

    def _aplicar_filtro(self):
        self._popular_tabela()
