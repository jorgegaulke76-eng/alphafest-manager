"""Inteligência visual central do Alpha Marketing Studio.

Mantém tipografia, paletas e integração com o Calendário Comercial em uma
única fonte de regras. O módulo não cria nem persiste um segundo calendário.
"""
from __future__ import annotations

import re
from datetime import date
from typing import Any, Iterable

TYPOGRAPHY_RULES: dict[str, dict[str, Any]] = {
    "title": {"min_px": 82, "max_px": 118, "max_lines": 3, "weight": "extra-bold", "case": "title"},
    "banner": {"min_px": 30, "max_px": 46, "max_lines": 2, "weight": "bold", "case": "sentence"},
    "benefit_title": {"min_px": 24, "max_px": 34, "max_lines": 1, "weight": "bold", "case": "upper"},
    "benefit_body": {"min_px": 18, "max_px": 24, "max_lines": 2, "weight": "regular", "case": "sentence"},
    "cta": {"min_px": 44, "max_px": 62, "max_lines": 1, "weight": "extra-bold", "case": "upper"},
    "phone": {"min_px": 40, "max_px": 56, "max_lines": 1, "weight": "bold", "case": "none"},
    "footer": {"min_px": 17, "max_px": 24, "max_lines": 1, "weight": "bold", "case": "upper"},
}

THEMES: dict[str, dict[str, Any]] = {
    "alphafest": {
        "label": "AlphaFest Clássico",
        "keywords": (),
        "palette": {"primary": "#0B63CE", "secondary": "#32B8F3", "accent": "#F0208B", "background": "#FFFFFF", "text": "#123A78", "metallic": "#FFD54F"},
        "decorations": ["formas líquidas azuis", "respingos 3D", "brilhos coloridos"],
        "mood": "moderno, comercial, alegre e premium",
    },
    "natal": {
        "label": "Natal",
        "keywords": ("natal", "natalino", "papai noel", "ceia"),
        "palette": {"primary": "#B71C1C", "secondary": "#1B5E20", "accent": "#D4AF37", "background": "#FFFDF7", "text": "#7A1515", "metallic": "#D4AF37"},
        "decorations": ["estrelas douradas", "laços", "pinheiros sutis", "brilhos e neve delicada"],
        "mood": "festivo, acolhedor e elegante",
    },
    "ano_novo": {
        "label": "Ano Novo",
        "keywords": ("ano novo", "réveillon", "reveillon", "virada"),
        "palette": {"primary": "#FFFFFF", "secondary": "#D4AF37", "accent": "#C0C0C0", "background": "#F9F9F7", "text": "#7B641A", "metallic": "#D4AF37"},
        "decorations": ["fogos elegantes", "confetes dourados", "luzes e brilhos metálicos"],
        "mood": "sofisticado, luminoso e celebrativo",
    },
    "pascoa": {
        "label": "Páscoa",
        "keywords": ("páscoa", "pascoa", "coelho", "ovos de chocolate"),
        "palette": {"primary": "#6D4C41", "secondary": "#D7CCC8", "accent": "#B39DDB", "background": "#FFF8E7", "text": "#4E342E", "metallic": "#C99A5B"},
        "decorations": ["texturas de chocolate", "ovos", "coelhos sutis", "fitas em tons pastel"],
        "mood": "delicado, doce e acolhedor",
    },
    "outubro_rosa": {
        "label": "Outubro Rosa",
        "keywords": ("outubro rosa", "câncer de mama", "cancer de mama"),
        "palette": {"primary": "#EC407A", "secondary": "#F8BBD0", "accent": "#AD1457", "background": "#FFF7FA", "text": "#8E1748", "metallic": "#F4A6C2"},
        "decorations": ["laços rosas", "formas suaves", "brilhos delicados"],
        "mood": "acolhedor, delicado e institucional",
    },
    "novembro_azul": {
        "label": "Novembro Azul",
        "keywords": ("novembro azul", "saúde do homem", "saude do homem"),
        "palette": {"primary": "#1565C0", "secondary": "#90CAF9", "accent": "#0D47A1", "background": "#F4FAFF", "text": "#0D47A1", "metallic": "#64B5F6"},
        "decorations": ["laços azuis", "formas institucionais", "luzes suaves"],
        "mood": "institucional, confiante e acolhedor",
    },
    "batizado_comunhao": {
        "label": "Batizado / 1ª Comunhão",
        "keywords": ("batizado", "batismo", "1ª comunhão", "1a comunhão", "primeira comunhão"),
        "palette": {"primary": "#FFFFFF", "secondary": "#E8D7A8", "accent": "#D4AF37", "background": "#FFFEFA", "text": "#8C7222", "metallic": "#D4AF37"},
        "decorations": ["luz suave", "arabescos dourados", "estrelas delicadas", "trigo ou cruz discreta"],
        "mood": "sereno, delicado e elegante",
    },
    "black_friday": {
        "label": "Black Friday",
        "keywords": ("black friday", "black", "mega promoção", "megapromoção"),
        "palette": {"primary": "#111111", "secondary": "#2C2C2C", "accent": "#FFD600", "background": "#080808", "text": "#FFFFFF", "metallic": "#FFD600"},
        "decorations": ["etiquetas de desconto", "raios", "contraste forte", "brilhos amarelos"],
        "mood": "urgente, energético e comercial",
    },
    "dia_maes": {
        "label": "Dia das Mães",
        "keywords": ("dia das mães", "dia das maes", "mães", "maes"),
        "palette": {"primary": "#D96C9D", "secondary": "#F7D6E5", "accent": "#D4AF37", "background": "#FFF9FB", "text": "#8F315D", "metallic": "#D4AF37"},
        "decorations": ["flores", "corações", "brilhos dourados", "formas delicadas"],
        "mood": "afetivo, delicado e elegante",
    },
    "dia_pais": {
        "label": "Dia dos Pais",
        "keywords": ("dia dos pais", "pais"),
        "palette": {"primary": "#143D6B", "secondary": "#5D7FA3", "accent": "#C79A54", "background": "#F7F9FC", "text": "#143D6B", "metallic": "#C79A54"},
        "decorations": ["faixas geométricas", "texturas discretas", "detalhes metálicos"],
        "mood": "sóbrio, moderno e sofisticado",
    },
    "festa_junina": {
        "label": "Festa Junina",
        "keywords": ("festa junina", "arraiá", "arraia", "são joão", "sao joao"),
        "palette": {"primary": "#E53935", "secondary": "#FBC02D", "accent": "#1976D2", "background": "#FFF8E1", "text": "#7A2D19", "metallic": "#FBC02D"},
        "decorations": ["bandeirinhas", "xadrez", "balões juninos", "texturas de tecido"],
        "mood": "alegre, popular e colorido",
    },
}


PALETTE_PRESETS: dict[str, dict[str, str]] = {
    "Cores do tema": {},
    "Azul Clássico": {"primary": "#123A9B", "secondary": "#087CE8", "accent": "#24C8F4", "background": "#FFFFFF", "text": "#102D50", "metallic": "#D7E7F5"},
    "Rosa Moderno": {"primary": "#B01972", "secondary": "#EF2A92", "accent": "#FF8FC7", "background": "#FFF7FB", "text": "#6D1648", "metallic": "#F8C5DE"},
    "Verde Elegante": {"primary": "#0B6E4F", "secondary": "#20A873", "accent": "#9ADCBF", "background": "#F6FFFB", "text": "#164C3C", "metallic": "#B8D8C8"},
    "Roxo Premium": {"primary": "#4C2A92", "secondary": "#7654D6", "accent": "#C49BFF", "background": "#FBF8FF", "text": "#36206D", "metallic": "#D8C6F5"},
    "Cinza Sofisticado": {"primary": "#2F3A46", "secondary": "#66727F", "accent": "#B8C0C8", "background": "#FAFBFC", "text": "#26313B", "metallic": "#D5D9DD"},
    "Dourado Luxo": {"primary": "#113B78", "secondary": "#235FA8", "accent": "#D4AF37", "background": "#FFFDF7", "text": "#102D50", "metallic": "#D4AF37"},
}
PALETTE_ORDER = list(PALETTE_PRESETS.keys()) + ["Personalizada"]


def resolve_palette(theme_palette: dict[str, str], preset: str = "Cores do tema", custom: dict[str, str] | None = None, use_metallic: bool = True) -> dict[str, str]:
    """Combina a paleta do tema com uma escolha manual sem alterar o calendário."""
    base = dict(theme_palette or THEMES["alphafest"]["palette"])
    if preset in PALETTE_PRESETS and PALETTE_PRESETS[preset]:
        base.update(PALETTE_PRESETS[preset])
    if preset == "Personalizada" and custom:
        base.update({k: v for k, v in custom.items() if k in {"primary", "secondary", "accent", "background", "text", "metallic"} and v})
    if not use_metallic:
        # Remove a aparência dourada/metálica usando o próprio acento da paleta.
        base["metallic"] = base.get("accent") or base.get("secondary") or base.get("primary")
    return base

THEME_ORDER = ["Automático"] + [v["label"] for v in THEMES.values()]
_LABEL_TO_ID = {v["label"]: k for k, v in THEMES.items()}


def normalize_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def theme_id_from_label(label: str | None) -> str:
    clean = normalize_text(label)
    if clean in THEMES:
        return clean
    return _LABEL_TO_ID.get(clean, "alphafest")


def detect_theme(*texts: Any, explicit: str | None = None) -> str:
    if explicit and normalize_text(explicit) not in {"", "Automático"}:
        return theme_id_from_label(explicit)
    joined = " ".join(normalize_text(x).casefold() for x in texts if x)
    for theme_id, theme in THEMES.items():
        if theme_id == "alphafest":
            continue
        if any(keyword.casefold() in joined for keyword in theme.get("keywords", ())):
            return theme_id
    return "alphafest"


def get_theme(theme_id: str | None) -> dict[str, Any]:
    selected = THEMES.get(theme_id or "alphafest", THEMES["alphafest"])
    return {"id": theme_id or "alphafest", **selected}


def resolve_event_theme(item: dict[str, Any]) -> str:
    """Resolve o tema do evento sem deixar um valor genérico esconder a data real.

    Eventos antigos podem ter ``tema_visual=alphafest`` por padrão. Nesse caso,
    o nome/categoria do próprio evento continua tendo prioridade para datas como
    Dia dos Pais, Natal, Outubro Rosa etc.
    """
    explicit = normalize_text(item.get("tema_visual") or item.get("tema"))
    detected = detect_theme(item.get("nome"), item.get("categoria"), item.get("observacoes"))
    if explicit and explicit not in {"Automático", "alphafest", "AlphaFest Clássico"}:
        return theme_id_from_label(explicit)
    return detected


def compact_marketing_text(value: Any, max_words: int = 8) -> str:
    """Encurta textos para a arte antes de reduzir o tamanho da fonte."""
    clean = normalize_text(value).strip(" .,-:;")
    if not clean:
        return ""
    words = clean.split()
    result = " ".join(words[:max_words])
    return result + ("…" if len(words) > max_words else "")


def smart_title(product_name: str, max_words: int = 4) -> str:
    """Cria um título publicitário curto, preservando as palavras principais."""
    clean = normalize_text(product_name)
    removable = {"elegante", "personalizado", "personalizada", "estilo", "modelo", "produto", "serviço"}
    words = [w for w in re.split(r"\s+", clean) if w.casefold().strip("()") not in removable]
    # Conteúdo entre parênteses costuma ser um estilo importante (ex.: Voronoi).
    parens = re.findall(r"\(([^)]+)\)", clean)
    base = [w.strip("(),") for w in words if not (w.startswith("(") and w.endswith(")"))]
    if parens:
        for term in parens:
            for word in term.split():
                if word.casefold() not in {x.casefold() for x in base}:
                    base.append(word)
    return " ".join(base[:max_words]) or clean


def calendar_theme_options(campaigns: Iterable[dict[str, Any]], reference: date | None = None, limit_days: int = 180) -> list[dict[str, Any]]:
    """Retorna campanhas do Calendário Mestre relevantes ao Marketing.

    Não salva nada e não cria outra fonte de dados.
    """
    reference = reference or date.today()
    result: list[dict[str, Any]] = []
    for item in campaigns or []:
        if not isinstance(item, dict) or not item.get("ativa", True):
            continue
        start_raw = str(item.get("data_inicio") or "")[:10]
        end_raw = str(item.get("data_fim") or start_raw)[:10]
        try:
            start = date.fromisoformat(start_raw)
            end = date.fromisoformat(end_raw)
        except ValueError:
            continue
        if item.get("recorrencia") == "Anual":
            try:
                start = start.replace(year=reference.year)
                end = end.replace(year=reference.year)
            except ValueError:
                pass
            if end < reference:
                try:
                    start = start.replace(year=reference.year + 1)
                    end = end.replace(year=reference.year + 1)
                except ValueError:
                    pass
        days = (start - reference).days
        in_period = start <= reference <= end
        anticipation = int(item.get("antecedencia_dias", 30) or 30)
        if not in_period and not (-7 <= days <= max(limit_days, anticipation)):
            continue
        theme_id = resolve_event_theme(item)
        result.append({
            "id": item.get("id"),
            "name": item.get("nome", "Campanha"),
            "theme_id": theme_id,
            "theme": get_theme(theme_id),
            "start": start,
            "end": end,
            "days": days,
            "in_period": in_period,
            "record": item,
        })
    return sorted(result, key=lambda x: (0 if x["in_period"] else 1, x["start"], x["name"]))


def typography_prompt_rules() -> str:
    r = TYPOGRAPHY_RULES
    return (
        "Hierarquia tipográfica obrigatória: "
        f"título principal entre {r['title']['min_px']} e {r['title']['max_px']} px equivalentes, máximo {r['title']['max_lines']} linhas; "
        f"banner entre {r['banner']['min_px']} e {r['banner']['max_px']} px; "
        f"títulos de benefícios entre {r['benefit_title']['min_px']} e {r['benefit_title']['max_px']} px em caixa alta; "
        f"descrições entre {r['benefit_body']['min_px']} e {r['benefit_body']['max_px']} px; "
        f"CTA entre {r['cta']['min_px']} e {r['cta']['max_px']} px; "
        f"telefone entre {r['phone']['min_px']} e {r['phone']['max_px']} px. "
        "Não usar textos minúsculos. Reduzir a quantidade de palavras antes de reduzir a fonte."
    )


def theme_prompt_rules(theme_id: str) -> str:
    theme = get_theme(theme_id)
    palette = theme["palette"]
    return (
        f"Tema visual: {theme['label']}. Clima: {theme['mood']}. "
        f"Paleta obrigatória: principal {palette['primary']}, secundária {palette['secondary']}, "
        f"destaque {palette['accent']}, fundo {palette['background']}, texto {palette['text']} e detalhe metálico {palette['metallic']}. "
        f"Elementos decorativos permitidos: {', '.join(theme['decorations'])}. "
        "Preservar o DNA AlphaFest na composição e no logo oficial, adaptando as cores à temática escolhida."
    )
