"""HF65.24.53 — laboratório SQLite para o diário privado de atribuições.

Não é adaptador de produção. Recebe uma conexão sqlite3 de teste explicitamente
fornecida; não abre arquivo, não conhece Supabase, não usa credenciais ou rede.
Controle de acesso deve ocorrer fora deste módulo antes de qualquer integração.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from typing import Any, Iterable, Mapping

from commercial_attribution_service import build_attribution_event, effective_attributions


class AttributionConflict(ValueError):
    """O histórico mudou desde que o formulário foi carregado."""


def install_test_schema(connection: sqlite3.Connection) -> None:
    """Cria estrutura descartável de laboratório, nunca tabela em produção."""
    connection.executescript("""
    CREATE TABLE IF NOT EXISTS hf53_attribution_events_lab (
      seq INTEGER PRIMARY KEY AUTOINCREMENT,
      event_id TEXT NOT NULL UNIQUE,
      numero_proposta TEXT NOT NULL,
      atendimento_id TEXT NOT NULL,
      campaign TEXT NOT NULL,
      decisao TEXT NOT NULL CHECK(decisao IN ('confirmar','revogar')),
      evidencia TEXT NOT NULL,
      usuario TEXT NOT NULL,
      ocorrido_em TEXT NOT NULL,
      payload TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS hf53_attribution_order_lab
      ON hf53_attribution_events_lab(numero_proposta, seq);
    CREATE TRIGGER IF NOT EXISTS hf53_attribution_no_update_lab
      BEFORE UPDATE ON hf53_attribution_events_lab
      BEGIN SELECT RAISE(ABORT, 'attribution log append-only'); END;
    CREATE TRIGGER IF NOT EXISTS hf53_attribution_no_delete_lab
      BEFORE DELETE ON hf53_attribution_events_lab
      BEGIN SELECT RAISE(ABORT, 'attribution log append-only'); END;
    """)


def read_events(connection: sqlite3.Connection, numero_proposta: str | None = None) -> list[dict[str, str]]:
    if numero_proposta is None:
        rows = connection.execute(
            "SELECT payload FROM hf53_attribution_events_lab ORDER BY seq"
        ).fetchall()
    else:
        rows = connection.execute(
            "SELECT payload FROM hf53_attribution_events_lab "
            "WHERE numero_proposta = ? ORDER BY seq", (numero_proposta,)
        ).fetchall()
    return [json.loads(row[0]) for row in rows]


def current_revision(connection: sqlite3.Connection, numero_proposta: str) -> int:
    row = connection.execute(
        "SELECT MAX(seq) FROM hf53_attribution_events_lab WHERE numero_proposta = ?",
        (numero_proposta,)
    ).fetchone()
    return int(row[0] or 0)


def append_validated_event_lab(
    connection: sqlite3.Connection, *, event_id: str,
    expected_revision: int, numero_proposta: str, atendimento_id: str,
    campaign: str, decisao: str, evidencia: str, usuario: str,
    ocorrido_em: str, propostas: Iterable[Mapping[str, Any]],
    atendimentos: Iterable[Mapping[str, Any]],
) -> dict[str, str]:
    """Confirma atômica e idempotentemente um evento em conexão de TESTE.

    expected_revision protege contra duas edições simultâneas. event_id
    identifica exclusivamente o clique de confirmação (retry seguro).
    Um retry do mesmo id somente é aceito com payload exatamente idêntico.
    """
    try:
        uuid.UUID(str(event_id))
    except (TypeError, ValueError, AttributeError):
        raise ValueError("event_id deve ser um UUID.") from None
    if not isinstance(expected_revision, int) or expected_revision < 0:
        raise ValueError("Revisão inválida.")
    event = build_attribution_event(
        numero_proposta=numero_proposta, atendimento_id=atendimento_id,
        campaign=campaign, decisao=decisao, evidencia=evidencia,
        usuario=usuario, ocorrido_em=ocorrido_em,
        propostas=propostas, atendimentos=atendimentos,
    )
    encoded = json.dumps(event, ensure_ascii=False, sort_keys=True)
    connection.execute("BEGIN IMMEDIATE")
    try:
        existing = connection.execute(
            "SELECT payload FROM hf53_attribution_events_lab WHERE event_id = ?",
            (str(event_id),)
        ).fetchone()
        if existing is not None:
            if existing[0] != encoded:
                raise AttributionConflict("ID reutilizado com conteúdo diferente.")
            connection.commit()
            return event
        if current_revision(connection, event["numero_proposta"]) != expected_revision:
            raise AttributionConflict("O vínculo foi alterado. Recarregue antes de salvar.")
        connection.execute(
            "INSERT INTO hf53_attribution_events_lab "
            "(event_id, numero_proposta, atendimento_id, campaign, decisao, "
            "evidencia, usuario, ocorrido_em, payload) VALUES (?,?,?,?,?,?,?,?,?)",
            (str(event_id), event["numero_proposta"], event["atendimento_id"],
             event["campaign"], event["decisao"], event["evidencia"],
             event["usuario"], event["ocorrido_em"], encoded)
        )
        connection.commit()
    except BaseException:
        connection.rollback()
        raise
    return event


def read_effective_lab(connection: sqlite3.Connection) -> list[dict[str, str]]:
    """Deriva atribuições; não converte cliques em mensagens ou vendas."""
    return effective_attributions(read_events(connection))
