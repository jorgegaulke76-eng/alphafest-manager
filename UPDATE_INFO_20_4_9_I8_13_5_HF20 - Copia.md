# 20.4.9-I8.13.5-HF20 — Agenda Atualizável da Anna

Base funcional: **HF19 em homologação**, preservando a **HF18 como última base homologada**.

## Correção
- O PDF registrado no **Início do dia** continua congelado como fotografia oficial para o comparativo do fechamento.
- A Central da Anna passa a oferecer, durante todo o expediente, **🔄 Atualizar e baixar agenda atual (PDF)**.
- Esse novo PDF é gerado com a situação do banco no momento do clique/rerun e pode ser baixado quantas vezes forem necessárias durante o dia.
- O arquivo recebe horário no nome para evitar confusão com versões anteriores e com o roteiro fixo da manhã.
- Atualizar a agenda atual **não sobrescreve nem altera** a fotografia do início do dia.
- O fechamento comparativo continua comparando a fotografia registrada pela manhã com o banco atual.

## Segurança
- Nenhuma proposta, status, pagamento, produção ou entrega é alterado ao gerar PDFs.
- Nenhuma imagem é incluída nos PDFs operacionais da Anna.
- Nenhum JSON/SQL operacional foi alterado.
