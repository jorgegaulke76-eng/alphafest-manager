# Validação — AlphaFest Manager HF65.24.52

## Resultado

A integração foi conferida localmente sobre o código fornecido da HF65.24.51. Os testes focados passaram, o gerador produziu o pacote público de teste e a conferência visual cobriu as larguras de celular e desktop.

## Testes automatizados executados

Comando:

```sh
python -m unittest -v test_site_vitrine_hf52 test_update_package_hf52 test_site_release_cache_hf52
```

Resultado: **14 testes aprovados**.

- 10 testes da ficha: geração com catálogo atual, ausência de mutação dos dados, links válidos/inválidos/inexistentes/privados, carregamento antes/depois de DOMContentLoaded, evento único, resize/scroll da viewport, retorno ao desktop, fechar/reabrir, teclado e fallback sem visualViewport. Executam o JavaScript emitido pelo gerador em Node com DOM mínimo; não utilizam rede.
- 3 testes da sessão/cache: descarte da prévia e confirmação de outra versão, preservação dos dados alheios, persistência da prévia atual e cache novo quando a versão muda. Executam os trechos reais extraídos de app.py sem iniciar o aplicativo.
- 1 teste do ZIP real: metadados de release incluídos e íntegros, dados/configurações/segredos excluídos, manifesto antigo substituído e hashes/tamanhos coerentes.

Também foi executado `python test_pwa_hf652414.py`, com resultado OK para manifesto PWA, ícones, service worker, pacote público e extração dos arquivos para Cloudflare.

## Revisão da integração de métricas

Foram executados juntos os scripts reais da ficha, de métricas e de contexto WhatsApp, com chamadas externas e armazenamento simulados:

- Entrada válida: page_view e exatamente um product_open, além do produto no contexto WhatsApp.
- Segundo disparo de DOMContentLoaded: sem duplicação.
- Parâmetro ausente, inválido ou produto inexistente: sem abertura e sem evento de produto.
- Documento já pronto: uma abertura pelo mesmo caminho de clique.

O comportamento foi corrigido antes do empacotamento final.

## Conferência no navegador

A página foi gerada pelos módulos atualizados com uma amostra de sete produtos obtida da prévia fornecida. O ambiente de conferência não utiliza os bancos nem os serviços de produção.

- Abertura direta da ficha de Bubble Personalizado com Confetes e Balões Metalizado.
- Exibição em 390 × 844, 844 × 390 e 1280 × 800, usando um quadro responsivo de teste em navegador Chrome.
- Mudança de largura com a ficha aberta: dimensões móveis removidas corretamente em paisagem/desktop e reaplicadas ao voltar para celular.
- Botão de fechar, imagem, descrição, ações e produtos relacionados visíveis.
- Adição ao orçamento, ajuste de quantidade pelo controle numérico, observação e revisão da mensagem, sem envio para WhatsApp.
- Retorno à escolha de produtos fecha os painéis corretamente.

O CSS móvel integrado corresponde exatamente ao bloco de 531 caracteres da prévia validada. Os dados e as imagens da amostra não são incluídos como base fixa na atualização do Manager.

## Diagnóstico e pacote

O diagnóstico oficial da release passou sem problemas ou avisos: **38 de 38 módulos críticos compilados**, arquivos obrigatórios e template mestre verificados. Esse diagnóstico não executa os testes acima: eles foram executados separadamente.

O pacote final é gerado com o builder do próprio projeto, usando UPDATE_INFO_HF65.24.52.md como nota da release. O builder recria UPDATE_MANIFEST.json e audita o ZIP. A entrega também confere a versão em VERSAO, VERSAO.txt, RELEASE_INFO.json e manifesto, assim como o tamanho e o SHA-256 de cada entrada listada.

## Limites da verificação

Não foi iniciada a aplicação completa no Streamlit Cloud nem acessados Supabase ou Cloudflare de produção. A conferência visual de celular utiliza largura de navegador, não um aparelho físico. A instalação no ambiente do usuário e a publicação do domínio devem seguir LEIA_ME_ATUALIZACAO.txt.
