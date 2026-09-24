r"""
core/eventos_watcher.py — Observa inbox do usuario logado e emite sinal quando chega evento novo.

Polling 1500ms na pasta S:/Almox/Eventos/inbox/<meu_usuario>/
Tambem tenta QFileSystemWatcher quando o FS suporta (SMB geralmente nao dispara).
"""

from PySide6.QtCore import QObject, Signal, QTimer, QFileSystemWatcher
import os


class EventosWatcher(QObject):
    novo_evento = Signal(dict)  # emite evento completo
    # para debug: Signal(str)
    erro = Signal(str)

    def __init__(self, parent=None, intervalo_ms: int = 1500):
        super().__init__(parent)
        self._usuario = ""
        self._vistos = set()  # ids já notificados
        self._timer = QTimer(self)
        self._timer.setInterval(intervalo_ms)
        self._timer.timeout.connect(self._poll)
        self._watcher = None
        self._pasta = ""

    def iniciar(self, username: str):
        self.parar()
        self._usuario = (username or "").strip().lower()
        self._vistos.clear()
        if not self._usuario:
            return
        # resolve pasta
        try:
            from core import eventos as ev
            self._pasta = ev._pasta_inbox(username)
            if self._pasta:
                os.makedirs(self._pasta, exist_ok=True)
                # pré-carrega vistos para não notificar histórico antigo na inicialização
                # Só marca como visto, não notifica
                for nome in os.listdir(self._pasta):
                    if nome.endswith(".json"):
                        path = os.path.join(self._pasta, nome)
                        try:
                            import json
                            with open(path, "r", encoding="utf-8") as f:
                                data = json.load(f)
                            eid = data.get("id") or nome
                            self._vistos.add(eid)
                        except Exception:
                            self._vistos.add(nome)
                # QFileSystemWatcher opcional
                try:
                    self._watcher = QFileSystemWatcher(self)
                    self._watcher.addPath(self._pasta)
                    self._watcher.directoryChanged.connect(lambda _: self._poll())
                except Exception:
                    self._watcher = None
        except Exception as e:
            try:
                self.erro.emit(str(e))
            except Exception:
                pass
        self._timer.start()
        # poll imediato já marcará histórico como visto acima, então novos só após start

    def parar(self):
        try:
            self._timer.stop()
        except Exception:
            pass
        if self._watcher is not None:
            try:
                # remove paths
                for p in self._watcher.directories():
                    self._watcher.removePath(p)
            except Exception:
                pass
            self._watcher = None
        self._pasta = ""
        self._usuario = ""

    def _poll(self):
        if not self._usuario or not self._pasta:
            return
        if not os.path.isdir(self._pasta):
            return
        try:
            import json
            for nome in os.listdir(self._pasta):
                if not nome.endswith(".json") or nome.endswith(".tmp"):
                    continue
                path = os.path.join(self._pasta, nome)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                except Exception:
                    continue
                if not isinstance(data, dict):
                    continue
                eid = data.get("id") or nome
                if eid in self._vistos:
                    continue
                # valida destinatário
                para = (data.get("para") or "").strip().lower()
                if para and para != self._usuario:
                    # não é para mim (pasta já filtra, mas garante)
                    self._vistos.add(eid)
                    continue
                # já lida? não notifica de novo
                if data.get("lida"):
                    self._vistos.add(eid)
                    continue
                self._vistos.add(eid)
                # emite
                data["_path"] = path
                data["_fname"] = nome
                try:
                    self.novo_evento.emit(data)
                except Exception as e:
                    try:
                        self.erro.emit(str(e))
                    except Exception:
                        pass
            # limpeza oportunista de antigos
            try:
                from core import eventos as ev
                ev._limpar_antigos_para_para(self._usuario)
            except Exception:
                pass
        except Exception as e:
            try:
                self.erro.emit(str(e))
            except Exception:
                pass

    def marcar_todos_vistos(self):
        """Chamado quando usuário abre a página e quer limpar badge."""
        # já feito via _vistos, mas pode marcialmente lido no disco
        pass
