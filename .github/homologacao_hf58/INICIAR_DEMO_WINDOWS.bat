@echo off
setlocal
cd /d "%~dp0\..\.."
echo.
echo ALPHAFEST HF65.24.58 RC5 - HOMOLOGACAO LOCAL
echo SIMULACAO FICTICIA - NAO CONECTA AO BANCO DE PRODUCAO
echo.
if not exist ".github\homologacao_hf58\demo.py" (
  echo ERRO: extraia a branch de homologacao completa em uma pasta separada.
  pause
  exit /b 2
)
if not exist "VERSAO.txt" (
  echo ERRO: pacote de homologacao incompleto.
  pause
  exit /b 2
)
py -3.11 -c "import streamlit" >nul 2>&1
if errorlevel 1 (
  echo Streamlit nao encontrado no Python 3.11.
  echo Instale em ambiente isolado com:
  echo py -3.11 -m venv .venv_hf58_demo
  echo .venv_hf58_demo\Scripts\python.exe -m pip install -r requirements.txt
  echo .venv_hf58_demo\Scripts\python.exe -m streamlit run .github\homologacao_hf58\demo.py --server.address 127.0.0.1 --server.port 8502
  echo.
  pause
  exit /b 2
)
echo Abrindo demonstracao apenas no seu computador: http://127.0.0.1:8502
py -3.11 -m streamlit run .github\homologacao_hf58\demo.py --server.address 127.0.0.1 --server.port 8502
if errorlevel 1 (
  echo Nao foi possivel iniciar. Confirme Python 3.11 e Streamlit instalados.
  pause
)
endlocal
