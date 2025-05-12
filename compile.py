import subprocess
import sys
import os

project_dir = os.path.dirname(os.path.abspath(__file__)) 

script_path = os.path.join(project_dir, 'downloader.py')
output_dir = os.path.join(project_dir, 'dist')
icon_path = os.path.join(project_dir, 'ico.ico')
logo_path = os.path.join(project_dir, 'bckg.png')


if not os.path.exists(script_path):
    print(f"[Ошибка] downloader.py не найден: {script_path}")
    sys.exit(1)

if not os.path.exists(icon_path):
    print(f"[Ошибка] ico.ico не найден: {icon_path}")
    sys.exit(1)

if not os.path.exists(logo_path):
    print(f"[Ошибка] bckg.png не найден: {logo_path}")
    sys.exit(1)

command = [
    'pyinstaller',
    '--onefile',
    '--windowed',
    '--icon', icon_path,
    '--distpath', output_dir,
    '--add-data', f'{logo_path};.',      
    '--add-data', f'{icon_path};.',       
    '--hidden-import=PySide6.QtCore',
    '--hidden-import=PySide6.QtGui',
    '--hidden-import=PySide6.QtWidgets',
    '--hidden-import=vk_api',
    '--hidden-import=requests',
    script_path
]

print("[INFO] Начинаю компиляцию...")
subprocess.run(command, check=True)

print(f"\n Готово .exe находится в: {output_dir}")