"""Preparação segura da virada do domínio AlphaFest (HF41).

Somente planejamento e arquivos de conferência. Este módulo não executa DNS,
não conecta domínio e não desativa a hospedagem atual.
"""
from __future__ import annotations

import io
import json
import zipfile
from datetime import datetime, timezone
from typing import Any, Dict

DOMINIO_FINAL = "alphafest.com.br"
STAGING_PROJETO = "alphafest-novo"
HOSPEDAGEM_NOVA = "Cloudflare Workers · Static Assets"


def resumo_pre_virada() -> Dict[str, Any]:
    """Estado conservador da preparação depois da homologação externa HF40."""
    return {
        "dominio_final": DOMINIO_FINAL,
        "staging_externo": "Homologado",
        "staging_projeto": STAGING_PROJETO,
        "hospedagem_nova": HOSPEDAGEM_NOVA,
        "dns_alterado": False,
        "backup_dns": "Pendente",
        "rollback": "Preparado",
        "pronto_para_mudar_dns": False,
    }


def gerar_ficha_backup_dns() -> str:
    """Ficha manual para copiar o estado DNS antes de qualquer mudança."""
    return f"""ALPHAFEST — BACKUP DO DNS ATUAL — PREENCHER ANTES DA VIRADA

Domínio: {DOMINIO_FINAL}
Data/hora da captura: ______________________________
Onde o DNS é administrado hoje: ___________________
Registrador do domínio: ____________________________
Nameservers atuais (NS):
1. _________________________________________________
2. _________________________________________________
3. _________________________________________________
4. _________________________________________________

REGISTROS ATUAIS — COPIAR TODOS OS QUE EXISTIREM
Tipo | Nome/Host | Conteúdo/Destino | TTL | Proxy/Observação
____ | _________ | ________________ | ___ | _________________
____ | _________ | ________________ | ___ | _________________
____ | _________ | ________________ | ___ | _________________
____ | _________ | ________________ | ___ | _________________
____ | _________ | ________________ | ___ | _________________
____ | _________ | ________________ | ___ | _________________
____ | _________ | ________________ | ___ | _________________
____ | _________ | ________________ | ___ | _________________

ATENÇÃO ESPECIAL
[ ] Registros A/AAAA do site copiados.
[ ] CNAME de www copiado.
[ ] MX de e-mail copiados.
[ ] TXT (SPF/DKIM/DMARC/verificações) copiados.
[ ] Outros subdomínios copiados.
[ ] Print/screenshot do painel DNS salvo.

NÃO ALTERAR NADA antes de esta ficha estar completa.
"""


def gerar_plano_rollback() -> str:
    return f"""ALPHAFEST — PLANO DE ROLLBACK DO DOMÍNIO

Objetivo: permitir voltar o site para a configuração anterior caso a virada de {DOMINIO_FINAL} apresente qualquer problema.

ANTES DA VIRADA
1. Salvar screenshot do DNS atual.
2. Preencher BACKUP-DNS-ATUAL.txt com todos os registros.
3. Confirmar que e-mail/MX/TXT estão documentados.
4. Confirmar que o staging {STAGING_PROJETO} continua funcionando.
5. Não cancelar Wix/hospedagem antiga.

SE HOUVER PROBLEMA APÓS A VIRADA
1. Restaurar os registros/NS exatamente como estavam no backup.
2. Aguardar a propagação e testar {DOMINIO_FINAL} e www.{DOMINIO_FINAL}.
3. Testar e-mail e WhatsApp do site.
4. Manter a hospedagem antiga ativa até estabilizar.

REGRA
A HF41 não executa nenhuma alteração de DNS. A mudança será manual e somente depois do backup conferido.
"""


def gerar_checklist_pre_virada() -> str:
    return f"""ALPHAFEST — CHECKLIST PRÉ-VIRADA HF41

CONCLUÍDO
[x] Novo site completo homologado no Manager — Desktop.
[x] Novo site completo homologado no Manager — Celular.
[x] Staging externo homologado em Cloudflare Workers.
[x] Navegação e WhatsApp testados.
[x] Domínio {DOMINIO_FINAL} ainda não alterado.

PENDENTE ANTES DE QUALQUER DNS
[ ] Identificar onde o DNS do domínio é administrado hoje.
[ ] Salvar screenshot/backup de todos os registros DNS atuais.
[ ] Conferir NS, A/AAAA, CNAME, MX e TXT.
[ ] Confirmar que e-mail não será afetado.
[ ] Só então adicionar o domínio à zona Cloudflare e preparar Custom Domain.
[ ] Fazer a troca em janela controlada e testar HTTPS/www/apex.
[ ] Manter rollback disponível e hospedagem antiga ativa durante estabilização.

NÃO cancelar hospedagem antiga nesta fase.
"""


def gerar_kit_pre_virada(*, versao_manager: str = "20.4.9-I8.13.5-HF41") -> bytes:
    status = resumo_pre_virada()
    status.update({
        "versao_manager": versao_manager,
        "gerado_em_utc": datetime.now(timezone.utc).isoformat(),
    })
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("BACKUP-DNS-ATUAL.txt", gerar_ficha_backup_dns())
        zf.writestr("CHECKLIST-PRE-VIRADA-HF41.txt", gerar_checklist_pre_virada())
        zf.writestr("ROLLBACK-DNS.txt", gerar_plano_rollback())
        zf.writestr("STATUS-PRE-VIRADA.json", json.dumps(status, ensure_ascii=False, indent=2))
    return buf.getvalue()
