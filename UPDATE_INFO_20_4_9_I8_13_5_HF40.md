# AlphaFest Manager 20.4.9-I8.13.5-HF40

## Site completo em paralelo

A HF40 transforma a vitrine homologada em um site institucional completo, ainda em staging e sem alterar `alphafest.com.br`.

### O que foi acrescentado
- Navegação única: **Início · Produtos · Serviços · Quem Somos · Contato**.
- Mesma identidade visual aprovada na vitrine HF36–HF38, responsiva para desktop e celular.
- Produtos, imagens, destaques e regra de preço opcional continuam vindo do **Catálogo oficial do Manager**.
- Endereço, e-mail, celular e WhatsApp vêm da **configuração oficial da empresa no Manager**.
- `Quem Somos` foi reescrito a partir da essência institucional do site antigo, sem copiar o layout antigo.
- `Serviços` reorganiza a atuação atual da AlphaFest: personalizados, balões, gráfica rápida, brindes, convites/papelaria, impressão 3D, gravação a laser e kits/composição de festa.
- Fotos antigas do site legado **não são importadas automaticamente**.

### Staging
- O pacote continua sem `CNAME`, sem configuração de DNS e com `noindex`/`robots.txt` de homologação.
- A documentação do staging agora reflete o fluxo efetivamente homologado no Cloudflare: **Workers · Static Assets** com endereço temporário `*.workers.dev`.
- O projeto temporário pode ser atualizado por **New deployment / Upload static files**, mantendo o domínio oficial intacto.

### Fonte Única e segurança
- Nenhum banco paralelo de site foi criado.
- Nenhum pedido, estoque, cliente, produção ou status é alterado por esta versão.
- `alphafest.com.br` continua protegido até a virada manual final com backup/rollback de DNS.
