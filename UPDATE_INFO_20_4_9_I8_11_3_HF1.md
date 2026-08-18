# 20.4.9-I8.11.3-HF1 — Ações do Jorge + formatação da prévia

Hotfix sobre a I8.11.3 homologando as regras de permissão e corrigindo a apresentação monetária dos itens.

## Correções
- Corrigida a linha `Quantidade × Valor unitário = Total` para impedir que `R$` seja interpretado como sintaxe matemática/Markdown e gere caracteres ou estilos diferentes.
- Restauradas, no perfil Jorge, as ações logo após salvar uma proposta: **Editar proposta**, **Duplicar pedido** e **Excluir proposta**.
- No Histórico, **Excluir** passa a ser exibido somente para Jorge.
- A função de exclusão possui trava interna: mesmo que seja chamada por outro caminho, somente o perfil Jorge consegue remover a proposta.
- Perfil Anna permanece sem permissão de exclusão; suas ações operacionais continuam preservadas.

## Preservado
- Campo Evento e sua propagação para WhatsApp/HTML/PDF/Histórico.
- Prévia em tempo real de quantidade × valor e total projetado da proposta.
- Preços especiais e abatimentos fixos do Perfil Comercial.
- Fonte única de status, Radar HF4, Resumo Mensal e demais regras homologadas.
