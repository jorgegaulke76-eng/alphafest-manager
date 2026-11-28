# AlphaFest HF84 — Fundação Segura, sem risco operacional

## Objetivo
Blindar futuras atualizações do Manager, manter o rodapé sincronizado e preservar
clientes, orçamentos, pedidos, estoque, preços e artefatos do site.

## Diagnóstico técnico de 28/11/2026 (somente leitura)
- O GitHub mostrou a branch `main` sem proteção habilitada e o repositório com visibilidade **pública**.
  Não mudar visibilidade sem revisar integrações do Streamlit, GitHub Actions e permissões.
  A auditoria não comprovou vazamento de nenhuma chave.
- A versão exibida pelo Manager é carregada de `VERSAO.txt` via `config.py`;
  `VERSAO` e `RELEASE_INFO.json` precisam coincidir.
- A sincronização atual das releases HF ocorre em
  `.github/workflows/sincronizar-rodape-manager.yml`, após merge na `main`.
- A tabela interna `public.app_data` tem RLS habilitado e nenhuma policy de acesso público.
  Isso é compatível com o servidor usar `SUPABASE_SERVICE_KEY`. Não ativar policies de leitura
  anônima para silenciar avisos informativos.
- Foi identificado um registro de agendamentos/backups no banco, **não** a prova de restauração.
- O site público é gerado em pacote separado e publicado no Cloudflare Worker `alphafest-novo`.
  Merge no GitHub **não significa** que uma versão do site foi publicada.

## Gate HF84 de release
1. O PR deve passar em `python -m unittest -v test_hf84_preflight.py test_sincronizar_release_rodape.py`.
2. Rodar `python scripts/hf84_preflight_seguranca.py --min-hf 83`.
3. O script falha se `VERSAO`, `VERSAO.txt` e `RELEASE_INFO.json` não coincidirem,
   se houver regressão de HF, SHA/data malformados ou se desaparecerem proteções básicas.
4. Depois do merge, a automação de release registra `HF84` nos três arquivos.
   Conferir a conclusão do workflow de sincronização e verificar os três valores na `main`.
5. Conferir versão no rodapé do Streamlit após novo carregamento e reiniciar o app somente
   se ele não estiver usando a versão atual do GitHub.
6. Se houver pacote de site gerado, validar a prévia, integridade e o fluxo de rollback
   antes de clicar em Publicar. Este PR **não publica** nem altera o site.

## Recuperação — execução controlada
- Antes de qualquer mudança estrutural do banco, gerar cópia consistente,
  registrar data e checksum e confirmar que foi armazenada fora do volume efêmero do Streamlit.
- Testar a leitura e a restauração **em ambiente isolado** (nunca sobrescrever produção).
- Conferir quantidade de documentos, clientes, propostas e pedidos por categoria, sem
  exportar dados pessoais para logs públicos.
- Nunca executar migrações destrutivas, troca de chaves ou RLS automaticamente pela HF84.
- Se falhar a homologação, reverter o commit do aplicativo por PR ou restaurar o
  pacote do site previamente aprovado; dados comerciais só podem ser restaurados
  com autorização expressa e conciliação.
- A presença de arquivos/agendamentos de backup **não garante recuperação**:
  marcar como pendente até existir teste de restauração concluído.

## Próximas decisões de infraestrutura (fora desta release)
- Revisar arquivos já versionados e histórico de Git com ferramenta de secret scanning.
- Decidir se o repositório deve tornar-se privado e configurar branch protection, respeitando
  permissões e conectores do ambiente atual.
- Validar política de retenção de backups, RPO/RTO e testes periódicos de restauração.
- Segmentar gradualmente `app.py` e dados JSON do banco com migração reversível.
- Reavaliar permissões específicas de Jorge/Anna com testes de autorização antes de
  habilitar novas automações comerciais.

## O que esta HF84 não faz
- Não altera tabelas, políticas RLS, secrets, produtos, preços, clientes, pedidos,
  orçamentos, inventário, créditos ou configurações de anúncios.
- Não publica o site, não reinicia Streamlit e não muda DNS ou Cloudflare.
- Não afirma que os backups são restauráveis sem teste isolado.
