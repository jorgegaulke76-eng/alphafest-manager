"""HF65.24.58 - gate de homologacao. Nunca gera release nem publica.

Executa o gate de testes criticos com Streamlit real instalado e registra JSONs.
"""
import json
import os
import sys
from pathlib import Path
from build_update_package import run_critical_tests
from release_diagnostics import run_release_diagnostics

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "qa_logs"
OUT.mkdir(exist_ok=True)

# Nao prosseguir em outra branch se executado no GitHub Actions.
if os.environ.get('GITHUB_ACTIONS') == 'true' and os.environ.get('GITHUB_REF') != 'refs/heads/homologacao-hf58':
    sys.exit('BLOQUEADO: a homologacao so executa na branch homologacao-hf58.')

version = (ROOT / 'VERSAO.txt').read_text(encoding='utf-8').strip()
manifest = json.loads((ROOT / 'UPDATE_MANIFEST.json').read_text(encoding='utf-8'))
if not version.endswith('HF65.24.58') or manifest.get('version') != version or (manifest.get('validation', {}).get('status') != 'HOMOLOGACAO_PARCIAL' or manifest.get('release_candidate') != 'RC5'):
    sys.exit('BLOQUEADO: expected RC5 com status HOMOLOGACAO_PARCIAL.')

keys = ['SUPABASE_URL', 'SUPABASE_SERVICE_ROLE_KEY', 'SUPABASE_SERVICE_KEY', 'SUPABASE_ANON_KEY', 'SUPABASE_KEY']
if os.environ.get('GITHUB_ACTIONS') == 'true' and any(os.environ.get(k) for k in keys):
    sys.exit('BLOQUEADO: conexao com banco real nao permitida neste job.')

pre = run_release_diagnostics(ROOT)
(OUT / 'diagnostico_release.json').write_text(json.dumps(pre.to_dict(), ensure_ascii=False, indent=2), encoding='utf-8')
print('Diagnostico estatico:', 'APROVADO' if pre.ok else 'REPROVADO', flush=True)
if not pre.ok:
    for problem in pre.problems:
        print('BLOQUEIO:', problem, flush=True)
    sys.exit(2)

execution = run_critical_tests(ROOT, timeout=60)
(OUT / 'gate_critico.json').write_text(json.dumps(execution, ensure_ascii=False, indent=2), encoding='utf-8')
print('Gate:', execution['status'], flush=True)
print('Arquivos:', execution['approved_files'], '/', execution['executed_files'], flush=True)
print('Testes:', execution['tests_passed'], '/', execution['tests_run'], flush=True)
print('Falhas:', execution['failures'], 'erros:', execution['errors'], 'ignorados:', execution['skipped'], flush=True)
for item in execution['results']:
    if item['status'] != 'APROVADO':
        print('PENDENTE:', item['file'], (item.get('detail') or '')[:400], flush=True)
if execution['status'] != 'APROVADO':
    sys.exit(3)

post = run_release_diagnostics(ROOT, test_execution=execution)
(OUT / 'diagnostico_pos_gate.json').write_text(json.dumps(post.to_dict(), ensure_ascii=False, indent=2), encoding='utf-8')
print('Diagnostico pos-gate:', 'APROVADO' if post.ok else 'REPROVADO', flush=True)
if not post.ok:
    for problem in post.problems:
        print('BLOQUEIO:', problem, flush=True)
    sys.exit(4)
print('TESTES AUTOMATIZADOS APROVADOS. HOMOLOGACAO MANUAL AINDA OBRIGATORIA; NAO PROMOVER AUTOMATICAMENTE.', flush=True)
