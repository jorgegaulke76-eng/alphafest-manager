"""HF65.24.21 — Detecção e remoção segura de artes repetidas."""
from __future__ import annotations
from datetime import date, datetime
from uuid import uuid4
from collections import defaultdict
from hashlib import sha256
import streamlit as st
from site_posts_service import CATEGORIES, normalize
from site_dicas_media_hf6524 import preparar_arte


def duplicate_groups(posts):
    """Duplicates only when the stored artwork data matches byte-for-byte.

    The preferred keeper is published/featured, then oldest by creation date.
    No mutation is performed here.
    """
    buckets = defaultdict(list)
    for post in posts:
        uri = post.get('image_data_uri') or ''
        if uri.startswith('data:image/'):
            buckets[sha256(uri.encode('utf-8')).hexdigest()].append(post)
    groups = []
    for same in buckets.values():
        if len(same) < 2:
            continue
        ordered = sorted(same, key=lambda x: (
            x.get('status') != 'publicado',
            not bool(x.get('featured')),
            x.get('created_at') or '',
            x.get('id') or '',
        ))
        groups.append(ordered)
    return sorted(groups, key=lambda group: (group[0].get('created_at') or '', group[0].get('id') or ''))


def render_duplicates(posts, save, clear_cache):
    groups = duplicate_groups(posts)
    extra_ids = [post['id'] for group in groups for post in group[1:]]
    with st.expander(f'🧹 Encontrar e excluir artes duplicadas · {len(extra_ids)} cópia(s)', expanded=False):
        if not groups:
            st.success('Nenhuma cópia idêntica encontrada entre as artes cadastradas.')
            return
        st.info(f'{len(groups)} grupo(s) de imagens idênticas. Encontradas {len(extra_ids)} cópias adicionais. A imagem original de cada grupo sempre será mantida.')
        st.caption('Comparação exata do arquivo de imagem armazenado. Artes visualmente semelhantes, porém com arquivos diferentes, não serão apagadas automaticamente.')
        st.caption('Priorizamos manter uma publicação aprovada, depois destacada, ou a mais antiga. Confira os exemplos antes de confirmar.')
        for idx, group in enumerate(groups):
            keeper = group[0]
            label = keeper.get('title') or 'Arte sem título'
            with st.container(border=True):
                cols = st.columns([1, 3])
                with cols[0]:
                    st.image(keeper['image_data_uri'], width=150)
                with cols[1]:
                    st.markdown(f'**Grupo {idx+1} · {len(group)} publicações da mesma arte**')
                    st.caption(f'MANTER: {label} · {keeper.get("status", "rascunho")} · ID {keeper["id"][-6:]}')
                    for copy in group[1:]:
                        st.caption(f'↳ Cópia: {copy.get("title") or "Sem título"} · {copy.get("status", "rascunho")} · ID {copy["id"][-6:]}')
        st.divider()
        names = {p['id']: f'{p.get("title") or "Sem título"} · {p.get("category") or "Outros"} · ID {p["id"][-6:]}' for group in groups for p in group[1:]}
        with st.form('afposts_remove_duplicates', clear_on_submit=False):
            remove_all = st.checkbox(f'Selecionar todas as {len(extra_ids)} cópias idênticas', value=False)
            selected = st.multiselect('Ou selecione apenas as cópias que deseja excluir', extra_ids,
                                      default=extra_ids if remove_all else [],
                                      format_func=lambda k: names.get(k,k), disabled=remove_all)
            ids = set(extra_ids if remove_all else selected)
            st.caption(f'{len(ids)} cópia(s) serão excluídas do cadastro. {len(posts)-len(ids)} registros serão mantidos.')
            confirmation = st.checkbox('Confirmo que revisei as cópias e autorizo a exclusão definitiva dos registros selecionados', value=False)
            clicked = st.form_submit_button('🗑️ Excluir cópias selecionadas do Manager',
                                            disabled=not ids or not confirmation, use_container_width=True)
        if clicked:
            # Always retain the keeper, even if a form state is malformed.
            removable = {p['id'] for group in groups for p in group[1:]}
            safe_ids = ids & removable
            if not safe_ids:
                st.error('Nenhuma cópia válida foi selecionada.')
                return
            updated = [p for p in posts if p['id'] not in safe_ids]
            try:
                if save(updated):
                    clear_cache()
                    st.success(f'{len(safe_ids)} cópia(s) excluída(s) do cadastro. Atualize a prévia e publique o site no Cloudflare para refletir a limpeza.')
                    st.rerun()
                else:
                    st.error('O banco não confirmou a gravação. Nenhuma exclusão foi confirmada.')
            except Exception as exc:
                st.error('Não foi possível excluir as cópias: '+str(exc)[:180])


def render(load, save, clear_cache):
    with st.container(border=True):
        st.markdown('#### 📣 Novidades & Ofertas · Mural de posts no site')
        st.caption('Envie a arte e aprove: no site aparece somente a imagem completa e o botão Quero este do WhatsApp. Salvar não publica automaticamente.')
        posts = normalize(load())
        approved = sum(p['status']=='publicado' for p in posts)
        a,b,c=st.columns(3)
        a.metric('Artes cadastradas',len(posts))
        b.metric('Aprovadas',approved)
        c.metric('Rascunhos',len(posts)-approved)
        render_duplicates(posts, save, clear_cache)
        with st.expander('📥 Importar várias artes de uma vez', expanded=False):
            uploads = st.file_uploader('Selecione várias imagens prontas (PNG, JPG ou WEBP)',type=['png','jpg','jpeg','webp'],accept_multiple_files=True,key='afposts_bulk')
            bulk_cat = st.selectbox('Categoria para este lote',CATEGORIES,key='afposts_bulk_cat')
            st.caption('O lote entra como RASCUNHO; imagens exatamente iguais às já cadastradas são ignoradas para evitar duplicação.')
            if st.button('Importar lote como rascunho',disabled=not uploads,key='afposts_import'):
                created=[]
                try:
                    if len(uploads)>30:
                        raise ValueError('Importe no máximo 30 imagens por lote.')
                    existing_art={sha256((p.get('image_data_uri') or '').encode('utf-8')).hexdigest() for p in posts if p.get('image_data_uri')}
                    ignored=0
                    for file in uploads:
                        img=preparar_arte(file.getvalue())
                        fingerprint=sha256(img.encode('utf-8')).hexdigest()
                        if fingerprint in existing_art:
                            ignored+=1
                            continue
                        existing_art.add(fingerprint)
                        title=file.name.rsplit('.',1)[0].replace('_',' ').replace('-',' ').strip()[:140]
                        created.append({'id':uuid4().hex[:16],'title':title or 'Arte AlphaFest','category':bulk_cat,
                                        'description':'','image_data_uri':img,'status':'rascunho',
                                        'created_at':datetime.now().isoformat(timespec='seconds'),
                                        'expires_at':'','featured':False})
                    if not created:
                        st.info(f'Nenhuma arte nova: {ignored} imagem(ns) idêntica(s) já estava(m) cadastrada(s).')
                    elif save(posts+created):
                        clear_cache()
                        st.success(f'{len(created)} arte(s) importada(s); {ignored} repetida(s) ignorada(s). Revise e aprove antes de publicar.')
                        st.rerun()
                    else:
                        st.error('O banco não confirmou o salvamento; nada foi publicado.')
                except Exception as exc:
                    st.error('Não foi possível importar: '+str(exc)[:180])
        with st.expander('✅ Aprovar ou retirar várias artes de uma vez', expanded=bool(posts and not approved)):
            st.caption('Selecione as artes para mudar o status. Essa ação apenas salva no Manager: a publicação no Cloudflare continua manual.')
            drafts=[p for p in posts if p['status']!='publicado']
            published_items=[p for p in posts if p['status']=='publicado']
            operation=st.radio('Ação em lote', ['Aprovar rascunhos para o site','Retirar publicações do site'], horizontal=True, key='afposts_action')
            candidates=drafts if operation.startswith('Aprovar') else published_items
            if not candidates:
                st.info('Não há artes para esta ação.')
            else:
                all_selected=st.checkbox(f'Selecionar todas ({len(candidates)} artes)',key='afposts_select_all')
                options=[p['id'] for p in candidates]
                title_by_id={p['id']:f"{p['title'] or 'Arte sem título'} · {p['category']} · {p['id'][-5:]}" for p in candidates}
                selection=st.multiselect('Ou escolha artes específicas',options=options,
                                         default=options if all_selected else [],
                                         format_func=lambda k:title_by_id.get(k,k),key='afposts_select_ids',
                                         disabled=all_selected)
                targets=options if all_selected else selection
                st.caption(f'{len(targets)} arte(s) selecionada(s) de {len(candidates)} disponíveis.')
                confirm=st.checkbox('Conferi as artes selecionadas e confirmo a alteração',key='afposts_confirm_bulk')
                action_label='✅ Aprovar artes selecionadas' if operation.startswith('Aprovar') else '📝 Retirar artes selecionadas'
                if st.button(action_label,disabled=not targets or not confirm,key='afposts_apply_bulk',use_container_width=True):
                    selected_ids=set(targets)
                    desired='publicado' if operation.startswith('Aprovar') else 'rascunho'
                    updated=[{**p,'status':desired} if p['id'] in selected_ids else p for p in posts]
                    try:
                        if save(updated):
                            clear_cache()
                            st.success(f'{len(selected_ids)} arte(s) atualizada(s). Prepare a prévia e publique no Cloudflare após conferir.')
                            st.rerun()
                        else:
                            st.error('A gravação não foi confirmada pelo banco. Nenhum item foi publicado.')
                    except Exception as exc:
                        st.error('Não foi possível salvar o lote: '+str(exc)[:180])
        choices={'__new__':'➕ Nova publicação'}
        choices.update({p['id']:(p['title'] or 'Sem título')+' · '+p['status'] for p in reversed(posts)})
        selected=st.selectbox('Editar publicação',list(choices),format_func=lambda k:choices[k],key='afposts_selected')
        old=next((p for p in posts if p['id']==selected),{})
        with st.form('afposts_editor'):
            title=st.text_input('Nome interno para identificar a arte (opcional)',value=old.get('title',''),max_chars=140,help='Não aparece no site; pode ser preenchido automaticamente pelo nome do arquivo.')
            category=st.selectbox('Categoria',CATEGORIES+([old['category']] if old.get('category') and old['category'] not in CATEGORIES else []),index=(CATEGORIES+([old['category']] if old.get('category') and old['category'] not in CATEGORIES else [])).index(old.get('category','Outros')))
            status=st.selectbox('Publicação',['rascunho','publicado'],index=1 if old.get('status')=='publicado' else 0,
                                format_func=lambda v:'✅ Aprovada para a próxima publicação' if v=='publicado' else '📝 Rascunho (não aparece no site)')
            featured=st.checkbox('Destacar na página inicial',value=bool(old.get('featured')))
            expires=st.text_input('Fim da divulgação (opcional, AAAA-MM-DD)',value=old.get('expires_at',''),help='Após a data, a oferta sai do site quando você publicar uma nova versão. Deixe vazio para manter.')
            upload=st.file_uploader('Arte finalizada (JPG, PNG, WEBP)',type=['jpg','jpeg','png','webp'],key='afposts_img_'+selected)
            delete=st.checkbox('Arquivar / retirar do site (manter no Manager)',value=False) if selected!='__new__' else False
            save_clicked=st.form_submit_button('💾 Salvar publicação (sem publicar site)',use_container_width=True)
        if old.get('image_data_uri'):
            st.image(old['image_data_uri'],caption='Arte atual · proporção original',use_container_width=False,width=340)
        if save_clicked:
            try:
                if expires:
                    date.fromisoformat(expires)
                image=preparar_arte(upload.getvalue()) if upload else old.get('image_data_uri','')
                if not image:
                    raise ValueError('Selecione uma imagem da publicação.')
                item={**old,'id':old.get('id') or uuid4().hex[:16],
                      'title':title.strip() or ((upload.name.rsplit('.',1)[0].replace('_',' ').strip()[:140]) if upload else (old.get('title') or 'Arte AlphaFest')),
                      'description':'','category':category,
                      'status':'rascunho' if delete else status,'featured':featured,
                      'expires_at':expires,'image_data_uri':image,
                      'created_at':old.get('created_at') or datetime.now().isoformat(timespec='seconds')}
                updated=[p for p in posts if p['id']!=item['id']]+[item]
                if save(updated):
                    clear_cache()
                    st.success('Publicação salva. Use “Preparar prévia” e depois publique o site quando quiser.')
                    st.rerun()
                else:
                    st.error('O banco não confirmou o salvamento; nenhum dado foi alterado.')
            except Exception as exc:
                st.error('Não foi possível salvar: '+str(exc)[:180])
        st.caption('Artes antigas permanecem no Manager. Para sair do site, selecione Rascunho ou informe a data de fim. A atualização do site exige publicação manual.')
