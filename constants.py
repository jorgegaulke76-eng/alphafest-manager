"""Constantes compartilhadas do FestManager.

Este arquivo inicia a modularização segura do aplicativo. Manter listas de
status e prioridades aqui evita NameError e divergências entre telas.
"""

STATUS_FLUXO = [
    "Pedido recebido",
    "Arte pendente",
    "Aguardando aprovação",
    "Pronto para produzir",
    "Em produção",
    "Pronto",
    "Entregue",
]

PRIORIDADES_FLUXO = [
    "Baixa",
    "Normal",
    "Alta",
    "Urgente",
]
