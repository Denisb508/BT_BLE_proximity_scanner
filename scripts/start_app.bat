@echo off
cd /d %~dp0\..
if exist venv\Scripts\activate.bat call venv\Scripts\activate.bat
python app\ble_gui_proximity_offline.py
pause
