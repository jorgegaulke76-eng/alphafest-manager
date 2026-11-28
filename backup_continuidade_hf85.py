"""HF85 — diagnóstico conservador de backups do AlphaFest Manager.

Somente leitura. Não cria/restaura backups, não solicita Secrets, não modifica dados.
Recebe somente metadados mínimos e sinaliza quando a cópia não é recente.
Uma assinatura SHA-256 armazenada não significa integridade comprovada.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
import re

SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")


def _data(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return None
        return parsed.astimezone(timezone.utc)
    except (TypeError, ValueError, OverflowError):
        return None


def diagnosticar_backups(
    configuracao: dict[str, Any] | None,
    historico: list[dict[str, Any]] | None,
    *,
    agora: datetime,
    tolerancia_horas: int = 36,
) -> dict[str, Any]:
    """Emite estado e motivos apenas a partir de metadados, sem ler documentos.

    - Configuracao 'ativo' indica intencao de agendar, nao uma tarefa persistente.
    - Sem metadados suficientes, estado 'desconhecido', nunca 'saudavel'.
    - Assinatura existente nao equivale a conteudo verificado por hash.
    """
    if agora.tzinfo is None or agora.utcoffset() is None:
        raise ValueError("O instante de referencia precisa ter fuso horario.")
    if tolerancia_horas < 1 or tolerancia_horas > 24 * 30:
        raise ValueError("Tolerancia fora do limite seguro.")
    agora_utc = agora.astimezone(timezone.utc)
    cfg = configuracao if isinstance(configuracao, dict) else {}
    items = [x for x in (historico or []) if isinstance(x, dict)]
    ativo = cfg.get("ativo") is True or str(cfg.get("ativo")).strip().lower() == "true"
    candidatos = []
    for item in items:
        data = _data(item.get("criado_em"))
        if data and data <= agora_utc + timedelta(minutes=5):
            candidatos.append((data, item))
    candidatos.sort(key=lambda pair: pair[0], reverse=True)
    ultimo = candidatos[0] if candidatos else None
    registrado = _data(cfg.get("ultimo_backup_em"))
    resultado = {
        "estado": "desconhecido",
        "agendamento_ativado": ativo,
        "backups_encontrados": len(items),
        "ultimo_backup_em": ultimo[0].isoformat() if ultimo else None,
        "horas_desde_ultimo_backup": round((agora_utc - ultimo[0]).total_seconds() / 3600, 1) if ultimo else None,
        "assinatura_registrada": False,
        "integridade_comprovada": False,
        "restauracao_comprovada": False,
        "requer_acao": True,
        "motivos": [],
    }
    if not ativo:
        resultado["motivos"].append("Agendamento interno de backup não está ativado.")
    if ultimo is None:
        resultado["motivos"].append("Nenhum backup com data válida disponível nos metadados.")
        return resultado
    backup = ultimo[1]
    resultado["assinatura_registrada"] = bool(SHA256.fullmatch(str(backup.get("sha256") or "")))
    if not resultado["assinatura_registrada"]:
        resultado["motivos"].append("Backup mais recente não possui assinatura SHA-256 válida.")
    if (agora_utc - ultimo[0]) > timedelta(hours=tolerancia_horas):
        resultado["estado"] = "atrasado"
        resultado["motivos"].append("Backup mais recente excede a tolerância de horas configurada.")
    else:
        resultado["estado"] = "recente_sem_restauracao_validada"
        resultado["motivos"].append("Backup recente encontrado, mas restauração não foi comprovada.")
    if registrado is None:
        resultado["motivos"].append("Data de último backup na configuração ausente ou inválida.")
    elif registrado > agora_utc + timedelta(minutes=5):
        resultado["motivos"].append("Configuração indica data futura de backup.")
    elif abs((registrado - ultimo[0]).total_seconds()) > 3600:
        resultado["motivos"].append("Registro da configuração diverge do backup mais recente.")
    if not ativo:
        resultado["estado"] = "agendamento_inativo"
    return resultado


def metadados_backup_registro(backup: dict[str, Any]) -> dict[str, Any]:
    """Extrai somente campos seguros do documento: nunca inclui 'documentos'."""
    if not isinstance(backup, dict):
        return {}
    return {
        "criado_em": backup.get("criado_em"),
        "sha256": backup.get("sha256"),
        "tipo": backup.get("tipo"),
        "protegido": backup.get("protegido"),
    }
