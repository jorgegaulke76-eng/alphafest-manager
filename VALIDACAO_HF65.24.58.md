# Validação HF65.24.58 (ambiente local)

- `python -m unittest -q test_ficha_producao_hf58.py`: 6 testes aprovados.
- Gate parcial com `test_ficha_producao_hf58.py`, `test_proposal_draft_hf57.py`, `test_roteiro_producao_hf51.py`: 59 testes aprovados, zero ignorados.
- `python -m py_compile app.py ficha_producao_hf58.py`: aprovado.
- Gate completo não aprovado neste ambiente: dependência `streamlit` ausente; tentativas de instalá-la falharam por indisponibilidade de acesso ao repositório de pacotes. Outros testes de interface foram ignorados sem Streamlit.
- O ZIP é uma **prévia de atualização para homologação**, não uma release certificada pelo gate completo. Instale primeiro em ambiente de teste, realize backup, valide com Jorge e Anna e confira operações no banco antes de aplicar em produção.

As ações de aprovação de arte exigem conferência manual do operador. Não correspondem à aprovação comercial do pedido nem a uma confirmação automática do cliente. Uma nova arte ou um arquivamento torna o estado pendente de conferência.
