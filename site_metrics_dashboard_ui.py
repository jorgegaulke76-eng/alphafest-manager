"""HF65.24.35 — Painel de decisão das métricas privadas da AlphaFest.

Somente apresentação: não altera coleta, persistência, permissões nem
considera cliques em WhatsApp como mensagens ou vendas efetivadas.
"""
from __future__ import annotations

from typing import Any, Callable


def _positive_int(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def decision_notes(metrics: dict) -> list[tuple[str, str]]:
    """Sugestões descritivas, baseadas no que efetivamente foi observado."""
    periods = metrics.get('periods') or {}
    month = periods.get('30d') or {}
    sessions = _positive_int(metrics.get('commercial_sessions_30d'))
    wa = _positive_int(month.get('whatsapp'))
    cart = _positive_int((metrics.get('commercial_clicks_30d') or {}).get('cart'))
    corp = _positive_int((metrics.get('commercial_clicks_30d') or {}).get('corporate'))
    top_products = metrics.get('top_products') or []
    wa_products = [x for x in (metrics.get('top_whatsapp_products') or [])
                   if not str(x[0]).lower().startswith(('orçamento com ', 'orçamento corporativo'))]
    notes = []
    if sessions < 30:
        notes.append(('Acompanhar amostra', 'Ainda há poucas sessões comerciais para interpretar tendências com segurança.'))
    else:
        notes.append(('Monitorar interesse', f'{sessions} sessões comerciais estimadas no período. Compare a evolução antes de mudar campanhas.'))
    if cart or corp:
        notes.append(('Acompanhar solicitações', f'{cart} abertura(s) de WhatsApp pelo carrinho e {corp} pela página Para Empresas. Confirme os pedidos recebidos no atendimento.'))
    elif wa:
        notes.append(('Investigar caminho do contato', 'Houve cliques gerais no WhatsApp, mas nenhum dos canais de orçamento específicos foi identificado neste período.'))
    else:
        notes.append(('Revisar chamadas para ação', 'Nenhum clique no WhatsApp foi registrado no período; confira o tráfego e as chamadas para orçamento.'))
    if top_products:
        name, count = top_products[0]
        notes.append(('Produto em destaque', f'“{name}” lidera as aberturas de produtos ({count}). Verifique fotos, oferta e capacidade de produção antes de priorizar divulgação.'))
    if wa_products:
        name, count = wa_products[0]
        notes.append(('Interesse por orçamento', f'“{name}” aparece entre os produtos associados a cliques no WhatsApp ({count}). Não representa venda confirmada.'))
    if not metrics.get('top_campaigns'):
        notes.append(('Identificar campanhas', 'Use links com UTM nas divulgações para diferenciar Instagram, Google e outras campanhas.'))
    return notes[:4]


def _ranking(st, rows, *, empty: str, max_items: int = 8, labeler: Callable[[str], str] | None = None):
    if not rows:
        st.caption(empty)
        return
    for idx, (name, qty) in enumerate(rows[:max_items], 1):
        label = labeler(str(name)) if labeler else str(name)
        a, b = st.columns([5, 1])
        a.markdown(f'**{idx:02d}. {label}**')
        b.markdown(f'**{_positive_int(qty)}**')


def render_dashboard(st, pd, summary: dict, friendly_name: Callable[[str], str]):
    """Interface privada; dados já calculados pelo serviço de métricas existente."""
    m = summary
    periods = m.get('periods') or {}
    today = periods.get('today') or {}
    week = periods.get('7d') or {}
    month = periods.get('30d') or {}
    commercial = m.get('commercial_clicks_30d') or {}
    pages = m.get('commercial_pages_30d') or {}

    st.markdown('### 📊 Inteligência Comercial · Site AlphaFest')
    st.caption('Visão executiva para Jorge e Anna · dados de navegação, não faturamento')
    tab_general, tab_products, tab_public, tab_evolution = st.tabs([
        '📌 Visão geral', '🎯 Produtos e oportunidades', '🌍 Público e canais', '📈 Evolução e diagnóstico'
    ])
    with tab_general:
        period_name = st.segmented_control('Período do resumo', ['Hoje', '7 dias', '30 dias'],
            default='30 dias', key='hf652433_period', help='Muda os indicadores gerais; os rankings detalhados continuam nos últimos 30 dias.')
        current = {'Hoje': today, '7 dias': week, '30 dias': month}[period_name or '30 dias']
        a, b, c, d = st.columns(4)
        a.metric('Visitas registradas', _positive_int(current.get('pageviews')), help='Aberturas de páginas no período. Podem incluir visitas técnicas ou repetidas.')
        b.metric('Produtos abertos', _positive_int(current.get('products')), help='Aberturas de fichas de produtos; não equivale a visitantes diferentes.')
        c.metric('Cliques no WhatsApp', _positive_int(current.get('whatsapp')), help='Tentativas de abrir o WhatsApp, não mensagens enviadas.')
        d.metric('Sessões estimadas', _positive_int(current.get('sessions')), help='Sessões identificadas pelo navegador; estimativa, não pessoas únicas.')
        st.caption('Acessos e cliques são eventos. O período selecionado não altera a janela de 30 dias dos rankings abaixo.')
        st.markdown('#### 🛒 Canais de orçamento · últimos 30 dias')
        a, b, c, d = st.columns(4)
        a.metric('Carrinho → WhatsApp', _positive_int(commercial.get('cart')))
        b.metric('Empresas → WhatsApp', _positive_int(commercial.get('corporate')))
        c.metric('Visitas Para Empresas', _positive_int(pages.get('corporate')))
        d.metric('Visitas Novidades', _positive_int(pages.get('news')))
        st.markdown('#### 💡 O que os dados sugerem')
        for title, detail in decision_notes(m):
            with st.container(border=True):
                st.markdown(f'**{title}**')
                st.caption(detail)
        st.markdown('#### 📍 Páginas e contatos · últimos 30 dias')
        p1, p2 = st.columns(2)
        with p1:
            st.markdown('**Páginas mais acessadas**')
            _ranking(st, m.get('top_pages_30d') or [], empty='Ainda não há páginas registradas.', labeler=friendly_name)
        with p2:
            st.markdown('**Páginas que originaram cliques no WhatsApp**')
            _ranking(st, m.get('top_whatsapp_pages_30d') or [], empty='Ainda não há cliques identificados.', labeler=friendly_name)
    with tab_products:
        st.markdown('#### 🧭 Ranking de oportunidades · últimos 30 dias')
        st.caption('Prioriza sinais de interesse observados. Não é ranking de vendas, pedidos ou faturamento.')
        candidates=m.get('product_opportunities_30d') or []
        if candidates:
            limit=st.selectbox('Produtos para analisar', [5, 10, 20], index=0, key='hf652435_limit')
            rows=[{'Produto':v['produto'], 'Aberturas':_positive_int(v['aberturas']),
                   'Cliques diretos':_positive_int(v['cliques_diretos']), 'Leitura':v['sinal']}
                  for v in candidates[:limit]]
            st.dataframe(pd.DataFrame(rows),hide_index=True,use_container_width=True)
            st.caption('Cliques diretos são associados ao produto nomeado no botão individual. Orçamentos com múltiplos itens no carrinho NÃO são atribuídos artificialmente a produtos específicos.')
            featured=candidates[0]
            with st.container(border=True):
                st.markdown('**💡 Próxima ação sugerida**')
                if featured['cliques_diretos']:
                    st.write(f"Verifique fotos, prazo e disponibilidade de **{featured['produto']}**, pois teve {_positive_int(featured['cliques_diretos'])} clique(s) direto(s) para WhatsApp no período. Confirme a demanda no atendimento antes de lançar uma promoção.")
                else:
                    st.write(f"**{featured['produto']}** está entre os mais abertos, mas ainda não tem cliques diretos associados. Revise a apresentação do produto e acompanhe novas sessões antes de investir em anúncio.")
        else:
            st.info('Ainda não há aberturas de produtos ou cliques diretos suficientes para montar o ranking.')
        st.divider()
        st.markdown('#### 🎯 Interesse por produtos · últimos 30 dias')
        a, b = st.columns(2)
        with a:
            st.markdown('**Mais visualizados**')
            _ranking(st, m.get('top_products') or [], empty='Nenhum produto aberto no período.')
        with b:
            st.markdown('**Associados a cliques no WhatsApp**')
            filtered = [(k, v) for k, v in (m.get('top_whatsapp_products') or [])
                if not str(k).lower().startswith(('orçamento com ', 'orçamento corporativo'))]
            _ranking(st, filtered, empty='Nenhum produto individual identificado nos cliques.')
        st.info('Um produto visualizado muitas vezes pode indicar interesse, mas não confirma intenção de compra. Os cliques do carrinho são agrupados e não são atribuídos a cada item individual.')
        st.markdown('#### 🔍 O que o público procura')
        a, b = st.columns(2)
        with a:
            st.markdown('**Buscas no site**')
            _ranking(st, m.get('top_search_terms') or [], empty='Ainda não há buscas registradas.')
        with b:
            st.markdown('**Fotos da galeria abertas**')
            _ranking(st, m.get('top_gallery') or [], empty='Ainda não há aberturas registradas.')
        a, b = st.columns(2)
        with a:
            st.markdown('**Datas e ocasiões pesquisadas**')
            _ranking(st, m.get('top_occasions') or [], empty='Nenhum filtro sazonal registrado.')
        with b:
            st.markdown('**Contextos dos contatos**')
            _ranking(st, m.get('whatsapp_contexts') or [], empty='Nenhum contexto identificado.')
    with tab_public:
        st.markdown('#### 🌍 Perfil de visitantes · últimos 30 dias')
        profile=m.get('audience_profile_30d') or {}
        n=_positive_int(profile.get('session_count'))
        cities=profile.get('cities') or []
        regions=profile.get('regions') or []
        countries=profile.get('countries') or []
        devices=profile.get('devices') or []
        sources=profile.get('sources') or []
        known=_positive_int(profile.get('known_city_sessions'))
        mobile=sum(_positive_int(v) for k,v in devices if str(k).lower() in ('celular','tablet'))
        computer=sum(_positive_int(v) for k,v in devices if str(k).lower()=='computador')
        a,b,c,d=st.columns(4)
        a.metric('Sessões com perfil',n, help='Uma entrada por sessão comercial identificada nos últimos 30 dias; não são pessoas únicas.')
        b.metric('Celular / tablet',f'{mobile/n*100:.1f}%' if n else '—',help='Percentual de sessões. Inclui tablet.')
        c.metric('Computador',f'{computer/n*100:.1f}%' if n else '—',help='Percentual de sessões.')
        d.metric('Cidade identificada',f'{known/n*100:.1f}%' if n else '—',help='Cobertura da localização aproximada, não precisão geográfica.')
        st.caption('Distribuição baseada na primeira página registrada de cada sessão. Sessões ≠ pessoas diferentes; dados podem faltar ou sofrer bloqueios de privacidade.')

        def profile_ranking(rows, empty, limit=8):
            if not rows:
                st.caption(empty)
                return
            for key,value in rows[:limit]:
                val=_positive_int(value)
                pct=100*val/n if n else 0
                x,y=st.columns([5,2])
                x.write(str(key))
                y.write(f'**{val}** · {pct:.1f}%')

        st.markdown('#### 📱 Tipo de aparelho e canais de chegada')
        left,right=st.columns(2)
        with left:
            st.markdown('**Como acessam o site**')
            profile_ranking(devices,'Sem aparelhos identificados.')
            if devices:
                df=pd.DataFrame(devices,columns=['Aparelho','Sessões']).set_index('Aparelho')
                st.bar_chart(df,height=190)
        with right:
            st.markdown('**De onde vieram**')
            profile_ranking(sources,'Sem canais identificados.',10)
            if sources:
                df=pd.DataFrame(sources[:10],columns=['Canal','Sessões']).set_index('Canal')
                st.bar_chart(df,height=190)
        st.caption('Direto significa que não foi possível identificar um site de origem ou campanha. Links sem UTM podem não permitir distinguir Instagram, WhatsApp e outros aplicativos.')

        st.markdown('#### 📍 Localização aproximada dos acessos')
        left,right=st.columns(2)
        with left:
            st.markdown('**Cidades**')
            profile_ranking(cities,'Nenhuma cidade disponível.')
            st.markdown('**Estados e regiões**')
            profile_ranking(regions,'Nenhuma região disponível.',6)
        with right:
            st.markdown('**Países**')
            profile_ranking(countries,'Nenhum país disponível.',6)
            st.markdown('**Navegador**')
            profile_ranking(profile.get('browsers') or [],'Sem navegador identificado.',6)
        st.caption('Localização estimada pela rede, quando disponível no Cloudflare; pode ser aproximada ou ausente. Nunca indica endereço residencial, GPS ou identidade do visitante.')

        st.markdown('#### 🎯 Canais com oportunidades de contato')
        st.caption('Sessões com ao menos um clique no WhatsApp, agrupadas pelo canal de chegada observado na primeira visita da sessão.')
        channel_rows=m.get('channel_opportunities_30d') or []
        if channel_rows:
            st.dataframe(pd.DataFrame([{'Canal':v['canal'], 'Sessões':v['sessoes'],
                'Sessões com WhatsApp':v['sessoes_whatsapp'],
                'Participação com clique':f"{v['percentual']:.1f}%"}
                for v in channel_rows]),hide_index=True,use_container_width=True)
        else:
            st.caption('Ainda não há sessões com origem identificada.')
        st.caption('Associação na mesma sessão, não comprovação de venda ou causalidade. Acesso Direto pode incluir aplicativos sem referência; testes internos também podem estar presentes. Compare períodos antes de escolher onde investir.')
        st.markdown('#### 📣 Campanhas com identificação')
        _ranking(st,m.get('top_campaigns') or [],empty='Nenhuma campanha UTM identificada. Use links com utm_source e utm_campaign nas divulgações.',max_items=10)
        with st.expander('Sobre homem, mulher e dados demográficos'):
            st.info('O site não coleta gênero/sexo. Não é possível determinar com confiabilidade se a pessoa é homem ou mulher pela visita, localização ou aparelho. Este dado permanece **não informado**; não fazemos inferências sobre visitantes. Se houver pesquisa voluntária no futuro, ela exige finalidade clara e cuidado com privacidade.')
        st.caption('Os indicadores anteriores por visualização continuam disponíveis nos relatórios históricos. Este perfil usa sessões para evitar que múltiplas páginas da mesma sessão inflem as contagens.')
    with tab_evolution:
        st.markdown('#### 📈 Evolução dos acessos')
        td, tm, ty = st.tabs(['Dia a dia', 'Mês a mês', 'Ano a ano'])
        for target, key, chart in ((td, 'daily_series', 'line'), (tm, 'monthly_series', 'bar'), (ty, 'yearly_series', 'bar')):
            with target:
                df = pd.DataFrame(m.get(key) or [])
                if not df.empty and {'Período', 'Acessos', 'Produtos', 'WhatsApp'}.issubset(df.columns):
                    df = df.set_index('Período')[['Acessos', 'Produtos', 'WhatsApp']]
                    if chart == 'line': st.line_chart(df, height=295)
                    else: st.bar_chart(df, height=295)
                else: st.caption('Dados insuficientes para este gráfico.')
        st.markdown('#### 📉 Funil por sessão · últimos 30 dias')
        a, b, c = st.columns(3)
        a.metric('Acesso → Produto', f"{month.get('conv_product', 0):.1f}%", help='Sessões que abriram ao menos um produto ÷ sessões com acesso.')
        b.metric('Acesso → WhatsApp', f"{month.get('conv_whatsapp', 0):.1f}%", help='Sessões com clique no WhatsApp ÷ sessões com acesso.')
        c.metric('Produto → WhatsApp', f"{month.get('conv_product_to_whatsapp', 0):.1f}%", help='Sessões com clique no WhatsApp ÷ sessões que abriram produto. Não exige que o clique venha daquele produto.')
        st.caption(f"Sessões estimadas: {_positive_int(m.get('sessions_30d'))} · Visitantes estimados: {_positive_int(m.get('visitors_30d'))}. Taxas por sessão, não vendas efetivadas.")
        st.markdown('#### 🧪 Qualidade dos dados')
        a, b, c = st.columns(3)
        a.metric('Visitas comerciais por URL', _positive_int(m.get('commercial_pageviews_30d')))
        b.metric('Acessos técnicos por URL', _positive_int(m.get('technical_pageviews_30d')))
        c.metric('Sessões comerciais estimadas', _positive_int(m.get('commercial_sessions_30d')))
        st.caption('A exclusão de URLs técnicas não identifica todos os robôs. Testes internos podem aparecer nas métricas; não há filtro confiável de testes neste histórico.')
        with st.expander('Arquivos técnicos identificados'):
            _ranking(st, m.get('top_technical_pages_30d') or [], empty='Nenhum arquivo técnico identificado.')
        st.caption('Os eventos específicos do carrinho e de Para Empresas são coletados somente desde a publicação do rastreamento correspondente; não são retroativos.')
