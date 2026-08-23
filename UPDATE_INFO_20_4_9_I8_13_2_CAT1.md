# 20.4.9-I8.13.2-CAT1 — Catálogo Legado Kit Festa / Linha de Alto Giro

Base: 20.4.9-I8.13.2-HF2

## Objetivo
Incorporar ao Acervo Inteligente o catálogo `Catálogo Kit Festa Personalizados 2026 - 2semestre.pdf`, preservando imagens, descrições, composições e preços históricos, sem sobrescrever o Catálogo Oficial e sem transformar preços antigos em preços atuais.

## Entregue
- Novo acervo `Kit Festa Personalizados • 2026 2º semestre`, com 11 páginas preservadas visualmente.
- 10 kits curados como produtos de alto giro:
  - Kit Festa Prática
  - Kit Festa Rápida
  - Kit Festa Mini
  - Kit Festinha
  - Kit Mesversário
  - Kit Festa Super
  - Kit Festa Mini Plus
  - Kit Festa Top
  - Kit Festa Bolinho
  - Kit Festa Super Top
- Composição de cada kit estruturada item a item.
- O cadastro preparado a partir do Acervo recebe a composição do kit como dado estrutural (`KitComposto` / `ComposicaoKit`).
- A linha recebe marca interna de alto giro (`LinhaAltoGiro` / `PrioridadeComercial=Alta`).
- Página do Acervo destaca a linha de alto giro e mostra a composição antes do cadastro.
- O botão de cadastro passa a exibir `Preparar kit` para páginas compostas.
- Produtos salvos a partir desta fonte exibem a composição na lista do Catálogo.
- Preços do PDF permanecem somente em histórico. Campo `Preco` oficial continua dependente de revisão humana.
- Nenhum componente do kit é criado automaticamente como produto novo; vínculos e saneamento continuam conservadores.

## Regras preservadas
- Catálogo Oficial continua sendo a fonte única de produto/preço atual.
- Nenhum preço histórico substitui o preço oficial automaticamente.
- Nenhuma quantidade mínima antiga vira regra.
- Nenhuma reserva/baixa de estoque é criada pela importação do catálogo.
- I8.13.2-HF2 (Ficha Técnica opcional/consumo por pedido) permanece inalterada.
