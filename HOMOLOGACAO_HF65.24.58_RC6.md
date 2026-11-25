# AlphaFest HF65.24.58 RC6 — Upload online seguro

**Exclusivamente homologacao. Nao instalar em producao e nao fazer merge do PR #5.**

## Mudanca
- `cloud_db.upload_library_file` passa a rejeitar uma falha de envio remoto quando o Supabase estiver configurado, retornando vazio em vez de criar um vinculo para arquivo local efemero.
- A gravacao offline em pasta local permanece disponivel quando nao ha Supabase configurado.
- Nao altera a aprovacao comercial nem a ficha de producao.

## Evidencias
- Quatro testes adicionais executam o caminho de bytes reais em pasta temporaria e em API HTTP simulada em 127.0.0.1: envio/leitura integral, timeout e HTTP 403.
- A nova regressao GitHub Actions esta pendente no momento da criacao da RC6.
- O arquivo `UPDATE_MANIFEST.json` e o preflight foram atualizados com SHA-256 correspondente para `cloud_db.py`.

## Ainda pendente
- Evidencia visual de `revisao_pendente` antes da reconfirmacao.
- Teste de upload real em Supabase de homologacao separado, sem credenciais de producao.
- Conclusao e aprovacao da regressao automatica e revisao antes do merge.
