@echo off
setlocal EnableExtensions DisableDelayedExpansion
pushd "%~dp0..\.."
if errorlevel 1 goto erro
echo.
echo ALPHAFEST HF65.24.58 - ENSAIO DE STORAGE DE HOMOLOGACAO
echo NUNCA usar o projeto Supabase de producao.
echo.
if not exist ".venv_hf58_demo\Scripts\python.exe" (
    echo Ambiente Python isolado nao encontrado.
    echo Execute primeiro INICIAR_DEMO_WINDOWS.bat em pasta separada.
    goto erro
)
if not exist "scripts\validar_storage_hf58_staging.py" (
    echo Verificador ausente. Baixe a branch homologacao-hf58 atualizada.
    goto erro
)
echo Primeiro, verifica os requisitos SEM ACESSAR A INTERNET:
".venv_hf58_demo\Scripts\python.exe" -B scripts\validar_storage_hf58_staging.py
if errorlevel 1 goto erro
echo.
echo Para o teste remoto e preciso ter criado OUTRO projeto Supabase
echo e um bucket publico catalogo COM arquivo sentinela de homologacao.
echo.
set /p CONFIRMA=Digite TESTAR para iniciar a conferencia do Supabase de testes:
if not "%CONFIRMA%"=="TESTAR" goto cancelado
".venv_hf58_demo\Scripts\python.exe" -B scripts\validar_storage_hf58_staging.py --executar
if errorlevel 1 goto erro
echo.
echo Teste de homologacao aprovado. Faca a conferencia no bucket de testes.
pause
popd
endlocal
exit /b 0
:cancelado
echo Cancelado sem gravar.
popd
endlocal
exit /b 0
:erro
echo.
echo Teste nao aprovado ou interrompido. Nao fazer merge.
pause
popd
endlocal
exit /b 2
