import json
import os

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QListWidget, QListWidgetItem, QAbstractItemView, QMessageBox,
)
from PySide6.QtCore import Qt, QSize, QMimeData
from PySide6.QtGui import QDrag


def _caminho_json():
    import config
    base = config.obter_caminho_jsons()
    if not base:
        return ""
    return os.path.normpath(os.path.join(base, "Almox", "ReajusteDeCusto", "reajuste.json"))


class ColunaKanban(QListWidget):
    _arrastando = None

    def __init__(self, indice, callback, parent=None):
        super().__init__(parent)
        self.indice = indice
        self._callback = callback
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setDropIndicatorShown(True)
        self.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

    def startDrag(self, actions):
        item = self.currentItem()
        if item is None:
            return
        ColunaKanban._arrastando = (self, item)
        mime = QMimeData()
        mime.setText("kanban")
        drag = QDrag(self)
        drag.setMimeData(mime)
        rect = self.visualItemRect(item)
        pixmap = self.viewport().grab(rect)
        if not pixmap.isNull():
            drag.setPixmap(pixmap)
            drag.setHotSpot(pixmap.rect().center())
        drag.exec(Qt.DropAction.MoveAction)
        ColunaKanban._arrastando = None

    def dragEnterEvent(self, event):
        event.acceptProposedAction()

    def dragMoveEvent(self, event):
        event.acceptProposedAction()

    def dropEvent(self, event):
        arrastando = ColunaKanban._arrastando
        if arrastando is None:
            event.ignore()
            return
        fonte, item = arrastando
        ColunaKanban._arrastando = None

        pos = event.position().toPoint()
        indice_alvo = self.indexAt(pos)
        alvo = indice_alvo.row() if indice_alvo.isValid() else -1

        if fonte is self:
            origem = self.row(item)
            self.takeItem(origem)
            if alvo < 0:
                alvo = self.count()
            elif alvo > origem:
                alvo -= 1
            self.insertItem(alvo, item)
        else:
            fonte.takeItem(fonte.row(item))
            if alvo < 0:
                self.addItem(item)
            else:
                self.insertItem(alvo, item)
            item.setSelected(True)
            self.setCurrentItem(item)

        event.acceptProposedAction()
        self._callback()


class ReajustePrecosPage(QWidget):
    COLUNAS = ["Pedido de reajuste", "Em processo", "Reajuste finalizado"]

    def __init__(self):
        super().__init__()
        self.dados = []
        self.colunas = []
        self._setup_ui()
        self._carregar_dados()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(16)

        card = QWidget()
        card.setObjectName("pageCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(28, 28, 28, 28)
        card_layout.setSpacing(16)

        titulo = QLabel("Reajuste de Preços")
        titulo.setObjectName("pageTitle")
        card_layout.addWidget(titulo)

        subtitulo = QLabel("Registre reajustes e acompanhe o status em cada etapa")
        subtitulo.setObjectName("pageSubtitle")
        card_layout.addWidget(subtitulo)

        linha_form = QHBoxLayout()
        linha_form.setSpacing(12)

        self.campo_item = QLineEdit()
        self.campo_item.setPlaceholderText("Item")
        self.campo_item.setFixedHeight(44)
        self.campo_item.returnPressed.connect(self._inserir)
        linha_form.addWidget(self.campo_item, 3)

        self.campo_valor_antigo = QLineEdit()
        self.campo_valor_antigo.setPlaceholderText("Valor antigo")
        self.campo_valor_antigo.setFixedHeight(44)
        self.campo_valor_antigo.returnPressed.connect(self._inserir)
        linha_form.addWidget(self.campo_valor_antigo, 1)

        self.campo_valor_novo = QLineEdit()
        self.campo_valor_novo.setPlaceholderText("Valor novo")
        self.campo_valor_novo.setFixedHeight(44)
        self.campo_valor_novo.returnPressed.connect(self._inserir)
        linha_form.addWidget(self.campo_valor_novo, 1)

        self.btn_inserir = QPushButton("Inserir")
        self.btn_inserir.setObjectName("btnPrimary")
        self.btn_inserir.setFixedHeight(44)
        self.btn_inserir.setFixedWidth(120)
        self.btn_inserir.setDefault(True)
        self.btn_inserir.clicked.connect(self._inserir)
        linha_form.addWidget(self.btn_inserir)

        card_layout.addLayout(linha_form)

        kanban_layout = QHBoxLayout()
        kanban_layout.setSpacing(16)

        cores_fundo = ["#dbeafe", "#fef9c3", "#dcfce7"]

        for i, nome in enumerate(self.COLUNAS):
            col_card = QWidget()
            col_card.setStyleSheet(f"""
                QWidget {{
                    background: {cores_fundo[i]};
                    border: 1px solid #eef1f6;
                    border-radius: 14px;
                }}
            """)
            col_layout = QVBoxLayout(col_card)
            col_layout.setContentsMargins(12, 12, 12, 12)
            col_layout.setSpacing(10)

            header = QLabel(nome)
            header.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            header.setStyleSheet("""
                QLabel {
                    color: #1e1b4b;
                    font-family: 'Segoe UI', 'Arial', sans-serif;
                    font-size: 15px;
                    font-weight: 700;
                    letter-spacing: 1px;
                }
            """)
            col_layout.addWidget(header)

            lista = ColunaKanban(i, self._apos_movimento)
            lista.setStyleSheet("""
                QListWidget {
                    background: transparent;
                    border: none;
                    outline: none;
                }

                QListWidget::item {
                    background: #ffffff;
                    color: #374151;
                    border: 1px solid #e5e7eb;
                    border-radius: 10px;
                    padding: 8px 12px;
                    margin: 4px 2px;
                }

                QListWidget::item:hover {
                    border-color: #c7d2fe;
                }

                QListWidget::item:selected {
                    background: #eef2ff;
                    border-color: #6366f1;
                    color: #1e1b4b;
                }
            """)
            col_layout.addWidget(lista, 1)
            self.colunas.append(lista)

            kanban_layout.addWidget(col_card, 1)

        card_layout.addLayout(kanban_layout, 1)

        layout.addWidget(card)

    def _carregar_dados(self):
        try:
            with open(_caminho_json(), "r", encoding="utf-8") as f:
                self.dados = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.dados = []
        self._popular_kanban()

    def _popular_kanban(self):
        for col in self.colunas:
            col.clear()
        for dado in self.dados:
            status = dado.get("status", self.COLUNAS[0])
            col_idx = self.COLUNAS.index(status) if status in self.COLUNAS else 0
            item = self._criar_item(dado)
            self.colunas[col_idx].addItem(item)

    def _criar_item(self, dado):
        item = QListWidgetItem(self._formatar(dado))
        item.setData(Qt.ItemDataRole.UserRole, dado)
        item.setSizeHint(QSize(0, 48))
        return item

    def _formatar(self, dado):
        nome = dado.get("item", "")
        va = dado.get("valorAntigo", "")
        vn = dado.get("valorNovo", "")
        if va or vn:
            return f"{nome}\n{va} → {vn}"
        return nome

    def _inserir(self):
        nome = self.campo_item.text().strip()
        if not nome:
            QMessageBox.warning(self, "Aviso", "Informe o item.")
            self.campo_item.setFocus()
            return
        dados = self._coletar_dados()
        proximo_id = max([d.get("id", 0) for d in dados], default=0) + 1
        dado = {
            "id": proximo_id,
            "item": nome,
            "valorAntigo": self.campo_valor_antigo.text().strip(),
            "valorNovo": self.campo_valor_novo.text().strip(),
            "status": self.COLUNAS[0],
        }
        self.colunas[0].addItem(self._criar_item(dado))
        self.campo_item.clear()
        self.campo_valor_antigo.clear()
        self.campo_valor_novo.clear()
        self.campo_item.setFocus()
        self._apos_movimento()

    def _apos_movimento(self):
        self._salvar()

    def _coletar_dados(self):
        dados = []
        for col in self.colunas:
            for i in range(col.count()):
                item = col.item(i)
                dado = item.data(Qt.ItemDataRole.UserRole)
                dado["status"] = self.COLUNAS[col.indice]
                dados.append(dado)
        return dados

    def _salvar(self):
        dados = self._coletar_dados()
        caminho = _caminho_json()
        if not caminho:
            import config
            config.avisar_sem_pasta(self)
            return
        try:
            os.makedirs(os.path.dirname(caminho), exist_ok=True)
            with open(caminho, "w", encoding="utf-8") as f:
                json.dump(dados, f, ensure_ascii=False, indent=2)
        except OSError:
            pass
