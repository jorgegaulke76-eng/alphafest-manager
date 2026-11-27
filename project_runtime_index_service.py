"""Índice de leitura para Projetos / Memória da Empresa.

HF41: consolida textos de busca, métricas e vínculos por proposta para evitar
revarrer a memória de projetos e o Histórico a cada cartão/rerun. O módulo é
puro e somente leitura; nenhuma regra de gravação de Projetos é alterada.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class ProjectRuntimeIndex:
    items: tuple[dict[str, Any], ...]
    by_id: dict[str, dict[str, Any]]
    by_proposal: dict[str, dict[str, Any]]
    search_text_by_object: dict[int, str]
    models_count: int
    favorites_count: int
    active_files_count: int


def _components_text(project: dict[str, Any] | None) -> str:
    project = project or {}
    data = project.get("componentes", {})
    if not isinstance(data, dict):
        return ""
    parts: list[str] = []
    for category, values in data.items():
        parts.append(str(category))
        if isinstance(values, (list, tuple, set)):
            parts.extend(str(v) for v in values)
        elif values:
            parts.append(str(values))
    return " ".join(parts)


def project_search_text(project: dict[str, Any] | None) -> str:
    """Replica o texto usado historicamente na busca da Memória da Empresa."""
    project = project or {}
    parts: list[Any] = [
        project.get("id", ""),
        project.get("numero_proposta", ""),
        project.get("cliente_nome", ""),
        project.get("whatsapp", ""),
        project.get("tema", ""),
        project.get("observacoes", ""),
        " ".join(str(v) for v in (project.get("produtos", []) or [])),
        _components_text(project),
        project.get("caracteristicas_livres", ""),
        project.get("necessidade", ""),
        project.get("detalhes", ""),
    ]
    for file_info in project.get("arquivos", []) or []:
        if not isinstance(file_info, dict):
            continue
        parts.extend([
            file_info.get("nome", ""),
            file_info.get("categoria", ""),
            file_info.get("descricao", ""),
            " ".join(str(v) for v in (file_info.get("tags", []) or [])),
        ])
    return " ".join(str(v) for v in parts).lower()


def build_project_runtime_index(projects: Iterable[dict[str, Any]] | None) -> ProjectRuntimeIndex:
    items = tuple(p for p in (projects or []) if isinstance(p, dict))
    by_id: dict[str, dict[str, Any]] = {}
    by_proposal: dict[str, dict[str, Any]] = {}
    search_text_by_object: dict[int, str] = {}
    models = favorites = active_files = 0

    for project in items:
        pid = str(project.get("id") or "").strip()
        if pid and pid not in by_id:
            by_id[pid] = project
        proposal = str(project.get("numero_proposta") or "").strip()
        if proposal and proposal not in by_proposal:
            by_proposal[proposal] = project
        search_text_by_object[id(project)] = project_search_text(project)
        if project.get("modelo"):
            models += 1
        if project.get("favorito"):
            favorites += 1
        active_files += sum(
            1 for file_info in (project.get("arquivos", []) or [])
            if isinstance(file_info, dict) and not file_info.get("arquivado")
        )

    return ProjectRuntimeIndex(
        items=items,
        by_id=by_id,
        by_proposal=by_proposal,
        search_text_by_object=search_text_by_object,
        models_count=models,
        favorites_count=favorites,
        active_files_count=active_files,
    )


def filter_projects(
    index: ProjectRuntimeIndex,
    term: str = "",
    mode: str = "Todos",
) -> list[dict[str, Any]]:
    needle = str(term or "").strip().lower()
    result: list[dict[str, Any]] = []
    for project in index.items:
        if needle and needle not in index.search_text_by_object.get(id(project), project_search_text(project)):
            continue
        if mode == "Modelos reutilizáveis" and not project.get("modelo"):
            continue
        if mode == "Favoritos" and not project.get("favorito"):
            continue
        result.append(project)
    return result


def proposal_map(history: Iterable[dict[str, Any]] | None) -> dict[str, dict[str, Any]]:
    """Número da proposta -> registro histórico, preservando a primeira ocorrência."""
    result: dict[str, dict[str, Any]] = {}
    for proposal in history or []:
        if not isinstance(proposal, dict):
            continue
        number = str(proposal.get("numero_proposta") or "").strip()
        if number and number not in result:
            result[number] = proposal
    return result
