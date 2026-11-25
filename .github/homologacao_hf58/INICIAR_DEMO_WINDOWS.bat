@echo off
setlocal EnableExtensions DisableDelayedExpansion
pushd "%~dp0..\.."
if errorlevel 1 goto erro_pasta
echo.
echo ================================================
echo ALPHAFEST HF65.24.58 RC5 - HOMOLOGACAO ISOLADA
echo Somente dados ficticios - sem banco de producao
echo ================================================
echo.
if not exist ".github\homologacao_hf58\demo.py" goto erro_pacote
if not exist "VERSAO.txt" goto erro_pacote
if not exist "UPDATE_MANIFEST.json" goto erro_pacote
if not exist "test_hf58_demo_isolada_ui.py" goto erro_pacote

rem Preferir Python 3.11 igual ao GitHub Actions. Aceitar 3.12/3.13 se necessario.
set "PYBASE="
py -3.11 -c "import sys; assert sys.version_info[:2] == (3, 11)" >nul 2>&1
if not errorlevel 1 set "PYBASE=py -3.11"
if not defined PYBASE (
    py -3.12 -c "import sys; assert sys.version_info[:2] == (3, 12)" >nul 2>&1
    if not errorlevel 1 set "PYBASE=py -3.12"
)
if not defined PYBASE (
    py -3.13 -c "import sys; assert sys.version_info[:2] == (3, 13)" >nul 2>&1
    if not errorlevel 1 set "PYBASE=py -3.13"
)
if not defined PYBASE (
    python -c "import sys; assert (3, 11) <= sys.version_info[:2] < (3, 14)" >nul 2>&1
    if not errorlevel 1 set "PYBASE=python"
)
if not defined PYBASE goto erro_python

set "VENV=%CD%\.venv_hf58_demo"
set "PYEXE=%VENV%\Scripts\python.exe"
if not exist "%PYEXE%" (
    echo Preparando Python isolado na pasta .venv_hf58_demo ...
    %PYBASE% -m venv "%VENV%"
    if errorlevel 1 goto erro_venv
)
"%PYEXE%" -c "import streamlit; from streamlit.testing.v1 import AppTest" >nul 2>&1
if errorlevel 1 (
    echo Instalando Streamlit SOMENTE neste ambiente de demonstracao...
    "%PYEXE%" -m pip install --disable-pip-version-check "streamlit>=1.51,<2"
    if errorlevel 1 goto erro_pip
)
"%PYEXE%" -c "import streamlit; from streamlit.testing.v1 import AppTest; print('Streamlit pronto:', streamlit.__version__)"
if errorlevel 1 goto erro_pip

if /I "%~1"=="--verificar" (
    echo Executando teste de abertura em modo isolado...
    "%PYEXE%" -B -m unittest -q test_hf58_demo_isolada_ui
    if errorlevel 1 goto erro_teste
    echo Teste Windows aprovado. Nenhum servidor foi iniciado.
    popd
    endlocal & exit /b 0
)

echo.
echo Abrindo demonstracao local: http://127.0.0.1:8502
echo Quando terminar, feche esta janela ou pressione Ctrl+C.
"%PYEXE%" -m streamlit run ".github\homologacao_hf58\demo.py" --server.address 127.0.0.1 --server.port 8502 --server.headless false
if errorlevel 1 goto erro_exec
popd
endlocal & exit /b 0

:erro_pasta
echo ERRO: nao foi possivel acessar a pasta principal da demonstracao.
goto erro_final
:erro_pacote
echo ERRO: faltam arquivos da branch homologacao-hf58.
echo Extraia o ZIP COMPLETO da branch em pasta separada do Manager atual.
goto erro_final
:erro_python
echo ERRO: Python 3.11, 3.12 ou 3.13 nao encontrado.
echo Instale o Python 3.11 com o launcher py e execute novamente.
echo Site oficial: https://www.python.org/downloads/
goto erro_final
:erro_venv
echo ERRO: nao foi possivel criar o ambiente Python isolado.
goto erro_final
:erro_pip
echo ERRO: instalacao do Streamlit falhou.
echo Verifique conexao com a internet e tente executar este arquivo novamente.
goto erro_final
:erro_teste
echo ERRO: o teste isolado da demonstracao nao passou.
goto erro_final
:erro_exec
echo ERRO: nao foi possivel abrir a demonstracao na porta 8502.
echo Confira se outro aplicativo ja esta utilizando essa porta.
goto erro_final
:erro_final
if not defined GITHUB_ACTIONS pause
popd
endlocal & exit /b 2
