# 20.4.9-I8.13.5-HF23 — Catálogo 3D do Jorge

Base funcional: **HF22 homologada**.

## Objetivo
Aproveitar a Biblioteca 3D já homologada como fonte única e acrescentar a geração de catálogo para apresentar os modelos aos clientes sem expor os arquivos de produção.

## Mudanças
- A aba do Jorge passa a se chamar **🧊 Catálogo 3D**.
- O acervo privado continua exatamente no mesmo `biblioteca_3d_db` e no bucket privado `biblioteca3d`; não há duplicação dos modelos.
- Novo gerador **📤 Gerar Catálogo 3D**.
- Permite selecionar todos ou somente alguns modelos.
- Título e subtítulo são editáveis.
- Prévia interna reutiliza a mesma sistemática responsiva do gerador de Catálogos da AlphaFest (celular/computador).
- Saída em HTML autocontido para envio/consulta do cliente.
- Cada modelo publica somente **nome, descrição, tempo de impressão e 1 imagem**.
- Preço não é exibido.
- O botão de consulta pelo WhatsApp pode ser habilitado/desabilitado.
- **Arquivo 3D, nome do arquivo, tamanho e caminho privado nunca entram no catálogo gerado.**

## Segurança e compatibilidade
- O arquivo 3D continua disponível apenas dentro do perfil Jorge para recuperação/download.
- Anna continua sem acesso à aba.
- Nenhum status de pedido, Agenda, THU, Orçamento ou Catálogo Oficial foi alterado.
- Nenhum JSON/SQL operacional novo é criado nesta HF.
