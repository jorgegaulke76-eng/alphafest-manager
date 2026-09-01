# 20.4.9-I8.13.5-HF7 — Clientes, Relacionamentos e Pós-venda modular

Base: **20.4.9-I8.13.5-HF6 homologada**.

## Objetivo
Retirar do `app.py` as regras puras de identidade/vínculo do relacionamento e próxima ação, sem alterar cadastro, propostas históricas, Perfil Comercial, faturamento, permissões ou persistência.

## Extraído para `relacionamentos_service.py`
- normalização de nome e telefone;
- chave estável de cliente: documento → WhatsApp → nome;
- localização comercial: documento → WhatsApp → nome;
- localização relacional legada: WhatsApp → nome;
- vínculo da proposta priorizando `relacionamento_id`;
- visão da proposta com dados atuais do cadastro sem alterar itens/valores/datas/status;
- seleção das propostas pertencentes ao relacionamento;
- pontuação usada para escolher cadastro canônico em consolidações seguras;
- próxima ação de CRM;
- próxima ação da proposta, incluindo pós-venda após Entregue.

## O que NÃO mudou
- nenhum JSON operacional foi migrado ou alterado;
- nenhum cadastro foi criado/mesclado pela atualização;
- Perfil Comercial e abatimentos continuam com as mesmas regras;
- faturamento mensal permanece igual;
- `Aprovado/Pago/Pronto/Entregue` continuam na Fonte Única da proposta;
- pós-venda continua sendo próxima ação, não um novo status automático da proposta;
- nenhuma tela ganhou gravação automática nova.

## Arquitetura
`Tela / cadastro → relacionamentos_service → persistência existente → Auditoria`

O serviço é puro e não depende de Streamlit, Supabase ou `session_state`.

## Testes
Foram adicionados testes de regressão para identidade, precedência de documento/WhatsApp/nome, vínculo por `relacionamento_id`, visão atual sem mutação histórica, histórico por cliente e transição de próxima ação para pós-venda.
