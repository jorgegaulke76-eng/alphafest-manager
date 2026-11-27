"""Índice leve para produtos dos Relatórios AlphaFest.

HF50: evita repetir o saneamento completo de nomes históricos contra o Catálogo
para cada item de proposta exibido nos relatórios. O módulo é somente leitura e
preserva a função oficial de resolução fornecida pelo app.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Sequence


NormalizeFn = Callable[[Any], str]
ResolveOfficialFn = Callable[[Any, Sequence[Mapping[str, Any]]], str]


@dataclass
class ReportsProductResolver:
    catalog: Sequence[Mapping[str, Any]]
    normalize: NormalizeFn
    resolve_official_name: ResolveOfficialFn
    graphical_name_map: dict[str, str]
    _cache: dict[str, str] = field(default_factory=dict)

    def resolve_official(self, raw_name: Any) -> str:
        original = str(raw_name or "").strip() or "Não informado"
        cached = self._cache.get(original)
        if cached is not None:
            return cached
        official = str(self.resolve_official_name(original, self.catalog) or original).strip() or original
        self._cache[original] = official
        return official

    def graphical_name(self, normalized_key: str, default: str = "") -> str:
        return str(self.graphical_name_map.get(str(normalized_key or ""), default) or default)

    @property
    def cache_size(self) -> int:
        return len(self._cache)


def build_reports_product_resolver(
    catalog: Sequence[Mapping[str, Any]] | None,
    historical_names: Sequence[Any] | None,
    *,
    normalize: NormalizeFn,
    resolve_official_name: ResolveOfficialFn,
) -> ReportsProductResolver:
    """Monta cache de resolução e mapa de grafias canônicas do relatório.

    O mapa gráfico replica a regra anterior do app: quando houver produto oficial
    com a mesma identidade normalizada, ele vence. Caso contrário, escolhe a
    variante histórica legível preferindo grafias que não estejam inteiramente em
    CAIXA ALTA, depois menor comprimento e ordem casefold.
    """
    cat = list(catalog or [])
    groups: dict[str, list[str]] = {}
    for raw in historical_names or []:
        name = str(raw or "").strip()
        if not name:
            continue
        key = normalize(name)
        if key:
            groups.setdefault(key, []).append(name)

    official_by_identity: dict[str, str] = {}
    for product in cat:
        name = str((product or {}).get("Nome") or "").strip()
        key = normalize(name)
        if key and key not in official_by_identity:
            official_by_identity[key] = name

    graphical_map: dict[str, str] = {}
    for key, variants in groups.items():
        official = official_by_identity.get(key, "")
        if official:
            canonical = official
        else:
            canonical = sorted(
                set(variants),
                key=lambda x: (str(x).isupper(), len(str(x)), str(x).casefold()),
            )[0]
        graphical_map[key] = canonical

    return ReportsProductResolver(
        catalog=cat,
        normalize=normalize,
        resolve_official_name=resolve_official_name,
        graphical_name_map=graphical_map,
    )
