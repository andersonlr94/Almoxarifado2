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

import qtawesome

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QStyledItemDelegate, QFileDialog, QMessageBox, QDialog,
)
from PySide6.QtCore import Qt, QSize, QRect
from PySide6.QtGui import QPainter, QColor
from ui.regras_automacao import digitar_texto, enter
from ui.pages.dpp_ativos_page import CredentialsDialog

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


class FreshStartPage(QWidget):
    COLUNAS = [
        "Local", "Kardex", "Descrição", "Loc", "Qtde Qad", "Qtde Sci",
        "Compras", "Fornecedor", "Pedido", "Lugar transferido",
    ]
    CHAVES = [
        "local", "kardex", "descricao", "loc", "qtde_qad", "qtde_sci",
        "compras", "fornecedor", "pedido", "lugar_transferido",
    ]

    def __init__(self):
        super().__init__()
        self.dados = []
        self._credenciais = None
        self._estado_grafico = 0
        self._setup_ui()
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
                    dialog = CredentialsDialog(self)
                    if dialog.exec() != QDialog.DialogCode.Accepted:
                        return
                    dados = dialog.obter_dados()
                    self._credenciais = (dados["usuario"], dados["senha"])

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
        QMessageBox.information(self, "zCusto", "Valores do zCusto atualizados.")

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
        self.campo_filtro.setFixedHeight(30)
        self.campo_filtro.setFixedWidth(220)
        self.campo_filtro.textChanged.connect(self._aplicar_filtro)
        self.filter_row.addWidget(self.campo_filtro)

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

        self.tabela = QTableWidget(0, len(self.COLUNAS))
        self.tabela.setObjectName("tabelaFreshStart")
        self.tabela.setHorizontalHeaderLabels(self.COLUNAS)
        header = self.tabela.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        larguras = [50, 140, 200, 100, 100, 100, 100, 150, 100]
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

        self.total_row = QHBoxLayout()
        self.total_row.setSpacing(8)
        self.total_row.addStretch()
        label_total = QLabel("Valor total zCentral:")
        label_total.setObjectName("statusLabel")
        self.total_row.addWidget(label_total)
        self.label_total_zcentral = QLabel("R$ 0,00")
        self.label_total_zcentral.setObjectName("statusLabel")
        self.label_total_zcentral.setStyleSheet("font-size: 15px; font-weight: 700; color: #6366f1;")
        self.total_row.addWidget(self.label_total_zcentral)

        self.total_row.addSpacing(24)

        label_total_dph = QLabel("Valor DPH:")
        label_total_dph.setObjectName("statusLabel")
        self.total_row.addWidget(label_total_dph)
        self.label_total_dph = QLabel("R$ 0,00")
        self.label_total_dph.setObjectName("statusLabel")
        self.label_total_dph.setStyleSheet("font-size: 15px; font-weight: 700; color: #16a34a;")
        self.total_row.addWidget(self.label_total_dph)

        self.total_row.addSpacing(24)

        label_total_dif = QLabel("Valor Central zCentral-DPH:")
        label_total_dif.setObjectName("statusLabel")
        self.total_row.addWidget(label_total_dif)
        self.label_total_dph_dif = QLabel("R$ 0,00")
        self.label_total_dph_dif.setObjectName("statusLabel")
        self.label_total_dph_dif.setStyleSheet("font-size: 15px; font-weight: 700; color: #ea580c;")
        self.total_row.addWidget(self.label_total_dph_dif)
        table_card_layout.addLayout(self.total_row)

        self.layout.addWidget(self.table_card)

        # ── Gráfico de histórico ──
        self.chart_card = QWidget()
        self.chart_card.setObjectName("pageCard")
        self.chart_card_layout = QVBoxLayout(self.chart_card)
        self.chart_card_layout.setContentsMargins(18, 14, 18, 14)
        self.chart_card_layout.setSpacing(10)

        chart_header = QHBoxLayout()
        chart_titulo = QLabel("Evolução dos valores")
        chart_titulo.setObjectName("pageSubtitle")
        chart_header.addWidget(chart_titulo)
        chart_header.addStretch()

        self.botao_grafico = QPushButton()
        self.botao_grafico.setObjectName("btnExpandirGrafico")
        self.botao_grafico.setIcon(qtawesome.icon('fa6s.window-minimize', color='#94a3b8'))
        self.botao_grafico.setIconSize(QSize(14, 14))
        self.botao_grafico.setFixedSize(28, 28)
        self.botao_grafico.setCursor(Qt.CursorShape.PointingHandCursor)
        self.botao_grafico.setToolTip("Expandir gráfico")
        self.botao_grafico.setStyleSheet(
            "QPushButton#btnExpandirGrafico {"
            " background-color: transparent; border: 1px solid #e2e8f0;"
            " border-radius: 8px;"
            "}"
            "QPushButton#btnExpandirGrafico:hover {"
            " background-color: #eef2ff; border-color: #c7d2fe;"
            "}"
        )
        self.botao_grafico.clicked.connect(self._alternar_grafico)
        chart_header.addWidget(self.botao_grafico)

        self.chart_card_layout.addLayout(chart_header)

        self.figure = Figure(figsize=(8, 3.2), facecolor="none")
        self.figure.subplots_adjust(left=0.06, right=0.98, top=0.92, bottom=0.18)
        self.canvas = FigureCanvas(self.figure)
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

                dialog = CredentialsDialog(self)
                if dialog.exec() != dialog.DialogCode.Accepted:
                    return

                dados = dialog.obter_dados()
                os.makedirs(os.path.dirname(caminho), exist_ok=True)
                self._baixar_zcentral_com_winscp(
                    dados["usuario"], dados["senha"], caminho
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
                kardex = linha[18:37].strip()
                loc = linha[37:56].strip()
                qtde_qad = linha[60:72].strip()
                if local.isdigit() and kardex and loc and qtde_qad:
                    novos.append({
                        "local": local,
                        "kardex": kardex,
                        "loc": loc,
                        "qtde_qad": qtde_qad,
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
            if estoque is not None:
                item["descricao"] = str(estoque.get("Descrição", ""))
                item["qtde_sci"] = str(estoque.get("Qtde novo", ""))
                item["fornecedor"] = str(estoque.get("Fornecedor", ""))
            if existente is not None:
                existente["loc"] = item["loc"]
                existente["qtde_qad"] = item["qtde_qad"]
                if estoque is not None:
                    existente["descricao"] = item["descricao"]
                    existente["qtde_sci"] = item["qtde_sci"]
                    existente["fornecedor"] = item["fornecedor"]
            else:
                novo_item = {chave: "" for chave in self.CHAVES}
                novo_item.update(item)
                self.dados.append(novo_item)
                por_chave[chave] = novo_item

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

    def _baixar_zcentral_com_winscp(self, usuario, senha, destino_local):
        caminhos = [
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
        resultado = subprocess.run(comando, capture_output=True, text=True)
        if resultado.returncode != 0:
            raise Exception(resultado.stderr or resultado.stdout)
        if not os.path.isfile(destino_local):
            retorno = resultado.stderr or resultado.stdout
            mensagem = "O WinSCP terminou, mas zCentral.prn não foi criado no destino."
            if retorno:
                mensagem += f"\n{retorno}"
            raise Exception(mensagem)

    def _baixar_zcusto_com_winscp(self, usuario, senha, destino_local):
        caminhos = [
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

    # ── Gráfico ──
    def _atualizar_grafico(self):
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.set_facecolor("none")
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.tick_params(colors="#94a3b8", length=0)
        ax.grid(axis="y", color="#e2e8f0", linewidth=0.8, alpha=0.6)

        registros = _carregar_historico()
        if not registros:
            ax.tick_params(bottom=False, labelbottom=False)
            ax.text(
                0.5, 0.5, "Sem dados no histórico ainda",
                transform=ax.transAxes,
                ha="center", va="center",
                fontsize=12, color="#94a3b8",
            )
            self.canvas.draw()
            return

        datas = [r[0] for r in registros]
        series = [
            ([r[1] for r in registros], "zCentral", "#6366f1"),
            ([r[2] for r in registros], "DPH", "#22c55e"),
            ([r[3] for r in registros], "zCentral - DPH", "#f97316"),
        ]
        xs = list(range(len(registros)))

        for valores, nome, cor in series:
            ax.plot(
                xs, valores,
                label=nome, color=cor, linewidth=2.5, zorder=3,
                marker="o", markersize=5,
                markerfacecolor="#ffffff", markeredgecolor=cor, markeredgewidth=2,
            )
            ax.fill_between(xs, valores, color=cor, alpha=0.08, zorder=2)

        ax.set_xticks(xs)
        ax.set_xticklabels(datas, rotation=30, ha="right", fontsize=8, color="#94a3b8")
        ax.legend(
            loc="upper left", frameon=False, fontsize=9,
            labelcolor="#334155",
        )
        self.canvas.draw()

    def _alternar_grafico(self):
        self._estado_grafico = (self._estado_grafico + 1) % 3
        self._aplicar_estado_grafico()

    def _aplicar_estado_grafico(self):
        maximizado = self._estado_grafico == 2
        for i in range(self.filter_row.count()):
            item = self.filter_row.itemAt(i)
            if item.widget():
                item.widget().setVisible(not maximizado)
        self.tabela.setVisible(not maximizado)
        if self._estado_grafico == 0:
            self.canvas.setVisible(False)
            self.chart_card.setFixedHeight(40)
            self.chart_card_layout.setContentsMargins(10, 4, 10, 4)
            self.chart_card_layout.setSpacing(0)
            self.layout.setStretch(2, 0)
            self.botao_grafico.setIcon(qtawesome.icon('fa6s.window-minimize', color='#94a3b8'))
            self.botao_grafico.setToolTip("Expandir para meia tela")
        elif self._estado_grafico == 1:
            self.canvas.setVisible(True)
            self.chart_card.setMinimumHeight(0)
            self.chart_card.setMaximumHeight(16777215)
            self.chart_card_layout.setContentsMargins(18, 14, 18, 14)
            self.chart_card_layout.setSpacing(10)
            self.canvas.setMinimumHeight(260)
            self.canvas.setMaximumHeight(16777215)
            self.layout.setStretch(2, 1)
            self.botao_grafico.setIcon(qtawesome.icon('fa6s.window-restore', color='#6366f1'))
            self.botao_grafico.setToolTip("Maximizar gráfico")
        else:
            self.canvas.setVisible(True)
            self.chart_card.setMinimumHeight(0)
            self.chart_card.setMaximumHeight(16777215)
            self.chart_card_layout.setContentsMargins(18, 14, 18, 14)
            self.chart_card_layout.setSpacing(10)
            self.canvas.setMinimumHeight(260)
            self.canvas.setMaximumHeight(16777215)
            self.layout.setStretch(2, 8)
            self.botao_grafico.setIcon(qtawesome.icon('fa6s.window-maximize', color='#6366f1'))
            self.botao_grafico.setToolTip("Minimizar gráfico")

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
        self.label_total_zcentral.setText(f"R$ {total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

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
        self.label_total_dph.setText(f"R$ {total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        self._atualizar_total_central_dph()

    def _atualizar_total_central_dph(self):
        zcentral = _parse_numero(self.label_total_zcentral.text().replace("R$", "").strip())
        dph = _parse_numero(self.label_total_dph.text().replace("R$", "").strip())
        valor = zcentral - dph
        self.label_total_dph_dif.setText(f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

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
                cell = QTableWidgetItem(str(item.get(chave, "")))
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
        for col in range(len(self.COLUNAS)):
            cell = QTableWidgetItem("")
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
            if item.text().strip():
                novo_item = {}
                for c, ch in enumerate(self.CHAVES):
                    celula = self.tabela.item(row, c)
                    novo_item[ch] = celula.text().strip() if celula else ""
                self.dados.append(novo_item)
                celula_origem.setData(Qt.ItemDataRole.UserRole, len(self.dados) - 1)
                self._salvar_json()
                self._inserir_linha_vazia()
            return

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
            for col, largura in enumerate([50, 140, 200, 100, 100, 100, 100, 150, 100, 200], start=1):
                ws.column_dimensions[chr(64 + col)].width = max(largura, 8)
            wb.save(caminho)
        except OSError as erro:
            QMessageBox.critical(self, "Exportar Excel", f"Não foi possível salvar o arquivo.\n{erro}")
            return

        QMessageBox.information(self, "Exportar Excel", f"Tabela exportada com sucesso:\n{caminho}")

    def _atualizar_contador(self):
        total = max(0, self.tabela.rowCount() - 1)
        self.label_contador.setText(f"{total} itens")
