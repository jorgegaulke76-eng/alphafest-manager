# 20.4.9-I8.13.5-HF35 — Central do Site AlphaFest

## Objetivo
Incorporar a gestão do site ao AlphaFest Manager sem criar um cadastro paralelo e sem alterar o site público atual antes da aprovação.

## O que muda
- Novo módulo **🌐 Site AlphaFest** no grupo Marketing.
- Acesso para Jorge e Anna, inclusive quando a configuração de usuários veio de uma base antiga.
- Leitura direta do Catálogo oficial para:
  - produtos ativos;
  - produtos marcados em `PublicarSite`;
  - destaques;
  - prontidão de foto e descrição;
  - preço quando cadastrado ou indicação de valor sob consulta;
  - prévia interna da futura vitrine.
- Produtos prontos, mas ainda não marcados para o site, aparecem como candidatos e podem ser abertos diretamente no Catálogo para decisão.
- O mecanismo existente de análise do site legado foi reaproveitado; o último scan continua salvo no mesmo documento de Marketing.

## Regras de segurança e Fonte Única
- Nenhum produto é copiado para um banco de site.
- Nenhum item é marcado ou desmarcado automaticamente para publicação.
- Nenhuma página do site atual é alterada pela HF35.
- A análise externa só ocorre quando o usuário clica em **Analisar site atual agora**, evitando custo no carregamento normal.
- Jorge e Anna enxergam a mesma leitura porque ambos consultam o mesmo Catálogo.

## Próxima etapa
Depois da homologação da Central, gerar a nova vitrine pública usando apenas os produtos aprovados nesta Fonte Única e submeter a prévia à aprovação antes de qualquer migração de domínio.
