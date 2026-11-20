"""Interface de controle DAS-MEI para a gestão AlphaFest."""
from __future__ import annotations
from datetime import date,datetime
import csv,io
import hmac
import streamlit as st
from das_mei_service import DOC_KEY,LOCAL_PATH,PGMEI_URL,new_record,normalize,money,status_of,change,totals,date_due
from das_mei_storage import upload,download

def authorized() -> bool:
    """Código de acesso guardado apenas nos Secrets do servidor (nunca em arquivos do pacote)."""
    try: configured=str(st.secrets.get('DAS_MEI_ACCESS_CODE','') or '')
    except Exception: configured=''
    if len(configured)<10:
        st.warning('Para liberar documentos fiscais, configure DAS_MEI_ACCESS_CODE (10+ caracteres) nos Secrets do Streamlit. O módulo permanece bloqueado até isso acontecer.')
        return False
    if st.session_state.get('_das_mei_authorized') is True:
        return True
    typed=st.text_input('Código de acesso ao Controle DAS-MEI',type='password',key='das_mei_login')
    if st.button('🔐 Desbloquear controle DAS',key='das_mei_unlock'):
        if hmac.compare_digest(typed,configured):
            st.session_state['_das_mei_authorized']=True
            st.rerun()
        else:
            st.error('Código de acesso inválido.')
    return False


def render(load_document,save_document,actor,now):
    if not authorized(): return
    st.subheader('🧾 Controle de DAS-MEI')
    if st.button('🔒 Bloquear documentos fiscais',key='das_mei_logout'):
        st.session_state.pop('_das_mei_authorized',None)
        st.rerun()
    st.caption('Emissão oficial pelo PGMEI; controle de competências, guias, comprovantes e pagamento no Manager.')
    st.info('O DAS-MEI normalmente vence no dia 20 do mês seguinte (ajuste para dia útil). Feriados e guias atrasadas devem ser conferidos no PGMEI; o valor oficial é o da guia, não uma estimativa do sistema.')
    today=now.date()
    year=st.selectbox('Ano de referência',list(range(today.year+1,max(2020,today.year-6),-1)),index=1,key='das_year')
    base=normalize(load_document(DOC_KEY,LOCAL_PATH,{'registros':{}}))
    records=base['registros']
    stats=totals(records,year,today)
    cols=st.columns(6)
    for c,name,key in zip(cols,['A emitir','A pagar','Vencidas','Informados','Pagas','Total pago'],['a_emitir','a_pagar','vencidas','informadas','pagas','total_pago']):
        c.metric(name, f"R$ {stats[key]:,.2f}" if key=='total_pago' else stats[key])
    if st.button('📅 Criar competências do ano (sem emitir ou pagar)',key='das_create_year'):
        added={f'{year}-{m:02d}':new_record(year,m) for m in range(1,13) if f'{year}-{m:02d}' not in records}
        if not added: st.info('As 12 competências desse ano já estão cadastradas.')
        else:
            fresh=normalize(load_document(DOC_KEY,LOCAL_PATH,{'registros':{}},force_refresh=True))
            items=fresh['registros']
            updates={k:v for k,v in added.items() if k not in items}
            items.update(updates)
            if save_document(DOC_KEY,fresh,LOCAL_PATH):
                st.success(f'{len(updates)} competência(s) cadastrada(s). Nenhuma guia foi emitida ou marcada como paga.')
                st.rerun()

    # HF65.24.16 — regularização sem inventar valores e datas nem declarar quitação verificada.
    if year == 2026:
        eligible=[f"2026-{m:02d}" for m in range(1,10)
                  if isinstance(records.get(f"2026-{m:02d}"),dict)
                  and records[f"2026-{m:02d}"].get("status") not in ("Paga","Pagamento informado")]
        if eligible:
            with st.expander(f"📘 Registrar {len(eligible)} competência(s) de janeiro a setembro como pagamento informado",expanded=False):
                st.info('Você informou que janeiro a setembro de 2026 foram pagos. O registro ficará como informado, aguardando conferência. Valores, datas e comprovantes permanecerão vazios.')
                acknowledged=st.checkbox('Confirmo que essas competências foram pagas e desejo registrar apenas a informação, sem comprovantes por enquanto.',key='das_mei_bulk_ack')
                if st.button('Registrar pagamento informado nas competências selecionadas',disabled=not acknowledged,key='das_mei_bulk_confirm'):
                    fresh=normalize(load_document(DOC_KEY,LOCAL_PATH,{'registros':{}},force_refresh=True))
                    changed=0
                    for comp in eligible:
                        old=fresh['registros'].get(comp)
                        if isinstance(old,dict) and old.get('status') not in ('Paga','Pagamento informado'):
                            fresh['registros'][comp]=change(old,{'status':'Pagamento informado'},actor,now)
                            changed+=1
                    if changed and save_document(DOC_KEY,fresh,LOCAL_PATH):
                        st.success(f'{changed} competência(s) registradas como pagamento informado; aguardando documentação.');st.rerun()
                    elif not changed: st.info('As competências já foram atualizadas em outra sessão.')

    keys=sorted((k for k in records if k.startswith(f'{year}-')),reverse=True)
    if keys:
        rows=[]
        for key in keys:
            x=records[key]
            rows.append({'Competência':key[5:]+'/'+key[:4], 'Vencimento':x.get('vencimento',''),
                         'Situação':status_of(x,today), 'Valor (R$)':x.get('valor'),
                         'Pagamento':x.get('pago_em',''), 'Guia': 'Sim' if x.get('guia_path') else 'Não',
                         'Comprovante':'Sim' if x.get('comprovante_path') else 'Não'})
        st.dataframe(rows,hide_index=True,width="stretch")
        stream=io.StringIO(); writer=csv.DictWriter(stream,fieldnames=list(rows[0]),delimiter=';');writer.writeheader();writer.writerows(rows)
        st.download_button('⬇️ Exportar controle CSV',stream.getvalue().encode('utf-8-sig'),file_name=f'das_mei_{year}.csv',mime='text/csv',key='das_csv')
    else: st.info('Nenhuma competência cadastrada para este ano. Use o botão acima.')
    st.link_button('🌐 Emitir ou consultar DAS no portal oficial (PGMEI)',PGMEI_URL)
    if not keys: return
    key=st.selectbox('Competência para consultar / atualizar',keys,format_func=lambda k:k[5:]+'/'+k[:4],key='das_current')
    row=records[key]
    st.caption('Pagamento informado = cliente confirma quitação anterior, aguardando conferência de guia/comprovante. Não contabiliza no total efetivamente conferido.')
    st.caption('Documentos privados: somente pessoal autorizado no Manager. Anexar PDF não confirma pagamento.')
    with st.form('das_edit_form'):
        a,b=st.columns(2)
        emitida=a.date_input('Data de emissão (opcional)',value=date.fromisoformat(row['emitido_em']) if row.get('emitido_em') else None,format='DD/MM/YYYY')
        due=b.date_input('Vencimento da guia',value=date.fromisoformat(row['vencimento']),format='DD/MM/YYYY',help='Altere se o PGMEI indicar outro vencimento.')
        valor=st.number_input('Valor conforme DAS oficial (R$)',min_value=0.0,step=0.01,format='%.2f',value=float(row.get('valor') or 0))
        option=st.selectbox('Situação', ['A emitir','Emitida / a pagar','Pagamento informado','Paga'],index=['A emitir','Emitida / a pagar','Pagamento informado','Paga'].index(row.get('status','A emitir')))
        payment=st.date_input('Data do pagamento (se pago)',value=date.fromisoformat(row['pago_em']) if row.get('pago_em') else None,format='DD/MM/YYYY')
        notes=st.text_area('Observações',value=row.get('observacoes') or '',max_chars=1000)
        pdf_guide=st.file_uploader('Guia DAS em PDF (até 8 MB)',type=['pdf'],key=f'das_guia_{key}')
        pdf_receipt=st.file_uploader('Comprovante de pagamento em PDF (até 8 MB)',type=['pdf'],key=f'das_receipt_{key}')
        confirm=st.checkbox('Confirmo que conferi o pagamento no banco/PGMEI',value=False)
        save=st.form_submit_button('💾 Salvar competência',type='primary',width="stretch")
    if save:
        try:
            if option == 'Paga' and not confirm:
                raise ValueError('Para marcar como Paga, confirme que verificou o pagamento.')
            if option == 'Paga' and not payment:
                raise ValueError('Informe a data do pagamento.')
            if option != 'Paga' and payment:
                raise ValueError('A data de pagamento só deve ser preenchida com situação Paga.')
            if option == 'A emitir' and emitida:
                raise ValueError('Após emitir a guia, selecione Emitida / a pagar.')
            upd={'status':option,'emitido_em':emitida.isoformat() if emitida else '',
                 'vencimento':due.isoformat(),'valor':money(valor) if valor>0 else None,
                 'pago_em':payment.isoformat() if payment else '', 'observacoes':notes.strip()}
            if option=='Paga' and (not upd['valor'] or upd['valor']<=0):
                raise ValueError('Informe o valor efetivamente pago conforme a guia.')
            if pdf_guide: upd['guia_path']=upload(pdf_guide,key,'guia')
            if pdf_receipt: upd['comprovante_path']=upload(pdf_receipt,key,'comprovante')
            fresh=normalize(load_document(DOC_KEY,LOCAL_PATH,{'registros':{}},force_refresh=True))
            current=fresh['registros'].get(key)
            if current != row:
                st.error('Esta competência foi alterada em outra sessão. Atualize o Manager antes de salvar.')
            else:
                fresh['registros'][key]=change(row,upd,actor,now)
                if save_document(DOC_KEY,fresh,LOCAL_PATH):
                    st.success('Competência salva e confirmada no banco.');st.rerun()
        except Exception as exc:
            st.error(f'Não foi possível salvar a competência: {exc}')
    for field,desc in [('guia_path','Guia DAS'),('comprovante_path','Comprovante')]:
        path=row.get(field)
        if path:
            if st.button(f'📄 Carregar {desc}',key=f'das_get_{field}_{key}'):
                try: st.session_state[f'das_bytes_{field}_{key}']=download(path)
                except Exception as exc: st.error(f'Erro ao abrir arquivo privado: {exc}')
            binary=st.session_state.get(f'das_bytes_{field}_{key}')
            if binary: st.download_button(f'⬇️ Baixar {desc}',binary,file_name=f'{key}-{field}.pdf',mime='application/pdf',key=f'das_down_{field}_{key}')
    with st.expander('Histórico de alterações / auditoria'):
        for item in reversed(row.get('historico') or []):
            st.caption(f"{item.get('quando','')} · {item.get('por','')} · campos: {', '.join(item.get('alteracoes') or [])}")
