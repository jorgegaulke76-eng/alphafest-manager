"""HF65.24.18 — Administração simplificada das artes diárias no site."""
from __future__ import annotations
from datetime import date, datetime
from uuid import uuid4
import streamlit as st
from site_posts_service import CATEGORIES, normalize
from site_dicas_media_hf6524 import preparar_arte


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
        with st.expander('📥 Importar várias artes de uma vez', expanded=False):
            uploads = st.file_uploader('Selecione várias imagens prontas (PNG, JPG ou WEBP)',type=['png','jpg','jpeg','webp'],accept_multiple_files=True,key='afposts_bulk')
            bulk_cat = st.selectbox('Categoria para este lote',CATEGORIES,key='afposts_bulk_cat')
            st.caption('O lote entra como RASCUNHO; você poderá editar títulos e aprovar as artes individualmente.')
            if st.button('Importar lote como rascunho',disabled=not uploads,key='afposts_import'):
                created=[]
                try:
                    if len(uploads)>30:
                        raise ValueError('Importe no máximo 30 imagens por lote.')
                    for file in uploads:
                        img=preparar_arte(file.getvalue())
                        title=file.name.rsplit('.',1)[0].replace('_',' ').replace('-',' ').strip()[:140]
                        created.append({'id':uuid4().hex[:16],'title':title or 'Arte AlphaFest','category':bulk_cat,
                                        'description':'','image_data_uri':img,'status':'rascunho',
                                        'created_at':datetime.now().isoformat(timespec='seconds'),
                                        'expires_at':'','featured':False})
                    if save(posts+created):
                        clear_cache()
                        st.success(f'{len(created)} artes importadas. Revise e aprove antes de publicar.')
                        st.rerun()
                    else:
                        st.error('O banco não confirmou o salvamento; nada foi publicado.')
                except Exception as exc:
                    st.error('Não foi possível importar: '+str(exc)[:180])
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
