# 20.4.9-I8.8.1 — Lixeira visível na Central de Catálogos

Base exclusiva: 20.4.9-I8.8.

## Motivo
Na homologação humana da I8.8, a exclusão protegida funcionou e enviou o catálogo para a Lixeira geral do FestManager, porém a Central de Catálogos não oferecia uma entrada visível para localizar e restaurar esses catálogos.

## Correção
- A própria `🗂️ Central` passa a exibir o indicador **Na lixeira**.
- Nova área visível `🗑️ Lixeira da Central (N)` dentro da Central.
- A área mostra somente itens do tipo `Catálogo gerado`.
- Ação `♻️ Restaurar catálogo` devolve a configuração à Central.
- Ação `❌ Remover definitivamente` exige confirmação explícita.
- Restauração e remoção definitiva continuam registradas na Auditoria.
- A Lixeira geral existente no módulo de segurança/saúde continua preservada.

## Regra de segurança preservada
A Lixeira armazena/restaura somente a configuração do catálogo salvo. Produtos, preços, fotos, descrições, materiais e campanhas continuam pertencendo exclusivamente ao Catálogo Oficial.

## Sem regressão
Nenhuma estrutura de dados comercial foi alterada. O Gerador I8.7.1, a Central I8.8, Saneamento, Acervo histórico, Cadastro, Produtos e a aba antiga de catálogo permanecem preservados.

## Próximo passo
Após homologação deste hotfix, a prévia interna planejada passa para a I8.8.2.
