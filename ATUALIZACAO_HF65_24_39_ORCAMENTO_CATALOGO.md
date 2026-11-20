# HF65.24.39 — Orçamentos × Catálogo Oficial

- Central de pedidos: itens orçados sem correspondência segura no Catálogo exibidos por recorrência (número de propostas distintas), abrangendo orçamentos e pedidos não encerrados.
- Botão de conferência/cadastro assistido. O cadastro **não é obrigatório** para avançar com produção sob encomenda.
- No formulário de cadastro, consulta por nome oficial e aliases existentes; sugestões semelhantes aparecem apenas para revisão, nunca geram vinculação automática.
- Ao salvar produto, impede duplicar nome/alias existente. Preserva aprovação manual, financeiro, status, prazos, dados antigos, site e Supabase.
- Sem publicação Cloudflare e sem mudanças em Secrets.

## Testes depois da instalação
1. Abrir Central e verificar "Orçamento × Catálogo".
2. Conferir que item recorrente mostra o número de propostas, sem multiplicar por quantidade.
3. Clicar "Conferir / cadastrar" e testar nome já existente ou alias — deve impedir duplicata.
4. Verificar que pedidos Aprovados continuam podendo avançar para Pronto sem estoque.
