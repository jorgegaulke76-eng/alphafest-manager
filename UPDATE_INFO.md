# AlphaFest Manager — HF65

## Campanha Destaque reutilizável no site

Atualização isolada sobre a HF64 para permitir ações temporárias no site sem alterar a estrutura homologada da vitrine.

### O que foi adicionado
- bloco **Campanha Destaque** dentro de **Site AlphaFest** no Manager;
- chave **Exibir campanha no site** para habilitar/desabilitar;
- arte do **Dia do Cliente 2026** já incluída no pacote, sem depender de serviço externo;
- opção de enviar uma arte personalizada para campanhas futuras;
- entrada animada do **Thu** e da **Fox** nas laterais;
- atraso configurável de 1, 2 ou 3 segundos;
- permanência configurável de 8, 9 ou 10 segundos;
- botão **X** para fechar antes;
- opção de mostrar apenas uma vez por visita/sessão;
- período automático opcional, com data inicial e final;
- CTA opcional para **WhatsApp**, **link personalizado** ou **sem botão**;
- prévia e publicação continuam usando o fluxo seguro já existente do Site AlphaFest;
- comportamento responsivo no celular e respeito a preferência de movimento reduzido.

### Segurança operacional
- a campanha inicia **desativada** após instalar a HF65;
- nenhuma campanha é publicada automaticamente pela atualização;
- para aparecer no site, é necessário habilitar, salvar, gerar a prévia e publicar;
- a configuração da campanha entra no backup do Manager;
- nenhum JSON de dados da empresa é incluído no ZIP de atualização;
- não há migração de banco nem alteração nas regras comerciais/produção/estoque.

### Caminho rápido
**Site AlphaFest → Campanha Destaque → habilitar → salvar → preparar/atualizar prévia → publicar**

### Preservado
- HF64 e todas as correções anteriores;
- publicação Cloudflare já homologada;
- Catálogo, Galeria, Métricas e busca do site;
- Template Mestre Comercial HF7 e Template Anna.
