# HF65.24.58 RC4 - Homologacao pendente

**Nao instalar em producao.** Incremento sobre RC3 para aumentar a seguranca da aprovacao de arte e evitar mensagens de sucesso sem persistencia.

## Mudancas RC4
- Novo marcador de mutacao de arte persistido no projeto ao enviar/arquivar arte. O aceite anterior nao reaparece ao restaurar uma arte, mesmo com o mesmo ID/nome/URL.
- Aprovacao ligada a arte ativa mais recente, inclusive na presenca de IDs repetidos.
- A Caixa do Projeto somente confirma atualizacoes de observacoes, arquivamento e vinculo de arquivo quando a gravacao retorna sucesso.
- Caso o upload externo tenha ocorrido e o vinculo ao projeto falhe, o Manager orienta a conferir antes de reenviar.
- Edicoes locais de arquivo sao feitas numa copia profunda da estrutura do projeto, reduzindo risco de refletir mudancas que nao foram salvas.

## O que permanece
- Ficha interna de producao TXT, completa e sem alterar situacao do pedido.
- Aprovacao comercial, estoque e Fluxo independentes; sem SQL ou dependencias novas.
- HF65.24.57 e melhorias anteriores preservadas pela base cumulativa.

## Validacao
Leia VALIDACAO_HF65.24.58.md e VALIDAR_HF58_WINDOWS.bat. A regressao integral e a interface Streamlit real ainda precisam passar antes de uma versao FINAL.

## RC5 - correções após execução real do GitHub Actions
- Em 25/11/2026, o primeiro job remoto instalou Streamlit 1.67.0 e executou 509 testes; identificou quatro erros.
- Compatibilidade Python 3.11: JSON-LD das páginas Dicas usa a variável `json_ld` fora da expressão de f-string.
- Importador do site: botão **Fechar revisão** é habilitado no mesmo rerun da análise, sem exigir interação adicional.
- Diagnóstico oficial passa a compilar também `site_dicas_multicanal_service.py`, impedindo regressão desse tipo.
- RC5 permanece **HOMOLOGACAO_PARCIAL** até regressão remota sem erros e conferência manual dos perfis. Não instalar em produção.
