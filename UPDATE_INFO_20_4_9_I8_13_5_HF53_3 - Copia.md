# HF53.3 — Biblioteca de Templates do Alpha Marketing

Evolução estrutural sobre o Template Mestre Comercial homologado HF53.2-HF5-HF7.

## Objetivo

Transformar a Biblioteca de Templates na fonte única do Alpha Marketing sem alterar o visual homologado do Template Mestre.

## Entregas

- Template Mestre Comercial HF53.2-HF5-HF7 registrado como **Oficial / Homologado / Protegido**.
- Prévia oficial preservada dentro do pacote para identificação visual no Template Studio.
- Piloto Automático passa a obter o template através do catálogo da Biblioteca, sem hardcode operacional no render.
- Somente templates com `autopilot_aprovado=True` entram na geração automática.
- Templates importados por ZIP entram sempre como **Em teste** e não podem substituir o mestre oficial apenas por metadados do pacote.
- Template Studio passa a exibir catálogo unificado, status, versão, proteção e disponibilidade para o Piloto Automático.
- Registros de campanha passam a gravar `template_id`, `template_nome`, `template_status`, `template_versao` e `template_oficial`.
- Motor de renderização do HF7 não foi alterado. Comparação byte a byte confirmou saída idêntica para o Template Mestre.

## Segurança de homologação

A instalação de um novo template não é equivalente a homologação. Novos layouts permanecem isolados para teste até uma etapa futura de aprovação explícita.

## Próximo passo do roteiro

Criar um segundo template comercial em paralelo, testar com produtos/campanhas distintos e só então liberar seu uso no Piloto Automático.

## Validação

- 359 testes automatizados aprovados.
- `app.py`, `marketing_template_engine.py` e `template_library_engine.py` compilados sem erro.
- Render oficial HF7 comparado antes/depois: saída PNG byte a byte idêntica no cenário de controle.
