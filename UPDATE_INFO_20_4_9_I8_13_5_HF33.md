# 20.4.9-I8.13.5-HF33 — Performance conservadora

## Objetivo
Deixar o AlphaFest Manager mais leve sem perder nenhuma função pronta ou homologada e sem criar divergência entre os perfis Jorge e Anna.

## O que muda
- Módulos opcionais/pesados passam a ser importados sob demanda, apenas ao abrir a função que realmente precisa deles.
- Marketing Template Engine, Template Library, Marketing Prompt Builder, Design Intelligence, Marketing AI, Altair, Alpha Intelligence, Central de Oportunidades, OpenAI, QR Code e fallbacks embutidos do THU deixam de pesar obrigatoriamente no boot operacional.
- O valor do template oficial padrão permanece `anna_base_dinamica`, igual à HF32.
- Não há aumento de TTL de documentos nem cache paralelo: Fonte Única e sincronização Jorge/Anna continuam com a mesma regra da HF32.
- Nenhuma tela, botão, módulo, fluxo, status ou permissão homologada é removida.

## Proteção de regressão
- Suíte existente é executada integralmente.
- Testes adicionais verificam o carregamento sob demanda e contratos de compatibilidade dos recursos movidos.
- Inventário do pacote é comparado com a HF32 para garantir que nenhum arquivo funcional desapareceu.
- JSON/SQL operacionais são comparados byte a byte com a HF32.

## Homologação sugerida
1. Abrir como Jorge e conferir Central do Dia / Agenda Executiva.
2. Abrir como Anna e conferir Central Operacional / Agenda diária.
3. Abrir Marketing e Catálogo 3D para confirmar que recursos sob demanda continuam carregando normalmente.
4. Observar se a navegação inicial e os retornos às telas operacionais ficaram mais leves.
