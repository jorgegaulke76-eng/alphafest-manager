import unittest
from datetime import date
from pathlib import Path
from resumo_operacional_hf61_service import montar_resumo_anna

class ResumoHF61(unittest.TestCase):
    def test_gera_totais_e_prioridades(self):
        t=montar_resumo_anna(date(2026,11,26), novos=2, aguardando=3, ativos=10, entregas=4)
        for word in ["26/11/2026","Novos atendimentos: 2","Aguardando cliente: 3","Pedidos ativos: 10","Entregas previstas hoje: 4","Conferir entregas"]:
            self.assertIn(word,t)
        self.assertNotIn("WhatsApp:",t)
    def test_sem_pendencia(self):
        t=montar_resumo_anna(date(2026,11,26),novos=0,aguardando=0,ativos=0,entregas=0)
        self.assertIn("Conferir agenda",t)
    def test_validacao(self):
        with self.assertRaises(ValueError):
            montar_resumo_anna(date(2026,11,26),novos=-1,aguardando=0,ativos=0,entregas=0)
    def test_app_integrou(self):
        s=(Path(__file__).parent/"app.py").read_text(encoding="utf-8")
        self.assertIn('with st.expander("📋 Resumo do dia · copiar ou baixar"',s)
        self.assertIn('ativos=len(ativos)',s)
