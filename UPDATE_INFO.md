# AlphaFest Manager — HF64

## Correção — Fechamentos Recorrentes visíveis na operação

Correção isolada sobre a HF63.

### Problema corrigido
O módulo HF62 existia no código, porém estava liberado apenas para o perfil Jorge. No perfil operacional/Anna, a navegação principal também é propositalmente mais enxuta, então **Fechamentos Recorrentes não aparecia** para uso diário.

### Novo comportamento
- **Relacionamentos** passa a mostrar no topo o botão **💳 Fechamentos Recorrentes**;
- o perfil Anna/operacional passa a ter acesso ao módulo;
- bases antigas de permissões são corrigidas em runtime, sem exigir alteração manual de usuários;
- a tela permite a rotina já definida no HF62: Semanal, Quinzenal e Mensal, boletim, WhatsApp, PDF e registro de recebimento;
- Jorge continua com acesso normalmente.

### Caminho rápido
**Relacionamentos → 💳 Fechamentos Recorrentes**

### Preservado
- HF63 — edição de cliente;
- HF62 — regras e documentos de fechamento periódico;
- HF61 a HF55 e base homologada anterior;
- Template Mestre Comercial HF7 e Template Anna.

Sem migração de banco e sem alteração nas regras de negócio.
