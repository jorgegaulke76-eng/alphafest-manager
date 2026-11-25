# AlphaFest Manager — HF65.24.52 · Site final integrado

## Origem da atualização

Base: ALPHAFEST_MANAGER_HF65.24.51_ROTEIROS_PRODUCAO.zip, informado como a versão em uso.
Referência visual: alphafest_HF65.24.52_previa_validada.zip.
Versão completa: 20.4.9-I8.13.5-HF53.3-HF8-HF65.24.52.

## O que mudou

- A ficha de produto incorpora os ajustes de celular da prévia validada: imagem em proporção 4:3, conteúdo em uma coluna, largura limitada à tela e botão de fechar acessível.
- O modal acompanha a área visível do navegador móvel. Ao voltar para uma largura de desktop, as dimensões móveis são removidas.
- Links com `?produto=slug-do-produto` abrem a ficha correspondente ao catálogo atual. Parâmetros inválidos e produtos inexistentes ou não publicados são ignorados.
- A entrada direta aguarda a inicialização da página e utiliza o mesmo caminho de abertura dos cartões, para manter o contexto de WhatsApp e o registro de visualização de produto já existentes.
- A prévia e o cache de produção passam a considerar a versão do Manager, evitando reutilizar HTML anterior após a atualização. Uma confirmação de publicação associada à prévia anterior também é descartada.
- O pacote passa a incluir RELEASE_INFO.json, necessário para exibir corretamente versão e data, e gera um UPDATE_MANIFEST.json novo com os hashes dos arquivos desta release.

## Conteúdo e operação

O site continua sendo gerado pelo Manager com o Catálogo, a Galeria, as campanhas e os conteúdos cadastrados. A atualização não transforma os produtos e as fotos da prévia em uma nova base fixa.

Não há migração de banco nem SQL novo. DATA_VERSION continua 5. Os módulos de pedidos, estoque, financeiro, permissões e os roteiros TXT/CSV da HF65.24.51 não foram modificados. O empacotador exclui dados operacionais e segredos; a exceção de JSON é restrita ao metadado RELEASE_INFO.json.

## Instalação do Manager

1. No Manager atual, use **Configurações → Núcleo Profissional → Atualização segura → Preparar atualização segura** e baixe o ponto de restauração.
2. Extraia o ZIP desta versão em uma pasta temporária.
3. Abra a pasta interna **alphafest-manager-main** e copie o conteúdo para a pasta do repositório já utilizado pelo Manager, a mesma que contém `app.py`. Substitua os arquivos correspondentes. Não crie uma segunda pasta `alphafest-manager-main` dentro do repositório e não apague a pasta existente antes de copiar. Os arquivos de dados/configuração já existentes permanecem no lugar.
4. No GitHub Desktop, confira as alterações, faça **Commit** e depois **Push** para o repositório/branch usados pelo aplicativo atual.
5. Aguarde a atualização do Streamlit. Confira no Manager a versão **HF65.24.52** e a data da release. Caso a sessão continue na versão anterior, reinicie o aplicativo pelo painel do Streamlit e abra novamente.

## Publicação do site

Depois de atualizar o Manager:

1. Abra a **Central do Site AlphaFest**.
2. Clique em **Preparar / atualizar prévia do site**. A prévia será gerada com os dados atuais.
3. Confira Desktop e Celular, abra um produto, feche a ficha e teste adicionar itens ao orçamento.
4. Marque a confirmação da prévia e clique em **Publicar site agora**, usando a conexão Cloudflare já configurada.
5. Confira o site no domínio habitual. Para testar a entrada direta, use o slug de um produto publicado após `?produto=`.

A alternativa já existente é **Contingência / ZIP manual → Baixar ZIP de produção**. Esse ZIP público é gerado pelo Manager atualizado. O arquivo ALPHAFEST_MANAGER_HF65.24.52_SITE_FINAL.zip desta entrega é a atualização do Manager e não deve ser enviado como pacote estático para o Cloudflare.

Atualizar o Manager e publicar o site são etapas distintas. A instalação do código não executa a publicação automaticamente.

## Verificação desta entrega

Os resultados finais de testes, geração e integridade estão documentados em VALIDACAO_HF65.24.52.md. A validação local utiliza fixtures de teste; a conferência final no Streamlit e a publicação usam os dados e as conexões do ambiente instalado.
