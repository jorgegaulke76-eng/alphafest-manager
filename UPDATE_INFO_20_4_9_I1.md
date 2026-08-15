# 20.4.9-I1 — THU alerta produto sem Catálogo na proposta

Base: 20.4.9-I.

## Comportamento
- após a proposta ser salva, o THU verifica todos os itens pelo nome oficial + aliases do Catálogo;
- se existir item sem cadastro oficial, a Anna recebe um aviso em destaque;
- o aviso permanece nas propostas da Central da Anna enquanto o produto continuar sem cadastro;
- quando o produto passa a existir no Catálogo (nome oficial ou alias), o aviso desaparece automaticamente;
- produtos repetidos na mesma proposta aparecem uma única vez;
- o botão `Cadastrar no Catálogo` abre o cadastro com o nome do produto já preenchido;
- se houver mais de um produto ausente, cada um pode ser cadastrado individualmente.

## Precisão
O sistema não afirma que o WhatsApp foi entregue/enviado, porque isso acontece fora do Streamlit.
O gatilho confiável é a proposta salva no sistema.

## Extra
Corrigido o texto visual `QUI` para `THU` nos avisos de campanha.

## Segurança
Nenhuma proposta antiga é alterada.
Nenhum produto é criado automaticamente.
O alerta é calculado dinamicamente a partir do Catálogo atual.
