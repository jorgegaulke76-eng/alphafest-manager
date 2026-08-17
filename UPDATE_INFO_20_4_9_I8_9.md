# 20.4.9-I8.9 — Compartilhamento Profissional

Base exclusiva: 20.4.9-I8.8.4 homologada.

## Objetivo
Transformar o catálogo homologado em uma saída comercial pronta para envio, mantendo governança, validade e uma única fonte de verdade.

## Link público
- O link público é criado somente a partir de um catálogo salvo na Central.
- Cada publicação gera uma URL própria e imutável no bucket público `catalogo` do Supabase.
- Uma nova publicação não sobrescreve a anterior; cada arquivo mantém a data, responsável e validade da geração correspondente.
- A Central salva apenas URL, caminho do objeto e metadados de geração; não salva snapshot de preço, foto, descrição ou material no banco operacional.

## QR Code
- Gerado localmente pelo AlphaFest Manager a partir da URL pública.
- Pode ser visualizado e baixado em PNG.
- O HTML público inclui o QR Code e o endereço online no rodapé.

## WhatsApp
- Campo opcional para informar o número do cliente.
- Se o número ficar vazio, o WhatsApp abre para escolha do contato.
- A mensagem inclui link, data da geração e validade.
- Catálogo comercialmente vencido não oferece o botão de envio; o sistema pede nova publicação.

## PDF / impressão
- PDF comercial preparado sob demanda para evitar lentidão nos reruns do Streamlit.
- Rodapé em todas as páginas com data, usuário, validade e número da página.
- Quando existe link público, o PDF inclui QR Code e URL.
- O HTML também possui botão `Imprimir / Salvar PDF`, permitindo preservar o layout web pelo navegador.

## Segurança e arquitetura
- Publicar gera um artefato comercial estático, mas não cria uma segunda fonte de dados dentro do AlphaFest Manager.
- Ao publicar nova versão, produtos e valores são consultados novamente do Catálogo Oficial.
- A publicação renova a validade de 30 dias e registra auditoria.
- Anna e Jorge podem usar o compartilhamento; as proteções já existentes da I8.8.4 permanecem.
- Se o Supabase online não estiver configurado, HTML e PDF continuam funcionando; somente a publicação de link público fica indisponível.

## Dependências
- `qrcode[pil]` para QR Code.
- `reportlab` para PDF comercial.
