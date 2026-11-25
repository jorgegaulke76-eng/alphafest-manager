# Validação — AlphaFest Manager HF65.24.54

## Resultado

A release HF65.24.54 foi integrada sobre a HF65.24.53. A seleção crítica executada pelo empacotador contém **175 testes em 23 arquivos**, todos aprovados, sem falhas, erros ou casos ignorados. Foram executados também **6 testes de interface da HF65.24.53**, aprovados na árvore integrada. O diagnóstico compila **48 de 48 módulos críticos**.

| Grupo | Casos aprovados |
|---|---:|
| Interpretação e preparação da mensagem do site | 26 |
| Integração com formulários, clientes, permissões e catálogo | 20 |
| Interface Streamlit da importação | 14 |
| Regressões críticas da base HF65.24.53 | 115 |
| **Total no gate do empacotador** | **175** |
| Interface de edição/abertura do Manager HF65.24.53, executada separadamente | 6 |

As contagens finais e a assinatura dos fontes ficam registradas no `UPDATE_MANIFEST.json` gerado pelo pacote. O inventário encontra 30 arquivos de teste; um arquivo é classificado como dependente de versão histórica e permanece fora da seleção crítica. Arquivos encontrados não são contabilizados como testes executados.

## Mensagem e catálogo

`test_site_quote_import_hf54.py` executa inclusive a função JavaScript `message()` real do carrinho por Node, evitando que o formato de teste seja apenas uma cópia manual do formato esperado.

A cobertura inclui:

- Mensagem padrão, 25 itens extensos, observações em várias linhas e listas numeradas.
- Mensagem original integral, inclusive quebras CRLF, e textos adicionais de prazo/entrega sem inferência automática desses campos.
- Produtos repetidos separados, preservando as respectivas personalizações.
- Correspondência única por nome/alias; nomes duplicados, aliases ambíguos e produtos inativos mantidos como texto livre.
- Preços sugeridos somente dos campos oficiais `Preco`/`preco`, sem aceitar valores citados na mensagem como preço confirmado.
- Quantidade ausente, inválida, decimal e fora do limite; valores não finitos recusados.
- Quantidade e preço revisados, confirmação explícita de zero e preservação da ordem/identidade das linhas.
- Limites explícitos de mensagem e itens, imutabilidade dos dados recebidos e assinatura dos campos comerciais do catálogo.

## Integração real com o Manager

`test_site_quote_import_integration_hf54.py` extrai os helpers reais do `app.py` por AST e utiliza o workflow e os localizadores reais de clientes. Nenhum teste importa/inicia o aplicativo completo.

Foram verificados:

- Permissão de visualizar/criar orçamento, inclusive revogação após enfileirar a abertura.
- Enfileiramento sem rerun prematuro ou gravação, recusa de outra abertura já pendente e cópia independente dos dados.
- Abrir, cancelar, continuar e substituir nos contextos de Jorge e Anna, sem repetição em nova execução.
- Limpeza dos vínculos e marcadores do trabalho anterior.
- Preservação de telefone novo diante de um cliente cadastrado com o mesmo nome.
- Os sete pontos reais de identificação, preço e perfil comercial dos dois formulários usando o localizador protegido.
- Seleção explícita de cliente e manutenção do comportamento anterior fora da importação.
- Callback de nome impedindo preenchimento por homônimo apenas no modo livre importado.
- Mensagem longa preservada no handoff, na exibição como texto e nas expressões reais de `briefing_origem`.
- Remoção dos marcadores de importação ao inicializar outro formulário.
- Leitura confirmada real com HTTP simulado: somente GET, sem fallback, importação local ou escrita; retorno inválido e erro de conexão recusados.

## Interface Streamlit

Os 14 testes de `test_site_quote_import_ui_hf54.py` utilizam **Streamlit AppTest e o parser real**, sem simular o parser nem adaptar os reruns da nova interface.

Cobrem análise/revisão, alterações de quantidade/preço/personalização/identificação, invalidação da confirmação, mensagem alterada, catálogo alterado, falha na consulta, quantidade ausente, preço zero, callback recusado e consumo único. Também verificam 25 itens longos e o isolamento entre os prefixos dos dois perfis.

Um cenário sai para uma tela que não renderiza o importador, confirma a limpeza dos widgets pelo Streamlit e volta. Texto original, preços, personalização, cliente, telefone e evento são recuperados pelo estado próprio da revisão. Retomar a revisão exige ação explícita e não reenvia os itens sozinho.

Os seis testes adicionais da interface HF53 verificam regressões de edição de itens e abertura protegida. O adaptador já existente para o rerun de fragmento da Anna continua restrito ao teste HF53, pois AppTest não fornece o identificador real do fragmento do navegador.

## Ambiente e empacotamento

Ambiente de QA: Python 3.12.14, Streamlit 1.51.0 e Node 24.22.3. A release não altera `requirements.txt` nem a versão de dados (`DATA_VERSION = 5`).

O empacotador executa cada arquivo crítico em subprocesso isolado, bloqueia rede e importação de `app.py`, verifica a assinatura dos fontes, gera um ZIP temporário e só promove o arquivo depois da auditoria.

```sh
python build_update_package.py --output ALPHAFEST_MANAGER_HF65.24.54_IMPORTACAO_ORCAMENTO_SITE.zip --release-note UPDATE_INFO_HF65.24.54.md
```

A conferência final do ZIP cobre CRC, versões em `VERSAO`, `VERSAO.txt`, `RELEASE_INFO.json` e manifesto, presença dos novos módulos, tamanho e SHA-256 das entradas e exclusão de dados operacionais, segredos, caches e arquivos compactados antigos. O template mestre HF7 mantém o hash de referência.

## Limites da conferência

Não foi executado o Manager completo no Streamlit Cloud nem acessados Supabase, WhatsApp ou Cloudflare de produção. Todos os dados e respostas HTTP usados nos testes são fictícios.

A prévia local não ficou acessível pelo navegador de conferência: as tentativas de conexão foram recusadas. Portanto, esta release não declara uma nova validação visual em navegador ou aparelho físico. A interface nova foi exercitada com AppTest. Depois de instalar, confira o expander de importação e a abertura do orçamento no ambiente real de Jorge e Anna.

A importação prepara rascunhos na sessão; o salvamento real de proposta e cliente continua no fluxo normal. Não foi criado um detector de propostas duplicadas. O original é mantido como referência, mas conteúdo ambíguo precisa de revisão humana.

Guia operacional: **LEIA_ME_ATUALIZACAO.txt**. Comportamento e instalação: **UPDATE_INFO_HF65.24.54.md**.
