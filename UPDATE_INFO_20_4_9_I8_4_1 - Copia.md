# 20.4.9-I8.4.1 — Hotfix Boot Seguro

Base: 20.4.9-I8.4.

## Motivo
Após a I8.4 o Streamlit Cloud passou a apresentar falha durante a inicialização do manager.
Para eliminar qualquer risco de auditoria/escrita de imagens durante renderização, a rotina automática foi removida.

## Mudança
- nenhuma auditoria de foto roda automaticamente ao abrir Central da Anna;
- nenhuma auditoria roda automaticamente ao abrir Catálogo;
- o helper de compatibilidade passou a ser no-op;
- `Auditar e reparar fotos do Catálogo` continua disponível somente sob clique;
- a auditoria manual agora possui `try/except` e não pode derrubar o restante do Manager;
- fotos já recuperadas no banco continuam preservadas.

## Segurança
O hotfix não altera produto, preço, descrição, material, campanha, aliases, pedidos ou histórico.
