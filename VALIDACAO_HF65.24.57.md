# Validação — AlphaFest Manager HF65.24.57

## Resultado da seleção crítica

Release cumulativa sobre a HF65.24.56. A seleção crítica contém **502 testes em 35 arquivos**, aprovados sem falhas, erros ou casos ignorados. Outros **6 testes de interface da HF53**, executados separadamente na árvore integrada, também passaram. O diagnóstico compila **54 de 54 módulos críticos**.

| Grupo | Casos aprovados |
|---|---:|
| Serviço de rascunho portátil HF57 | 47 |
| Interface de preparação, retomada e referências HF57 | 26 |
| Integração com app.py e workflow HF53 | 24 |
| Regressões HF56 e anteriores | 405 |
| **Total no gate do empacotador** | **502** |
| Interface de edição/abertura HF53, executada separadamente | 6 |

O inventário encontra **42 arquivos de teste**; um arquivo depende de versão histórica e fica fora da seleção crítica. Inventário de arquivos não é contagem de casos executados. O `UPDATE_MANIFEST.json` registra o resultado final por arquivo e a assinatura dos fontes usados.

## Serviço de arquivo portátil

Os 47 testes do serviço exercitam captura por whitelist, cópia independente de dados, ida e volta por JSON, formulários incompletos, quantidades fracionárias, preços, personalizações, ordem das linhas, metadados e mensagem original.

As pendências são recuperadas como listas informativas, com original e campos recebidos no caso do editor. Os testes verificam que referências anteriores sobrevivem à nova exportação, que somente conteúdos integralmente iguais são deduplicados e que limites não removem dados silenciosamente.

A preparação usa o workflow real para provar retomada entre perfis como orçamento novo, sem número de edição, vínculos ativos, status, permissões ou aceites. Não cria arquivos, consulta rede, salva cliente ou grava proposta.

### Dados inválidos e limites

A suíte cobre esquema e versão, chaves estruturais ausentes/extras, tipos, JSON inválido, codificação UTF-8, Unicode inválido, nomes duplicados inclusive com escapes equivalentes, NaN, infinito, expoentes que excedem a representação numérica, inteiros excessivos, referências circulares e limites globais.

As verificações abrangem 2 MiB, 1.000 itens, 100 mil caracteres por string, profundidade 12, 40 mil nós e 50 referências manuais de cada tipo, inclusive dentro de metadados. Todo documento aceito precisa poder ser reexportado integralmente.

Inteiros comerciais cuja conversão para os campos numéricos alteraria o valor são recusados. A regra não remove precisão de inteiros presentes em metadados desconhecidos: os casos `2**53 + 1` e `2**128 + 1` continuam exatos nesses metadados, inclusive em um campo chamado `quantidade` dentro de metadata.

O rótulo inicial legado **Retirada em Itatiba** é reconhecido como a modalidade **Retirada** durante a captura, sem alterar o estado. A data de entrega pode ser vazia; datas informadas são limitadas aos anos **1010–9989**, compatíveis com os controles atuais e seus limites automáticos.

## Interface Streamlit

São **25 AppTests com o serviço real** e um teste por AST que confirma que apenas a retomada solicita rerun global. A exportação e a dispensa de referências preservam o comportamento do diálogo da Anna.

Os cenários incluem:

- Preparação de arquivo completo e sem itens, bytes JSON parseáveis e download sem rerun.
- Invalidação de arquivo preparado depois de alterar dados ou ocorrer erro de captura, sem apagar o formulário.
- Tamanho verificado antes da leitura do upload, arquivo inválido e substituição/remoção do arquivo.
- Revisão completa e aceites vinculados ao arquivo; confirmação adicional quando existe proposta anterior.
- Falha, recusa e sucesso do callback de abertura; revisão preservada e possibilidade de reabrir após cancelar o handoff.
- Revisões independentes entre perfis e preservação ao ocultar/reabrir a área.
- Pendências apenas informativas, dispensa explícita, tratamento de falha do callback e conservação dos itens.
- Nova geração do formulário exigindo nova confirmação das referências, mesmo quando o mesmo arquivo é retomado novamente.
- Encerramento da revisão de referências quando o formulário deixa de ter origem e pendências, evitando mensagem de sucesso de outro trabalho.

### Alcance dos testes de upload e download

O AppTest do Streamlit 1.51 não oferece ação nativa de transferência de arquivos. A fixture renderiza o uploader real e fornece um `UploadedFile` real à entrada da interface, incluindo o callback de alteração. O download é verificado pelos bytes produzidos e pelo botão real configurado sem rerun.

Esses testes não representam uma transferência de arquivo realizada no navegador do usuário. A interface foi exercitada por AppTest, sem iniciar o Manager completo ou um navegador de produção.

## Integração dos formulários

Os 24 testes de integração extraem por AST os helpers e trechos reais de `app.py`, usam os serviços e o workflow reais e tornam as gravações proibidas ou observáveis por doubles. Os cenários comprovam:

- Captura do perfil correto e retomada de um arquivo de qualquer dos dois perfis no perfil atual.
- Preservação de campos, itens, personalizações, metadados, contatos, mensagem e data vazia.
- Abertura como novo orçamento, referências de origem informativas e defesa contra IDs ativos inseridos no payload intermediário.
- Permissões antes de enfileirar e novamente antes de aplicar; proibição de sobrescrever outra intenção pendente.
- Trabalho atual preservado até a escolha; **Continuar** e **Cancelar** mantendo também referências e aceites existentes.
- **Substituir** limpando apenas as conferências do perfil que recebeu o arquivo, sem reiniciar seus contadores ou afetar o outro perfil.
- Cliente homônimo sem substituição automática de contato, mantendo disponível a seleção explícita de cadastro.
- Pendências sem inclusão nos itens, nos totais ou no payload comercial, conservadas na nova exportação.
- Proteção de um rascunho composto apenas por informações pendentes de recuperação manual.
- Limpeza de escopo ao abrir outro orçamento ou limpar o formulário, e inicialização da Anna preservando o contexto recuperado.
- Item comercial inválido recuperado sendo bloqueado pelo trecho real de salvar antes de qualquer cadastro ou gravação.
- Exportador antes do botão de salvar, inclusive em caso de falha posterior, e disponível sem itens nos dois perfis.

### Depois do salvamento

Os trechos reais posteriores à confirmação de gravação foram exercitados com e sem pendências. Com pendências, os itens já salvos saem do rascunho sem alterar a cópia da proposta gravada; identificação, condições e informações manuais ficam disponíveis em contexto novo.

O cenário **salvar → solicitar outra abertura → Continuar → inicializar a Anna → exportar novamente** conserva as pendências e não reinsere os itens já salvos. Sem pendências, a limpeza habitual continua ativa.

A suíte HF56 de integração passou usando o novo helper real. Mantém a cobertura da ordem das conferências, falha de persistência, ausência de sucesso falso e retenção do trabalho quando a gravação não é confirmada.

## Revisão independente e compatibilidade dos controles

A revisão independente encontrou e acompanhou as correções de três casos: pendências sozinhas ignoradas pela detecção de rascunho; datas extremas incompatíveis com os controles; informações manuais perdidas depois de salvar. Uma revisão adicional confirmou os dois caminhos de pós-salvamento e executou seus testes específicos.

Probes adicionais passaram pela preparação real, workflow e controles equivalentes aos campos de condições de Jorge e Anna. Identificaram perda de precisão de `9007199254740993` após interação no campo numérico e problema de serialização dos limites de datas antigas. O serviço foi ajustado para recusar essas entradas antes da abertura.

Os casos representáveis, a data vazia e as fronteiras aceitas foram conferidos após nova interação e captura. A limitação de anos com poucos dígitos foi observada no parser de `DateInput` do AppTest; não é apresentada como prova independente de falha em navegador. Esses probes ficam fora da contagem de casos do gate.

## Ambiente e pacote

Python **3.12.14**, Streamlit **1.51.0** e Node **24.22.3**. `requirements.txt` permanece igual à base HF56 e `DATA_VERSION` permanece **5**.

O empacotador executa cada arquivo crítico em subprocesso isolado, bloqueia rede e importação do Manager, verifica a assinatura dos fontes e só promove o ZIP temporário depois da auditoria. Os dois módulos HF57 fazem parte da lista obrigatória do runtime e da compilação crítica.

A auditoria final verifica CRC, tamanho e SHA-256 de cada entrada, presença dos módulos obrigatórios, concordância entre os arquivos de versão e o manifesto e exclusão de dados operacionais, credenciais, caches e compactados antigos. O template mestre HF7 mantém o hash congelado.

```sh
python build_update_package.py --output ALPHAFEST_MANAGER_HF65.24.57_RASCUNHOS_RECUPERAVEIS.zip --release-note UPDATE_INFO_HF65.24.57.md
```

## Limites da verificação e da funcionalidade

Não houve acesso ao Supabase de produção, publicação no Streamlit Cloud ou alteração do site público nesta entrega. A confirmação operacional após instalar deve conferir o fluxo no ambiente efetivamente usado pela empresa. Gravações devem ser verificadas em homologação ou com registros de teste identificados.

O arquivo preserva somente dados que chegaram ao Manager. Campos ainda não enviados por um formulário podem existir apenas no navegador. A funcionalidade não introduz armazenamento automático de rascunhos entre sessões: a recuperação depende do arquivo que foi efetivamente baixado.

A retomada abre um orçamento novo. Não sincroniza alterações com a proposta anterior, não restaura aprovações e não substitui a conferência comercial. O controle de edição simultânea do banco permanece fora do escopo desta versão.

As funcionalidades HF57 são do Manager. A atualização não exige republicação do site para usá-las.
