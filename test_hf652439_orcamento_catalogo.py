from catalogo_orcamento_service import produto_existente_ou_alias, sugestoes_produtos_parecidos

def test_nome_existente():
    produtos=[{'Nome':'Caneca personalizada','Aliases':['canecas; mug personalizada']},{'Nome':'Chaveiro 3D','Aliases':['Impressão Chaveiro']}]
    assert produto_existente_ou_alias('  CANECA-PERSONALIZADA ',produtos)['nome']=='Caneca personalizada'
    assert produto_existente_ou_alias('MUG personalizada',produtos)['motivo']=='nome alternativo já cadastrado'
    assert produto_existente_ou_alias('Caneca personalizada',produtos,ignorar_indice=0) is None
    assert produto_existente_ou_alias('Outro produto',produtos) is None
    assert produto_existente_ou_alias('',produtos) is None
    assert sugestoes_produtos_parecidos('Caneca personalisada',produtos)[0][0]=='Caneca personalizada'
    assert sugestoes_produtos_parecidos('xyz',produtos)==[]

if __name__=='__main__':
    test_nome_existente();print('PASS HF65.24.39')
