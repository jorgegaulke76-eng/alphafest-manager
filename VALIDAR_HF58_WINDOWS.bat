@echo off
setlocal EnableExtensions
cd /d "%~dp0"
echo.
echo ======================================
echo ALPHAFEST HF65.24.58 - HOMOLOGACAO
 echo ======================================
echo ATENCAO: executar SOMENTE numa COPIA, sem banco de producao.
echo.
where py >nul 2>nul
if errorlevel 1 (
  echo ERRO: Python Launcher nao encontrado. Instale Python na maquina de TESTE.
  exit /b 10
)
set "QA_ENV=%~dp0..\_hf58_qa_venv"
if not exist "%QA_ENV%\Scripts\python.exe" (
  py -3 -m venv "%QA_ENV%"
  if errorlevel 1 exit /b 11
)
call "%QA_ENV%\Scripts\activate.bat"
python -m pip install --disable-pip-version-check -r requirements.txt
if errorlevel 1 (
  echo FALHA: nao foi possivel instalar requirements.txt.
  exit /b 12
)
echo.
echo Executando a regressao completa...
python -m unittest discover -p "test_*.py" -q > "%~dp0..\HF58_REGRESSAO_WINDOWS.log" 2>&1
if errorlevel 1 (
  echo REPROVADO. Confira ..\HF58_REGRESSAO_WINDOWS.log
  exit /b 13
)
echo Regressao concluida. Executando o gate oficial...
python build_update_package.py --root . --output "..\HF58_VALIDADO_TESTE.zip" --release-note UPDATE_INFO_HF65.24.58.md > "..\HF58_GATE_WINDOWS.log" 2>&1
if errorlevel 1 (
  echo REPROVADO. Confira ..\HF58_GATE_WINDOWS.log
  exit /b 14
)
echo.
echo Testes automatizados aprovados. A homologacao manual de arte,
echo ficha e concorrencia ainda e obrigatoria antes da liberacao final.
echo Arquivos: ..\HF58_REGRESSAO_WINDOWS.log e ..\HF58_GATE_WINDOWS.log
endlocal
exit /b 0
