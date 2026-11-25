"""HF65.24.58: controle explícito de aprovação por arquivo e ficha interna TXT.

Não substitui aprovação comercial nem modifica status do Fluxo/Histórico.
"""
from __future__ import annotations
from datetime import datetime


def _texto(value, max_len=500):
    return ' '.join(str(value or '').replace('\x00', '').split())[:max_len]


def artes(projeto):
    return [a for a in (projeto.get('arquivos') or []) if isinstance(a, dict)
            and not a.get('arquivado') and a.get('categoria') == 'Arte' and a.get('id')]


def situacao_arte(projeto):
    lista = artes(projeto)
    registro = projeto.get('aprovacao_arte_hf58') or {}
    if not lista:
        return 'sem_arte', None
    if not registro.get('arquivo_id'):
        return 'sem_aprovacao', None
    selecionada = next((a for a in lista if a.get('id') == registro.get('arquivo_id')), None)
    if not selecionada:
        return 'revisao_pendente', None
    # Um upload posterior exige nova conferência, ainda que a arte anterior permaneça.
    todas_artes = [a for a in (projeto.get('arquivos') or []) if isinstance(a, dict) and a.get('categoria') == 'Arte' and a.get('id')]
    ultima = lista[-1]
    if ultima.get('id') != selecionada.get('id') or registro.get('total_artes_no_registro') != len(todas_artes):
        return 'revisao_pendente', selecionada
    return 'aprovada', selecionada


def registrar_aprovacao(projeto, arquivo_id, responsavel, instante):
    lista = artes(projeto)
    todas_artes = [a for a in (projeto.get('arquivos') or []) if isinstance(a, dict) and a.get('categoria') == 'Arte' and a.get('id')]
    if not lista or lista[-1].get('id') != arquivo_id:
        raise ValueError('Selecione a arte mais recente e ativa para aprovação.')
    nome = _texto(responsavel, 90)
    if not nome:
        raise ValueError('Informe quem registrou a confirmação da arte.')
    if not isinstance(instante, datetime):
        raise ValueError('Data de aprovação inválida.')
    resultado = dict(projeto)
    evento = {'arquivo_id': arquivo_id, 'arquivo_nome': _texto(lista[-1].get('nome'), 180),
              'responsavel': nome, 'registrado_em': instante.isoformat(timespec='seconds'),
              'total_artes_no_registro': len(todas_artes)}
    historico = list(resultado.get('historico_aprovacao_arte_hf58') or [])
    historico.append(evento)
    resultado['historico_aprovacao_arte_hf58'] = historico[-100:]
    resultado['aprovacao_arte_hf58'] = evento
    return resultado


def ficha_producao_txt(proposta, projeto, instante):
    if not isinstance(instante, datetime):
        raise ValueError('Data de geração inválida.')
    proposta = proposta or {}
    projeto = projeto or {}
    status, arte = situacao_arte(projeto)
    etiquetas = {'aprovada':'APROVADA (registro interno)',
                 'revisao_pendente':'REVISÃO PENDENTE',
                 'sem_aprovacao':'NÃO APROVADA', 'sem_arte':'SEM ARTE CADASTRADA'}
    linhas = [
        'ALPHAFEST | FICHA INTERNA DE PRODUÇÃO',
        'Gerada em: ' + instante.strftime('%d/%m/%Y %H:%M'),
        'CONSULTA: não aprova arte, pedido ou produção; conferir dados atuais no Manager.', '',
        'Pedido: ' + _texto(proposta.get('numero_proposta') or 'não informado', 80),
        'Cliente: ' + _texto(proposta.get('cliente_nome') or 'não informado', 180),
        'Entrega prevista: ' + _texto(proposta.get('data_entrega') or 'a combinar', 80),
        'Tema: ' + _texto(projeto.get('tema') or 'não informado', 200),
        'Status da arte: ' + etiquetas[status],
    ]
    if status == 'aprovada' and arte:
        reg = projeto['aprovacao_arte_hf58']
        linhas.extend(['Arquivo aprovado: ' + _texto(arte.get('nome'), 200),
                       'Identificador: ' + _texto(arte.get('id'), 100),
                       'Conferência registrada por: ' + _texto(reg.get('responsavel'), 90),
                       'Data do registro: ' + _texto(reg.get('registrado_em'), 50)])
    else:
        linhas.append('ATENÇÃO: conferir aprovação da arte antes de produzir, quando necessária.')
    linhas.extend(['', 'ITENS E PERSONALIZAÇÕES'])
    itens = [i for i in proposta.get('itens', []) if isinstance(i, dict)]
    if not itens:
        linhas.append('Nenhum item informado na proposta.')
    for i, item in enumerate(itens, 1):
        linhas.append(f'{i}. {_texto(item.get("produto") or item.get("nome") or "Produto", 180)}')
        linhas.append('   Quantidade: ' + _texto(item.get('quantidade', item.get('qtd', 'a conferir')), 50))
        linhas.append('   Especificações: ' + _texto(item.get('especificacoes') or 'a conferir', 3000))
    linhas.extend(['', 'OBSERVAÇÕES INTERNAS',
                   _texto(projeto.get('observacoes') or 'Sem observações cadastradas.', 3000), '',
                   'Conferência física: [ ] itens  [ ] personalizações  [ ] arte  [ ] embalagem',
                   'A ficha não altera os registros oficiais nem libera produção.'])
    return ('\n'.join(linhas) + '\n').encode('utf-8-sig')
