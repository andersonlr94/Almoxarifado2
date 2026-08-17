import json
import os
from datetime import datetime

from PySide6.QtCore import Qt, QTimer, QMimeData, QPropertyAnimation, QEasingCurve, Property
from PySide6.QtGui import QDrag, QColor
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QScrollArea, QFrame, QGridLayout, QInputDialog, QMessageBox, QDialog,
    QGraphicsDropShadowEffect, QListWidget, QListWidgetItem,
)


def _caminho_json():
    import config
    base = config.obter_caminho_jsons()
    if not base:
        return ""
    pasta = os.path.normpath(os.path.join(base, "Almox", "MaterialHolders"))
    os.makedirs(pasta, exist_ok=True)
    return os.path.join(pasta, "MaterialHolders.json")


def _todas_locations():
    locs = []
    for i in range(101, 119):
        locs.append(f"F{i}")
    for i in range(201, 219):
        locs.append(f"F{i}")
    return locs


def _garantir_todas_locations(dados):
    existentes = {(d.get("localizacao"), d.get("slot")) for d in dados}
    for loc in _todas_locations():
        for slot in ("A", "B", "C", "D"):
            if (loc, slot) not in existentes:
                dados.append({
                    "localizacao": loc, "slot": slot, "sa": "", "data": "",
                    "grupo": f"{loc}-{slot}",
                })
    for d in dados:
        d.setdefault("grupo", f"{d.get('localizacao', '')}-{d.get('slot', '')}")
    return dados


def _ler_dados():
    caminho = _caminho_json()
    dados = []
    if caminho and os.path.exists(caminho):
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                dados = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            dados = []
    dados = _garantir_todas_locations(dados)
    _salvar_dados(dados)
    return dados


def _salvar_dados(dados):
    caminho = _caminho_json()
    if not caminho:
        return
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)


ORDEM_SLOTS = {"A": 0, "B": 1, "C": 2, "D": 3}


class SlotButton(QPushButton):
    def __init__(self, texto, localizacao, slots, pagina):
        super().__init__(texto)
        self._localizacao = localizacao
        self._slots = tuple(slots)
        self._pagina = pagina
        self._inicio_arrasto = None
        self.setAcceptDrops(True)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._inicio_arrasto = e.position().toPoint()
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self._inicio_arrasto is not None:
            dist = (e.position().toPoint() - self._inicio_arrasto).manhattanLength()
            if dist >= QApplication.startDragDistance():
                drag = QDrag(self)
                mime = QMimeData()
                mime.setText(f"{self._localizacao}|{self._slots[0]}")
                drag.setMimeData(mime)
                self._inicio_arrasto = None
                drag.exec(Qt.DropAction.MoveAction)
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        self._inicio_arrasto = None
        super().mouseReleaseEvent(e)

    def dragEnterEvent(self, e):
        if e.mimeData().hasText():
            e.acceptProposedAction()

    def dropEvent(self, e):
        texto = e.mimeData().text()
        e.acceptProposedAction()
        if not texto or "|" not in texto:
            return
        origem_loc, origem_slot = texto.split("|", 1)
        idx = ORDEM_SLOTS[origem_slot]
        lo = min(ORDEM_SLOTS[s] for s in self._slots)
        hi = max(ORDEM_SLOTS[s] for s in self._slots)
        if idx < lo:
            alvo_slot = max(self._slots, key=lambda s: ORDEM_SLOTS[s])
        elif idx > hi:
            alvo_slot = min(self._slots, key=lambda s: ORDEM_SLOTS[s])
        else:
            return
        if self._pagina._agrupar_slots((origem_loc, origem_slot), (self._localizacao, alvo_slot)):
            if self._pagina._alocar_sa((self._localizacao, alvo_slot)):
                self._pagina._limpar_agrupamento_anterior()
            else:
                self._pagina._reverter_ultimo_agrupamento()


class PainelLateral(QWidget):
    LARGURA_MINIMA = 2

    def __init__(self, parent=None):
        super().__init__(parent)
        self._largura = self.LARGURA_MINIMA
        self._expandido = False
        self.setFixedWidth(self.LARGURA_MINIMA)
        self.setObjectName("painelLateral")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self._anim = QPropertyAnimation(self, b"largura", self)
        self._anim.setDuration(200)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutCubic)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 12, 0, 12)
        layout.setSpacing(10)

        self.titulo = QLabel("Resumo")
        self.titulo.setObjectName("pageSubtitle")
        self.titulo.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.titulo.setContentsMargins(0, 4, 0, 0)
        layout.addWidget(self.titulo)

        self._stat_widgets = {}
        for chave, nome in (
            ("alocadas", "Locações alocadas"),
            ("livres", "Locações livres"),
            ("grupos", "Grupos ativos"),
            ("ocupacao", "Ocupação"),
        ):
            linha = QHBoxLayout()
            linha.setContentsMargins(14, 0, 14, 0)
            nome_lb = QLabel(nome)
            nome_lb.setStyleSheet("font-size: 12px; color: #64748b; background: transparent; border: none;")
            val_lb = QLabel("—")
            val_lb.setAlignment(Qt.AlignmentFlag.AlignRight)
            val_lb.setStyleSheet("font-size: 14px; font-weight: 700; color: #4f46e5; background: transparent; border: none;")
            linha.addWidget(nome_lb)
            linha.addStretch()
            linha.addWidget(val_lb)
            layout.addLayout(linha)
            self._stat_widgets[chave] = val_lb

        self.titulo_lista = QLabel("Alocadas há +15 dias")
        self.titulo_lista.setObjectName("pageSubtitle")
        self.titulo_lista.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.titulo_lista.setContentsMargins(0, 10, 0, 0)
        layout.addWidget(self.titulo_lista)

        self.lista_antigas = QListWidget()
        self.lista_antigas.setFrameShape(QFrame.Shape.NoFrame)
        self.lista_antigas.setStyleSheet(
            "QListWidget { background: transparent; border: none; font-size: 12px; color: #334155; }"
            "QListWidget::item { padding: 5px 4px; border-bottom: 1px solid #f1f5f9; }"
        )
        layout.addWidget(self.lista_antigas, 1)

        layout.addStretch()

    def atualizar_resumo(self, alocadas, livres, grupos):
        total = alocadas + livres
        self._stat_widgets["alocadas"].setText(str(alocadas))
        self._stat_widgets["livres"].setText(str(livres))
        self._stat_widgets["grupos"].setText(str(grupos))
        self._stat_widgets["ocupacao"].setText(
            f"{round(alocadas / total * 100)}%" if total else "0%"
        )

    def atualizar_lista(self, dados):
        self.lista_antigas.clear()
        agora = datetime.now()
        por_grupo = {}
        for d in dados:
            grp = d.get("grupo") or ""
            sa = (d.get("sa") or "").strip()
            data = d.get("data") or ""
            if not sa or not data:
                continue
            info = por_grupo.setdefault(grp, {"sa": sa, "data": data, "loc": d.get("localizacao", ""), "slots": []})
            info["slots"].append(d.get("slot", ""))
        itens = []
        for grp, info in por_grupo.items():
            try:
                dt = datetime.strptime(info["data"], "%d/%m/%Y %H:%M:%S")
            except ValueError:
                continue
            dias = (agora - dt).days
            if dias > 15:
                slots = "".join(sorted(s for s in info["slots"] if s))
                itens.append(f"{info['loc']}-{slots} — {info['sa']} ({dias}d)")
        if not itens:
            item_vazio = QListWidgetItem("Nenhuma alocação antiga")
            item_vazio.setForeground(QColor("#94a3b8"))
            self.lista_antigas.addItem(item_vazio)
        else:
            for texto in itens:
                self.lista_antigas.addItem(QListWidgetItem(texto))

    def _obter_largura(self):
        return self._largura

    def _definir_largura(self, valor):
        self._largura = valor
        self.setFixedWidth(int(valor))

    largura = Property(int, _obter_largura, _definir_largura)

    def _alternar(self):
        if self._expandido:
            self._colapsar()
        else:
            self._expandir()

    def _expandir(self):
        alvo = int(self.parentWidget().width() * 0.30) if self.parentWidget() else 400
        self._anim.stop()
        self._anim.setStartValue(self._largura)
        self._anim.setEndValue(alvo)
        self._anim.start()
        self._expandido = True

    def _colapsar(self):
        self._anim.stop()
        self._anim.setStartValue(self._largura)
        self._anim.setEndValue(self.LARGURA_MINIMA)
        self._anim.start()
        self._expandido = False


class MaterialHoldersPage(QWidget):
    """Página de alocação/baixa de material para holders por localização (F101-F118, F201-F218)."""

    COLUNAS_LINHA = 6
    SLOTS = ("A", "B", "C", "D")

    def __init__(self):
        super().__init__()
        self._modo_alocacao = True
        self._modo_baixa = False
        self._cards = {}
        self._slot_botoes = {}
        self._layouts_slots = {}
        self._alocados = set()
        self._sa_por_chave = {}
        self._dados = []
        self._setup_ui()
        self._carregar_alocacoes()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        titulo = QLabel("Material para Holders")
        titulo.setObjectName("pageTitle")
        layout.addWidget(titulo)

        linha_modo = QHBoxLayout()
        linha_modo.setSpacing(8)

        self.btn_modo_alocacao = QPushButton("Modo alocação")
        self.btn_modo_alocacao.setObjectName("segmented")
        self.btn_modo_alocacao.setCheckable(True)
        self.btn_modo_alocacao.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_modo_alocacao.setFixedHeight(34)
        self.btn_modo_alocacao.setChecked(True)
        self.btn_modo_alocacao.clicked.connect(lambda: self._selecionar_modo("alocacao"))
        linha_modo.addWidget(self.btn_modo_alocacao)

        self.btn_modo_baixa = QPushButton("Modo baixa")
        self.btn_modo_baixa.setObjectName("segmented")
        self.btn_modo_baixa.setCheckable(True)
        self.btn_modo_baixa.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_modo_baixa.setFixedHeight(34)
        self.btn_modo_baixa.clicked.connect(lambda: self._selecionar_modo("baixa"))
        linha_modo.addWidget(self.btn_modo_baixa)

        self.campo_busca = QLineEdit()
        self.campo_busca.setPlaceholderText("Filtrar localização...")
        self.campo_busca.setFixedHeight(34)
        self.campo_busca.setFixedWidth(220)
        self.campo_busca.returnPressed.connect(self._aplicar_filtro)
        linha_modo.addWidget(self.campo_busca)

        btn_buscar = QPushButton("Buscar")
        btn_buscar.setObjectName("btnPrimary")
        btn_buscar.setFixedHeight(34)
        btn_buscar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_buscar.clicked.connect(self._aplicar_filtro)
        linha_modo.addWidget(btn_buscar)

        linha_modo.addStretch()

        self.btn_quadro = QPushButton("◀ Expandir quadro")
        self.btn_quadro.setObjectName("btnSecondary")
        self.btn_quadro.setFixedHeight(34)
        self.btn_quadro.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_quadro.clicked.connect(self._alternar_quadro)
        linha_modo.addWidget(self.btn_quadro)

        layout.addLayout(linha_modo)

        self._localizacoes = _todas_locations()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            "QScrollBar:vertical { background: transparent; width: 8px; margin: 0; }"
            "QScrollBar::handle:vertical { background: #cbd5e1; border-radius: 4px; min-height: 30px; }"
            "QScrollBar::handle:vertical:hover { background: #94a3b8; }"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }"
            "QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }"
        )

        container = QWidget()
        container.setObjectName("holderContainer")
        container.setStyleSheet("QWidget#holderContainer { background: transparent; }")
        grid = QGridLayout(container)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(12)

        for idx, loc in enumerate(self._localizacoes):
            card = self._criar_card(loc)
            self._cards[loc] = card
            grid.addWidget(card, idx // self.COLUNAS_LINHA, idx % self.COLUNAS_LINHA)

        for col in range(self.COLUNAS_LINHA):
            grid.setColumnStretch(col, 1)

        scroll.setWidget(container)

        corpo = QHBoxLayout()
        corpo.setSpacing(16)
        corpo.addWidget(scroll, 1)
        self.painel_lateral = PainelLateral()
        corpo.addWidget(self.painel_lateral, 0, Qt.AlignmentFlag.AlignTop)
        layout.addLayout(corpo, 1)

        self._rebuild_cards()

    def _criar_card(self, localizacao):
        card = QFrame()
        card.setObjectName("holderCard")
        card.setMinimumHeight(64)

        sombra = QGraphicsDropShadowEffect(card)
        sombra.setBlurRadius(14)
        sombra.setOffset(0, 2)
        sombra.setColor(QColor(15, 23, 42, 40))
        card.setGraphicsEffect(sombra)

        v = QVBoxLayout(card)
        v.setContentsMargins(8, 6, 8, 6)
        v.setSpacing(6)

        titulo = QLabel(localizacao)
        titulo.setObjectName("holderTitle")
        titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(titulo)

        linha_slots = QHBoxLayout()
        linha_slots.setSpacing(6)
        v.addLayout(linha_slots)
        self._layouts_slots[localizacao] = linha_slots

        return card

    def _limpar_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def _rebuild_cards(self):
        for loc in self._localizacoes:
            self._rebuild_card(loc)

    def _rebuild_card(self, localizacao):
        layout = self._layouts_slots[localizacao]
        self._limpar_layout(layout)
        self._slot_botoes = {
            k: v for k, v in self._slot_botoes.items() if k[0] != localizacao
        }

        grupos = []
        for slot in ("A", "B", "C", "D"):
            chave = (localizacao, slot)
            grp = self._grupo_de(chave)
            if grupos and grupos[-1][1] == grp:
                grupos[-1][0].append(slot)
            else:
                grupos.append(([slot], grp))

        for slots, _grp in grupos:
            texto = "".join(slots)
            btn = SlotButton(texto, localizacao, slots, self)
            btn.setObjectName("slotBtn")
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(28)
            btn.clicked.connect(
                lambda checked, b=btn, l=localizacao, sl=tuple(slots): self._on_slot_clicado(b, l, sl[0])
            )
            for s in slots:
                self._slot_botoes[(localizacao, s)] = btn
            layout.addWidget(btn, len(slots))

    def _carregar_alocacoes(self):
        self._dados = _ler_dados()
        self._rebuild_cards()
        self._atualizar_estado_slots()

    def _atualizar_estado_slots(self):
        self._alocados.clear()
        self._sa_por_chave.clear()
        for d in self._dados:
            chave = (d.get("localizacao"), d.get("slot"))
            if not all(chave):
                continue
            sa = d.get("sa", "")
            btn = self._slot_botoes.get(chave)
            if not btn:
                continue
            if sa:
                self._alocados.add(chave)
                self._sa_por_chave[chave] = sa
                btn.setChecked(True)
                btn.setToolTip(f"{chave[0]}-{chave[1]} — {sa}")
            else:
                btn.setChecked(False)
                btn.setToolTip("")
        self._atualizar_painel()

    def _atualizar_painel(self):
        total = len(self._dados)
        alocadas = len(self._alocados)
        grupos = len({
            d.get("grupo") for d in self._dados
            if (d.get("sa") or "").strip()
        })
        self.painel_lateral.atualizar_resumo(alocadas, total - alocadas, grupos)
        self.painel_lateral.atualizar_lista(self._dados)

    def _alternar_quadro(self):
        p = self.painel_lateral
        if p._expandido:
            p._colapsar()
            self.btn_quadro.setText("◀ Expandir quadro")
        else:
            p._expandir()
            self.btn_quadro.setText("▶ Recolher quadro")

    def _grupo_de(self, chave):
        for d in self._dados:
            if d.get("localizacao") == chave[0] and d.get("slot") == chave[1]:
                return d.get("grupo") or f"{chave[0]}-{chave[1]}"
        return f"{chave[0]}-{chave[1]}"

    def _membros_do_grupo(self, chave):
        grp = self._grupo_de(chave)
        return [
            (d.get("localizacao"), d.get("slot"))
            for d in self._dados if d.get("grupo") == grp
        ]

    def _agrupar_slots(self, origem, alvo):
        if origem == alvo:
            return False
        if origem[0] != alvo[0]:
            QMessageBox.information(
                self,
                "Agrupamento inválido",
                f"Locações só podem ser agrupadas no mesmo número.\n"
                f"{alvo[0]} não pode agrupar com {origem[0]}.",
            )
            return False
        i_o = ORDEM_SLOTS[origem[1]]
        i_a = ORDEM_SLOTS[alvo[1]]
        i_min, i_max = sorted((i_o, i_a))
        slots_faixa = [(origem[0], s) for s in ("A", "B", "C", "D")[i_min:i_max + 1]]

        alocadas = [ch for ch in slots_faixa if ch in self._alocados]
        if alocadas:
            QMessageBox.information(
                self,
                "Agrupamento inválido",
                "Não é possível agrupar uma locação já alocada.\n"
                "Libere a alocação (Modo baixa) antes de agrupar.",
            )
            return False

        sa_final = ""
        grp_novo = self._grupo_de(alvo)
        alvos_chaves = set(slots_faixa)
        self._agrupamento_anterior = [
            dict(d) for d in self._dados
            if (d.get("localizacao"), d.get("slot")) in alvos_chaves
        ]
        for ch in slots_faixa:
            for d in self._dados:
                if d.get("localizacao") == ch[0] and d.get("slot") == ch[1]:
                    d["grupo"] = grp_novo
                    d["sa"] = ""
                    d["data"] = ""
        _salvar_dados(self._dados)
        self._rebuild_cards()
        self._atualizar_estado_slots()
        return True

    def _limpar_agrupamento_anterior(self):
        self._agrupamento_anterior = None

    def _reverter_ultimo_agrupamento(self):
        anterior = getattr(self, "_agrupamento_anterior", None)
        if not anterior:
            return
        for snap in anterior:
            for d in self._dados:
                if d.get("localizacao") == snap["localizacao"] and d.get("slot") == snap["slot"]:
                    d["grupo"] = snap["grupo"]
                    d["sa"] = snap["sa"]
                    d["data"] = snap["data"]
                    break
        _salvar_dados(self._dados)
        self._rebuild_cards()
        self._atualizar_estado_slots()
        self._agrupamento_anterior = None

    def _selecionar_modo(self, modo):
        self._modo_alocacao = modo == "alocacao"
        self._modo_baixa = modo == "baixa"
        self.btn_modo_alocacao.setChecked(self._modo_alocacao)
        self.btn_modo_baixa.setChecked(self._modo_baixa)

    def _pedir_sa(self, localizacao, slot):
        dlg = QInputDialog(self)
        dlg.setWindowTitle("Alocar SA")
        dlg.setLabelText(f"Digite o número da SA para {localizacao}-{slot}:")
        dlg.setTextValue("SA")
        editor = dlg.findChild(QLineEdit)
        if editor:
            def posicionar_cursor():
                editor.setCursorPosition(len("SA"))
                editor.deselect()
            QTimer.singleShot(0, posicionar_cursor)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return "", False
        return dlg.textValue(), True

    def _on_slot_clicado(self, btn, localizacao, slot):
        chave = (localizacao, slot)
        if self._modo_alocacao:
            self._alocar_sa(chave)
        elif self._modo_baixa:
            if chave not in self._alocados:
                btn.setChecked(False)
                return
            sa_atual = self._sa_por_chave.get(chave, "")
            resposta = QMessageBox.question(
                self,
                "Baixa",
                f"Locação {localizacao}-{slot} {sa_atual}\nLiberar locação?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if resposta != QMessageBox.StandardButton.Yes:
                btn.setChecked(True)
                return
            for m in self._membros_do_grupo(chave):
                for d in self._dados:
                    if d.get("localizacao") == m[0] and d.get("slot") == m[1]:
                        d["sa"] = ""
                        d["data"] = ""
                        d["grupo"] = f"{m[0]}-{m[1]}"
            _salvar_dados(self._dados)
            self._rebuild_cards()
            self._atualizar_estado_slots()

    def _alocar_sa(self, chave):
        localizacao, slot = chave
        if chave in self._alocados:
            btn = self._slot_botoes.get(chave)
            if btn:
                btn.setChecked(True)
            sa_atual = self._sa_por_chave.get(chave, "")
            QMessageBox.information(
                self,
                "Locação já alocada",
                f"A localização {localizacao}-{slot} já possui a {sa_atual} alocada.",
            )
            return True
        sa, ok = self._pedir_sa(localizacao, slot)
        if not ok:
            btn = self._slot_botoes.get(chave)
            if btn:
                btn.setChecked(False)
            return False
        sa = sa.strip().upper()
        if not sa or sa == "SA":
            btn = self._slot_botoes.get(chave)
            if btn:
                btn.setChecked(False)
            return False
        membros = set(self._membros_do_grupo(chave))
        ocupantes = {
            (d.get("localizacao"), d.get("slot"))
            for d in self._dados
            if (d.get("sa") or "").upper() == sa
        }
        ocupantes.difference_update(membros)
        if ocupantes:
            loc_ocup = next(iter(ocupantes))
            QMessageBox.information(
                self,
                "SA já alocada",
                f"{sa} já se encontra alocada em {loc_ocup[0]}-{loc_ocup[1]}",
            )
            btn = self._slot_botoes.get(chave)
            if btn:
                btn.setChecked(False)
            return False
        agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        for m in self._membros_do_grupo(chave):
            for d in self._dados:
                if d.get("localizacao") == m[0] and d.get("slot") == m[1]:
                    d["sa"] = sa
                    d["data"] = agora
        _salvar_dados(self._dados)
        self._atualizar_estado_slots()
        return True

    def _aplicar_filtro(self):
        texto = self.campo_busca.text().strip()
        if not texto:
            for card in self._cards.values():
                card.setVisible(True)
            return
        encontradas = self._procurar_sa(texto)
        if encontradas:
            sa_dig = texto.upper()
            if len(encontradas) == 1:
                mensagem = f"{sa_dig} está alocada na {encontradas[0]}"
            else:
                mensagem = f"{sa_dig} está alocada nas {', '.join(encontradas)}"
            QMessageBox.information(self, "SA encontrada", mensagem)
            return
        t = texto.lower()
        for loc, card in self._cards.items():
            card.setVisible(t in loc.lower())

    def _procurar_sa(self, texto):
        if not texto:
            return []
        texto_up = texto.strip().upper()
        por_loc = {}
        for d in self._dados:
            sa = (d.get("sa") or "").upper()
            if not sa or texto_up not in sa:
                continue
            por_loc.setdefault(d.get("localizacao", ""), []).append(d.get("slot", ""))
        resultado = []
        for loc in self._localizacoes:
            slots = por_loc.get(loc)
            if slots:
                resultado.append(f"{loc}-{''.join(sorted(slots))}")
        return resultado