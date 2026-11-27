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
from collections import Counter
from datetime import datetime
from statistics import median
from typing import Any, Iterable

from proposal_status import resumo_status

_STATUS_EM_PRODUCAO = "Em produção"
_STATUS_FINAIS = {"Pronto", "Entregue"}

# HF32 — revisão humana do contexto de variações. A revisão nunca apaga nem
# altera a duração observada; apenas acrescenta contexto auditado para uso futuro.
CATEGORIAS_REVISAO_CICLO = {
    "pausa_espera": "Pausa / espera",
    "retrabalho_ajuste": "Retrabalho / ajuste",
    "maquina_autonoma": "Máquina trabalhando sozinha",
    "status_atualizado_depois": "Status atualizado depois",
    "lote_atipico": "Lote / quantidade atípica",
    "ciclo_valido_longo": "Ciclo válido, duração real",
    "outro": "Outro contexto",
}
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


def chave_revisao_amostra(amostra: dict[str, Any] | None) -> str:
    """Chave estável da amostra usada pela revisão auditada da HF32."""
    a = amostra or {}
    partes = (
        str(a.get("numero_proposta") or "").strip(),
        str(a.get("tarefa_id") or a.get("id") or "").strip(),
        str(a.get("iniciado_em") or "").strip(),
        str(a.get("concluido_em") or "").strip(),
        str(int(a.get("duracao_minutos") or 0)),
    )
    return "|".join(partes)


def _mapa_revisoes_amostras(revisoes: Iterable[dict[str, Any]] | None) -> dict[str, dict[str, Any]]:
    """Mantém a revisão mais recente de cada amostra sem reescrever auditoria."""
    mapa: dict[str, dict[str, Any]] = {}
    for revisao in (revisoes or []):
        if not isinstance(revisao, dict):
            continue
        chave = str(revisao.get("chave_amostra") or "").strip()
        if not chave:
            chave = chave_revisao_amostra(revisao)
        if not chave or chave.endswith("|0"):
            continue
        atual = mapa.get(chave)
        data_nova = str(revisao.get("data_hora") or revisao.get("revisado_em") or "")
        data_atual = str((atual or {}).get("data_hora") or (atual or {}).get("revisado_em") or "")
        if atual is None or data_nova >= data_atual:
            mapa[chave] = copy.deepcopy(revisao)
    return mapa


def _mapa_propostas_oficiais(propostas: Iterable[dict[str, Any]] | None) -> dict[str, dict[str, Any]]:
    """Indexa a Fonte Única por número sem alterar nenhum registro."""
    saida: dict[str, dict[str, Any]] = {}
    for proposta in (propostas or []):
        if not isinstance(proposta, dict):
            continue
        numero = str(proposta.get("numero_proposta") or "").strip()
        if numero:
            saida[numero] = proposta
    return saida


def _fim_oficial_confiavel(
    proposta: dict[str, Any] | None,
    *,
    iniciado_em: Any,
) -> tuple[str, str] | None:
    """Retorna o primeiro fim oficial confiável posterior ao início do ciclo.

    HF30: um pedido já Pronto/Entregue não pode continuar aparecendo como ciclo
    aberto só porque o espelho ``producao_db`` foi desativado antes de reconciliar
    sua etapa final. Para não inventar duração, só fechamos amostra quando existe
    carimbo oficial de data/hora posterior ao início.
    """
    proposta = proposta or {}
    estado = resumo_status(proposta)
    dt_inicio = _parse_data(iniciado_em)
    if not dt_inicio or not (estado.get("pronto") or estado.get("entregue")):
        return None

    candidatos: list[tuple[datetime, str, str]] = []
    # ``pronto_em`` só é usado quando foi carimbado como confiável pela Fonte Única.
    if estado.get("pronto") and proposta.get("pronto_em") and bool(proposta.get("pronto_em_confiavel")):
        dt = _parse_data(proposta.get("pronto_em"))
        if dt and dt > dt_inicio:
            candidatos.append((dt, "Pronto", str(proposta.get("pronto_em"))))
    # Entrega concluída possui carimbo oficial próprio e também encerra o ciclo.
    if estado.get("entregue") and proposta.get("entregue_em"):
        dt = _parse_data(proposta.get("entregue_em"))
        if dt and dt > dt_inicio:
            candidatos.append((dt, "Entregue", str(proposta.get("entregue_em"))))

    if not candidatos:
        return None
    candidatos.sort(key=lambda x: x[0])
    _, status_final, texto = candidatos[0]
    return status_final, texto


def _amostra_fechamento_oficial(
    tarefa: dict[str, Any],
    proposta: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Deriva amostra somente leitura quando a Fonte Única já encerrou o pedido."""
    inicio = (
        tarefa.get("ciclo_observado_atual")
        if isinstance(tarefa.get("ciclo_observado_atual"), dict)
        and tarefa["ciclo_observado_atual"].get("iniciado_em")
        else inicio_aberto_timeline(tarefa)
    )
    if not inicio:
        return None
    fim = _fim_oficial_confiavel(proposta, iniciado_em=inicio.get("iniciado_em"))
    if not fim:
        return None
    status_final, concluido_em = fim
    minutos = _duracao_minutos(inicio.get("iniciado_em"), concluido_em)
    if not minutos:
        return None
    return {
        "iniciado_em": str(inicio.get("iniciado_em") or ""),
        "concluido_em": str(concluido_em or ""),
        "duracao_minutos": int(minutos),
        "iniciado_por": str(inicio.get("iniciado_por") or ""),
        "concluido_por": str((proposta or {}).get("entregue_por") or (proposta or {}).get("pronto_por") or "Fonte Única"),
        "status_final": status_final,
        "origem": "hf30_fechamento_status_oficial",
    }


def extrair_amostras(
    tarefas: Iterable[dict[str, Any]] | None,
    propostas_oficiais: Iterable[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Extrai amostras persistidas + timeline + fechamento oficial sem duplicação."""
    saida: list[dict[str, Any]] = []
    mapa_oficial = _mapa_propostas_oficiais(propostas_oficiais)
    vistos: set[tuple[str, str, str, int]] = set()
    for tarefa in (tarefas or []):
        if not isinstance(tarefa, dict):
            continue
        produto = str(tarefa.get("produto") or "Item do pedido").strip() or "Item do pedido"
        numero = str(tarefa.get("numero_proposta") or "").strip()
        processos = [str(x) for x in (tarefa.get("processos") or []) if str(x).strip()]
        candidatas = [x for x in (tarefa.get("ciclos_observados") or []) if isinstance(x, dict)]
        candidatas += amostras_timeline_legado(tarefa)
        # HF30 — se o Histórico oficial já está Pronto/Entregue, mas o espelho
        # ficou com ciclo aberto, fechar em leitura usando somente carimbo confiável.
        derivada_oficial = _amostra_fechamento_oficial(tarefa, mapa_oficial.get(numero))
        if derivada_oficial:
            inicio_derivado = str(derivada_oficial.get("iniciado_em") or "")
            if not any(str(x.get("iniciado_em") or "") == inicio_derivado for x in candidatas if isinstance(x, dict)):
                candidatas.append(derivada_oficial)
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
                "cliente_nome": str(tarefa.get("cliente_nome") or tarefa.get("cliente") or "Cliente").strip() or "Cliente",
                "tarefa_id": str(tarefa.get("id") or ""),
                "processos": processos,
                "quantidade": tarefa.get("quantidade"),
            })
    return saida



def _texto_quantidade(valor: Any) -> str:
    try:
        qtd = float(valor)
        if qtd <= 0:
            return "—"
        return str(int(qtd)) if qtd.is_integer() else f"{qtd:.2f}".rstrip("0").rstrip(".")
    except Exception:
        return "—"


def _indices_atipicos_duracao(amostras: list[dict[str, Any]]) -> set[int]:
    """HF31: sinaliza variação extrema sem excluir ou reescrever amostra.

    Usa o *modified z-score* baseado em mediana/MAD quando há pelo menos quatro
    observações. É propositalmente conservador e serve apenas como fila de
    revisão visual; capacidade e prazo continuam proibidos de usar esse sinal.
    """
    if len(amostras) < 4:
        return set()
    vals = [int(x.get("duracao_minutos") or 0) for x in amostras]
    if any(v <= 0 for v in vals):
        return set()
    med = float(median(vals))
    desvios = [abs(float(v) - med) for v in vals]
    mad = float(median(desvios))
    marcados: set[int] = set()
    if mad > 0:
        for idx, valor in enumerate(vals):
            score = 0.6745 * abs(float(valor) - med) / mad
            if score > 3.5:
                marcados.add(idx)
        return marcados

    # Quando MAD=0 (muitas durações iguais), só sinalizar discrepância grande.
    # Continua sendo aviso, nunca descarte automático.
    for idx, valor in enumerate(vals):
        diferenca = abs(float(valor) - med)
        razao = (float(valor) / med) if med > 0 else 0.0
        if diferenca >= max(60.0, med * 2.0) and (razao >= 3.0 or (razao > 0 and razao <= 1 / 3)):
            marcados.add(idx)
    return marcados


def _resumo_quantidades(amostras: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
    contador: Counter[str] = Counter()
    ordem: dict[str, float] = {}
    for amostra in amostras:
        txt = _texto_quantidade(amostra.get("quantidade"))
        if txt == "—":
            contador[txt] += 1
            ordem.setdefault(txt, float("inf"))
            continue
        contador[txt] += 1
        try:
            ordem.setdefault(txt, float(txt.replace(",", ".")))
        except Exception:
            ordem.setdefault(txt, float("inf"))
    itens = sorted(contador.items(), key=lambda kv: (ordem.get(kv[0], float("inf")), kv[0]))
    detalhes = [{"quantidade": qtd, "amostras": int(n)} for qtd, n in itens]
    texto = " · ".join(f"{qtd} un × {n}" if qtd != "—" else f"Sem qtd × {n}" for qtd, n in itens) or "—"
    return texto, detalhes

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
    propostas_oficiais: Iterable[dict[str, Any]] | None = None,
    revisoes: Iterable[dict[str, Any]] | None = None,
    limite_produtos: int = 12,
) -> dict[str, Any]:
    """Monta memória descritiva; não calcula capacidade ou promessa de prazo."""
    tarefas_lista = [x for x in (tarefas or []) if isinstance(x, dict)]
    mapa_oficial = _mapa_propostas_oficiais(propostas_oficiais)
    mapa_revisoes = _mapa_revisoes_amostras(revisoes)
    amostras = extrair_amostras(tarefas_lista, propostas_oficiais=propostas_oficiais)
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
        amostras_grupo = [x for x in grupo["amostras"] if int(x.get("duracao_minutos") or 0) > 0]
        vals = sorted(int(x.get("duracao_minutos") or 0) for x in amostras_grupo)
        if not vals:
            continue
        n = len(vals)
        nivel = "Base inicial" if n < 3 else "Base crescente" if n < 5 else "Referência observada"
        med = int(round(float(median(vals))))
        indices_atipicos = _indices_atipicos_duracao(amostras_grupo)
        amostras_atipicas = [amostras_grupo[i] for i in sorted(indices_atipicos)]
        revisadas_atipicas = [x for x in amostras_atipicas if chave_revisao_amostra(x) in mapa_revisoes]
        pendentes_atipicas = len(amostras_atipicas) - len(revisadas_atipicas)
        vals_centrais = [int(x.get("duracao_minutos") or 0) for i, x in enumerate(amostras_grupo) if i not in indices_atipicos]
        if not vals_centrais:
            vals_centrais = vals[:]  # proteção: nunca produzir faixa vazia
        vals_centrais.sort()
        lotes_texto, lotes_detalhes = _resumo_quantidades(amostras_grupo)
        if pendentes_atipicas:
            qualidade = f"Revisar {pendentes_atipicas} variação(ões)"
            if revisadas_atipicas:
                qualidade += f" · {len(revisadas_atipicas)} revisada(s)"
        elif revisadas_atipicas:
            qualidade = f"{len(revisadas_atipicas)} variação(ões) revisada(s)"
        else:
            qualidade = "Base em formação" if n < 5 else "Sem variação extrema sinalizada"
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
            "faixa_central_minimo": formatar_duracao(vals_centrais[0]),
            "faixa_central_maximo": formatar_duracao(vals_centrais[-1]),
            "amostras_atipicas": len(amostras_atipicas),
            "amostras_atipicas_pendentes": int(pendentes_atipicas),
            "amostras_atipicas_revisadas": len(revisadas_atipicas),
            "qualidade": qualidade,
            "lotes_observados": lotes_texto,
            "lotes_detalhes": lotes_detalhes,
            "quantidade_observada": faixa_qtd,
            "nivel": nivel,
            "processos": sorted(str(x) for x in grupo["processos"] if str(x).strip()),
        })
    linhas.sort(key=lambda x: (-int(x.get("amostras") or 0), str(x.get("produto") or "").casefold()))

    em_andamento = 0
    sem_inicio = 0
    finalizados_sem_fim_confiavel = 0
    ciclos_em_andamento: list[dict[str, Any]] = []
    ciclos_sem_inicio: list[dict[str, Any]] = []
    for tarefa in tarefas_lista:
        if _status(tarefa.get("status")) != _STATUS_EM_PRODUCAO:
            continue
        numero_tarefa = str(tarefa.get("numero_proposta") or "").strip()
        proposta_oficial = mapa_oficial.get(numero_tarefa)
        estado_oficial = resumo_status(proposta_oficial) if proposta_oficial else {}
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
        # HF30 — Fonte Única final prevalece sobre status operacional residual.
        # Um pedido Pronto/Entregue nunca continua como ciclo aberto. Se não houver
        # carimbo de fim confiável, apenas deixamos de chamá-lo de "em andamento";
        # nenhuma duração é inventada.
        if estado_oficial.get("pronto") or estado_oficial.get("entregue"):
            if inicio_atual and not _fim_oficial_confiavel(proposta_oficial, iniciado_em=inicio_atual.get("iniciado_em")):
                finalizados_sem_fim_confiavel += 1
            continue
        if tarefa.get("ativa") is False:
            continue
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

    # HF31/HF32 — variações continuam preservadas; a HF32 permite registrar
    # contexto humano auditado sem apagar, corrigir ou excluir a duração.
    amostras_variacao: list[dict[str, Any]] = []
    amostras_para_revisar: list[dict[str, Any]] = []
    amostras_revisadas: list[dict[str, Any]] = []
    for grupo in grupos.values():
        amostras_grupo = [x for x in grupo.get("amostras", []) if int(x.get("duracao_minutos") or 0) > 0]
        if len(amostras_grupo) < 4:
            continue
        med_grupo = int(round(float(median([int(x.get("duracao_minutos") or 0) for x in amostras_grupo]))))
        for idx in sorted(_indices_atipicos_duracao(amostras_grupo)):
            amostra = copy.deepcopy(amostras_grupo[idx])
            chave = chave_revisao_amostra(amostra)
            revisao = copy.deepcopy(mapa_revisoes.get(chave) or {})
            codigo = str(revisao.get("categoria") or "").strip()
            amostra["chave_revisao"] = chave
            amostra["mediana_produto_minutos"] = med_grupo
            amostra["motivo_revisao"] = (
                f"Duração {formatar_duracao(amostra.get('duracao_minutos'))} muito distante da mediana "
                f"observada de {formatar_duracao(med_grupo)}; sinal para conferência, sem exclusão automática."
            )
            amostra["revisao_registrada"] = bool(revisao)
            amostra["revisao"] = revisao
            amostra["revisao_categoria_label"] = str(
                revisao.get("categoria_label") or CATEGORIAS_REVISAO_CICLO.get(codigo) or codigo
            ).strip()
            amostras_variacao.append(amostra)
            if revisao:
                amostras_revisadas.append(amostra)
            else:
                amostras_para_revisar.append(amostra)
    ordem_variacao = lambda x: (str(x.get("produto") or "").casefold(), -int(x.get("duracao_minutos") or 0))
    amostras_variacao.sort(key=ordem_variacao)
    amostras_para_revisar.sort(key=ordem_variacao)
    amostras_revisadas.sort(key=ordem_variacao)

    return {
        "total_amostras": len(amostras),
        "produtos_com_amostras": len(linhas),
        "em_andamento_com_inicio": em_andamento,
        "em_producao_sem_inicio_confiavel": sem_inicio,
        "finalizados_sem_fim_confiavel": finalizados_sem_fim_confiavel,
        "amostras_variacao": amostras_variacao,
        "total_variacoes_detectadas": len(amostras_variacao),
        "amostras_para_revisar": amostras_para_revisar,
        "total_amostras_para_revisar": len(amostras_para_revisar),
        "amostras_revisadas": amostras_revisadas,
        "total_amostras_revisadas": len(amostras_revisadas),
        "ciclos_em_andamento": ciclos_em_andamento,
        "ciclos_sem_inicio_confiavel": ciclos_sem_inicio,
        "produtos": linhas[: max(1, int(limite_produtos or 12))],
    }
