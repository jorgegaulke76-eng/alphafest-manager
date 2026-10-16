# Plano de implantação e reversão — preços na AlphaFest

> Documento de preparação. **Nenhum passo de publicação foi executado.**

## Estado de referência (verificado em 16/10/2026)
- Repositório: `jorgegaulke76-eng/alphafest-manager`
- Branch oficial: `main`
- Commit de referência: `008f1a306e6ff21382b98a9ca6c02ec08d6089b7`
- Versão declarada nesse commit: `20.4.9-I8.13.5-HF53.3-HF8-HF65.19`
- Aplicativo oficial no Streamlit Community Cloud: `alphafest-manager`, implantado a partir de `main` e `app.py`, conforme conferência visual do responsável.
- PR de preços: #1, branch `feature/modalidades-preco-site`, ainda rascunho e não mesclado.

**Revalidar o SHA da main imediatamente antes de qualquer implantação**; não presumir que permaneceu igual.

## Preparação obrigatória
1. Executar os testes automatizados do último commit do PR e conferir resultado.
2. Finalizar a homologação integral do formulário oficial com persistência isolada; a demonstração `tests/demo_cadastro_preco_isolado.py` não o substitui.
3. Identificar tarefas de publicação automática e o comportamento do deploy no Streamlit.
4. Fazer um backup consistente e restaurável do catálogo, clientes e pedidos com procedimento próprio já homologado. Não guardar cópias de produção no GitHub nem nas ferramentas de teste.
5. Definir janela de implantação e usuário responsável por aprovar a liberação.
6. Validar catálogo sem preço, preço textual `SOB/CONSULTA`, preços fixos, preços iniciais e compatibilidade com legado.

## Implantação controlada (somente depois da aprovação)
1. Anotar o SHA atual da `main` (será o ponto de retorno).
2. Confirmar backup e testes.
3. Fazer merge do PR #1 mediante autorização específica.
4. Aguardar deploy do Streamlit e verificar inicialização, leitura, cadastro, edição e confirmação de salvamento.
5. Não publicar a vitrine do site até verificar manualmente os três modos em prévia/staging.
6. Monitorar erros de aplicativo e de gravação.

## Reversão em caso de falha
1. Interromper novas operações administrativas relevantes e **não tentar corrigir dados às cegas**.
2. Localizar o merge commit no histórico do GitHub e reverter as mudanças por um **novo commit/PR de revert**, preservando o histórico. Evitar `reset --hard` e `push --force` na `main`.
3. Aguardar o Streamlit implantar o revert e conferir funcionamento.
4. Se a falha atingir dados, restaurar somente com análise de impacto, backup validado e aprovação explícita; **revert de código não restaura registros alterados**.
5. Se a vitrine já tiver sido publicada separadamente, reverter também a publicação do site pelo procedimento próprio; o revert do Manager não reverte automaticamente o HTML do site.

## Critérios de bloqueio
- Falha em qualquer teste essencial, conflito não investigado ou perda de confirmação de gravação.
- Falta de backup restaurável, falta de teste isolado integral do `app.py` ou dúvida sobre deploy.
- Divergência entre preço anunciado e preço efetivamente praticado.

## Riscos não resolvidos
- Uma segunda instância pública de **demonstração** do Streamlit não substitui um ambiente integral do Manager.
- A automação atual valida componentes do código e HTTP simulado; ainda não é ensaio completo de implantação.
- Publicações do site podem depender de operações distintas do Streamlit.
