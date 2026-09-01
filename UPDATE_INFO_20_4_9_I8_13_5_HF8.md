# 20.4.9-I8.13.5-HF8 — Orçamento + Catálogo + seleção de produto modular

Base: **20.4.9-I8.13.5-HF7 homologada**.

## Objetivo
Retirar do `app.py` as regras puras que ligam o Novo Orçamento ao Catálogo Oficial, sem alterar o formulário, preços, dados históricos, aliases cadastrados ou a liberdade de digitar um produto novo.

## Extraído para `catalogo_orcamento_service.py`
- normalização estrita de identidade de produto;
- leitura compatível de aliases atuais e formatos legados agrupados;
- mapa nome/alias → nome oficial, com prioridade do nome oficial;
- lista pesquisável de produtos ativos e aliases para o orçamento;
- resolução híbrida: escolha explícita do Catálogo → nome/alias digitado → produto livre;
- recuperação do produto oficial por `CatalogoId` ou nome oficial;
- resumo informativo de categoria/material/variações;
- snapshot comercial seguro gravado no item da proposta.

## Regra preservada do orçamento
Ao selecionar um produto do Catálogo Oficial, o Manager pode carregar o **preço oficial** e metadados comerciais do item.

Continuam **100% manuais e nunca são preenchidos pelo serviço**:
- Tema / Ocasião;
- Nome(s) personalizado(s);
- Cor / Material do pedido;
- Idade / Data do Evento;
- Outros Detalhes.

Produto novo continua permitido como texto livre e não é cadastrado automaticamente no Catálogo.

## O que NÃO mudou
- nenhum produto foi criado, alterado, mesclado ou inativado;
- nenhum alias foi gravado automaticamente;
- nenhum JSON operacional foi migrado;
- preço especial por cliente/Perfil Comercial continua com a regra existente;
- Ficha Técnica e materiais continuam independentes do Catálogo Comercial;
- Jorge e Anna continuam usando o mesmo comportamento visual já homologado.

## Arquitetura
`Novo Orçamento → catalogo_orcamento_service → item da proposta → persistência existente`

O serviço é puro e não depende de Streamlit, Supabase ou `session_state`.

## Testes
Foram adicionados testes para normalização, aliases legados, precedência do nome oficial, produtos inativos, resolução por alias, produto livre, vínculo por CatalogoId e proteção dos campos manuais de personalização.
