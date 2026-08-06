"""Prompt Mestre AlphaFest para campanhas IA Premium."""
from __future__ import annotations

import re
from typing import Any

from alphafest_dna import ALPHAFEST_DNA

CATEGORY_PROFILES: dict[str, dict[str, Any]] = {
    "confeitaria": {
        "keywords": ("carimbo", "brigadeiro", "doce", "biscoito", "confeitaria", "pasta americana"),
        "scene": "composição gastronômica premium, doces coloridos, utensílios organizados e sensação artesanal profissional",
        "applications": ["Brigadeiros", "Doces finos", "Biscoitos", "Pasta americana"],
        "benefits": ["Design exclusivo", "Fácil de usar", "Material de qualidade", "Seguro para alimentos", "Múltiplos usos"],
    },
    "papel_arroz": {
        "keywords": ("papel arroz", "papel de arroz", "bolo", "cupcake"),
        "scene": "bolo e doces personalizados em destaque, acabamento de confeitaria profissional e aplicações variadas",
        "applications": ["Bolos", "Doces", "Bolachas", "Drinks"],
        "benefits": ["Cores vibrantes", "Aplicação prática", "Vários temas", "Impressão detalhada", "Resultado profissional"],
    },
    "impressao_3d": {
        "keywords": ("3d", "voronoi", "escultura", "leopardo", "pla", "miniatura"),
        "scene": "produto decorativo fotografado como objeto de design, sem fundo retangular, integrado ao cenário e com sombra realista",
        "applications": ["Sala", "Escritório", "Decoração", "Presente"],
        "benefits": ["Design exclusivo", "Impressão 3D premium", "Alta definição", "Acabamento impecável", "Presente especial"],
    },
    "baloes": {
        "keywords": ("balão", "baloes", "balões", "decoração de festa"),
        "scene": "decoração festiva elegante com balões em destaque, volume, brilho e atmosfera de celebração",
        "applications": ["Aniversários", "Eventos", "Empresas", "Comemorações"],
        "benefits": ["Decoração personalizada", "Cores vibrantes", "Montagem profissional", "Vários temas", "Impacto visual"],
    },
    "brindes": {
        "keywords": ("caneca", "camiseta", "azulejo", "copo", "brinde", "lembrança"),
        "scene": "produto personalizado em cenário comercial limpo, com apresentação de presente e acabamento premium",
        "applications": ["Presentes", "Empresas", "Eventos", "Datas especiais"],
        "benefits": ["Personalização exclusiva", "Alta qualidade", "Acabamento profissional", "Presente marcante", "Produção sob encomenda"],
    },
    "personalizados": {
        "keywords": (),
        "scene": "produto personalizado como protagonista, integrado a uma composição publicitária premium",
        "applications": ["Presentes", "Eventos", "Empresas", "Datas especiais"],
        "benefits": ["Design exclusivo", "Personalização", "Alta qualidade", "Acabamento profissional", "Produção sob encomenda"],
    },
}

CHANNEL_SPECS = {
    "Instagram Feed": "arte quadrada 1080x1080, leitura forte no feed do Instagram",
    "Instagram Story": "composição vertical 1080x1920, áreas seguras no topo e rodapé",
    "Status WhatsApp": "composição vertical 1080x1920, texto direto e muito legível",
    "Carrossel": "arte quadrada 1080x1080 com capa de alto impacto",
    "Reel": "capa vertical 1080x1920 com título central e leitura imediata",
    "TikTok": "capa vertical 1080x1920 com alto contraste",
    "YouTube Shorts": "capa vertical 1080x1920 com título grande",
    "YouTube Horizontal": "composição horizontal 1920x1080 com áreas seguras",
}


def classify_product(name: str, description: str = "", category: str = "") -> str:
    text = f"{name} {description} {category}".casefold()
    for profile_name, profile in CATEGORY_PROFILES.items():
        if profile_name == "personalizados":
            continue
        if any(keyword in text for keyword in profile["keywords"]):
            return profile_name
    return "personalizados"


def _clean_items(items: list[str] | None, fallback: list[str]) -> list[str]:
    result = []
    for item in items or []:
        clean = re.sub(r"\s+", " ", str(item)).strip(" -•✓")
        if clean and clean.casefold() not in {x.casefold() for x in result}:
            result.append(clean)
    return (result or fallback)[:5]


def build_master_prompt(
    *,
    product_name: str,
    description: str = "",
    category: str = "",
    objective: str = "Vender",
    campaign: str = "",
    offer: str = "",
    subtitle: str = "",
    cta: str = "FAÇA SEU PEDIDO",
    phone: str = "",
    channel: str = "Instagram Feed",
    benefits: list[str] | None = None,
    applications: list[str] | None = None,
) -> dict[str, Any]:
    profile_id = classify_product(product_name, description, category)
    profile = CATEGORY_PROFILES[profile_id]
    benefit_list = _clean_items(benefits, profile["benefits"])
    application_list = _clean_items(applications, profile["applications"])
    phone = phone.strip() or ALPHAFEST_DNA["telefone"]
    subtitle = subtitle.strip() or "Transforme seu produto em uma peça ainda mais especial!"
    channel_spec = CHANNEL_SPECS.get(channel, CHANNEL_SPECS["Instagram Feed"])

    prompt = f"""Crie uma arte publicitária {channel_spec}, extremamente profissional, moderna e colorida para divulgação de {product_name}.

OBJETIVO COMERCIAL
- Objetivo: {objective}.
- Campanha/data: {campaign or 'campanha permanente'}.
- Informações obrigatórias: {offer or 'não há oferta específica; não invente preço ou promoção'}.

IDENTIDADE VISUAL OBRIGATÓRIA ALPHAFEST
- Paleta predominante: {', '.join(ALPHAFEST_DNA['paleta'])}.
- Estilo: {'; '.join(ALPHAFEST_DNA['estilo'])}.
- Estrutura visual: {'; '.join(ALPHAFEST_DNA['estrutura'])}.
- {ALPHAFEST_DNA['regras_logo']}
- {ALPHAFEST_DNA['regras_texto']}

PRODUTO E CENA
- Produto: {product_name}.
- Categoria visual: {profile_id.replace('_', ' ')}.
- Descrição confirmada: {description or 'usar somente o produto apresentado na imagem enviada'}.
- Direção da cena: {profile['scene']}.
- Usar a imagem enviada como referência obrigatória do produto. Preservar sua forma, cor, textura e identidade; não trocar por outro produto.
- O produto deve ocupar grande parte da composição e parecer integrado ao anúncio, sem cartão branco, moldura ou retângulo atrás dele.

TEXTOS DA ARTE
- Título principal grande: “{product_name}”.
- Banner azul: “{subtitle}”.
- Benefícios com ícones modernos: {', '.join(benefit_list)}.
- Aplicações em pequenas imagens ou selos: {', '.join(application_list)}.
- Selo superior direito: “Testado e Aprovado!” somente quando adequado; para peças decorativas usar “Peça Exclusiva!”.
- CTA grande: “{cta.upper()}”.
- WhatsApp: “{phone}”.
- Faixa rosa: “Pequenos detalhes que fazem toda a diferença!”.
- Barra inferior: “Prático • Criativo • Valoriza seu produto • Aumenta suas vendas”.

REGRAS DE QUALIDADE
- Aparência de anúncio comercial premium e qualidade de agência.
- Composição equilibrada, texto grande, fotografia integrada, iluminação de estúdio e sombras suaves.
- Não criar outro logotipo e não escrever “AlphaFest” dentro da imagem; reservar espaço limpo para o logo oficial aplicado pelo sistema.
- Não inventar informações que não foram fornecidas.
- Não incluir marcas d’água, mockups de celular, bordas externas ou textos minúsculos.
""".strip()
    return {
        "prompt": prompt,
        "profile_id": profile_id,
        "benefits": benefit_list,
        "applications": application_list,
        "channel_spec": channel_spec,
    }
