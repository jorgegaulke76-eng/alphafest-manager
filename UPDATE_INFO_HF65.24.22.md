# AlphaFest Manager HF65.24.22 — Correção do botão de duplicadas

- Os controles de seleção e confirmação agora ficam fora de `st.form`, atualizando o botão imediatamente.
- A opção **Selecionar todas** considera todas as cópias idênticas já identificadas.
- Confirmação explícita continua obrigatória.
- Os originais permanecem protegidos e a gravação deve ser confirmada pelo Supabase.
- Nenhum cadastro é excluído na instalação.

Após o commit e o deploy, abra Central do Site → Novidades & Ofertas → Encontrar e excluir artes duplicadas. Selecione todas, confirme, confira a contagem e só então exclua. Atualize prévia e publique no Cloudflare após verificar.
