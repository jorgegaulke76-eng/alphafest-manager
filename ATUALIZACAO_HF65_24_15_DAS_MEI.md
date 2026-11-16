# HF65.24.15 — Controle DAS-MEI AlphaFest

**Base:** HF65.24.14 (site instalável). Esta atualização não altera o Cloudflare, WhatsApp, YouTube, catálogos ou o acervo do Supabase.

## Como habilitar o controle

1. Faça backup do repositório atual e instale todos os arquivos do pacote.
2. Em Streamlit Community Cloud > Settings > Secrets, adicione **uma frase de acesso de pelo menos 10 caracteres** (sem revelar a frase aqui):

   ```toml
   DAS_MEI_ACCESS_CODE = "SUA_FRASE_PRIVADA_COM_10_OU_MAIS_CARACTERES"
   ```
3. Mantenha `SUPABASE_URL` e `SUPABASE_SERVICE_KEY` existentes, sem alterá-las. Não coloque a chave em arquivos do GitHub.
4. Abra Gestão > Controle DAS-MEI, selecione Jorge e forneça a frase. O código deve ser pessoal e não compartilhado.
5. Selecione o ano e clique **Criar competências do ano**. O sistema nunca presume que uma competência foi paga ou emitida.
6. Emita a guia verdadeira no PGMEI do portal Gov.br; preencha valor, vencimento e a data de emissão conforme a guia. Se desejado, anexe o PDF da guia.
7. Após confirmar efetivamente o pagamento, informe data, situação Paga, conferência e anexe comprovante em PDF.

## Alertas

A Central do Jorge mostrará lembretes de vencimentos em até 10 dias e de atrasados, apenas após desbloqueio do módulo na sessão. Não há disparos automáticos de WhatsApp/e-mail nesta versão.

## Segurança

As guias e comprovantes PDF são enviados a um bucket **privado** `das-mei-privado` no Supabase. Não há fallback para bucket público. O upload falha em vez de declarar sucesso quando Storage não confirma a escrita. Registros JSON têm gravação com proteção contra conflitos e trilha básica de mudanças.

**Importante:** o seletor de usuário do Manager não equivale a autenticação forte. O código de acesso adiciona uma barreira ao módulo, mas o Streamlit inteiro deve continuar protegido por uma autenticação adequada. Não publique Secrets ou dados bancários no GitHub.

O sistema oferece gestão interna, não substitui o extrato do PGMEI nem a conciliação bancária. Vencimentos em feriados exigem conferência no portal oficial.

## Testes

Compilação dos arquivos Python e testes isolados da regra de vencimento, bloqueio de pagamento incompleto, trilha de alterações, cálculo de totais e importação dos módulos. **Não foi validado por instalação no Streamlit Cloud nem por envio real a esse Storage**, então validar com uma competência e um documento sem dados sensíveis antes de uso definitivo.
