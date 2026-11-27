-- Banco D1 exclusivo do resumo comercial; executar manualmente no banco novo.
-- A PRIMARY KEY impede duas reservas da mesma data de Brasilia.
CREATE TABLE IF NOT EXISTS quote_summary_delivery (
  day_key TEXT PRIMARY KEY NOT NULL,
  claimed_at TEXT NOT NULL,
  confirmed_at TEXT
);
