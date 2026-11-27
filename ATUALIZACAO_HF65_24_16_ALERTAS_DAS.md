# HF65.24.16 — Alertas DAS-MEI Jorge + Anna

- Alerta operacional em ambas as centrais, desde 10 dias antes do vencimento, no dia do vencimento e após vencimento.
- Exibe competência e urgência, sem detalhes fiscais, anexos, credenciais nem pagamentos.
- Leitura usa o banco existente e não depende de desbloquear o cofre de documentos.
- Competências marcadas **Pagamento informado** deixam de ser classificadas como vencidas; essa situação não equivale à confirmação bancária.
- Botão, com confirmação, para marcar janeiro a setembro de 2026 como pagamento informado, sem inventar valor, data ou comprovante. Não altera competências já pagas ou informadas.
- Registro auditado com usuário e timestamp; gravação verificada antes de informar sucesso.
- Emissão e pagamento continuam manuais pelo portal oficial PGMEI.

Instalação: substituir o pacote anterior e reiniciar o Streamlit. Testar as duas Centrais, depois Gestão > Controle DAS-MEI. Não exige Secrets novos.
