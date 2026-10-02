import json
import os

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QListWidget, QListWidgetItem, QAbstractItemView, QMessageBox,
    QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, QSize, QMimeData
from PySide6.QtGui import QDrag, QColor


def _caminho_json():
    import config
    base = config.obter_caminho_jsons()
    if not base:
        return ""
    return os.path.normpath(os.path.join(base, "Almox", "ReajusteDeCusto", "reajuste.json"))


class ItemReajusteWidget(QWidget):
    def __init__(self, dado, parent=None):
        super().__init__(parent)
        self.setStyleSheet("QWidget { background: transparent; }")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(6)
        
        nome = dado.get("item", "")
        va = dado.get("valorAntigo", "")
        vn = dado.get("valorNovo", "")
        
        lbl_nome = QLabel(nome)
        lbl_nome.setStyleSheet("font-weight: 700; font-size: 14px; color: #1e293b; background: transparent;")
        lbl_nome.setWordWrap(True)
        layout.addWidget(lbl_nome)
        
        if va or vn:
            row = QHBoxLayout()
            row.setContentsMargins(0, 4, 0, 0)
            
            lbl_va = QLabel(f"R$ {va}")
            lbl_va.setStyleSheet("color: #94a3b8; font-size: 13px; text-decoration: line-through; background: transparent;")
            
            lbl_seta = QLabel(" ➔ ")
            lbl_seta.setStyleSheet("color: #cbd5e1; font-size: 12px; font-weight: 800; background: transparent;")
            
            lbl_vn = QLabel(f"R$ {vn}")
            lbl_vn.setStyleSheet("color: #10b981; font-size: 14px; font-weight: 800; background: transparent;")
            
            row.addWidget(lbl_va)
            row.addWidget(lbl_seta)
            row.addWidget(lbl_vn)
            row.addStretch()
            layout.addLayout(row)


class ColunaKanban(QListWidget):
    _arrastando = None

    def __init__(self, indice, callback, factory_widget, parent=None):
        super().__init__(parent)
        self._factory_widget = factory_widget
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
            dado = item.data(Qt.ItemDataRole.UserRole)
            if dado:
                self.setItemWidget(item, self._factory_widget(dado))
        else:
            fonte.takeItem(fonte.row(item))
            if alvo < 0:
                self.addItem(item)
            else:
                self.insertItem(alvo, item)
            item.setSelected(True)
            self.setCurrentItem(item)
            dado = item.data(Qt.ItemDataRole.UserRole)
            if dado:
                self.setItemWidget(item, self._factory_widget(dado))

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

    def showEvent(self, event):
        super().showEvent(event)
        self._carregar_dados()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 12)
        layout.setSpacing(16)

        titulo = QLabel("Reajuste de Preços")
        titulo.setStyleSheet("font-size: 16px; font-weight: 700; color: #1e293b;")
        
        linha_cabecalho = QHBoxLayout()
        linha_cabecalho.setContentsMargins(4, 0, 4, 0)
        linha_cabecalho.addWidget(titulo)
        linha_cabecalho.addStretch()
        
        layout.addLayout(linha_cabecalho)



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

        layout.addLayout(linha_form)

        kanban_layout = QHBoxLayout()
        kanban_layout.setSpacing(16)

        cores_fundo = ["#eff6ff", "#fefce8", "#f0fdf4"]
        cores_borda = ["#3b82f6", "#eab308", "#22c55e"]
        icones = ["📋", "⏳", "✅"]

        for i, nome in enumerate(self.COLUNAS):
            col_card = QWidget()
            col_card.setObjectName(f"kanbanCol_{i}")
            col_card.setStyleSheet(f"""
                QWidget#kanbanCol_{i} {{
                    background: {cores_fundo[i]};
                    border: 1px solid #e2e8f0;
                    border-top: 4px solid {cores_borda[i]};
                    border-radius: 12px;
                }}
            """)
            shadow = QGraphicsDropShadowEffect(col_card)
            shadow.setBlurRadius(16)
            shadow.setXOffset(0)
            shadow.setYOffset(4)
            shadow.setColor(QColor(0, 0, 0, 20))
            col_card.setGraphicsEffect(shadow)
            
            col_layout = QVBoxLayout(col_card)
            col_layout.setContentsMargins(16, 16, 16, 16)
            col_layout.setSpacing(12)

            header = QLabel(f"{icones[i]}  {nome}")
            header.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            header.setStyleSheet("""
                QLabel {
                    color: #0f172a;
                    font-family: 'Segoe UI', 'Arial', sans-serif;
                    font-size: 15px;
                    font-weight: 800;
                    border: none;
                    background: transparent;
                }
            """)
            col_layout.addWidget(header)

            lista = ColunaKanban(i, self._apos_movimento, self._criar_widget_item)
            lista.setStyleSheet("""
                QListWidget {
                    background: transparent;
                    border: none;
                    outline: none;
                }

                QListWidget::item {
                    background: #ffffff;
                    border: 1px solid #cbd5e1;
                    border-radius: 8px;
                    margin: 4px 0px;
                }

                QListWidget::item:hover {
                    border-color: #94a3b8;
                    background: #f8fafc;
                }

                QListWidget::item:selected {
                    background: #ffffff;
                    border: 2px solid #6366f1;
                }
            """)
            col_layout.addWidget(lista, 1)
            self.colunas.append(lista)

            kanban_layout.addWidget(col_card, 1)

        layout.addLayout(kanban_layout, 1)

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
            self.colunas[col_idx].setItemWidget(item, self._criar_widget_item(dado))

    def _criar_item(self, dado):
        item = QListWidgetItem()
        item.setData(Qt.ItemDataRole.UserRole, dado)
        # Altura do widget costuma dar ~84px com duas linhas
        item.setSizeHint(QSize(0, 84))
        return item

    def _criar_widget_item(self, dado):
        return ItemReajusteWidget(dado)

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
        item_novo = self._criar_item(dado)
        self.colunas[0].addItem(item_novo)
        self.colunas[0].setItemWidget(item_novo, self._criar_widget_item(dado))
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
