import sys
import multiprocessing
import numpy  # <-- FORÇA O CARREGAMENTO ÚNICO AQUI

if __name__ == "__main__":
    # Necessário para o PyInstaller lidar corretamente com bibliotecas que 
    # iniciam subprocessos (como o Numpy/Matplotlib)
    multiprocessing.freeze_support()

    from PySide6.QtWidgets import QApplication, QDialog
    from PySide6.QtCore import Qt
    from qfluentwidgets import setTheme, Theme
    from ui.main_window import MainWindow
    from ui.login_dialog import LoginDialog
    from core import session as session_core
    from core import auth as auth_core

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    setTheme(Theme.LIGHT)

    # Tentativa de auto-login apenas na primeira abertura (Entrar diretamente)
    try:
        auto_user = auth_core.try_auto_login()
        if auto_user:
            session_core.set_current_user(auto_user)
    except Exception:
        pass

    # Loop de login -> MainWindow -> logout -> login novamente
    exit_code = 0
    primeira_vez = True
    while True:
        # Se não há sessão (sem auto ou após logout), exige login manual
        if not session_core.is_authenticated():
            # Na primeira vez já tentamos auto; nas vezes seguintes (pós-logout) não tenta auto novamente
            # para permitir troca de usuário manual
            login = LoginDialog()
            resultado = login.exec()
            if resultado != QDialog.Accepted:
                # usuário fechou login sem autenticar
                sys.exit(0)
        else:
            # Sessão já preenchida via auto-login: pula diálogo na primeira abertura
            # (apenas log para debug, sem UI)
            pass

        primeira_vez = False

        # Login aceito (manual ou auto), session já preenchida
        window = MainWindow()
        window.show()

        # exec() bloqueia até a janela fechar
        # Se a janela fechou por logout, ela define uma flag _logout_requested
        app_exit = app.exec()

        # Verifica se foi logout solicitado (reconectar login) ou fechamento normal
        solicitou_logout = getattr(window, "_logout_requested", False)
        # Limpa referência
        window = None

        if solicitou_logout:
            # limpa sessão mas MANTÉM config de auto-login persistida
            # próxima iteração exigirá login manual (para permitir troca de usuário)
            # a menos que o usuário feche e reabra o app -> aí auto entra de novo
            session_core.clear_current_user()
            # continua o while para novo login manual
            continue
        else:
            # fechamento normal -> encerra aplicação (mantém auto para próxima abertura)
            sys.exit(app_exit)
