# Atualização HF65.20 — Verificação Google AdSense no site AlphaFest

Partindo da versão **HF65.19**, esta atualização prepara a verificação do site no
Google AdSense SEM ativar anúncios ou alterar o visual aprovado.

- Nova seção **Central do Site > Publicar site > Google AdSense · Verificação do site**.
- Aceita o ID do editor (`ca-pub-` + 16 dígitos) ou a metatag oficial colada.
- Salva a configuração no documento `site_adsense_db` da Fonte Única do Manager.
- Gera a metatag `google-adsense-account` dentro do `<head>` de produção.
- Gera `ads.txt` com a linha do Google e permite seu envio pelo pipeline Cloudflare existente.
- Mantém o valor salvo nas republicações subsequentes.
- A ausência de ID conserva o comportamento anterior.
- Não injeta scripts de anúncios, não ativa blocos e não altera DNS, produtos,
  galeria, carrossel, WhatsApp nem a lógica de publicação.

## Instalação

1. Preserve um backup integral da versão HF65.19 e da base de dados.
2. Use Configurações > Atualização segura no Manager; verifique a integridade antes de atualizar.
3. Instale o ZIP desta atualização, preservando os dados existentes.
4. Abra Central do Site, prepare a prévia, expanda Publicar site > Google AdSense.
5. Cole o identificador real fornecido pela sua conta AdSense e clique em Salvar.
6. Confira a prévia e, somente quando decidir, publique no `alphafest-novo`.
7. Confirme a presença da metatag no código-fonte e de `https://alphafest.com.br/ads.txt`.
8. Só então solicite a verificação no painel do Google AdSense.

**Atenção:** não copie o ID ilustrativo deste texto. O site NÃO foi publicado por esta atualização.
A aprovação do AdSense e a exibição efetiva dos anúncios dependem do Google e de passos posteriores.
