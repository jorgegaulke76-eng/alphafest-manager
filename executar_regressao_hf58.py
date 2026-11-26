#!/usr/bin/env python3
"""Reexecuta a descoberta completa, deixando evidencias JSON mesmo se falhar.

A descoberta unittest nao substitui a bateria critica de funcoes test_* legadas.
"""
from __future__ import annotations
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'qa_logs'
OUT.mkdir(parents=True, exist_ok=True)

suite = unittest.defaultTestLoader.discover(start_dir=str(ROOT), pattern='test_*.py', top_level_dir=str(ROOT))
result = unittest.TextTestRunner(verbosity=1).run(suite)
summary = {
    'status': 'APROVADO' if result.wasSuccessful() and result.testsRun > 0 and not result.skipped else 'REPROVADO',
    'tests_run': result.testsRun,
    'failures': len(result.failures),
    'errors': len(result.errors),
    'skipped': len(result.skipped),
    'expected_failures': len(result.expectedFailures),
    'unexpected_successes': len(result.unexpectedSuccesses),
    'note': 'unittest discover nao inclui automaticamente funcoes legadas; o gate critico as valida separadamente',
}
(OUT / 'regressao_unittest.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print('ALPHAFEST_REGRESSAO='+json.dumps(summary,ensure_ascii=False),flush=True)
if summary['status'] != 'APROVADO':
    sys.exit(3)
