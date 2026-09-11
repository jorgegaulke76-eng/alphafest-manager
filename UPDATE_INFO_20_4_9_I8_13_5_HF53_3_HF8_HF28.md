# AlphaFest Manager — HF53.3-HF8-HF28

## Organização interna IV — Alpha Connect Pro

Esta atualização continua a modularização conservadora do Manager, sem alterar regras de negócio ou fluxos operacionais.

### Alteração
- a tela `Configurações → Alpha Connect` foi movida do `app.py` para `alpha_connect_ui.py`;
- diagnósticos de OpenAI, Meta/Facebook, Instagram, WhatsApp Business, YouTube e TikTok mantêm o mesmo comportamento;
- histórico de testes continua usando o mesmo documento `integracoes_db`;
- bloqueio de testes durante operação protegida permanece igual;
- nenhum segredo é exibido ou incluído no pacote.

### Blindagem
- `alpha_connect_ui.py` passa a ser arquivo obrigatório do runtime;
- o módulo entra na compilação crítica do diagnóstico de release;
- HF7, Template Anna e Marketing Engine permanecem congelados.
