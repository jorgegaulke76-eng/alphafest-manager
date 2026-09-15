# AlphaFest Manager — HF65.1

## Correção do upload de arte personalizada na Campanha Destaque

Correção isolada sobre a HF65 já homologada no site.

### Corrigido
- ao selecionar **Usar arte personalizada**, o campo **Enviar nova arte (PNG, JPG ou WEBP)** agora aparece imediatamente;
- o seletor de arte foi retirado de dentro do formulário do Streamlit, evitando a necessidade de salvar antes de o upload aparecer;
- prévia da nova arte aparece assim que o arquivo é escolhido;
- se já existir uma arte personalizada e nenhum arquivo novo for escolhido, a arte atual é preservada.

### Preservado
- campanha atual do Dia do Cliente e sua configuração salva;
- Thu + Fox, tempo, período, CTA e regra de uma vez por visita;
- publicação Cloudflare e toda a base HF64/HF65;
- Catálogo, Galeria, Métricas e busca;
- Template Mestre Comercial HF7 e Template Anna.

### Segurança
- não inclui JSON de dados da empresa;
- não altera banco de dados nem configurações já salvas;
- atualização apenas de código/interface.
