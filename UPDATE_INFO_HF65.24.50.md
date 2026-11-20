# AlphaFest Manager — HF65.24.50 · Otimização e Organização

## O que mudou

- Na **Central**, o modo sob encomenda não executa mais a análise da fila antiga de reserva/liberação de materiais. A operação continua orientada por status e prazos.
- A seção **Orçamento × Catálogo** agora é aberta pelo controle **Revisar Orçamento × Catálogo**. **Somente ao abrir** são carregados o catálogo e as correspondências dos itens dos orçamentos. Busca, filtros, paginação, cadastro assistido e vínculos permanecem.
- A opção de **restaurar backup** na barra lateral agora fica recolhida por padrão e exige confirmação explícita antes da ação. A ferramenta e os backups para download foram preservados.
- Nenhum dado do Supabase, pedido, status, pagamento, estoque histórico, integração de WhatsApp ou site foi modificado.

## Validação

Compilação Python; testes da camada de fluxo sob encomenda e navegação; guarda dos custos de revisão e de reserva; verificação estrutural e integridade do ZIP.

## Publicação

Somente Manager (GitHub Desktop Commit + Push). Não há necessidade de republicar o site no Cloudflare, nem de alterar Secrets/Supabase.
