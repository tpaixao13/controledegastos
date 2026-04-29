@echo off
chcp 65001 > nul
echo.
echo  ============================================
echo   Build FinFam.exe
echo  ============================================
echo.

echo  [1/3] Instalando dependencias de build...
pip install waitress pyinstaller --quiet
if errorlevel 1 (
    echo  ERRO ao instalar dependencias.
    pause
    exit /b 1
)

echo  [2/3] Limpando build anterior...
if exist dist\FinFam.exe del /f /q dist\FinFam.exe

echo  [3/3] Gerando FinFam.exe...
pyinstaller finfam.spec --clean --noconfirm
if errorlevel 1 (
    echo.
    echo  ERRO durante o build. Verifique as mensagens acima.
    pause
    exit /b 1
)

echo.
echo  ============================================
echo   Pronto!
echo   Executavel: dist\FinFam.exe
echo.
echo   Dados e banco de dados ficam em:
echo   %%APPDATA%%\FinFam\
echo  ============================================
echo.
pause
