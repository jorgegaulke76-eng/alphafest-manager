# 20.4.9-H2.1 — Hotfix Cadastro em Modal

Base: 20.4.9-H2.

## Correção
O botão `Criar produto oficial` não navegava corretamente para o cadastro.

Agora:
- o botão abre diretamente uma janela/modal de cadastro;
- o nome sugerido já vem preenchido;
- categoria, material, valor, campanhas, descrição, aliases e imagens continuam editáveis;
- ao salvar, a janela fecha;
- o usuário permanece em Relatórios;
- a área de Padronização volta aberta;
- a equivalência continua dependendo do clique manual em `Confirmar equivalência`.

## Segurança
- nenhum produto é criado sem o clique em Salvar;
- nenhum alias é confirmado automaticamente;
- nenhuma proposta histórica é alterada;
- estados antigos da rota H2 foram neutralizados para evitar redirecionamentos inesperados.
