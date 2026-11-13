# HF65.23 — YouTube OAuth conectado ao AlphaFest Manager

**Base:** HF65.22 (conteúdo multicanal) construída sobre a HF65.21 estável. Sem alterações nos módulos de estoque, pedidos, caixa ou integração AdSense.

## Recursos

- Botão **Conectar / renovar autorização Google** dentro de **Site AlphaFest → Atualizar o site → Dicas & Inspirações**.
- OAuth web com URI de retorno fixa `https://alphafest-manager-msbdyvs7cg2zxzqmxzbqu5.streamlit.app/`.
- Contas Google de teste permitidas: e-mails administrativos já configurados no Google Cloud.
- Confirma que a conta autenticada gerencia o canal com handle `@AlphafestItatiba2026`, antes de gravar autorização.
- Refresh token armazenado **cifrado com Fernet** no documento `site_youtube_oauth_db` do Manager (somente após autorização bem-sucedida).
- Upload privado em YouTube disponível **apenas após OAuth confirmado na sessão** e clique com confirmação explícita.
- Verifica novamente o ID do canal ao enviar vídeo; canal diferente impede upload.
- O artigo do site continua em rascunho até aprovação e publicação separada. Vídeos não são enviados automaticamente.

## Configuração necessária antes de conectar

**Google Cloud → Google Auth Platform → Clientes → FestManager Web**:
- Em *URIs de redirecionamento autorizados*, adicionar **exatamente**:
  `https://alphafest-manager-msbdyvs7cg2zxzqmxzbqu5.streamlit.app/`
- Não apagar as URIs já existentes. A origem JavaScript **não é necessária** para este fluxo OAuth do servidor Streamlit.
- A API YouTube Data API v3 precisa estar habilitada (já ativada pelo administrador).
- Manter os administradores como usuários de teste; não publicar o aplicativo sem avaliar requisitos do Google.

**Streamlit Cloud → app → Settings → Secrets**: adicionar ou completar a seção TOML abaixo, sem enviar os valores por e-mail, conversa ou GitHub:

```toml
[youtube]
client_id = "COPIAR_CLIENT_ID_DO_GOOGLE_CLOUD"
client_secret = "COPIAR_CLIENT_SECRET_DO_GOOGLE_CLOUD"
redirect_uri = "https://alphafest-manager-msbdyvs7cg2zxzqmxzbqu5.streamlit.app/"
fernet_key = "CHAVE_FERNET_GERADA_COM_SEGURANCA"
```

Gerar `fernet_key` localmente com Python que tenha a biblioteca `cryptography`:
`python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`

**Não** coloque chaves reais no código nem em arquivos versionados. Se configurar Secrets na aplicação errada, o OAuth não funcionará.

## Limitações e segurança

- O OAuth externo em **Testing** normalmente emite refresh tokens que expiram após **7 dias**; será necessário reconectar até resolver a publicação/verificação com o Google.
- O projeto atual não tem verificação/auditoria de upload público. Os uploads pela API serão privados, para inspeção no YouTube Studio.
- Conteúdo textual do site produz roteiro/Short, mas o sistema não converte todo artigo em um vídeo completo com narração automaticamente.
- Não há alteração automática de visibilidade de vídeo. Para tornar público, revisar no YouTube Studio.
- Não configure redirecionamento para um domínio diferente do usado no código, nem envie prints com `client_secret`/`fernet_key`.
- Este pacote foi testado localmente com APIs simuladas. A primeira autorização e o primeiro upload real ainda precisam de homologação na conta do canal.
