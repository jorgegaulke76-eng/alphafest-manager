# HF65.24.58 — revisão de homologação RC2 (25/11/2026)

**Status: SOMENTE HOMOLOGAÇÃO. Não liberar como atualização definitiva sem regressão completa e testes no Manager com banco de teste.**

## Verificações realizadas neste ambiente
- 61 testes selecionados de ficha de produção, rascunhos e roteiro: aprovados, 0 ignorados.
- `python -m py_compile app.py ficha_producao_hf58.py`: aprovado.
- Conferência de integridade e hashes de todos os arquivos do ZIP: aprovada.
- A execução ampla de `python -m unittest discover -p 'test_*.py' -q` encontrou 422 testes, 93 ignorados e 4 falhas de importação por falta de `streamlit`; **não constitui aprovação da regressão completa**.
- A tentativa de instalar Streamlit neste ambiente falhou por falta de acesso ao repositório de pacotes.

## Proteções acrescentadas na revisão RC2
- A aprovação é invalidada se o nome, URL, categoria ou metadados de criação do arquivo aprovado forem alterados, mesmo quando o identificador permanece igual.
- Um registro anterior sem assinatura de arquivo exige nova confirmação, de forma conservadora.
- A marcação de confirmação na interface usa a identidade da arte mais recente para não reaproveitar o aceite visual de outra arte.

## Roteiro de homologação em ambiente de testes
1. Preparar ponto de restauração e usar dados fictícios ou cópia autorizada da base.
2. Abrir Caixa do Projeto de um pedido com dois itens e personalizações distintas.
3. Enviar arte v1. Registrar a confirmação e baixar ficha TXT; conferir nome, ID, cliente, entrega e itens.
4. Enviar arte v2. Verificar que a aprovação anterior ficou pendente e que a ficha não mostra v1 como aprovada.
5. Confirmar v2 conscientemente, conferir responsável e data.
6. Alterar/arquivar a arte, verificar a invalidação e testar upload de novo arquivo.
7. Conferir permissões de Jorge/Anna e se falhas de gravação mantêm dados sem sucesso falso.
8. Confirmar que a ficha não altera status comercial ou produtivo, e que o conteúdo do TXT está completo.
9. Executar o gate integral após instalar `requirements.txt` em ambiente compatível e registrar relatório sem falhas nem skips críticos.

## Critério de liberação
Somente publicar como release final depois de concluir os passos acima e obter gate completo aprovado; este ZIP tem manifesto identificado como `HOMOLOGACAO_PARCIAL` para evitar confusão com pacote final.
