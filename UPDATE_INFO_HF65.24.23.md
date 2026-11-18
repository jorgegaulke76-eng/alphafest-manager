# AlphaFest Manager HF65.24.23 — Carrinho de Orçamento WhatsApp

## Arquivos alterados
- `site_carrinho_orcamento_service.py` (novo): interface isolada e responsiva, armazenamento local, edição de itens e preparação da mensagem.
- `site_completo_service.py`: chama a injeção do carrinho após o mural e antes do rastreamento.
- `VERSAO`, `VERSAO.txt`, `RELEASE_INFO.json`: versão e data do pacote.

## Como testar
1. Atualizar somente os arquivos citados no repositório e fazer Commit/Push; manter Secrets intactos.
2. No Manager, Central do Site -> preparar prévia. Abrir a ficha de um produto e clicar em `Adicionar ao orçamento`.
3. Adicionar outro produto, editar quantidades e observações, remover algum item e revisar a mensagem.
4. Confirmar que WhatsApp abre com **uma única mensagem** contendo todos os itens, mas não envia automaticamente.
5. Testar o CTA individual anterior e navegação para Galeria/Dicas/Novidades.
6. Publicar pelo Cloudflare **somente depois** de conferir a prévia.

## Limites
- Não é checkout nem pagamento online. A AlphaFest confirma preço, prazo e disponibilidade.
- Itens são salvos apenas no navegador do visitante; não há backend nem dados pessoais no Supabase.
- Máximo de 25 produtos distintos e 999 unidades por produto.
- A seleção permanece no mesmo navegador enquanto o armazenamento local existir.
- Sem alterações nos registros do catálogo ou do Supabase.
