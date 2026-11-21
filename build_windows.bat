@echo off
python -m venv .venv
call .venv\Scripts\activate
pip install -r windows_app\requirements.txt
pyinstaller --noconfirm --onefile --windowed --name SamahiApp --icon branding/logo_icon_1024.png --add-data "windows_app\vectorfont;vectorfont" windows_app\app.py
echo Built: dist\SamahiApp.exe
