# HF53.3-HF5-HF1 — Catálogo • Fotos sempre editáveis

Hotfix isolado do Catálogo. O Alpha Marketing e o Template Anna HF53.3-HF5 permanecem sem alteração visual.

## Correção
- Fotos do produto podem ser removidas, substituídas e adicionadas novamente a qualquer momento.
- Foto remota marcada para remoção não volta pelo campo `URLs de fotos`, mesmo quando o Streamlit ainda tinha o valor antigo no estado do widget.
- Apagar manualmente uma URL da lista também remove a referência do cadastro.
- Foto principal removida não é reinserida; a primeira foto restante ou nova assume automaticamente.
- `Substituir TODAS as fotos atuais pelas novas` ignora integralmente a galeria antiga.
- Após salvar/cancelar, o estado dos widgets de mídia é limpo, inclusive checkboxes indexados de remoção, evitando que URL/cache visual antigo reapareça ao reabrir o mesmo produto.

## Regra permanente
A galeria do Catálogo permanece aberta à manutenção contínua: atualizar fotos não exige recriar o produto.

## Segurança
- Limite de 5 mídias preservado.
- Vídeo continua tratado separadamente.
- Site, Alpha Marketing, Template Mestre HF7 e Template Anna não foram alterados por este hotfix.
