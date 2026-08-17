# 20.4.9-I8.8.4 — Validade Comercial + Liberação Anna

Base exclusiva: 20.4.9-I8.8.3 homologada.

## Objetivo
Proteger comercialmente os catálogos da AlphaFest diante de variações frequentes de fornecedores e liberar o fluxo moderno de catálogos para a Anna sem abrir operações irreversíveis.

## Validade comercial obrigatória
Todo catálogo gerado pela nova estrutura e também pelo gerador legado passa a exibir no rodapé:
- data da geração;
- horário da geração;
- usuário responsável;
- validade de 30 dias;
- data final de validade;
- aviso para reconfirmar valores e condições após o vencimento.

A validade é calculada a partir da data/hora da geração. Exemplo: uma geração em 17/08/2026 fica válida até 16/09/2026.

## Central de Catálogos
- Catálogo salvo registra `ultima_geracao_em`, `ultima_geracao_por` e `validade_ate`.
- Catálogos antigos sem esses campos continuam compatíveis: a Central usa os metadados existentes como fallback até a próxima geração.
- A Central mostra status visual `Válido`, `Próximo do vencimento` ou `Vencido`.
- `Gerar novamente com dados atuais` produz um HTML com nova data/hora e renova a validade por mais 30 dias.
- A nova geração é registrada na auditoria.
- Editar/salvar um catálogo também cria uma nova versão comercial com nova validade.

## Perfil da Anna
A Anna passa a poder entrar deliberadamente no módulo Catálogo moderno a partir da sua Central Operacional, com acesso a:
- Gerador I8.7.1;
- Prévia Interna I8.8.2;
- Modelos I8.8.3;
- Central de Catálogos I8.8.4;
- downloads e geração com dados atuais.

O botão `✨ Gerador / Modelos / Central` foi incluído na Central da Anna. Há também um botão explícito para voltar à Central Operacional.

## Segurança
- Exclusão comum continua enviando catálogo/modelo para a Lixeira.
- Exclusão definitiva na Lixeira fica bloqueada para a Anna e reservada ao Jorge.
- Nenhum preço, foto, descrição, material ou campanha é copiado para o catálogo salvo.
- A validade comercial não cria snapshot de preço; ao gerar novamente, os dados continuam vindo do Catálogo Oficial atual.

## Compatibilidade
- Gerador I8.7.1 preservado.
- Prévia I8.8.2 preservada.
- Modelos I8.8.3 preservados.
- Central/Lixeira preservadas.
- Catálogo para cliente (fallback) também recebe o rodapé comercial obrigatório.
- Gerador rápido da Anna também recebe o rodapé comercial obrigatório.
