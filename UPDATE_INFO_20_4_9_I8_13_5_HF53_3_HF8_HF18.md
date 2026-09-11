# AlphaFest Manager — HF53.3-HF8-HF18

## Etapa 1 — Higiene e Blindagem do Manager

Primeiro pacote da revisão sistêmica com foco em otimização e automação invisível.

### Entregas
- gerador oficial de atualização limpa (`build_update_package.py`);
- regra central de exclusão de bancos JSON, arquivos `Copia`, caches, backups de código e pacotes antigos;
- `UPDATE_MANIFEST.json` com hashes de todos os arquivos enviados;
- preflight do ZIP após a própria geração; pacote inválido é recusado automaticamente;
- verificação do hash congelado do Template Mestre HF7;
- checagem de `VERSAO` x `VERSAO.txt` e arquivos obrigatórios;
- preflight integrado à tela **Configurações → Atualização segura**;
- atualização não altera regras de negócio, Catálogo, Template Anna, Site ou HF7.

### Política
Pacote de atualização = código + assets + migrações. Dados da empresa permanecem no banco/instalação e nunca são transportados pelo ZIP.
