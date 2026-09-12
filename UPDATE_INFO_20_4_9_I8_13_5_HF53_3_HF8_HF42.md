# AlphaFest Manager — HF53.3-HF8-HF42

## Documentos / PDFs — runtime otimizado

- PDFs da Agenda da Anna passam a usar cache por assinatura do conteúdo.
- Agenda atual invalida imediatamente quando os dados mudam e renova por minuto.
- Roteiro registrado da manhã é reaproveitado enquanto o snapshot não mudar.
- Fechamento comparativo é reaproveitado enquanto o comparativo permanecer igual, com renovação por minuto.
- Cache limitado por quantidade e TTL para não acumular PDFs em memória.
- Nenhuma regra de agenda, fechamento, status, documento ou layout foi alterada.
- Template Mestre HF7, Template Anna e Marketing Engine permanecem preservados.
