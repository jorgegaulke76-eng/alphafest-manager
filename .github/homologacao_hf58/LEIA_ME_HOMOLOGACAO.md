# AlphaFest HF65.24.58 RC5 — demonstração isolada (Windows)

**Somente homologação. Não instalar sobre o Manager em uso e não publicar no Streamlit Cloud.**

## Abrir sem modificar produção

1. No GitHub, escolha a branch **homologacao-hf58** e utilize **Code → Download ZIP**.
2. Extraia o ZIP em uma **pasta nova**, fora da pasta atual de GitHub Desktop que publica o Manager.
3. Tenha Python 3.11 e Streamlit instalados nessa pasta/ambiente separado. Para preparar:
   ```bat
   py -3.11 -m venv .venv_hf58_demo
   .venv_hf58_demo\Scripts\python.exe -m pip install -r requirements.txt
   .venv_hf58_demo\Scripts\python.exe -m streamlit run .github\homologacao_hf58\demo.py --server.address 127.0.0.1 --server.port 8502
   ```
   Alternativamente, com o Streamlit instalado no Python 3.11, execute `INICIAR_DEMO_WINDOWS.bat`.
4. Acesse **http://127.0.0.1:8502** no navegador do próprio computador.

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
