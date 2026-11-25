# AlphaFest HF65.24.58 RC5 — demonstração isolada (Windows)

**Somente homologação. Não instalar sobre o Manager em uso e não publicar no Streamlit Cloud.**

## Abrir sem modificar produção

1. No GitHub, escolha a branch **homologacao-hf58** e utilize **Code → Download ZIP**.
2. Extraia o ZIP inteiro em uma **pasta nova**, fora da pasta atual de GitHub Desktop que publica o Manager.
3. Abra `.github → homologacao_hf58 → INICIAR_DEMO_WINDOWS.bat` com duplo clique.
4. O inicializador procura **Python 3.11** (aceita 3.12 ou 3.13), cria automaticamente a pasta **`.venv_hf58_demo`**, instala **Streamlit somente nela**, e inicia a demonstração local em **http://127.0.0.1:8502**.
5. Na primeira execução, o computador precisa de internet para instalar Streamlit. Nas seguintes, reutiliza o mesmo ambiente. Se Python não estiver instalado, o inicializador indicará a página oficial para instalação.

**Não é necessário executar comandos de pip manualmente.** O programa não instala pacotes no Python do Manager em produção.

Opcional, para verificar sem iniciar a interface:

```bat
.github\homologacao_hf58\INICIAR_DEMO_WINDOWS.bat --verificar
```

## Conferir os fluxos

- Selecione **Jorge**; envie um PNG fictício de arte v1 e confirme o nome do responsável.
- Baixe a ficha TXT e confira a arte v1, a personalização **Nome Ana** e a personalização **Nome Pedro**.
- Envie uma segunda arte v2; confirme que a situação passa para **revisão pendente** e que o aceite anterior não é reutilizado.
- Registre uma nova aprovação; confira a ficha TXT com a nova versão.
- Repita com **Anna**. Verifique que o pedido continua *Em andamento* e com aprovação comercial em *Não*.
- Clique em **Reiniciar simulação** para restaurar todos os dados fictícios.

## Limitações e segurança

- A Caixa do Projeto exibida é a função real extraída de `app.py`; contudo o salvamento de projeto e dos arquivos é **somente na memória da sessão**.
- O controle `file_uploader` é real, mas a função de armazenamento foi substituída por um endereço reservado `exemplo.invalid`. O link exibido **não aponta para o arquivo de verdade**. Não carregue arquivos reais ou confidenciais.
- A ficha TXT é gerada pela função oficial da HF58, mas contém **apenas dados fictícios**.
- O programa não importa `app.py`, não inicializa `cloud_db.py`, não utiliza credenciais e não conecta ao banco. O navegador roda no endereço local `127.0.0.1`.
- Esta demonstração **não substitui** a homologação manual com upload real em um ambiente de testes com banco próprio, nem autoriza o merge do PR #5.
