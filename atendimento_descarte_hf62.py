"""Retirada reversivel de consultas sem venda da Caixa Unificada (HF62).

Nao apaga atendimentos, propostas ou pedidos. O historico permanece acessivel
pelo filtro 'Mostrar arquivados'. Sem conexao com banco nesta camada.
"""
from copy import deepcopy

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
    return valor is True or (isinstance(valor, (int, str)) and str(valor).strip().casefold() in ("1", "true", "sim", "yes"))


def preparar_retirada(atendimento, motivo, atualizado_em, propostas_vinculadas=()):
    """Devolve uma copia arquivada; recusa pedidos e propostas aprovadas.

    As propostas informadas ja devem estar filtradas por atendimento_id, ou
    por numero_proposta registrado neste atendimento. Nao altera propostas.
    """
    if not isinstance(atendimento, dict):
        raise ValueError("Atendimento inválido.")
    if not str(atendimento.get("id") or "").strip():
        raise ValueError("O atendimento precisa de identificador para ser retirado.")
    if str(atendimento.get("status") or "") in STATUS_PROTEGIDOS:
        raise ValueError("Este atendimento já representa um pedido ou pós-venda; não pode ser descartado.")
    if str(atendimento.get("status") or "") == "Arquivado":
        raise ValueError("O atendimento já está arquivado.")
    if motivo not in MOTIVOS_RETIRADA:
        raise ValueError("Selecione um motivo válido para retirar da fila.")
    for proposta in propostas_vinculadas or ():
        if not isinstance(proposta, dict):
            continue
        if any(_verdadeiro(proposta.get(campo)) for campo in ("aprovado", "pago", "pronto", "entregue", "confirmada")):
            raise ValueError("Há uma proposta vinculada aprovada ou em operação. Confira o Histórico antes de retirar.")
    resultado = deepcopy(atendimento)
    resultado["status"] = "Arquivado"
    resultado["motivo_arquivamento"] = motivo
    resultado["descartado_em"] = str(atualizado_em)
    resultado["atualizado_em"] = str(atualizado_em)
    return resultado
