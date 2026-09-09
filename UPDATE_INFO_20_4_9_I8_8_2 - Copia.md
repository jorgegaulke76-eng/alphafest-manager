# 20.4.9-I8.8.2 — Prévia Interna do Catálogo

Base exclusiva: 20.4.9-I8.8.1 homologada.

## Objetivo
Permitir conferir o catálogo dentro do AlphaFest Manager antes de baixar, gerar novamente ou salvar alterações, usando exatamente o mesmo HTML da saída final.

## Entrega
- Nova área `👀 Prévia interna I8.8.2` no Gerador I8.7.1.
- Visualização `📱 Celular`, em largura reduzida para acionar os breakpoints responsivos reais do catálogo.
- Visualização `🖥️ Computador` em largura ampla.
- Na Central, `👁️ Abrir / prévia` exibe a geração atual do catálogo salvo usando os dados atuais do Catálogo Oficial.
- No editor da Central, a prévia reflete título, subtítulo, produtos, preço, descrição, material, WhatsApp, produtos sem foto e rodapé **antes** de salvar as alterações.
- A prévia fica recolhida por padrão para não pesar a interface.

## Regra arquitetural preservada
A prévia não salva snapshot comercial, não duplica produto e não altera preço, foto, descrição, material, campanha ou saneamento. Ela renderiza o mesmo HTML que será exportado a partir dos dados atuais do Catálogo Oficial.

## Sem regressão
Gerador I8.7.1, Central I8.8.1, Lixeira da Central, Cadastro, Produtos, Saneamento, Acervo histórico e Catálogo para cliente permanecem preservados.
