# 20.4.9-F — Auditoria de Dados Antigos do Catálogo

Base: Atual 2049E1 aprovada.

## Objetivo
Detectar problemas de migração/cadastros antigos sem alterar automaticamente nenhum dado.

## Detecta
- Material com informações concatenadas ou estrutura suspeita;
- referências locais de imagem que não existem mais;
- descrições excessivamente longas;
- inconsistências simples de classificação.

## Jorge
- nova métrica “Dados antigos suspeitos”;
- novo filtro específico na Revisão do Catálogo;
- aviso detalhado por produto;
- botão Editar continua abrindo o cadastro oficial.

## Anna
- aviso de dados antigos suspeitos também aparece na visualização/edição do catálogo.

## Segurança
Nenhum campo é limpo, removido ou reescrito automaticamente.
A correção continua sendo manual e auditável no cadastro oficial.
