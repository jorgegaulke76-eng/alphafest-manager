"""HF65.24.58: controle explícito de aprovação por arquivo e ficha interna TXT.

Não substitui aprovação comercial nem modifica status do Fluxo/Histórico.
"""
from __future__ import annotations
from datetime import datetime
from hashlib import sha256
import json


def _texto(value, max_len=500):
    texto = ' '.join(str(value or '').replace('\x00', '').split())
    return texto if max_len is None else texto[:max_len]


def artes(projeto):
    return [a for a in (projeto.get('arquivos') or []) if isinstance(a, dict)
            and not a.get('arquivado') and a.get('categoria') == 'Arte' and a.get('id')]


def assinatura_arquivo(arquivo):
    """Detecta alterações na referência aprovada, sem depender do nome isolado."""
    campos = {k: str(arquivo.get(k) or '') for k in ('id', 'nome', 'url', 'criado_em', 'categoria')}
    return sha256(json.dumps(campos, sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()



def identidade_conferencia_arte(projeto):
    """Versão imutável da arte exibida na tela; troca a chave do aceite quando ela muda.

    Inclui arte ativa mais recente, arquivos arquivados e ordem das artes, pois
    apenas verificar o ID permite reaproveitar um checkbox de um arquivo trocado.
    """
    lista = artes(projeto)
    if not lista:
        return ''
    todas = [a for a in (projeto.get('arquivos') or [])
             if isinstance(a, dict) and a.get('categoria') == 'Arte' and a.get('id')]
    estado = {
        'projeto': str(projeto.get('id') or ''),
        'recente': assinatura_arquivo(lista[-1]),
        'artes': [{'assinatura': assinatura_arquivo(a),
                   'arquivado': bool(a.get('arquivado'))} for a in todas],
    }
    return sha256(json.dumps(estado, sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()[:24]


def registrar_aprovacao_conferida(projeto_exibido, projeto_mais_recente, arquivo_id, responsavel, instante):
    """Revalida o alvo da confirmação antes de gerar o registro a ser salvo.

    Não substitui controle transacional entre usuários no banco: a aplicação
    também precisa usar dados atualizados e confirmar que o save foi aceito.
    """
    if (not isinstance(projeto_mais_recente, dict)
            or str(projeto_exibido.get('id') or '') != str(projeto_mais_recente.get('id') or '')
            or identidade_conferencia_arte(projeto_exibido) != identidade_conferencia_arte(projeto_mais_recente)):
        raise ValueError('A arte mudou desde a conferência. Atualize a Caixa do Projeto e confirme novamente.')
    return registrar_aprovacao(projeto_mais_recente, arquivo_id, responsavel, instante)


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
    if (ultima.get('id') != selecionada.get('id')
            or registro.get('total_artes_no_registro') != len(todas_artes)
            or registro.get('assinatura_arquivo') != assinatura_arquivo(selecionada)):
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
              'total_artes_no_registro': len(todas_artes),
              'assinatura_arquivo': assinatura_arquivo(lista[-1])}
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
        linhas.append('   Especificações: ' + _texto(item.get('especificacoes') or 'a conferir', None))
    linhas.extend(['', 'OBSERVAÇÕES INTERNAS',
                   _texto(projeto.get('observacoes') or 'Sem observações cadastradas.', None), '',
                   'Conferência física: [ ] itens  [ ] personalizações  [ ] arte  [ ] embalagem',
                   'A ficha não altera os registros oficiais nem libera produção.'])
    return ('\n'.join(linhas) + '\n').encode('utf-8-sig')
