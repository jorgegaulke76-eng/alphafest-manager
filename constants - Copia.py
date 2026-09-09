"""Constantes compartilhadas do FestManager.

Centralizar listas de domínio evita NameError e divergências entre telas.
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

PROCESSOS_FLUXO = [
    "Criação/ajuste de arte",
    "Papel de arroz",
    "Impressão 3D",
    "Corte/laser",
    "Balões",
    "Impressão papelaria",
    "Montagem",
    "Acabamento",
    "Conferência",
    "Embalagem",
]

PRIORIDADES_FLUXO = [
    "Baixa",
    "Normal",
    "Alta",
    "Urgente",
]
