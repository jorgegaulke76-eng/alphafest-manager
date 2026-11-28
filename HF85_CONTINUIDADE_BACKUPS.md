# HF85 — Continuidade e integridade de backups (etapa HF84.1)

## Escopo
Diagnóstico exclusivamente de metadados de backups, sem leitura de documentos de clientes, escrita, exclusão ou restauração. O rodapé é sincronizado pela automação de release após o merge.

## Achados do banco de produção — 28/11/2026 (consultas somente leitura)
- Agendamento lógico consta como ativo e configurado para 22h (Brasil).
- A data `ultimo_backup_em` registrada aponta 08/09/2026 às 22:21 (Brasil).
- Foram encontrados 5 documentos com prefixo `backup_20`, de agosto/setembro, com campo de assinatura SHA-256 registrado; o índice contém 4 itens (possível divergência a conferir, não corrigir automaticamente).
- O último backup de setembro contém 26 chaves de documentos no objeto `documentos`; o banco tem 38 documentos que não são backups, e 25 deles foram atualizados após o último backup.
- Estes contadores não representam clientes/pedidos e não atestam que arquivos antigos possam ser restaurados.
- O Supabase mostra RLS em `public.app_data` sem policy, compatível com acesso pelo serviço. Nenhuma policy foi alterada.
- A branch `main` não está protegida. Qualquer ajuste nas permissões exige primeiro avaliar GitHub Actions, integração Streamlit e autorização adequada.

## O que esta etapa implementa
O serviço `backup_continuidade_hf85.py` compara datas de metadados com uma tolerância explícita, diferencia backup recente de restauração comprovada e sinaliza:
- backup atrasado ou ausente;
- agendamento desligado;
- assinatura SHA-256 ausente/malformada;
- divergência entre data da configuração e último backup;
- ausência de prova de restauração.

O serviço **não** verifica o conteúdo dos backups nem sua assinatura, e **não** cria backups. É uma fundação testada para futura exibição do alerta no Health Monitor do Manager.

## Operação recomendada
1. **Antes de qualquer migração ou mudança de permissões**, verificar a existência de cópia atual e recuperável fora do processo Streamlit.
2. Programar backup via executor confiável e autorizado, com credenciais restritas e armazenamento separado. O agendamento dentro da sessão Streamlit, sozinho, não garante execução diária.
3. Testar recuperação em ambiente isolado, sem tocar no banco de produção e sem registrar dados pessoais nos logs.
4. Só depois conectar o alerta ao Health Monitor e revisar retenção e proteção do índice.
5. Verificar o novo valor do rodapé: `VERSAO`, `VERSAO.txt`, `RELEASE_INFO.json` iguais e terminando em `HF85`.

## O que permanece intocado
Sem alterações em dados, banco, RLS, GitHub visibilidade/branch protection, Streamlit Secrets, Worker Cloudflare, publicações, pedidos, clientes, preços ou arquivos antigos de backup.
