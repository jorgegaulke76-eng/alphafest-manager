# AlphaFest HF65.24.58 — homologação RC3 (25/11/2026 14:06)

**Status: HOMOLOGAÇÃO PARCIAL. NÃO SUBSTITUIR O MANAGER EM PRODUÇÃO COM ESTE PACOTE.**

## Base conferida
- ZIP de origem: `ALPHAFEST_MANAGER_HF65.24.58_HOMOLOGACAO_REV2.zip`, recebido neste diálogo.
- Versão interna mantida: `20.4.9-I8.13.5-HF53.3-HF8-HF65.24.58`.
- Mudanças RC3: aceite de arte versionado por identidade da referência + histórico/arquivamento; revalidação da versão atual do projeto antes de registrar; preservação integral de instruções extensas na ficha TXT; documentação de homologação.
- A aplicação continua usando o mecanismo CAS existente para proteger a gravação do documento `projetos_db` no Supabase; em caso de conflito de edição, não há confirmação de salvamento.

## Testes executados
- **64 testes selecionados em 3 módulos** (`test_ficha_producao_hf58`, `test_proposal_draft_hf57`, `test_roteiro_producao_hf51`): **64 aprovados, 0 falhas, 0 ignorados**.
- Desses, **11 são específicos da ficha e aprovação HF58**. Cobrem nova arte, substituição por URL/nome com mesmo ID, registros antigos, invalidação por arquivamento, token de interface, checagem da versão fresca, personalizações e observações extensas.
- Compilação com `py_compile` de `app.py`, `ficha_producao_hf58.py` e teste específico: **aprovada**.
- Regressão ampla real `python -m unittest discover -p 'test_*.py' -q`: **427 testes, 93 ignorados e quatro erros de importação** (`test_proposal_draft_integration_hf57`, `test_proposal_duplicate_integration_hf55`, `test_site_integrity_hf53`, `test_site_quote_import_integration_hf54`) por ausência do pacote `streamlit`. **Não passou**, não conta como homologação integral.
- Tentativa de instalar o Streamlit pelo gerenciador de pacotes: **indisponível por falha de resolução de DNS**. Uma tentativa adicional com substituto temporário apenas para importação não concluiu dentro do limite; esse substituto **não está no ZIP** e não comprova compatibilidade com Streamlit.
- ZIP: conferência integral de CRC, hash SHA-256 por arquivo, versões e política de exclusão de dados operacionais, a ser registrada no manifesto do pacote RC3.

## Limitações de segurança/escopo
- A assinatura da arte protege os **metadados registrados** (ID, nome, URL, criação, categoria); não verifica uma troca silenciosa dos bytes em um armazenamento remoto sem alteração desses campos.
- O aceite é um **registro operacional manual**: depende da confirmação humana do cliente e não substitui comprovante de concordância, aprovação comercial ou a liberação de produção.
- O arquivo TXT é **interno**, contém dados do pedido e não deve ser compartilhado publicamente sem revisão.
- Não há alteração de banco/SQL, dependências, cadastro de clientes ou site público nesta RC3.

## Homologação obrigatória para liberação final
1. Em **ambiente separado e com dados fictícios**, instalar `requirements.txt` e executar toda a regressão e o gate crítico oficial (`python build_update_package.py --root . --output ../HF58_VALIDADO_TESTE.zip --release-note UPDATE_INFO_HF65.24.58.md`). Não ignorar falhas/skips críticos.
2. Abrir a **Caixa do Projeto** de uma proposta fictícia, com dois itens e personalizações diferentes; conferir a ficha TXT inteira, incluindo textos longos.
3. Enviar **arte v1**; confirmar com responsável; baixar a ficha, conferir versão, data e status.
4. Enviar **arte v2**; confirmar que v1 perdeu a validade e que o checkbox aparece **desmarcado**, mesmo se o ID do registro de arte for mantido e o nome ou URL for alterado.
5. Arquivar ou substituir arte; verificar que a ficha acusa revisão pendente ou ausência de arte e não descreve arquivo antigo como aprovado.
6. Testar em **Jorge e Anna** e com duas sessões: salvar uma alteração do projeto em outra sessão e verificar que o aceite antigo não sobrescreve essa alteração.
7. Conferir falha de rede/gravação: nenhuma mensagem de sucesso quando não houve persistência.
8. Confirmar que gerar ou baixar a ficha não altera proposta, status do Fluxo ou estoque.
9. Registrar os resultados com screenshots e o relatório do gate antes de converter esta RC3 em release de produção.

> Até esses passos terminarem, manter em produção a última versão estável já instalada. Não copiar este ZIP sobre o repositório ativo.
