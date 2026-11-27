"""Runtime index for THU Marketing Intelligence.

HF46: memoizes product resolution against the official Catalog during one
analysis run and lets the caller share the already-normalized social history.
The business rules stay in app.py; this module only removes repeated work.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Sequence


NormalizeFn = Callable[[Any], str]
ResolveFn = Callable[[Any, Sequence[Mapping[str, Any]]], tuple[Any, Any, Mapping[str, Any]]]


@dataclass
class MarketingProductResolver:
    catalog: Sequence[Mapping[str, Any]]
    normalize: NormalizeFn
    resolve_sanitized: ResolveFn
    _cache: dict[str, tuple[str, bool]] = field(default_factory=dict)

    def resolve(self, name: Any) -> tuple[str, bool]:
        original = str(name or "").strip()
        if not original:
            return "", False
        key = self.normalize(original) or original.casefold()
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        _, product, _ = self.resolve_sanitized(original, self.catalog)
        official = str((product or {}).get("Nome") or original).strip()
        result = (official, product is not None)
        self._cache[key] = result
        return result

    def official_name(self, name: Any) -> str:
        return self.resolve(name)[0]

    def exists(self, name: Any) -> bool:
        return self.resolve(name)[1]

    @property
    def cache_size(self) -> int:
        return len(self._cache)


def build_marketing_product_resolver(
    catalog: Sequence[Mapping[str, Any]] | None,
    *,
    normalize: NormalizeFn,
    resolve_sanitized: ResolveFn,
) -> MarketingProductResolver:
    return MarketingProductResolver(
        catalog=list(catalog or []),
        normalize=normalize,
        resolve_sanitized=resolve_sanitized,
    )
