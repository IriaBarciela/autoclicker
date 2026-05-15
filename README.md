# 🖱 AutoClicker Pro

Autoclicker para Windows con interfaz gráfica moderna. No requiere instalar Python.

## Características

- Intervalo configurable (horas / minutos / segundos / milisegundos)
- Countdown antes de iniciar (0-10 segundos)
- Clic izquierdo, derecho o central
- Clic simple o doble
- Repeticiones infinitas o cantidad fija
- Hotkey configurable para activar/desactivar desde cualquier ventana (por defecto **F6**)

## Uso

1. Descarga la carpeta `AutoClicker Pro` de [Releases](../../releases)
2. Abre `AutoClicker Pro.exe`
3. Configura el intervalo y opciones
4. Pulsa **INICIAR** o la tecla **F6**

## Compilar desde código fuente

```bash
pip install customtkinter pynput pyinstaller pillow
pyinstaller --noconfirm --onedir --windowed --collect-all pynput --collect-all customtkinter --icon=autoclicker_icon.ico --name="AutoClicker Pro" autoclicker.py
```
