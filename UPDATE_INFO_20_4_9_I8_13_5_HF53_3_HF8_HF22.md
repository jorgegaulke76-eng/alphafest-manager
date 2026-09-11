# AlphaFest Manager — HF53.3-HF8-HF22

## Objetivo
Tornar o backup automático realmente diário no primeiro acesso útil após o horário e aplicar retenção física dos backups antigos.

## Entregas
- backup pendente é detectado mesmo quando o primeiro acesso acontece no dia seguinte;
- sessão aberta reavalia o horário a cada cinco minutos, sem exigir reinício do Manager;
- reserva de slot diário com CAS para evitar dois backups automáticos simultâneos;
- retenção remove também o documento `backup_*` do Supabase e a contingência local;
- falha de remoção mantém o item no índice para nova tentativa, evitando órfãos silenciosos;
- gravação do backup completo e do índice precisa ser confirmada antes de declarar sucesso;
- HF7, Template Anna, métricas e regras operacionais preservados.
