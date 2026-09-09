# 20.4.9-I2 — Auditoria de Cadastro + Banco de Imagens das Entregas

Base: Atual 2049I1 aprovada.

## 1. Auditoria pós-cadastro do produto
Depois que um produto é salvo ou atualizado, o THU confere:
- Nome;
- Categoria;
- Descrição;
- Material;
- Valor;
- Campanhas/Datas permitidas;
- Foto principal;
- alertas de dados antigos já detectados pelo auditor do Catálogo.

O painel mostra:
- status do cadastro;
- quantidade de fotos;
- quantidade de campanhas;
- aliases;
- checklist dos campos essenciais;
- campos faltantes;
- aviso quando o banco possui somente uma foto.

A auditoria aparece na Central da Anna, Catálogo e também no retorno para Relatórios quando o cadastro veio da padronização de nomes.

## 2. Sugestão de atualização do banco de imagens
Quando uma proposta é marcada como entregue, o THU sugere revisar as fotos daquele produto.
A sugestão continua disponível no Histórico se o pedido já estiver concluído.

Para cada produto oficial da entrega, a Anna pode:
- adicionar fotos como novas referências;
- colocar a primeira nova foto como foto principal;
- salvar as fotos como variação do produto;
- registrar que aquela entrega não trouxe imagem nova útil.

Existe campo opcional para registrar o que mudou:
- cor;
- estampa;
- composição;
- acessório;
- acabamento;
- qualquer outra variação relevante.

## 3. Regra de armazenamento
As fotos aprovadas usam o mesmo armazenamento do Catálogo.
Não foi criado um segundo banco paralelo de imagens.

O produto recebe histórico de atualização de imagens:
- origem da foto;
- proposta;
- ação;
- observação;
- data;
- usuário.

Variações também ficam registradas em `VariacoesImagem`.

## 4. Comportamento contínuo
A revisão é registrada por proposta + produto.
Assim:
- a mesma entrega não fica cobrando revisão depois de concluída;
- uma nova entrega futura do mesmo produto volta a sugerir atualização do banco;
- se o produto ainda não existir no Catálogo, primeiro permanece o alerta da I1 para cadastrá-lo.

## Segurança
- nenhuma foto é salva automaticamente;
- nenhum cadastro é preenchido automaticamente;
- nenhuma proposta é reescrita;
- fotos só entram no Catálogo após confirmação explícita;
- o THU sugere enriquecimento do banco, mas a Anna decide se a imagem é útil.
