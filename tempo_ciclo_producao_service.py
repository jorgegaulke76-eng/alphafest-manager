"""20.4.9-I8.13.5-HF27 — memória de tempo de ciclo observado.

O objetivo deste serviço NÃO é medir mão de obra nem prometer capacidade exata.
Ele registra o intervalo observado entre uma transição explícita para
``Em produção`` e a conclusão em ``Pronto``/``Entregue``. Esse intervalo pode
incluir pausas, espera e tempo de máquina autônoma; portanto é tratado como
*tempo de ciclo observado*.

O módulo é puro: não conhece Streamlit, Supabase ou arquivos. O chamador decide
como persistir os metadados adicionados às tarefas do Fluxo.
"""
from __future__ import annotations

import copy
import re
from datetime import datetime
from statistics import median
from typing import Any, Iterable

_STATUS_EM_PRODUCAO = "Em produção"
_STATUS_FINAIS = {"Pronto", "Entregue"}
_FORMATOS_DATA = (
    "%d/%m/%Y %H:%M:%S",
    "%d/%m/%Y %H:%M",
    "%Y-%m-%dT%H:%M:%S.%f",
    "%Y-%m-%dT%H:%M:%S",
)


def _status(valor: Any) -> str:
    txt = str(valor or "").strip()
    mapa = {
        "em producao": "Em produção",
        "em produção": "Em produção",
        "pronto": "Pronto",
        "entregue": "Entregue",
        "pronto para produzir": "Pronto para produzir",
        "arte pendente": "Arte pendente",
        "aguardando aprovação": "Aguardando aprovação",
        "pedido recebido": "Pedido recebido",
    }
    return mapa.get(txt.casefold(), txt)


def _parse_data(valor: Any) -> datetime | None:
    if isinstance(valor, datetime):
        return valor
    txt = str(valor or "").strip()
    if not txt:
        return None
    # ISO com timezone: remove apenas o sufixo Z e deixa fromisoformat tentar.
    try:
        return datetime.fromisoformat(txt.replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        pass
    for fmt in _FORMATOS_DATA:
        try:
            return datetime.strptime(txt, fmt)
        except Exception:
            continue
    return None


def _duracao_minutos(inicio: Any, fim: Any) -> int | None:
    dt_ini = _parse_data(inicio)
    dt_fim = _parse_data(fim)
    if not dt_ini or not dt_fim or dt_fim <= dt_ini:
        return None
    minutos = int(round((dt_fim - dt_ini).total_seconds() / 60.0))
    return minutos if minutos > 0 else None


def inicio_aberto_timeline(tarefa: dict[str, Any] | None) -> dict[str, Any] | None:
    """Recupera um início explícito ainda aberto na timeline do Fluxo."""
    inicio: dict[str, Any] | None = None
    for evento in [x for x in ((tarefa or {}).get("timeline") or []) if isinstance(x, dict)]:
        antes, depois = _transicao_da_descricao(evento.get("descricao"))
        momento = str(evento.get("data") or evento.get("em") or "").strip()
        if depois == _STATUS_EM_PRODUCAO:
            inicio = {
                "iniciado_em": momento,
                "iniciado_por": str(evento.get("usuario") or ""),
                "origem": "timeline_fluxo_recuperada",
            }
            continue
        if inicio and depois in _STATUS_FINAIS:
            inicio = None
        elif inicio and antes == _STATUS_EM_PRODUCAO and depois not in (None, _STATUS_EM_PRODUCAO):
            inicio = None
    return inicio


def aplicar_transicao_ciclo(
    tarefa: dict[str, Any] | None,
    status_anterior: Any,
    status_novo: Any,
    *,
    now_text: str,
    usuario_nome: str = "Sistema",
) -> dict[str, Any]:
    """Retorna cópia da tarefa com metadados de ciclo coerentes com a transição.

    Regras:
    - entrar explicitamente em ``Em produção`` abre um ciclo se ainda não houver;
    - sair de ``Em produção`` para ``Pronto``/``Entregue`` fecha uma amostra;
    - sair de ``Em produção`` para outra etapa interrompe a coleta sem gerar
      amostra, pois o intervalo deixou de representar um ciclo contínuo;
    - pular direto para ``Pronto`` não inventa início retroativo.
    """
    t = copy.deepcopy(tarefa or {})
    antes = _status(status_anterior)
    depois = _status(status_novo)
    agora = str(now_text or "").strip()
    usuario = str(usuario_nome or "Sistema").strip() or "Sistema"

    atual = t.get("ciclo_observado_atual") if isinstance(t.get("ciclo_observado_atual"), dict) else None

    if depois == _STATUS_EM_PRODUCAO and antes != _STATUS_EM_PRODUCAO:
        if not atual:
            t["ciclo_observado_atual"] = {
                "iniciado_em": agora,
                "iniciado_por": usuario,
                "origem": "transicao_fluxo",
            }
        return t

    if antes == _STATUS_EM_PRODUCAO and depois in _STATUS_FINAIS:
        if not atual:
            atual = inicio_aberto_timeline(t)
        if atual:
            minutos = _duracao_minutos(atual.get("iniciado_em"), agora)
            if minutos:
                amostras = t.get("ciclos_observados") if isinstance(t.get("ciclos_observados"), list) else []
                amostra = {
                    "iniciado_em": str(atual.get("iniciado_em") or ""),
                    "concluido_em": agora,
                    "duracao_minutos": int(minutos),
                    "iniciado_por": str(atual.get("iniciado_por") or ""),
                    "concluido_por": usuario,
                    "status_final": depois,
                    "origem": (
                        "hf27_transicao_confirmada"
                        if str(atual.get("origem") or "") != "timeline_fluxo_recuperada"
                        else "hf27_fechamento_com_inicio_recuperado"
                    ),
                }
                chave = (amostra["iniciado_em"], amostra["concluido_em"], amostra["duracao_minutos"])
                ja_existe = any(
                    isinstance(x, dict)
                    and (str(x.get("iniciado_em") or ""), str(x.get("concluido_em") or ""), int(x.get("duracao_minutos") or 0)) == chave
                    for x in amostras
                )
                if not ja_existe:
                    amostras.append(amostra)
                    t["ciclos_observados"] = amostras[-30:]
                    t["ultimo_ciclo_observado_minutos"] = int(minutos)
                    t["ultimo_ciclo_observado_em"] = agora
        t.pop("ciclo_observado_atual", None)
        return t

    if antes == _STATUS_EM_PRODUCAO and depois != _STATUS_EM_PRODUCAO:
        # Mudou para uma etapa não final: não transformar espera/retorno em amostra.
        if atual:
            t["ciclo_observado_interrompido_em"] = agora
            t["ciclo_observado_interrompido_motivo"] = f"Transição para {depois or 'outra etapa'}"
        t.pop("ciclo_observado_atual", None)
    return t


def _transicao_da_descricao(descricao: Any) -> tuple[str | None, str | None]:
    txt = str(descricao or "").strip()
    if not txt:
        return None, None
    # Eventos atuais do Fluxo/Central: "X → Y" ou "de X para Y".
    m = re.search(r"(.+?)\s*[→>-]+\s*(Em produção|Pronto|Entregue)\b", txt, flags=re.I)
    if m:
        return _status(m.group(1).strip()), _status(m.group(2).strip())
    m = re.search(r"\bde\s+(.+?)\s+para\s+(Em produção|Pronto|Entregue)\b", txt, flags=re.I)
    if m:
        return _status(m.group(1).strip()), _status(m.group(2).strip())
    low = txt.casefold()
    if "produção iniciada" in low or "producao iniciada" in low:
        return None, _STATUS_EM_PRODUCAO
    if "marcado como pronto" in low or "pedido pronto" in low:
        return _STATUS_EM_PRODUCAO, "Pronto"
    return None, None


def amostras_timeline_legado(tarefa: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Recupera apenas pares explícitos Em produção -> Pronto/Entregue da timeline.

    Serve para leitura histórica inicial. Não persiste nem altera a tarefa.
    """
    tarefa = tarefa or {}
    eventos = [x for x in (tarefa.get("timeline") or []) if isinstance(x, dict)]
    inicio: dict[str, Any] | None = None
    saida: list[dict[str, Any]] = []
    for evento in eventos:
        antes, depois = _transicao_da_descricao(evento.get("descricao"))
        momento = str(evento.get("data") or evento.get("em") or "").strip()
        if depois == _STATUS_EM_PRODUCAO:
            inicio = {"em": momento, "usuario": str(evento.get("usuario") or "")}
            continue
        if depois in _STATUS_FINAIS and inicio:
            minutos = _duracao_minutos(inicio.get("em"), momento)
            if minutos:
                saida.append({
                    "iniciado_em": str(inicio.get("em") or ""),
                    "concluido_em": momento,
                    "duracao_minutos": int(minutos),
                    "iniciado_por": str(inicio.get("usuario") or ""),
                    "concluido_por": str(evento.get("usuario") or ""),
                    "status_final": depois,
                    "origem": "timeline_fluxo_recuperada",
                })
            inicio = None
        elif antes == _STATUS_EM_PRODUCAO and depois not in (None, _STATUS_EM_PRODUCAO):
            inicio = None
    return saida


def _chave_amostra(amostra: dict[str, Any]) -> tuple[str, str, int]:
    return (
        str(amostra.get("iniciado_em") or ""),
        str(amostra.get("concluido_em") or ""),
        int(amostra.get("duracao_minutos") or 0),
    )


def extrair_amostras(tarefas: Iterable[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """Extrai amostras persistidas + histórico explícito sem duplicação."""
    saida: list[dict[str, Any]] = []
    vistos: set[tuple[str, str, str, int]] = set()
    for tarefa in (tarefas or []):
        if not isinstance(tarefa, dict):
            continue
        produto = str(tarefa.get("produto") or "Item do pedido").strip() or "Item do pedido"
        numero = str(tarefa.get("numero_proposta") or "").strip()
        processos = [str(x) for x in (tarefa.get("processos") or []) if str(x).strip()]
        candidatas = [x for x in (tarefa.get("ciclos_observados") or []) if isinstance(x, dict)]
        candidatas += amostras_timeline_legado(tarefa)
        for amostra in candidatas:
            minutos = int(amostra.get("duracao_minutos") or 0)
            if minutos <= 0:
                continue
            base = _chave_amostra(amostra)
            chave = (str(tarefa.get("id") or numero or produto), base[0], base[1], base[2])
            if chave in vistos:
                continue
            vistos.add(chave)
            saida.append({
                **copy.deepcopy(amostra),
                "produto": produto,
                "numero_proposta": numero,
                "tarefa_id": str(tarefa.get("id") or ""),
                "processos": processos,
                "quantidade": tarefa.get("quantidade"),
            })
    return saida


def formatar_duracao(minutos: Any) -> str:
    try:
        total = max(0, int(round(float(minutos or 0))))
    except Exception:
        total = 0
    if total < 60:
        return f"{total} min"
    horas, mins = divmod(total, 60)
    if horas < 24:
        return f"{horas}h {mins:02d}min" if mins else f"{horas}h"
    dias, horas = divmod(horas, 24)
    return f"{dias}d {horas}h" if horas else f"{dias}d"


def resumir_tempos_observados(
    tarefas: Iterable[dict[str, Any]] | None,
    *,
    limite_produtos: int = 12,
) -> dict[str, Any]:
    """Monta memória descritiva; não calcula capacidade ou promessa de prazo."""
    tarefas_lista = [x for x in (tarefas or []) if isinstance(x, dict)]
    amostras = extrair_amostras(tarefas_lista)
    grupos: dict[str, dict[str, Any]] = {}
    for amostra in amostras:
        produto = str(amostra.get("produto") or "Item do pedido").strip() or "Item do pedido"
        chave = re.sub(r"\s+", " ", produto).casefold()
        grupo = grupos.setdefault(chave, {"produto": produto, "amostras": [], "processos": set(), "quantidades": []})
        grupo["amostras"].append(amostra)
        grupo["processos"].update(amostra.get("processos") or [])
        try:
            qtd = float(amostra.get("quantidade"))
            if qtd > 0:
                grupo["quantidades"].append(qtd)
        except Exception:
            pass

    linhas: list[dict[str, Any]] = []
    for grupo in grupos.values():
        vals = sorted(int(x.get("duracao_minutos") or 0) for x in grupo["amostras"] if int(x.get("duracao_minutos") or 0) > 0)
        if not vals:
            continue
        n = len(vals)
        nivel = "Base inicial" if n < 3 else "Base crescente" if n < 5 else "Referência observada"
        med = int(round(float(median(vals))))
        quantidades = sorted(float(x) for x in grupo.get("quantidades") or [] if float(x) > 0)
        if quantidades:
            qmin, qmax = quantidades[0], quantidades[-1]
            def _qtxt(q):
                return str(int(q)) if float(q).is_integer() else (f"{q:.2f}".rstrip("0").rstrip("."))
            faixa_qtd = _qtxt(qmin) if qmin == qmax else f"{_qtxt(qmin)} a {_qtxt(qmax)}"
        else:
            faixa_qtd = "—"
        linhas.append({
            "produto": grupo["produto"],
            "amostras": n,
            "mediana_minutos": med,
            "mediana": formatar_duracao(med),
            "minimo": formatar_duracao(vals[0]),
            "maximo": formatar_duracao(vals[-1]),
            "quantidade_observada": faixa_qtd,
            "nivel": nivel,
            "processos": sorted(str(x) for x in grupo["processos"] if str(x).strip()),
        })
    linhas.sort(key=lambda x: (-int(x.get("amostras") or 0), str(x.get("produto") or "").casefold()))

    em_andamento = 0
    sem_inicio = 0
    ciclos_em_andamento: list[dict[str, Any]] = []
    ciclos_sem_inicio: list[dict[str, Any]] = []
    for tarefa in tarefas_lista:
        if _status(tarefa.get("status")) != _STATUS_EM_PRODUCAO:
            continue
        inicio_atual = (
            tarefa.get("ciclo_observado_atual")
            if isinstance(tarefa.get("ciclo_observado_atual"), dict)
            and tarefa["ciclo_observado_atual"].get("iniciado_em")
            else inicio_aberto_timeline(tarefa)
        )
        detalhe_base = {
            "numero_proposta": str(tarefa.get("numero_proposta") or "").strip(),
            "cliente_nome": str(tarefa.get("cliente_nome") or tarefa.get("cliente") or "Cliente").strip() or "Cliente",
            "produto": str(tarefa.get("produto") or "Item do pedido").strip() or "Item do pedido",
            "quantidade": tarefa.get("quantidade"),
            "tarefa_id": str(tarefa.get("id") or ""),
        }
        if inicio_atual:
            em_andamento += 1
            ciclos_em_andamento.append({
                **detalhe_base,
                "iniciado_em": str(inicio_atual.get("iniciado_em") or "").strip(),
                "iniciado_por": str(inicio_atual.get("iniciado_por") or "").strip(),
                "origem_inicio": str(inicio_atual.get("origem") or "").strip(),
            })
        else:
            # Não presumir início: só aceitamos metadado HF27 ou evento explícito da timeline.
            sem_inicio += 1
            ciclos_sem_inicio.append(detalhe_base)

    def _ordem_inicio(item: dict[str, Any]) -> tuple[int, str]:
        dt = _parse_data(item.get("iniciado_em"))
        if dt:
            return (0, dt.isoformat())
        return (1, str(item.get("numero_proposta") or item.get("produto") or "").casefold())

    ciclos_em_andamento.sort(key=_ordem_inicio)
    ciclos_sem_inicio.sort(key=lambda x: str(x.get("numero_proposta") or x.get("produto") or "").casefold())

    return {
        "total_amostras": len(amostras),
        "produtos_com_amostras": len(linhas),
        "em_andamento_com_inicio": em_andamento,
        "em_producao_sem_inicio_confiavel": sem_inicio,
        "ciclos_em_andamento": ciclos_em_andamento,
        "ciclos_sem_inicio_confiavel": ciclos_sem_inicio,
        "produtos": linhas[: max(1, int(limite_produtos or 12))],
    }
