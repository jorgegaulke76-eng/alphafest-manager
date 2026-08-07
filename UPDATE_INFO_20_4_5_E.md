# 20.4.5-E — Correção do Motor de Fontes

Base oficial: ATUAL 20.4.5.D enviada pelo usuário.

## Causa corrigida
O renderizador de templates importáveis dependia de caminhos de fontes do Linux.
Quando essas fontes não estavam presentes no Streamlit Cloud, Pillow usava
ImageFont.load_default(), uma fonte bitmap de tamanho fixo. Por isso títulos e
benefícios continuavam minúsculos mesmo com 60, 80 ou 110 px configurados.

## Correção
- template_library_engine agora usa alphafest_font_manager.get_font().
- Fonte vetorial portátil respeita o tamanho solicitado no Streamlit Cloud.
- Mantidos auto-fit, clipping, Post Comercial e todas as zonas da 20.4.5-D.
- Fundo Anna Base Dinâmica, foto, miniaturas e WhatsApp verde preservados.
- Orçamentos 20.4.4-B preservados.
