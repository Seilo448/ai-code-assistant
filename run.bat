@echo off
cd /d "%~dp0"
echo Installation des dependances...
pip install -r requirements.txt > nul 2>&1
echo Demarrage du serveur...
echo.
echo Ouvre http://localhost:5000 dans ton navigateur
echo.
echo Compte admin: admin@example.com / admin123
echo.
echo Appuie sur Ctrl+C pour arreter le serveur
echo.
python app.py
pause
