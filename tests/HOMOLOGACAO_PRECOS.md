# Homologação das modalidades de preço — AlphaFest

## Resultado até aqui
- [x] 17 testes automatizados aprovados no GitHub Actions
- [x] Vitrine: preço fixo, a partir de e sob orçamento
- [x] Segurança: sem vazamento de preço interno para sob orçamento
- [x] Compatibilidade com produtos legados
- [x] Cadastro e edição fictícios salvos em arquivo temporário
- [ ] **Pendente**: fluxo completo do formulário **oficial** em ambiente isolado

## Limites dos testes já feitos
Os testes de interface usam `tests/demo_cadastro_preco_isolado.py`, não
`formulario_catalogo` de `app.py`. Os testes de persistência usam JSON local,
não a função real de gravação em `cloud_db.py`. Eles **não demonstram**
que a gravação do Manager oficial está pronta.

## Critérios obrigatórios para liberar
1. Criar ambiente de testes separado, sem credenciais nem dados de produção.
2. Exercitar `formulario_catalogo` com cadastro fictício e edição do mesmo item.
3. Reabrir o item e confirmar `ModalidadePrecoSite`, `ExibirPrecoSite` e `Preco`.
4. Exercitar edição rápida, reabrir e verificar as mesmas propriedades.
5. Verificar cancelamento, falha de gravação, ausência de preço e produto legado.
6. Gerar HTML do site somente com itens fictícios para as três modalidades.
7. Conferir como a implantação do Manager e a publicação do site são disparadas
   antes de mesclar `main`; ter procedimento de reversão documentado.
8. Revisar se preço público representa oferta real (especialmente `a_partir`).

## Restrições
Não usar a instância de produção do Supabase para estes testes.
Não copiar dados reais de clientes, pedidos, produtos ou credenciais.
Não mesclar nem publicar o PR antes dos critérios obrigatórios.
