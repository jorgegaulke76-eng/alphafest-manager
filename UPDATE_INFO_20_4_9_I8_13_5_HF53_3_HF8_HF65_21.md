# HF65.21 — Interface AdSense e estabilidade de painéis (12/11/2026)

## Base preservada
- Pacote completo reconstruído a partir do ZIP HF65.19 fornecido pelo usuário.
- Mantidas as correções de orçamentos e demais recursos anteriores da HF65.19.
- Incorporados os serviços AdSense da HF65.20 (metatag, ads.txt e publicação via Manager).

## Correções desta versão
- **AdSense sempre acessível** em Site AlphaFest → Central do Site → Atualizar o site, antes de qualquer prévia.
- O formulário e a ação de salvar código funcionam sem depender de Preparar prévia.
- Painel AdSense usa contêiner, em vez de expander aninhado.
- Painel Publicar site usa contêiner, preservando apenas o expansor de configurações Cloudflare.
- Continua sendo necessário confirmar manualmente a publicação, que não ocorre ao salvar o código.
- Nenhum script publicitário é ativado; apenas verificação e ads.txt com publisher ID real.

## Diagnósticos e limitações
- Sintaxe Python e integridade do pacote conferidas localmente.
- O erro de navegador `NotFoundError: removeChild` pode ter outras causas (por exemplo tradução automática/extensões ou estado de sessão do Streamlit). A reorganização corrige os painéis aninhados, mas **não garante** eliminar qualquer erro de navegador.
- Ainda é necessária homologação funcional no Streamlit Cloud em uso antes de declarar a interface totalmente validada.

## Instalação
- Primeiro faça backup da versão online e dos dados.
- Para Streamlit Cloud, publique os arquivos alterados na branch `main` do GitHub por processo de PR/revisão.
- O ZIP completo serve como pacote para restauração e comparação, não é publicado automaticamente.
- A publicação do site Cloudflare é uma ação separada dentro da Central do Site.
