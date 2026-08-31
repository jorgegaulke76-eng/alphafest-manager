# 20.4.9-I8.13.3 — Núcleo de Integridade e Segurança

## Objetivo
Consolidar a HF12 homologada antes de novas expansões, mantendo custo zero.

## Entregas desta etapa
- Cache de documentos só é promovido após confirmação real de persistência.
- Em falha de gravação, o cache do documento é invalidado.
- `cloud_db.save_document` passa a gravar online primeiro; cópia local acompanha apenas confirmação online.
- Suporte opcional a `SUPABASE_SERVICE_KEY` para retirar escrita anônima sem custo.
- Health Monitor exibe modo da credencial e última tentativa de gravação da sessão.
- `.gitignore` para Secrets, caches, ZIPs, backups e bancos operacionais locais.
- SQL de hardening separado e seguro para aplicar somente após configurar SERVICE KEY.
- Pacote de release sem `__pycache__`, backups antigos do `app.py` e ZIP legado interno.

## Não alterado
- Fluxo Aprovado → Pago → Pronto → Entregue.
- Regras de reserva/consumo.
- Catálogo, propostas, clientes e dados operacionais.
- Nenhum serviço pago ou dependência nova.
