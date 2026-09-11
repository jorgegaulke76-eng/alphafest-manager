# AlphaFest Manager — HF53.3-HF8-HF23

## Diagnóstico automático de release

- separa testes portáveis/atuais de testes históricos presos a versões antigas;
- compila automaticamente os módulos Python críticos antes de liberar uma atualização;
- mantém runtime, versão e hash congelado do Template Mestre HF7 como bloqueios reais;
- integra o diagnóstico ao painel **Configurações → Atualização segura**;
- integra o diagnóstico ao gerador oficial do ZIP e ao `UPDATE_MANIFEST.json`;
- testes históricos podem continuar arquivados sem gerar falso alarme só por esperar HF antigo;
- nenhuma regra operacional, Template Anna, Template Mestre HF7, site ou dados foi alterada.
