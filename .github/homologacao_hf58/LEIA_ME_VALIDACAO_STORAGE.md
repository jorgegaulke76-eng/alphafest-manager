# AlphaFest HF65.24.58 — verificação real de Storage SOMENTE em homologação

Este verificador foi criado para ensaiar a função **real** `cloud_db.upload_library_file` usando **um PNG fictício de 1 × 1 pixel**. A versão de demonstração `127.0.0.1:8502` continua isolada e não usa credenciais. **Não execute no Supabase de produção.**

## Preparação única (separada da empresa)

Crie um **projeto Supabase exclusivo para homologação**, com outra URL/referência. Não clone o banco de clientes, não replique chaves de produção e não reutilize o projeto que opera o Manager.

Nesse novo projeto, configure um bucket público chamado **`catalogo`** (mesmo nome usado pelo upload real do Manager, porém no projeto de testes). Na raiz do bucket, carregue o arquivo de identificação:

- Nome: `HF58_HOMOLOGACAO_<REFERENCIA_DO_PROJETO_TESTES>.txt`
- Conteúdo UTF-8: `ALPHAFEST_HF58_STAGING_ONLY:<REFERENCIA_DO_PROJETO_TESTES>`

Substitua o texto entre colchetes pela referência do **projeto de testes**, extraída de `https://<referencia>.supabase.co`. Não use os sinais `<` e `>` no nome real. O conteúdo deve corresponder exatamente, admitindo uma quebra de linha final.

Use uma credencial **somente do projeto de testes**, com as permissões necessárias ao Storage. O verificador solicita a chave no terminal sem exibi-la. Nunca coloque essa chave em arquivos do GitHub, no chat, no ZIP ou no gerenciador de produção.

## Executar no Windows

Baixe a branch `homologacao-hf58` em uma **pasta separada**. O inicializador da demonstração (`INICIAR_DEMO_WINDOWS.bat`) já configura a pasta `.venv_hf58_demo`.

Abra `.github\homologacao_hf58\TESTAR_SUPABASE_HOMOLOGACAO.bat` e siga as instruções. Ele pedirá as URLs dos **dois projetos** (a de produção apenas para confirmar que são diferentes), a referência digitada novamente, a confirmação `EU_CONFIRMO_PROJETO_DE_TESTES` e a chave do projeto de testes. A URL de produção não precisa de chave.

Antes de enviar qualquer byte, o programa confere as duas URLs, a referência informada, o bucket `catalogo` e a sentinela. Se algum item faltar, **nenhum upload é feito**.

Se passar, envia um PNG fictício para `biblioteca/HF58_STAGING_ONLY/`, lê o objeto publicado e compara o SHA-256 com o original. Depois **apaga exclusivamente o arquivo criado nessa execução**. Se uma etapa falhar, registra que a validação não foi aprovada e orienta a inspeção da pasta de testes.

## O que é e o que não é validado

**Validado após execução bem-sucedida:** upload real de bytes no bucket público de homologação, download integral e exclusão do objeto de ensaio, utilizando a função real da RC6.

**Não validado por esse roteiro:** escrita na tabela `app_data`, concorrência de usuários, permissões de produção, aprovação comercial, implantação no Streamlit ou migração de dados. Nada disso é executado.

**Atenção:** não podemos executar o ensaio remoto sem um projeto de homologação que esteja separado e identificado. A CI executa apenas os testes com respostas simuladas e sem credenciais. Até a evidência do ensaio real e a revisão final, **mantenha o PR #5 como Draft e não faça merge**.

Documentação: https://supabase.com/docs/guides/storage/uploads/standard-uploads
