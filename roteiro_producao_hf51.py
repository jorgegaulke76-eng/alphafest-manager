"""HF65.24.51 — exportação local de planos de ação já calculados na Central.

Sem consultas, alteração de status, envio de mensagens ou dados financeiros.
Separação por permissão: retornos comerciais só quando a tela Jorge os fornece.
"""
from __future__ import annotations

import csv
from datetime import date, datetime
from io import StringIO

_GRUPOS = ('Atrasados', 'Hoje', 'Amanhã', 'Sem prazo')


def _limpar(valor, limite=160) -> str:
    texto = ' '.join(str(valor or '').split())
    return texto[:limite]


def _csv_celula(valor) -> str:
    """Impede que nomes/produtos virem fórmulas em planilhas."""
    texto = _limpar(valor, 180)
    if texto.lstrip().startswith(('=', '+', '-', '@')):
        texto = "'" + texto
    return texto


def _data_txt(valor) -> str:
    if isinstance(valor, datetime):
        valor = valor.date()
    return valor.strftime('%d/%m/%Y') if isinstance(valor, date) else 'Sem data'


def roteiro_diario(diario: dict, *, retornos=None, incluir_retornos=False, limite_por_grupo=40) -> str:
    """Roteiro TXT para uso interno: uma linha por pedido dentro de cada situação."""
    if not 1 <= limite_por_grupo <= 200:
        raise ValueError('Limite de itens fora da faixa')
    diario = diario or {}
    grupos = diario.get('grupos') or {}
    hoje = diario.get('hoje')
    linhas = [f"ALPHAFEST | ROTEIRO DE PRODUÇÃO | {_data_txt(hoje)}",
              'Consulta interna · dados do Manager no momento de gerar o arquivo',
              'NÃO muda status, NÃO avisa clientes e NÃO confirma entregas.', '']
    for grupo in _GRUPOS:
        itens = [i for i in (grupos.get(grupo) or []) if isinstance(i, dict)]
        linhas.append(f"{grupo.upper()} — {len(itens)} pedido(s)")
        if not itens:
            linhas.append('  Nenhuma pendência nesta situação.')
        vistos = set()
        exibidos = 0
        for item in itens:
            numero = _limpar(item.get('numero_proposta'), 45)
            chave = numero or id(item)
            if chave in vistos:
                continue
            vistos.add(chave)
            if exibidos >= limite_por_grupo:
                continue
            exibidos += 1
            cliente = _limpar(item.get('cliente_nome') or 'Cliente', 85)
            data = _limpar(item.get('data_texto_hf41') or 'Sem data', 30)
            fase = _limpar(item.get('fase_nome_hf41') or 'Etapa a conferir', 70)
            acao = _limpar(item.get('acao_hf49') or 'Conferir pedido', 100)
            produto = _limpar(item.get('resumo_produtos') or 'Itens não informados', 160)
            linhas.extend([f"  • Pedido {numero or 'sem número'} | {cliente} | {data}",
                            f"    {fase} | Próxima ação: {acao}",
                            f"    Itens: {produto}"])
        if len(vistos) < len(itens):
            linhas.append('  Observação: registros repetidos foram consolidados.')
        if len(vistos) > limite_por_grupo:
            linhas.append(f"  (+{len(vistos) - limite_por_grupo} outro(s) pedido(s): consultar o Manager)")
        linhas.append('')
    if incluir_retornos:
        retornos_validos = [x for x in (retornos or [])
                            if isinstance(x, dict) and str(x.get('nivel') or '').lower() not in ('aguardar', '')]
        linhas.append(f"RETORNOS COMERCIAIS A VERIFICAR — {len(retornos_validos)}")
        # Somente retornos com contato previamente registrado; sem valores ou telefones.
        for item in retornos_validos[:limite_por_grupo]:
            numero = _limpar(item.get('numero_proposta'), 45)
            cliente = _limpar(item.get('cliente_nome') or 'Cliente', 85)
            acao = _limpar(item.get('acao') or 'Conferir retorno', 120)
            linhas.append(f"  • {numero or 'Sem número'} | {cliente} | {acao}")
        if len(retornos_validos) > limite_por_grupo:
            linhas.append(f"  (+{len(retornos_validos) - limite_por_grupo} outro(s) na Central)")
        linhas.append('')
    linhas.extend(['ATENÇÃO: a agenda oficial e os status devem ser conferidos no Manager.',
                   'Nenhum cliente recebeu mensagem por meio deste roteiro.'])
    return '\n'.join(linhas) + '\n'


def agenda_semanal_csv(semanal: dict) -> bytes:
    """CSV UTF-8 BOM com entrega prevista e etapa, uma linha por pedido.

    Inclui vencidos e sem prazo para não ocultar pendências relevantes.
    """
    semanal = semanal or {}
    saida = StringIO(newline='')
    wr = csv.writer(saida, delimiter=';', quoting=csv.QUOTE_MINIMAL, lineterminator='\r\n')
    wr.writerow(['Situação', 'Data prevista', 'Pedido', 'Cliente', 'Produtos', 'Etapa'])
    vistos = set()

    def escrever(tipo, item, data=None):
        if not isinstance(item, dict):
            return
        numero = _limpar(item.get('numero_proposta'), 45)
        chave = numero or ('sem-numero', id(item))
        if chave in vistos:
            return
        vistos.add(chave)
        entrega = data or item.get('entrega_hf41')
        wr.writerow([_csv_celula(tipo), _csv_celula(_data_txt(entrega)),
                     _csv_celula(numero), _csv_celula(item.get('cliente_nome')),
                     _csv_celula(item.get('resumo_produtos')),
                     _csv_celula(item.get('fase_nome_hf41'))])

    for item in semanal.get('vencidos') or []:
        escrever('Prazo vencido', item)
    for dia in semanal.get('dias') or []:
        for item in dia.get('pedidos') or []:
            escrever('Entrega prevista', item, dia.get('data'))
    for item in semanal.get('sem_data') or []:
        escrever('Sem prazo', item)
    return ('\ufeff' + saida.getvalue()).encode('utf-8')
