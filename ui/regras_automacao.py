import time

import pyautogui

_VELOCIDADE = 0.02


def configurar_velocidade(segundos):
    global _VELOCIDADE
    _VELOCIDADE = segundos


def esperar_inicio():
    for i in range(5, 0, -1):
        print(f"Começando em {i}...")
        time.sleep(1)


def digitar_texto(texto):
    pyautogui.write(str(texto), interval=_VELOCIDADE)


def enter(vezes=1):
    for _ in range(vezes):
        pyautogui.press("enter")
        time.sleep(0.03)
