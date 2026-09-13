# AlphaFest Manager — HF63

## Correção — Editar cliente abre diretamente

Correção isolada em **Relacionamentos**, baseada na HF62.

### Problema corrigido
- o botão **✏️ Editar cliente** selecionava corretamente o cliente, porém após o rerun o Streamlit voltava visualmente para a aba **Consultar relacionamentos**;
- isso dava a impressão de que a edição não havia aberto.

### Novo comportamento
- ao clicar em **✏️ Editar cliente**, a tela reabre automaticamente com **✏️ Editar cliente** como primeira aba ativa;
- o cadastro completo do cliente já aparece preenchido;
- o bloco **💼 Perfil Comercial do Cliente · HF62** fica acessível imediatamente para marcar **Fechamento periódico** e escolher **Semanal / Quinzenal / Mensal**;
- ao salvar ou cancelar, a tela volta para a consulta normal.

### Preservado
- HF62 — clientes recorrentes e fechamento periódico;
- HF61 — categorias rápidas;
- HF60 — publicação Cloudflare;
- HF59/HF58/HF57/HF56/HF55 e regras homologadas anteriores;
- Template Mestre Comercial HF7 e Template Anna.

Sem migração de banco e sem alteração nas regras de negócio.
