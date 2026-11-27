"""Descarte reversivel de consultas sem venda no AlphaFest Manager (HF62).

Somente prepara copias do atendimento. Nao grava no banco, nao apaga proposta,
nao altera pedido nem confunde consulta sem retorno com venda.
"""
from copy import deepcopy

from proposal_status import resumo_status

STATUS_PROTEGIDOS = frozenset({
    "Pedido aprovado", "Comprovante recebido", "Arte aprovada",
    "Em produção", "Pronto", "Entregue", "Pós-venda",
})
MOTIVOS_RETIRADA = (
    "Sem retorno do cliente",
    "Apenas consulta / especulação",
    "Cliente desistiu / não fechou",
    "Cadastro duplicado",
    "Outro",
)


def _verdadeiro(valor):
    return valor is True or (
        isinstance(valor, (int, str))
        and str(valor).strip().casefold() in ("1", "true", "sim", "yes", "aprovado")
    )


def propostas_ligadas(atendimento, historico):
    """Localiza somente vinculos explicitos, sem adivinhar pelo nome/telefone."""
    aid = str((atendimento or {}).get("id") or "").strip()
    numero = str((atendimento or {}).get("numero_proposta") or "").strip()
    return [
        p for p in (historico or []) if isinstance(p, dict) and (
            (aid and str(p.get("atendimento_id") or "").strip() == aid)
            or (numero and str(p.get("numero_proposta") or "").strip() == numero)
        )
    ]


def preparar_retirada(atendimento, motivo, atualizado_em, propostas_vinculadas=()):
    """Devolve copia arquivada. Recusa pedidos ou propostas aprovadas/em operacao."""
    if not isinstance(atendimento, dict):
        raise ValueError("Atendimento inválido.")
    if not str(atendimento.get("id") or "").strip():
        raise ValueError("O atendimento precisa de identificador para ser retirado.")
    status = str(atendimento.get("status") or "").strip()
    if status in STATUS_PROTEGIDOS:
        raise ValueError("Este atendimento já representa um pedido ou pós-venda; não pode ser descartado.")
    if status == "Arquivado":
        raise ValueError("O atendimento já está arquivado.")
    if motivo not in MOTIVOS_RETIRADA:
        raise ValueError("Selecione um motivo válido para retirar da fila.")
    for proposta in propostas_vinculadas or ():
        if not isinstance(proposta, dict):
            continue
        situacao = resumo_status(proposta)
        if any(situacao.get(campo) for campo in ("aprovado", "pago", "pronto", "entregue")) or _verdadeiro(proposta.get("confirmada")):
            raise ValueError("Há proposta vinculada aprovada ou em operação. Confira o Histórico antes de retirar.")
        status_proposta = str(proposta.get("status") or "").strip().casefold()
        if status_proposta in {"pedido aprovado", "em produção", "pronto", "entregue"}:
            raise ValueError("O status da proposta vinculada indica um pedido. Confira o Histórico.")
    resultado = deepcopy(atendimento)
    resultado["status_anterior_descarte"] = status or "Novo contato"
    resultado["status"] = "Arquivado"
    resultado["motivo_arquivamento"] = motivo
    resultado["descartado_em"] = str(atualizado_em)
    resultado["atualizado_em"] = str(atualizado_em)
    return resultado


def preparar_reativacao(atendimento, atualizado_em):
    """Restaura o estado anterior sem apagar a trilha do descarte."""
    if not isinstance(atendimento, dict) or str(atendimento.get("status") or "") != "Arquivado":
        raise ValueError("O atendimento não está arquivado.")
    anterior = str(atendimento.get("status_anterior_descarte") or "").strip()
    if not atendimento.get("descartado_em") or not anterior or anterior in STATUS_PROTEGIDOS or anterior == "Arquivado":
        raise ValueError("Este arquivamento não possui um estado anterior seguro para reativação.")
    resultado = deepcopy(atendimento)
    resultado["status"] = anterior
    resultado["descartado_em"] = ""
    resultado["reativado_em"] = str(atualizado_em)
    resultado["atualizado_em"] = str(atualizado_em)
    return resultado
