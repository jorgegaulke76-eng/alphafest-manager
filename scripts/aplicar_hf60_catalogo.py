"""Aplicar somente o ajuste HF60 ao app.py da branch isolada.

Nao alterar o app.py de producao e nao executar rede / banco de dados.
"""
from pathlib import Path
import ast
import subprocess

ROOT = Path(__file__).resolve().parents[1]
p = ROOT / "app.py"
sha = subprocess.check_output(["git", "hash-object", str(p)], text=True).strip()
if sha != "a26438fab582b8713f0f849556691e3911f0099b":
    raise SystemExit(f"app.py diferente da base HF59; patch abortado: {sha}")

s = p.read_text(encoding="utf-8")

def trocar(antes, depois, etiqueta):
    global s
    n = s.count(antes)
    if n != 1:
        raise RuntimeError(f"{etiqueta}: esperava 1 ancora; achei {n}")
    s = s.replace(antes, depois)

trocar('import json\n',
       'import json\nfrom catalogo_modalidade_preco_service import MODALIDADES as PRECO_MODALIDADES_HF60, modalidade_atual as preco_modalidade_atual_hf60\n', 'importar modalidade')
trocar('''            exibir_preco_site = st.checkbox(
                "Exibir preço no site",
                value=bool(item_edicao.get("ExibirPrecoSite", False)),
                key=f"cat_exibir_preco_site_{sufixo}",
                help=(
                    "Desativado por padrão. Quando desligado, a vitrine mostra apenas o botão de orçamento. "
                    "Ative somente quando o valor cadastrado puder ser divulgado como preço público deste produto."
                ),
            )''',
'''            _preco_modos_hf60 = list(PRECO_MODALIDADES_HF60)
            modalidade_preco_site = st.selectbox(
                "Preço mostrado no site",
                options=_preco_modos_hf60,
                index=_preco_modos_hf60.index(preco_modalidade_atual_hf60(item_edicao)),
                format_func=lambda codigo: PRECO_MODALIDADES_HF60[codigo],
                key=f"cat_modalidade_preco_site_{sufixo}",
                help="A partir de: anuncie somente um valor inicial realmente disponível. Sem preço numérico válido, o site exibirá Consultar valores.",
            )
            exibir_preco_site = modalidade_preco_site != "sob_orcamento"''', 'seletor cadastro')
trocar('"PublicarSite": publicar_site, "ExibirPrecoSite": bool(exibir_preco_site), "Destaque": destaque_cat,',
       '"PublicarSite": publicar_site, "ExibirPrecoSite": bool(exibir_preco_site), "ModalidadePrecoSite": modalidade_preco_site, "Destaque": destaque_cat,', 'gravar modalidade')
trocar('"💰 Mostrar preço": bool(_prod_hf492.get("ExibirPrecoSite", False)),',
       '"💰 Preço no site": PRECO_MODALIDADES_HF60[preco_modalidade_atual_hf60(_prod_hf492)],', 'linha edicao rapida')
trocar('''                        "💰 Mostrar preço": st.column_config.CheckboxColumn(
                            "💰 Mostrar preço",
                            help="Quando marcado, o preço é exibido no site. Desmarcado = orçamento pelo WhatsApp.",
                            width="small",
                        ),''',
'''                        "💰 Preço no site": st.column_config.SelectboxColumn(
                            "💰 Preço no site",
                            options=list(PRECO_MODALIDADES_HF60.values()),
                            help="Sob orçamento, Preço fixo ou A partir de. O site só publica valores numéricos válidos.",
                            width="medium",
                        ),''', 'coluna edicao rapida')
trocar('''                _hf492_mudancas = []
                if isinstance(_hf492_editado, pd.DataFrame):''',
'''                _hf492_mudancas = []
                _hf60_preco_codigos = {rotulo: codigo for codigo, rotulo in PRECO_MODALIDADES_HF60.items()}
                if isinstance(_hf492_editado, pd.DataFrame):''', 'mapear modos')
trocar('                        _novo_preco_hf492 = bool(_linha_hf492.get("💰 Mostrar preço", False))',
'''                        _novo_preco_hf492 = _hf60_preco_codigos.get(
                            str(_linha_hf492.get("💰 Preço no site", "")).strip(),
                            preco_modalidade_atual_hf60(_produto_hf492),
                        )''', 'ler escolha')
trocar('                            or _novo_preco_hf492 != bool(_produto_hf492.get("ExibirPrecoSite", False))',
       '                            or _novo_preco_hf492 != preco_modalidade_atual_hf60(_produto_hf492)', 'comparar modos')
trocar('                        _registro_hf492["ExibirPrecoSite"] = bool(_preco_hf492)',
'''                        _registro_hf492["ModalidadePrecoSite"] = _preco_hf492
                        _registro_hf492["ExibirPrecoSite"] = _preco_hf492 != "sob_orcamento"''', 'autosave modos')
trocar('''            # Evita abrir o formulário completo produto por produto apenas para
            # PublicarSite / ExibirPrecoSite / Destaque.''',
'''            # Evita abrir o formulário completo produto por produto apenas para
            # PublicarSite / ModalidadePrecoSite / Destaque.''', 'comentario')
trocar('                "Marque diretamente na tabela quais produtos entram no site, se o preço aparece, quais ficam em destaque e quais entram no carrossel comercial. "',
       '                "Escolha na tabela os produtos do site, o tipo de preço (sob orçamento, fixo ou a partir de), os destaques e o carrossel comercial. "', 'texto rapido')

ast.parse(s, filename=str(p))
assert s.count('modalidade_preco_site = st.selectbox(') == 1
assert '"ModalidadePrecoSite": modalidade_preco_site' in s
p.write_text(s, encoding="utf-8")
print("App HF60 integrado; sintaxe verificada; sem rede nem dados reais.")
