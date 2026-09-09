# 20.4.9-I8 — THU Acervo Inteligente de Catálogos Históricos

Base: Atual 2049I7 aprovada.

## Objetivo
Transformar os catálogos antigos da AlphaFest em um acervo estruturado e revisável dentro do padrão atual do AlphaFest Manager.

O PDF antigo é fonte histórica. O Catálogo Oficial continua sendo a única fonte oficial de produto, preço e elegibilidade.

## Acervo incluído
Foram preservados 13 catálogos históricos, totalizando 236 páginas.

Cada página possui:
- pré-visualização leve da página original;
- texto extraído;
- valores históricos detectados;
- observações antigas de quantidade mínima;
- materiais/medidas/opções identificados;
- produtos candidatos;
- campanha/ocasião sugerida pela origem;
- referência do catálogo e página.

As páginas foram convertidas em prévias leves para evitar incorporar cerca de centenas de MB de PDFs ao pacote operacional.

## Regra oficial: sem quantidade mínima
A AlphaFest atual atende conforme a necessidade do cliente, de 1 unidade a grandes quantidades.

Qualquer `pedido mínimo` encontrado nos PDFs:
- é preservado somente como informação histórica da fonte;
- não cria campo comercial atual;
- não bloqueia orçamento;
- não altera o Catálogo Oficial;
- aparece com aviso de que a regra foi descontinuada.

## Regra oficial: preços antigos
Todo preço encontrado nos PDFs é tratado como `Preço histórico`.

O sistema:
- nunca preenche `Preco` automaticamente com valor antigo;
- nunca substitui o preço atual;
- mostra validade histórica quando conhecida;
- preserva a referência para comparação/revisão.

Em páginas com vários produtos, valores da página não são atribuídos automaticamente a um produto específico.

## Novo campo oficial: Variações
O Catálogo passa a aceitar `Variacoes`.

Exemplos: 240 ml, 300 ml, 500 ml, Redonda, Liso, Jateado e Bicolor.

O campo foi integrado em cadastro rápido da Anna, cadastro principal, edição, busca, visualização e catálogo para cliente.

## Nova área
Catálogo > `📚 Acervo histórico`

A área mostra:
- quantidade de catálogos;
- páginas preservadas;
- páginas revisadas;
- páginas em revisão/cadastro;
- filtro por catálogo e texto;
- filtro por status;
- preview da página;
- texto completo extraído;
- valores históricos;
- aviso de mínimos antigos;
- materiais/opções identificados;
- produtos/serviços identificados;
- possíveis correspondências no Catálogo Oficial.

## Revisar produto existente
Ao encontrar um produto já cadastrado, o THU permite revisar individualmente alias, descrição, material, variações e campanha elegível.

Nada é aplicado sem confirmação. O preço oficial é sempre preservado.

A origem fica registrada em `FontesHistoricasCatalogos`, `PrecosHistoricosCatalogos` quando a página é de produto único, e `HistoricoEnriquecimentoCatalogos`.

## Preparar produto novo
Quando o item ainda não existe:
- o THU prepara o formulário oficial do Catálogo;
- nome/categoria/descrição/material/variações seguros podem ser pré-preenchidos;
- preço oficial fica vazio;
- preço antigo aparece somente como referência;
- campanha histórica aparece apenas como sugestão;
- `CampanhasPermitidas` não é marcada automaticamente.

Em páginas multiproduto, descrição/material/variações não são pré-preenchidos automaticamente para evitar associar conteúdo ao item errado.

## Anti-duplicação
Quando o produto já existe por nome oficial ou alias, o fluxo de novo cadastro é bloqueado e o usuário é direcionado para revisar o cadastro existente.

## Elegibilidade de campanhas
Catálogos temáticos são evidência histórica de associação. Incluem Outubro Rosa, Novembro Azul, Setembro Amarelo, Natal, Dia das Crianças, Dia dos Professores, Volta às Aulas, Nascimento, Batizado, Crisma e 1ª Comunhão.

A campanha nunca entra em `CampanhasPermitidas` sem confirmação humana.

## Páginas multiproduto
Uma página pode conter vários produtos. Vincular um produto deixa a página como `Em revisão`. A página só vira `Revisada` quando o operador confirma explicitamente que terminou de tratar todos os itens.

Também existe `Página institucional / sem produto`.

## Curadoria visual
Páginas cuja extração textual não descrevia bem os produtos receberam curadoria visual de nomes de itens, especialmente Catálogo COPOS, Outubro Rosa, Novembro Azul, Setembro Amarelo e Lembranças Natal.

A página original permanece visível ao lado da informação estruturada para conferência.

## Rastreabilidade
Cada vínculo guarda catálogo, arquivo de origem, hash SHA-256, página, preview, trecho do texto, preços históricos, validade histórica, mínimos antigos ignorados, materiais/variações detectados, campanha sugerida, usuário, data/hora e regras aplicadas.

## Segurança
- Catálogo Oficial continua sendo a fonte de verdade;
- nenhum preço antigo vira preço atual automaticamente;
- nenhum mínimo antigo vira regra;
- nenhuma campanha é habilitada automaticamente;
- páginas multiproduto não distribuem preço/material/variação sem confirmação;
- produto já existente não é duplicado;
- toda alteração relevante possui fonte histórica rastreável.
