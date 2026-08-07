# AlphaFest Manager 20.3.2

## Hotfix — fotos locais do catálogo

Corrige a persistência das fotos adicionadas pelo computador. O Streamlit Cloud possui filesystem efêmero; por isso caminhos locais em `uploads/` podiam desaparecer após reinícios ou deploys.

### Novo comportamento

1. O sistema tenta primeiro enviar a foto ao Storage público do Supabase.
2. Se o Storage não aceitar o arquivo ou estiver indisponível, a imagem é otimizada e gravada como data URL no próprio documento persistente do catálogo.
3. A renderização já suporta URLs públicas e data URLs, então nenhuma alteração de uso é necessária.

### Observação

Fotos antigas que já desapareceram do filesystem precisam ser enviadas novamente uma única vez, pois o arquivo original não existe mais no servidor.
