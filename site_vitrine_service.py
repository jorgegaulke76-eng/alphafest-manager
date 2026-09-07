"""Vitrine pública responsiva AlphaFest (HF43).

Somente leitura: seleciona produtos diretamente do Catálogo oficial marcados
para o site e prontos para apresentação. A HF43 acrescenta uma camada de
agrupamento comercial apenas para navegação pública, sem criar cadastro paralelo.
Não persiste, publica ou altera dados.
"""
from __future__ import annotations

import html
import re
import unicodedata
from typing import Any, Callable, Dict, Iterable, List, Optional
from urllib.parse import quote

from site_manager_service import avaliar_produto_site
from catalogo_orcamento_service import aliases_catalogo_atomicos


ImagemResolver = Optional[Callable[[str], str]]


CATEGORIAS_COMERCIAIS = (
    "Festas & Personalizados",
    "Balões & Decoração",
    "Gráfica Rápida",
    "Brindes",
    "Convites & Papelaria",
    "Impressão 3D",
    "Gravação a Laser",
    "Kits Festa",
)


def _normalizar_texto(texto: Any) -> str:
    base = unicodedata.normalize("NFKD", str(texto or ""))
    base = "".join(c for c in base if not unicodedata.combining(c))
    base = re.sub(r"[^a-zA-Z0-9]+", " ", base).strip().casefold()
    return re.sub(r"\s+", " ", base)


def _tem(texto: str, *termos: str) -> bool:
    return any(_normalizar_texto(t) in texto for t in termos if str(t or "").strip())


def categoria_comercial_produto(item: Dict[str, Any]) -> str:
    """Agrupa a categoria técnica do Catálogo em uma categoria comercial pública.

    A decisão é derivada somente dos dados existentes no produto. Nenhum valor é
    salvo de volta no Catálogo e não existe segunda Fonte Única. Regras mais
    específicas vêm antes das genéricas para evitar, por exemplo, que um troféu
    impresso em 3D caia em Brindes.
    """
    nome = _normalizar_texto(item.get("nome"))
    categoria = _normalizar_texto(item.get("categoria"))
    subcategoria = _normalizar_texto(item.get("subcategoria"))
    material = _normalizar_texto(item.get("material"))
    processos = _normalizar_texto(" ".join(_lista(item.get("processos"))))
    descricao = _normalizar_texto(item.get("descricao"))
    nucleo = " ".join(x for x in [nome, categoria, subcategoria, material, processos] if x)
    fonte = " ".join(x for x in [nucleo, descricao] if x)

    if _tem(fonte, "kit festa", "kit personalizado", "composicao de festa", "composicao festa"):
        return "Kits Festa"
    if _tem(fonte, "gravacao a laser", "gravacao laser", "laser"):
        return "Gravação a Laser"
    # "3D" isolado na descrição pode significar apenas efeito visual. A técnica
    # de produção só é assumida quando 3D está no nome/categoria/processo ou
    # quando a descrição fala explicitamente em impressão 3D.
    if _tem(nucleo, "3d") or _tem(descricao, "impressao 3d", "impresso em 3d", "produzido em 3d"):
        return "Impressão 3D"
    if _tem(fonte, "bubble", "balao", "baloes", "gas helio", "helio"):
        return "Balões & Decoração"

    # Itens tipicamente de festa devem vencer palavras genéricas como "brinde"
    # presentes em categorias internas antigas (ex.: Bandeirola).
    if _tem(nome, "bandeirola", "topo de bolo", "topo flork", "topper", "vela personalizada"):
        return "Festas & Personalizados"

    if _tem(fonte, "dtf", "adesivo", "banner", "faixa", "grafica", "grafico", "papel de arroz", "impressao rapida"):
        return "Gráfica Rápida"
    if _tem(fonte, "convite", "papelaria", "caixa cone", "sacola", "saco metalizado", "tag papel", "caixinha"):
        return "Convites & Papelaria"
    if _tem(fonte, "caneca", "copo", "ecobag", "medalha", "trofeu", "brinde", "squeeze", "chaveiro", "camiseta", "lembranca"):
        return "Brindes"
    return "Festas & Personalizados"


def _ordem_categoria_comercial(nome: str) -> int:
    try:
        return CATEGORIAS_COMERCIAIS.index(str(nome))
    except ValueError:
        return len(CATEGORIAS_COMERCIAIS)


def _slug(texto: str) -> str:
    base = unicodedata.normalize("NFKD", str(texto or ""))
    base = "".join(c for c in base if not unicodedata.combining(c))
    base = re.sub(r"[^a-zA-Z0-9]+", "-", base).strip("-").lower()
    return base or "sem-categoria"


def _lista(valor: Any) -> List[str]:
    if valor is None:
        return []
    if isinstance(valor, (str, bytes, bytearray)):
        valor = [valor]
    try:
        itens = list(valor)
    except TypeError:
        itens = [valor]
    return [str(x).strip() for x in itens if str(x or "").strip()]


def _preco_br(valor: Any) -> str:
    texto = str(valor or "").strip()
    if not texto:
        return "Sob consulta"
    limpo = re.sub(r"[^0-9,.-]", "", texto)
    try:
        if "," in limpo:
            numero = float(limpo.replace(".", "").replace(",", "."))
        else:
            numero = float(limpo)
        return f"R$ {numero:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return texto if texto.upper().startswith("R$") else f"R$ {texto}"


def selecionar_produtos_vitrine(
    catalogo: Iterable[Dict[str, Any]],
    *,
    usar_taxonomia_catalogo: bool = False,
) -> List[Dict[str, Any]]:
    """Seleciona somente itens ativos, marcados e prontos, sem alterar a origem.

    HF45.4 mantém o modo de prévia que usa diretamente Categoria e
    Subcategoria do Catálogo Oficial e acrescenta navegação visual hierárquica. O modo padrão permanece idêntico ao HF44
    para que a publicação oficial não mude enquanto a revisão da Anna não for
    concluída/homologada.
    """
    saida: List[Dict[str, Any]] = []
    for indice, produto in enumerate(catalogo or []):
        if not isinstance(produto, dict):
            continue
        leitura = avaliar_produto_site(produto)
        if not (leitura["ativo"] and leitura["publicar_site"] and leitura["pronto"]):
            continue
        item = dict(leitura)
        item["indice_catalogo"] = indice
        item["variacoes"] = _lista(produto.get("Variacoes"))
        item["subcategoria"] = str(produto.get("Subcategoria") or "").strip()
        item["material"] = str(produto.get("Material") or "").strip()
        item["processos"] = _lista(produto.get("Processos") or produto.get("Processo") or produto.get("processos"))
        item["campanhas"] = _lista(produto.get("Campanhas"))
        item["aliases"] = aliases_catalogo_atomicos(produto)
        item["temas_busca"] = _lista(produto.get("Temas") or produto.get("Tema"))
        item["ocasioes_busca"] = _lista(produto.get("Ocasioes") or produto.get("Ocasiões") or produto.get("Ocasiao") or produto.get("Ocasião"))
        item["tags_busca"] = _lista(produto.get("Tags") or produto.get("PalavrasChave") or produto.get("Palavras-chave"))
        item["carrossel_site"] = bool(produto.get("CarrosselSite", False))
        item["categoria_origem"] = str(item.get("categoria") or "").strip()
        item["categoria_comercial"] = categoria_comercial_produto(item)
        if usar_taxonomia_catalogo:
            item["categoria_publica"] = item["categoria_origem"] or "Sem categoria"
            item["subcategoria_publica"] = item["subcategoria"] or "Sem subcategoria"
        else:
            item["categoria_publica"] = item["categoria_comercial"] or "Festas & Personalizados"
            item["subcategoria_publica"] = ""
        saida.append(item)

    if usar_taxonomia_catalogo:
        saida.sort(key=lambda x: (
            not bool(x.get("destaque")),
            str(x.get("categoria_publica") or "").casefold(),
            str(x.get("subcategoria_publica") or "").casefold(),
            str(x.get("nome") or "").casefold(),
        ))
    else:
        saida.sort(key=lambda x: (
            not bool(x.get("destaque")),
            _ordem_categoria_comercial(str(x.get("categoria_comercial") or "")),
            str(x.get("nome") or "").casefold(),
        ))
    return saida


def resumir_vitrine(
    catalogo: Iterable[Dict[str, Any]],
    *,
    usar_taxonomia_catalogo: bool = False,
) -> Dict[str, Any]:
    produtos = selecionar_produtos_vitrine(catalogo, usar_taxonomia_catalogo=usar_taxonomia_catalogo)
    if usar_taxonomia_catalogo:
        categorias = sorted(
            {str(x.get("categoria_publica") or "Sem categoria").strip() or "Sem categoria" for x in produtos},
            key=str.casefold,
        )
        subcategorias_por_categoria: Dict[str, List[str]] = {}
        for categoria in categorias:
            subs = sorted(
                {
                    str(x.get("subcategoria_publica") or "Sem subcategoria").strip() or "Sem subcategoria"
                    for x in produtos
                    if str(x.get("categoria_publica") or "Sem categoria").strip() == categoria
                },
                key=str.casefold,
            )
            subcategorias_por_categoria[categoria] = subs
        total_subcategorias = len({
            (str(x.get("categoria_publica") or "Sem categoria").strip(), str(x.get("subcategoria_publica") or "Sem subcategoria").strip())
            for x in produtos
        })
        sem_subcategoria = sum(1 for x in produtos if str(x.get("subcategoria_publica") or "").strip() == "Sem subcategoria")
        contagem_por_categoria = {
            categoria: sum(1 for x in produtos if str(x.get("categoria_publica") or "Sem categoria").strip() == categoria)
            for categoria in categorias
        }
        contagem_por_subcategoria = {
            categoria: {
                sub: sum(
                    1 for x in produtos
                    if str(x.get("categoria_publica") or "Sem categoria").strip() == categoria
                    and str(x.get("subcategoria_publica") or "Sem subcategoria").strip() == sub
                )
                for sub in subcategorias_por_categoria.get(categoria, [])
            }
            for categoria in categorias
        }
    else:
        presentes = {str(x.get("categoria_comercial") or "Festas & Personalizados").strip() for x in produtos}
        categorias = [cat for cat in CATEGORIAS_COMERCIAIS if cat in presentes]
        subcategorias_por_categoria = {}
        total_subcategorias = 0
        sem_subcategoria = 0
        contagem_por_categoria = {categoria: sum(1 for x in produtos if str(x.get("categoria_comercial") or "Festas & Personalizados").strip() == categoria) for categoria in categorias}
        contagem_por_subcategoria = {}

    return {
        "produtos": produtos,
        "total": len(produtos),
        "destaques": sum(1 for x in produtos if x.get("destaque")),
        "categorias": categorias,
        "total_categorias": len(categorias),
        "subcategorias_por_categoria": subcategorias_por_categoria,
        "total_subcategorias": total_subcategorias,
        "sem_subcategoria": sem_subcategoria,
        "contagem_por_categoria": contagem_por_categoria,
        "contagem_por_subcategoria": contagem_por_subcategoria,
        "modo_taxonomia_catalogo": bool(usar_taxonomia_catalogo),
    }


def gerar_html_vitrine(
    catalogo: Iterable[Dict[str, Any]],
    empresa: Dict[str, Any],
    *,
    logo_src: str = "",
    imagem_resolver: ImagemResolver = None,
    modo_preview: bool = True,
    usar_taxonomia_catalogo: bool = False,
    produtos_com_galeria: Optional[Iterable[str]] = None,
) -> str:
    """Gera HTML autônomo da vitrine. Nenhuma publicação é realizada.

    Quando ``usar_taxonomia_catalogo`` é True, Categoria e Subcategoria do
    Catálogo Oficial viram a navegação hierárquica da prévia HF45.4. O padrão
    False preserva integralmente o comportamento público homologado no HF44.
    """
    resumo = resumir_vitrine(catalogo, usar_taxonomia_catalogo=usar_taxonomia_catalogo)
    produtos = resumo["produtos"]
    categorias = resumo["categorias"]
    produtos_galeria_slugs = {_slug(x) for x in (produtos_com_galeria or []) if str(x or "").strip()}
    tem_algum_produto_com_galeria = bool(produtos_galeria_slugs)

    nome_empresa = str((empresa or {}).get("nome") or "AlphaFest").strip() or "AlphaFest"
    subtitulo = str((empresa or {}).get("subtitulo") or "Personalizados & Balões").strip()
    slogan = str((empresa or {}).get("slogan") or "O poder de estar presente em cada presente!").strip()
    cidade = str((empresa or {}).get("cidade") or "").strip()
    uf = str((empresa or {}).get("uf") or "").strip()
    local = " · ".join(x for x in [cidade, uf] if x)
    numero = re.sub(r"\D", "", str((empresa or {}).get("whatsapp_catalogo") or (empresa or {}).get("celular") or ""))
    if numero and not numero.startswith("55"):
        numero = "55" + numero
    mensagem_geral = quote("Olá! Vim pelo site da AlphaFest e gostaria de fazer um orçamento. Preciso de ajuda para definir produto, tamanho/personalização, cor, quantidade, material e prazo.")
    whatsapp_geral = f"https://wa.me/{numero}?text={mensagem_geral}" if numero else "#"

    chips = [f'<button class="filter active" data-cat="todos"><span>Todos</span><b>{resumo["total"]}</b></button>'] if usar_taxonomia_catalogo else ['<button class="filter active" data-cat="todos">Todos</button>']
    for cat in categorias:
        if usar_taxonomia_catalogo:
            qtd_cat = int(resumo.get("contagem_por_categoria", {}).get(cat, 0) or 0)
            chips.append(
                f'<button class="filter category-filter" data-cat="{html.escape(_slug(cat), quote=True)}" data-label="{html.escape(cat, quote=True)}">'
                f'<span>{html.escape(cat)}</span><b>{qtd_cat}</b></button>'
            )
        else:
            chips.append(f'<button class="filter" data-cat="{html.escape(_slug(cat), quote=True)}">{html.escape(cat)}</button>')

    subchips: List[str] = []
    if usar_taxonomia_catalogo:
        subchips.append('<button class="subfilter active" data-parent="*" data-sub="todos" data-label="Todas"><span>Todas</span></button>')
        for cat in categorias:
            parent = _slug(cat)
            for sub in resumo.get("subcategorias_por_categoria", {}).get(cat, []):
                qtd_sub = int(resumo.get("contagem_por_subcategoria", {}).get(cat, {}).get(sub, 0) or 0)
                incompleta = ' incomplete' if sub == "Sem subcategoria" else ''
                subchips.append(
                    f'<button class="subfilter{incompleta}" data-parent="{html.escape(parent, quote=True)}" '
                    f'data-sub="{html.escape(_slug(sub), quote=True)}" data-label="{html.escape(sub, quote=True)}">'
                    f'<span>{html.escape(sub)}</span><b>{qtd_sub}</b></button>'
                )
    subfilters_html = (
        '<section class="taxonomy-step taxonomy-sub" id="subfilters" hidden>'
        '<div class="taxonomy-heading"><div><span class="step-number">2</span><strong id="sub-title">Escolha uma subcategoria</strong></div>'
        '<small>Mostra somente as subcategorias da categoria escolhida.</small></div>'
        '<div class="subfilters">' + ''.join(subchips) + '</div></section>'
        if usar_taxonomia_catalogo else ''
    )

    cards: List[str] = []
    for item in produtos:
        nome = str(item.get("nome") or "Produto").strip() or "Produto"
        descricao = str(item.get("descricao") or "").strip()
        categoria_origem = str(item.get("categoria_origem") or item.get("categoria") or "").strip()
        categoria = str(item.get("categoria_publica") or item.get("categoria_comercial") or "Festas & Personalizados").strip() or "Festas & Personalizados"
        subcategoria_publica = str(item.get("subcategoria_publica") or "").strip() if usar_taxonomia_catalogo else ""
        exibir_preco = bool(item.get("exibir_preco_site")) and bool(str(item.get("preco") or "").strip())
        preco = _preco_br(item.get("preco")) if exibir_preco else ""
        img = str(item.get("imagem_principal") or "").strip()
        if img and imagem_resolver is not None:
            try:
                resolvida = str(imagem_resolver(img) or "").strip()
                if resolvida:
                    img = resolvida
                elif not img.startswith(("http://", "https://", "data:image/")):
                    # Nunca expor caminho interno/local na prévia exportável.
                    img = ""
            except Exception:
                if not img.startswith(("http://", "https://", "data:image/")):
                    img = ""
        imagem_html = (
            f'<img src="{html.escape(img, quote=True)}" alt="{html.escape(nome, quote=True)}" loading="lazy" decoding="async" fetchpriority="low">'
            if img else '<div class="placeholder">AlphaFest</div>'
        )
        opcoes = item.get("variacoes") or []
        opcoes_html = ""
        if opcoes:
            texto_opcoes = " • ".join(opcoes[:5]) + (" …" if len(opcoes) > 5 else "")
            opcoes_html = f'<div class="options"><strong>Opções:</strong> {html.escape(texto_opcoes)}</div>'
        msg = quote(f"Olá! Vim pelo site da AlphaFest e gostaria de um orçamento para: {nome}. Quero definir tamanho/personalização, cor, quantidade, material e prazo.")
        href = f"https://wa.me/{numero}?text={msg}" if numero else "#"
        busca = " ".join([
            nome, descricao, categoria, categoria_origem, subcategoria_publica,
            item.get("subcategoria") or "", item.get("material") or "",
            " ".join(item.get("processos") or []),
            " ".join(item.get("variacoes") or []),
            " ".join(item.get("campanhas") or []),
            " ".join(item.get("aliases") or []),
            " ".join(item.get("temas_busca") or []),
            " ".join(item.get("ocasioes_busca") or []),
            " ".join(item.get("tags_busca") or []),
        ])
        busca = unicodedata.normalize("NFKD", busca).encode("ascii", "ignore").decode("ascii").casefold()
        produto_slug = _slug(nome)
        sub_data = html.escape(_slug(subcategoria_publica), quote=True) if subcategoria_publica else ""
        tem_galeria = produto_slug in produtos_galeria_slugs
        # HF51.2 — vitrine limpa: na listagem pública aparece somente a foto +
        # nome. Destaque, descrição, preço, opções e CTA ficam exclusivamente
        # na ficha aberta pelo cliente.
        cards.append(
            f'''<article class="product-card product-card-compact" role="button" tabindex="0" aria-label="Ver detalhes de {html.escape(nome, quote=True)}"
                data-cat="{html.escape(_slug(categoria), quote=True)}" data-sub="{sub_data}" data-product="{html.escape(produto_slug, quote=True)}" data-search="{html.escape(busca, quote=True)}"
                data-detail-name="{html.escape(nome, quote=True)}" data-detail-description="{html.escape(descricao, quote=True)}"
                data-detail-category="{html.escape(categoria, quote=True)}" data-detail-subcategory="{html.escape(subcategoria_publica, quote=True)}"
                data-detail-price="{html.escape(preco, quote=True)}" data-detail-image="{html.escape(img, quote=True)}"
                data-detail-whatsapp="{html.escape(href, quote=True)}" data-detail-gallery="{'1' if tem_galeria else '0'}"
                {f'data-gallery-product="{html.escape(produto_slug, quote=True)}" data-gallery-label="{html.escape(nome, quote=True)}"' if tem_galeria else ''}>
                <div class="photo">{imagem_html}</div>
                <div class="card-body compact-body"><h3>{html.escape(nome)}</h3></div>
            </article>'''
        )

    logo = f'<img class="brand-logo" src="{html.escape(str(logo_src), quote=True)}" alt="AlphaFest Personalizados e Balões" decoding="async" fetchpriority="high">' if logo_src else '<div class="brand-word">AlphaFest</div>'
    if modo_preview:
        preview_bar = (
            '<div class="preview-bar">PRÉVIA INTERNA HF45.4-HF1 · CATEGORIA → SUBCATEGORIA · NÃO PUBLICADA</div>'
            if usar_taxonomia_catalogo
            else '<div class="preview-bar">PRÉVIA INTERNA HF40 · AINDA NÃO PUBLICADA</div>'
        )
    else:
        preview_bar = ""
    vazio = '<div class="empty">Nenhum produto pronto está marcado para o site.</div>' if not cards else ""
    rotulo_categorias = "categorias do Catálogo" if usar_taxonomia_catalogo else "categorias comerciais"
    texto_escolha = "Pesquise por nome, tema, material ou ocasião — ou escolha uma categoria e depois uma subcategoria." if usar_taxonomia_catalogo else "Pesquise ou escolha uma categoria."

    if usar_taxonomia_catalogo:
        script_filtros = r"""
(function(){
  let cat='todos', sub='todos', catLabel='Todos', subLabel='Todas';
  const cards=[...document.querySelectorAll('.product-card')];
  const input=document.getElementById('search');
  const count=document.getElementById('result-count');
  const subbox=document.getElementById('subfilters');
  const subTitle=document.getElementById('sub-title');
  const current=document.getElementById('taxonomy-current');
  const catsBox=document.getElementById('taxonomy-cats');
  const focusBox=document.getElementById('taxonomy-focus');
  const focusLabel=document.getElementById('taxonomy-focus-label');
  const backButton=document.getElementById('taxonomy-back');
  const subbuttons=[...document.querySelectorAll('.subfilter')];
  const catbuttons=[...document.querySelectorAll('.filter')];
  function norm(s){return (s||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/[^a-z0-9]+/g,' ').trim().replace(/\s+/g,' ');}
  function editDistance(a,b,maxDist){
    if(Math.abs(a.length-b.length)>maxDist)return maxDist+1;
    let prev=Array.from({length:b.length+1},(_,i)=>i);
    for(let i=1;i<=a.length;i++){
      const cur=[i]; let rowMin=cur[0];
      for(let j=1;j<=b.length;j++){
        const cost=a[i-1]===b[j-1]?0:1;
        cur[j]=Math.min(cur[j-1]+1,prev[j]+1,prev[j-1]+cost);
        rowMin=Math.min(rowMin,cur[j]);
      }
      if(rowMin>maxDist)return maxDist+1; prev=cur;
    }
    return prev[b.length];
  }
  function smartMatch(haystack,query){
    const h=norm(haystack), q=norm(query); if(!q)return true; if(h.includes(q))return true;
    const hw=h.split(' ').filter(Boolean), qw=q.split(' ').filter(Boolean);
    return qw.every(token=>hw.some(word=>{
      if(word.includes(token)||token.includes(word))return true;
      if(token.length>=3 && word.startsWith(token.slice(0,Math.min(3,token.length))))return true;
      const lim=token.length>=7?2:(token.length>=4?1:0);
      return lim>0 && editDistance(word,token,lim)<=lim;
    }));
  }
  function updateCurrent(){
    if(!current)return;
    if(cat==='todos') current.innerHTML='<strong>Todos os produtos</strong><span>Escolha uma categoria para ver as subcategorias.</span>';
    else current.innerHTML='<strong>'+catLabel+'</strong><span>'+(sub==='todos'?'Todas as subcategorias':subLabel)+'</span>';
  }
  function updateFocus(){
    const focado=cat!=='todos';
    if(catsBox) catsBox.hidden=focado;
    if(focusBox) focusBox.hidden=!focado;
    if(focusLabel) focusLabel.textContent=focado?catLabel:'Categoria';
  }
  function resetSub(){
    sub='todos'; subLabel='Todas';
    subbuttons.forEach(b=>{
      const geral=b.dataset.sub==='todos';
      const pertence=b.dataset.parent===cat;
      b.hidden=!(geral||pertence);
      b.classList.toggle('active',geral);
    });
    if(subbox) subbox.hidden=(cat==='todos');
    if(subTitle) subTitle.textContent=cat==='todos'?'Escolha uma subcategoria':catLabel+' · escolha uma subcategoria';
    updateFocus();
  }
  function apply(){
    const q=norm(input.value); let n=0;
    cards.forEach(c=>{
      const okCat=cat==='todos'||c.dataset.cat===cat;
      const okSub=sub==='todos'||c.dataset.sub===sub;
      const okQ=smartMatch(c.dataset.search,q);
      const ok=okCat&&okSub&&okQ;
      c.style.display=ok?'flex':'none'; if(ok)n++;
    });
    count.textContent=n+' produto(s)'; updateCurrent(); updateFocus();
  }
  function selecionarCategoria(botao){
    catbuttons.forEach(x=>x.classList.remove('active')); botao.classList.add('active');
    cat=botao.dataset.cat; catLabel=botao.dataset.label||'Todos'; resetSub(); apply();
    if(cat!=='todos' && subbox && window.innerWidth<700) subbox.scrollIntoView({behavior:'smooth',block:'nearest'});
  }
  catbuttons.forEach(b=>b.addEventListener('click',()=>selecionarCategoria(b)));
  subbuttons.forEach(b=>b.addEventListener('click',()=>{
    subbuttons.forEach(x=>x.classList.remove('active')); b.classList.add('active');
    sub=b.dataset.sub; subLabel=b.dataset.label||b.textContent.trim(); apply();
  }));
  if(backButton) backButton.addEventListener('click',()=>{
    const todos=catbuttons.find(b=>b.dataset.cat==='todos');
    cat='todos'; catLabel='Todos'; sub='todos'; subLabel='Todas';
    if(input) input.value='';
    catbuttons.forEach(x=>x.classList.toggle('active',x===todos));
    resetSub(); apply();
    const categorias=document.getElementById('categorias');
    if(categorias) categorias.scrollIntoView({behavior:'smooth',block:'start'});
    else if(catsBox) catsBox.scrollIntoView({behavior:'smooth',block:'start'});
  });
  input.addEventListener('input',apply); resetSub(); apply();
})();
"""
    else:
        script_filtros = r"""
(function(){let cat='todos';const cards=[...document.querySelectorAll('.product-card')];const input=document.getElementById('search');const count=document.getElementById('result-count');function norm(s){return (s||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/[^a-z0-9]+/g,' ').trim().replace(/\s+/g,' ');}function dist(a,b,m){if(Math.abs(a.length-b.length)>m)return m+1;let p=Array.from({length:b.length+1},(_,i)=>i);for(let i=1;i<=a.length;i++){let c=[i],r=i;for(let j=1;j<=b.length;j++){const z=a[i-1]===b[j-1]?0:1;c[j]=Math.min(c[j-1]+1,p[j]+1,p[j-1]+z);r=Math.min(r,c[j]);}if(r>m)return m+1;p=c;}return p[b.length];}function match(h,q){h=norm(h);q=norm(q);if(!q||h.includes(q))return true;const hw=h.split(' '),qw=q.split(' ');return qw.every(t=>hw.some(w=>w.includes(t)||t.includes(w)||(t.length>=3&&w.startsWith(t.slice(0,3)))||(t.length>=4&&dist(w,t,t.length>=7?2:1)<=(t.length>=7?2:1))));}function apply(){const q=input.value;let n=0;cards.forEach(c=>{const okCat=cat==='todos'||c.dataset.cat===cat;const okQ=match(c.dataset.search,q);const ok=okCat&&okQ;c.style.display=ok?'flex':'none';if(ok)n++;});count.textContent=n+' produto(s)';}document.querySelectorAll('.filter').forEach(b=>b.addEventListener('click',()=>{document.querySelectorAll('.filter').forEach(x=>x.classList.remove('active'));b.classList.add('active');cat=b.dataset.cat;apply();}));input.addEventListener('input',apply);apply();})();
"""

    # HF51.2 — ficha comercial: preço em destaque quando autorizado, CTAs antes da descrição e relacionados preservados.
    product_detail_script = r'''<script>
(function(){
  const modal=document.getElementById('product-detail-modal');
  if(!modal)return;
  const cards=[...document.querySelectorAll('.product-card[data-detail-name]')];
  const nameEl=document.getElementById('product-detail-name');
  const descEl=document.getElementById('product-detail-description');
  const taxEl=document.getElementById('product-detail-tax');
  const priceEl=document.getElementById('product-detail-price');
  const imgEl=document.getElementById('product-detail-image');
  const placeholder=document.getElementById('product-detail-placeholder');
  const waEl=document.getElementById('product-detail-whatsapp');
  const galEl=document.getElementById('product-detail-gallery');
  const related=document.getElementById('product-related');
  const relatedGrid=document.getElementById('product-related-grid');
  let current=null;
  function esc(s){return (s||'').replace(/[&<>"]/g,function(ch){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[ch];});}
  function relatedFor(card){
    const sameSub=cards.filter(c=>c!==card && card.dataset.sub && c.dataset.sub===card.dataset.sub && c.dataset.cat===card.dataset.cat);
    const sameCat=cards.filter(c=>c!==card && c.dataset.cat===card.dataset.cat && !sameSub.includes(c));
    return [...sameSub,...sameCat].slice(0,4);
  }
  function open(card){
    current=card;
    const d=card.dataset;
    nameEl.textContent=d.detailName||'Produto';
    descEl.textContent=d.detailDescription||'';
    taxEl.textContent=[d.detailCategory,d.detailSubcategory].filter(Boolean).join(' · ');
    if(d.detailPrice){priceEl.textContent=d.detailPrice;priceEl.hidden=false;}else{priceEl.textContent='';priceEl.hidden=true;}
    if(d.detailImage){imgEl.src=d.detailImage;imgEl.alt=d.detailName||'Produto';imgEl.hidden=false;placeholder.hidden=true;}else{imgEl.removeAttribute('src');imgEl.hidden=true;placeholder.hidden=false;}
    waEl.href=d.detailWhatsapp||'#';
    if(galEl){galEl.hidden=d.detailGallery!=='1'; galEl.dataset.galleryProduct=d.product||''; galEl.dataset.galleryLabel=d.detailName||'Produto';}
    const rel=relatedFor(card); relatedGrid.innerHTML='';
    rel.forEach(function(r){
      const b=document.createElement('button'); b.type='button'; b.className='product-related-card';
      const src=r.dataset.detailImage||'';
      b.innerHTML=(src?'<img src="'+esc(src)+'" alt="" loading="lazy" decoding="async" fetchpriority="low">':'')+'<span>'+esc(r.dataset.detailName||'Produto')+'</span>';
      b.addEventListener('click',function(){open(r);}); relatedGrid.appendChild(b);
    });
    related.hidden=!rel.length;
    modal.hidden=false; modal.setAttribute('aria-hidden','false'); document.body.classList.add('product-modal-open');
    const closeBtn=modal.querySelector('.product-detail-close'); if(closeBtn)closeBtn.focus();
  }
  function close(){modal.hidden=true;modal.setAttribute('aria-hidden','true');document.body.classList.remove('product-modal-open');if(current)current.focus();}
  cards.forEach(function(card){
    card.addEventListener('click',function(){open(card);});
    card.addEventListener('keydown',function(e){if(e.key==='Enter'||e.key===' '){e.preventDefault();open(card);}});
  });
  modal.querySelectorAll('[data-product-close]').forEach(function(el){el.addEventListener('click',close);});
  document.addEventListener('keydown',function(e){if(e.key==='Escape'&&!modal.hidden)close();});
  if(galEl)galEl.addEventListener('click',function(){
    const slug=galEl.dataset.galleryProduct||'', label=galEl.dataset.galleryLabel||'Produto'; close();
    if(typeof window.alphaFestGalleryShowProduct==='function'){window.alphaFestGalleryShowProduct(slug,label);}
    else{const g=document.getElementById('galeria');if(g)g.scrollIntoView({behavior:'smooth',block:'start'});}
  });
})();
</script>'''

    return f'''<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(nome_empresa)} · {html.escape(subtitulo)}</title>
<meta name="description" content="AlphaFest Itatiba: personalizados, balões, gráfica rápida, brindes, impressão 3D, gravação a laser e soluções sob medida para festas, presentes e marcas.">
<meta name="theme-color" content="#079de0">
<meta property="og:type" content="website">
<meta property="og:site_name" content="AlphaFest">
<meta property="og:title" content="AlphaFest · Personalizados &amp; Balões">
<meta property="og:description" content="Personalizados, balões, gráfica rápida, brindes e soluções sob medida para festas, presentes e marcas.">
<meta name="twitter:card" content="summary_large_image">
<style>
:root{{--blue:#0b67c6;--cyan:#2db7e5;--pink:#f44f8d;--ink:#14253d;--soft:#f4faff;--line:#dbe9f5;--green:#25d366}}
*{{box-sizing:border-box}} html{{scroll-behavior:smooth}} body{{margin:0;font-family:Inter,Arial,Helvetica,sans-serif;color:var(--ink);background:#fff}}
.preview-bar{{background:#15233a;color:#fff;text-align:center;font-size:11px;font-weight:800;letter-spacing:.08em;padding:8px 12px}}
.header{{position:sticky;top:0;z-index:20;background:rgba(255,255,255,.96);backdrop-filter:blur(12px);border-bottom:1px solid var(--line)}}
.header-in{{max-width:1240px;margin:auto;padding:12px 22px;display:flex;align-items:center;gap:18px}} .brand{{display:flex;align-items:center;gap:10px;text-decoration:none;color:var(--ink)}}
.brand-logo{{width:68px;height:54px;object-fit:contain}} .brand-word{{font-size:26px;font-weight:900;color:var(--blue)}} .brand-copy strong{{display:block;font-size:16px}} .brand-copy span{{font-size:12px;color:#60748e}}
.header-actions{{margin-left:auto;display:flex;gap:10px;align-items:center}} .header-actions .cta{{white-space:nowrap}} .ghost{{color:var(--blue);text-decoration:none;font-weight:800;padding:10px 12px}}
.cta{{display:inline-flex;align-items:center;justify-content:center;background:var(--green);color:#fff;text-decoration:none;font-weight:900;border-radius:12px;padding:12px 17px;box-shadow:0 7px 18px rgba(37,211,102,.22)}} .cta.small{{padding:10px 12px;font-size:13px;border-radius:9px;min-height:42px}}
.hero{{background:radial-gradient(circle at 88% 12%,rgba(244,79,141,.18),transparent 25%),radial-gradient(circle at 10% 75%,rgba(45,183,229,.24),transparent 30%),linear-gradient(135deg,#f8fcff,#fff 48%,#fff7fb);border-bottom:1px solid var(--line)}}
.hero-in{{max-width:1240px;margin:auto;padding:58px 22px 48px;display:grid;grid-template-columns:1.35fr .65fr;gap:40px;align-items:center}}
.eyebrow{{color:var(--blue);font-size:13px;font-weight:900;text-transform:uppercase;letter-spacing:.1em}} .hero h1{{font-size:clamp(38px,6vw,72px);line-height:.98;margin:12px 0 18px;letter-spacing:-.04em}} .hero h1 span{{background:linear-gradient(90deg,var(--blue),var(--cyan),var(--pink));-webkit-background-clip:text;background-clip:text;color:transparent}}
.hero p{{font-size:18px;line-height:1.6;color:#50657f;max-width:720px}} .hero-actions{{display:flex;flex-wrap:wrap;gap:12px;margin-top:24px}} .secondary{{display:inline-flex;text-decoration:none;color:var(--ink);border:1px solid var(--line);background:#fff;padding:12px 17px;border-radius:12px;font-weight:850}}
.hero-card{{background:#fff;border:1px solid var(--line);border-radius:24px;padding:26px;box-shadow:0 24px 60px rgba(11,103,198,.12)}} .hero-stat{{display:grid;grid-template-columns:repeat(2,1fr);gap:12px}} .stat{{padding:16px;border-radius:16px;background:var(--soft)}} .stat strong{{display:block;font-size:28px;color:var(--blue)}} .stat span{{font-size:12px;color:#60748e}}
.main{{max-width:1240px;margin:auto;padding:36px 22px 70px}} .toolbar{{display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin-bottom:18px}} .search{{flex:1;min-width:260px;position:relative}} .search input{{width:100%;border:1px solid var(--line);border-radius:14px;padding:14px 16px 14px 42px;font-size:15px;outline:none;background:#fff}} .search:before{{content:'🔎';position:absolute;left:14px;top:13px}}
.filters{{display:flex;gap:8px;overflow-x:auto;padding:2px 0 10px;scrollbar-width:thin}} .filter{{border:1px solid var(--line);background:#fff;color:var(--ink);padding:9px 13px;border-radius:999px;white-space:nowrap;font-weight:800;cursor:pointer}} .filter.active{{background:var(--blue);border-color:var(--blue);color:#fff}}
.taxonomy-nav{{display:grid;gap:12px;margin:8px 0 18px}} .taxonomy-step{{border:1px solid var(--line);background:#fff;border-radius:18px;padding:16px}} .taxonomy-focus[hidden]{{display:none}} .taxonomy-focus{{display:flex;align-items:center;gap:14px;border:1px solid #cfe3f5;background:linear-gradient(90deg,#f5fbff,#fff);border-radius:18px;padding:12px 14px}} .taxonomy-back{{border:1px solid #bcd8ef;background:#fff;color:var(--blue);border-radius:12px;padding:10px 13px;font-weight:900;cursor:pointer;white-space:nowrap}} .taxonomy-back:hover{{background:#eef7ff}} .taxonomy-focus-copy{{display:flex;flex-direction:column;gap:2px}} .taxonomy-focus-copy small{{font-size:10px;text-transform:uppercase;letter-spacing:.08em;font-weight:900;color:#7890a7}} .taxonomy-focus-copy strong{{font-size:16px;color:var(--ink)}} .taxonomy-heading{{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:12px}} .taxonomy-heading>div{{display:flex;align-items:center;gap:9px}} .taxonomy-heading strong{{font-size:15px}} .taxonomy-heading small{{color:#71849c;font-size:12px}} .step-number{{width:26px;height:26px;display:inline-flex;align-items:center;justify-content:center;border-radius:50%;background:#e8f4ff;color:var(--blue);font-weight:950}} .taxonomy-cats .filters{{padding-bottom:2px}} .category-filter{{display:inline-flex;align-items:center;gap:8px}} .filter b,.subfilter b{{display:inline-flex;align-items:center;justify-content:center;min-width:22px;height:22px;padding:0 6px;border-radius:999px;background:#edf5fb;color:#50708d;font-size:11px}} .filter.active b{{background:rgba(255,255,255,.2);color:#fff}}
.taxonomy-sub[hidden]{{display:none}} .subfilter[hidden]{{display:none!important}} .subfilters{{display:flex;align-items:center;gap:8px;overflow-x:auto;padding:2px 0;scrollbar-width:thin}} .subfilter{{border:1px solid #cfe0ee;background:#f7fbff;color:#31526f;padding:8px 12px;border-radius:999px;white-space:nowrap;font-weight:800;cursor:pointer;display:inline-flex;align-items:center;gap:7px}} .subfilter.active{{background:#e8f4ff;border-color:#7db8e8;color:var(--blue)}} .subfilter.incomplete{{border-style:dashed;background:#fffbea;color:#856900}} .taxonomy-current{{display:flex;align-items:center;gap:10px;border-radius:13px;background:#f4f9fd;padding:10px 13px;color:#60748e;font-size:12px}} .taxonomy-current strong{{color:var(--ink);font-size:13px}} .taxonomy-current span:before{{content:'›';margin-right:10px;color:#91a6b8}}
.section-head{{display:flex;justify-content:space-between;gap:18px;align-items:end;margin:20px 0}} .section-head h2{{font-size:30px;margin:0}} .section-head p{{margin:5px 0 0;color:#667b94}} #result-count{{font-weight:800;color:var(--blue);white-space:nowrap}}
.grid{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:22px}} .product-card{{border:1px solid var(--line);border-radius:20px;overflow:hidden;background:#fff;box-shadow:0 10px 30px rgba(20,37,61,.06);display:flex;flex-direction:column;transition:.18s}} .product-card:hover{{transform:translateY(-3px);box-shadow:0 16px 36px rgba(20,37,61,.11)}}
.photo{{position:relative;background:var(--soft);aspect-ratio:4/3;overflow:hidden}} .photo img{{width:100%;height:100%;object-fit:cover;display:block}} .placeholder{{height:100%;display:flex;align-items:center;justify-content:center;font-size:28px;font-weight:900;color:#84a9ca}} .badge{{position:absolute;top:12px;left:12px;background:#fff;color:#a26100;border-radius:999px;padding:7px 10px;font-size:11px;font-weight:900;box-shadow:0 3px 12px rgba(0,0,0,.12)}}
.gallery-proof-btn{{width:100%;border:1px solid #b9d9f4;background:#f3f9ff;color:#0b68b5;border-radius:10px;min-height:39px;margin:0 0 10px;font-weight:900;cursor:pointer}} .gallery-proof-btn:hover{{background:#e9f5ff;border-color:#80bbe9}}
.card-body{{padding:18px;display:flex;flex-direction:column;flex:1}} .category{{font-size:11px;text-transform:uppercase;letter-spacing:.08em;font-weight:900;color:var(--blue)}} .subcategory{{font-size:12px;font-weight:800;color:#6a7f97;margin-top:4px}} .card-body h3{{font-size:20px;line-height:1.15;margin:7px 0 10px}} .card-body p{{font-size:14px;line-height:1.55;color:#60748e;margin:0 0 12px;flex:1}} .options{{font-size:12px;color:#60748e;margin:0 0 12px}} .card-footer{{display:flex;gap:10px;align-items:center;justify-content:space-between;border-top:1px solid #edf3f8;padding-top:14px}} .card-footer.no-price .cta{{width:100%}} .price{{font-weight:950;font-size:17px}}
.product-card-compact{{cursor:pointer;content-visibility:auto;contain-intrinsic-size:340px 420px}} .product-card-compact .photo{{aspect-ratio:1/1}} .compact-body{{padding:14px 15px 16px;min-height:70px;justify-content:center}} .compact-body h3{{font-size:18px;line-height:1.18;margin:0;color:var(--ink)}}
.product-detail-modal[hidden]{{display:none!important}} .product-detail-modal{{position:fixed;inset:0;z-index:120;display:flex;align-items:center;justify-content:center;padding:24px}} .product-detail-backdrop{{position:absolute;inset:0;background:rgba(7,24,45,.68);backdrop-filter:blur(5px)}} .product-detail-panel{{position:relative;z-index:2;width:min(1040px,96vw);max-height:92vh;overflow:auto;background:#fff;border-radius:26px;box-shadow:0 30px 90px rgba(4,24,48,.30);padding:26px}} .product-detail-close{{position:absolute;right:15px;top:13px;z-index:5;width:42px;height:42px;border:0;border-radius:50%;background:#edf6fd;color:#153b61;font-size:30px;line-height:1;cursor:pointer}} .product-detail-layout{{display:grid;grid-template-columns:minmax(0,1.05fr) minmax(320px,.95fr);gap:30px;align-items:start}} .product-detail-media{{background:#f4f9fd;border-radius:20px;overflow:hidden;aspect-ratio:1/1;display:flex;align-items:center;justify-content:center}} .product-detail-media img{{width:100%;height:100%;object-fit:contain;display:block}} .product-detail-placeholder{{font-size:34px;font-weight:950;color:#83a8c8}} .product-detail-copy{{padding:12px 4px 4px}} .product-detail-tax{{font-size:12px;font-weight:900;text-transform:uppercase;letter-spacing:.07em;color:var(--blue);margin-bottom:8px}} .product-detail-copy h2{{font-size:34px;line-height:1.06;margin:0 0 14px;color:var(--ink)}} .product-detail-price{{display:flex;align-items:center;justify-content:space-between;gap:16px;border:1px solid #bfe9cf;background:#effcf4;border-radius:15px;padding:13px 15px;font-size:25px;font-weight:950;color:#08773a;margin:0 0 14px}} .product-detail-price:before{{content:'Preço';font-size:12px;font-weight:900;letter-spacing:.06em;text-transform:uppercase;color:#43825e}} .product-detail-price[hidden]{{display:none!important}} .product-detail-copy p{{font-size:16px;line-height:1.65;color:#566f89;white-space:pre-line;margin:0 0 18px}} .product-detail-actions{{display:grid;grid-template-columns:1fr;gap:9px;margin:4px 0 18px}} .product-detail-gallery{{margin:0;min-height:46px;border:1px solid #9bc9ee;background:#f3f9ff;color:#075fae;border-radius:12px;font-weight:900;cursor:pointer}} .product-detail-whatsapp{{min-height:52px;font-size:16px}} .product-related{{border-top:1px solid #e7eef5;margin-top:24px;padding-top:20px}} .product-related-head{{display:flex;justify-content:space-between;gap:14px;align-items:end;margin-bottom:12px}} .product-related-head strong{{font-size:19px}} .product-related-head span{{font-size:12px;color:#71849b}} .product-related-grid{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px}} .product-related-card{{border:1px solid #dce8f3;background:#fff;border-radius:14px;overflow:hidden;cursor:pointer;text-align:left;padding:0;color:var(--ink)}} .product-related-card img{{width:100%;aspect-ratio:1/1;object-fit:cover;display:block;background:#f4f9fd}} .product-related-card span{{display:block;padding:9px 10px;font-size:12px;font-weight:850;line-height:1.25}} body.product-modal-open{{overflow:hidden}}
.empty{{padding:50px;text-align:center;border:1px dashed var(--line);border-radius:18px;color:#60748e}} .mobile-whatsapp{{display:none}} .footer{{background:#10243c;color:#d7e8f7}} .footer-in{{max-width:1240px;margin:auto;padding:34px 22px;display:flex;gap:24px;justify-content:space-between;align-items:center}} .footer strong{{color:#fff}} .footer small{{color:#9fb7cb}}
@media(max-width:900px){{.hero-in{{grid-template-columns:1fr}}.hero-card{{display:none}}.grid{{grid-template-columns:repeat(2,minmax(0,1fr))}}}}
@media(max-width:620px){{body{{padding-bottom:76px}}.preview-bar{{font-size:9px;padding:6px 10px}}.brand-copy{{display:none}}.ghost{{display:none}}.header-in{{padding:8px 12px;gap:8px}}.brand-logo{{width:54px;height:44px}}.header-actions .cta{{padding:10px 12px;font-size:13px;box-shadow:none}}.hero-in{{padding:30px 14px 26px}}.eyebrow{{font-size:11px}}.hero h1{{font-size:36px;line-height:1.02;margin:9px 0 14px}}.hero p{{font-size:15px;line-height:1.5}}.hero-actions{{gap:8px;margin-top:18px}}.hero-actions>a{{width:100%;min-height:46px}}.main{{padding:22px 12px 38px}}.section-head{{align-items:flex-start;flex-direction:column;gap:6px;margin:14px 0}}.section-head h2{{font-size:25px}}.search{{min-width:100%}}.search input{{font-size:16px;padding-top:13px;padding-bottom:13px}}.filters{{gap:7px;padding-bottom:9px}}.filter{{padding:10px 13px;min-height:42px}}.taxonomy-step{{padding:13px;border-radius:15px}}.taxonomy-focus{{align-items:stretch;flex-direction:column;padding:11px;border-radius:15px;gap:8px}}.taxonomy-back{{width:100%;min-height:42px}}.taxonomy-focus-copy{{padding:0 4px 3px}}.taxonomy-heading{{align-items:flex-start;flex-direction:column;gap:5px}}.taxonomy-heading small{{font-size:11px}}.subfilters{{gap:7px;padding-bottom:2px}}.subfilter{{padding:9px 12px;min-height:40px}}.taxonomy-current{{align-items:flex-start;flex-direction:column;gap:3px}}.taxonomy-current span:before{{display:none}}.grid{{grid-template-columns:1fr 1fr;gap:10px}}.product-card{{border-radius:14px;box-shadow:0 7px 22px rgba(20,37,61,.07)}}.product-card:hover{{transform:none}}.product-card-compact .photo{{aspect-ratio:1/1}}.compact-body{{padding:10px 10px 12px;min-height:58px}}.compact-body h3{{font-size:14px;line-height:1.2}}.product-detail-modal{{padding:8px;align-items:flex-end}}.product-detail-panel{{width:100%;max-height:94vh;border-radius:22px 22px 12px 12px;padding:18px 14px 16px}}.product-detail-close{{right:10px;top:9px;width:38px;height:38px}}.product-detail-layout{{grid-template-columns:1fr;gap:15px}}.product-detail-media{{aspect-ratio:4/3}}.product-detail-copy{{padding:0 2px}}.product-detail-copy h2{{font-size:25px;padding-right:36px}}.product-detail-copy p{{font-size:14px;line-height:1.55}}.product-detail-price{{font-size:21px}}.product-related-head{{align-items:flex-start;flex-direction:column;gap:3px}}.product-related-grid{{grid-template-columns:repeat(2,minmax(0,1fr))}}.product-related-card span{{font-size:11px}}.footer-in{{flex-direction:column;align-items:flex-start;padding-bottom:28px}}.mobile-whatsapp{{display:flex;position:fixed;left:12px;right:12px;bottom:max(10px,env(safe-area-inset-bottom));z-index:50;align-items:center;justify-content:center;background:var(--green);color:#fff;text-decoration:none;font-weight:950;border-radius:14px;min-height:52px;box-shadow:0 10px 28px rgba(20,37,61,.25);border:2px solid rgba(255,255,255,.9)}}}}
</style></head>
<body>{preview_bar}
<header class="header"><div class="header-in"><a class="brand" href="#inicio">{logo}<div class="brand-copy"><strong>{html.escape(nome_empresa)}</strong><span>{html.escape(subtitulo)}</span></div></a><div class="header-actions"><a class="ghost" href="#produtos">Ver produtos</a><a class="cta" href="{html.escape(whatsapp_geral, quote=True)}" target="_blank" rel="noopener">💬 Falar no WhatsApp</a></div></div></header>
<section class="hero" id="inicio"><div class="hero-in"><div><div class="eyebrow">Personalização que vira presença</div><h1>Seu evento, sua marca, <span>do seu jeito.</span></h1><p>{html.escape(slogan)} Escolha uma ideia na vitrine e fale com a AlphaFest para personalizar detalhes, quantidade e prazo.</p><div class="hero-actions"><a class="cta" href="{html.escape(whatsapp_geral, quote=True)}" target="_blank" rel="noopener">💬 Quero um orçamento</a><a class="secondary" href="#produtos">Explorar produtos ↓</a></div></div><aside class="hero-card"><div class="eyebrow">Vitrine AlphaFest</div><h2>Personalizados & Balões</h2><p>Ideias selecionadas para você encontrar uma referência e pedir seu orçamento.</p><div class="hero-stat"><div class="stat"><strong>{resumo['total']}</strong><span>produtos na vitrine</span></div><div class="stat"><strong>{resumo['total_categorias']}</strong><span>{html.escape(rotulo_categorias)}</span></div></div></aside></div></section>
<main class="main" id="produtos"><div class="section-head"><div><h2>Encontre seu personalizado</h2><p>{html.escape(texto_escolha)}</p></div><div id="result-count">{resumo['total']} produto(s)</div></div><div class="toolbar"><label class="search"><input id="search" type="search" placeholder="Buscar produto, tema, material, ocasião, categoria..."></label></div>{('<div class="taxonomy-nav"><section class="taxonomy-focus" id="taxonomy-focus" hidden><button type="button" class="taxonomy-back" id="taxonomy-back">← Voltar às categorias</button><div class="taxonomy-focus-copy"><small>Categoria escolhida</small><strong id="taxonomy-focus-label">Categoria</strong></div></section><section class="taxonomy-step taxonomy-cats" id="taxonomy-cats"><div class="taxonomy-heading"><div><span class="step-number">1</span><strong>Escolha uma categoria</strong></div><small>Selecione uma categoria para ver somente os produtos e subcategorias dela.</small></div><div class="filters">' + ''.join(chips) + '</div></section>' + subfilters_html + '<div class="taxonomy-current" id="taxonomy-current"><strong>Todos os produtos</strong><span>Escolha uma categoria para ver as subcategorias.</span></div></div>') if usar_taxonomia_catalogo else ('<div class="filters">' + ''.join(chips) + '</div>')}<div class="grid" id="grid">{''.join(cards)}</div>{vazio}</main>
<div class="product-detail-modal" id="product-detail-modal" hidden aria-hidden="true">
  <div class="product-detail-backdrop" data-product-close></div>
  <section class="product-detail-panel" role="dialog" aria-modal="true" aria-labelledby="product-detail-name">
    <button type="button" class="product-detail-close" data-product-close aria-label="Fechar detalhes">×</button>
    <div class="product-detail-layout">
      <div class="product-detail-media"><img id="product-detail-image" alt="" loading="eager"><div id="product-detail-placeholder" class="product-detail-placeholder" hidden>AlphaFest</div></div>
      <div class="product-detail-copy">
        <div class="product-detail-tax" id="product-detail-tax"></div>
        <h2 id="product-detail-name"></h2>
        <div class="product-detail-price" id="product-detail-price" hidden></div>
        <div class="product-detail-actions">
          {'<button type="button" class="gallery-proof-btn product-detail-gallery" id="product-detail-gallery" hidden>📸 Ver trabalhos realizados</button>' if tem_algum_produto_com_galeria else ''}
          <a class="cta product-detail-whatsapp" id="product-detail-whatsapp" href="#" target="_blank" rel="noopener">💬 Pedir orçamento deste produto</a>
        </div>
        <p id="product-detail-description"></p>
      </div>
    </div>
    <div class="product-related" id="product-related" hidden><div class="product-related-head"><strong>Você também pode gostar</strong><span>Outros itens da mesma categoria</span></div><div class="product-related-grid" id="product-related-grid"></div></div>
  </section>
</div>
<a class="mobile-whatsapp" href="{html.escape(whatsapp_geral, quote=True)}" target="_blank" rel="noopener">💬 Pedir orçamento</a>
<footer class="footer"><div class="footer-in"><div><strong>{html.escape(nome_empresa)}</strong><br><small>{html.escape(subtitulo)}{(' · ' + html.escape(local)) if local else ''}</small></div><div>{html.escape(slogan)}</div></div></footer>
<script>{script_filtros}</script>{product_detail_script}</body></html>'''
