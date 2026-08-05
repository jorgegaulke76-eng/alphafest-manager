# AlphaFest Manager 14.2.5 — Health Monitor

## Central do Jorge

- Corrigido o falso alerta de integridade de `componentes_db`.
- `componentes_db` agora é validado corretamente como objeto categorizado.
- Adicionado Health Monitor compacto na barra lateral, exclusivo para Jorge.
- O monitor reutiliza os dados já carregados, sem criar consultas adicionais pesadas.
- Exibe estado geral, banco, etapas do boot, contingências e tempo acumulado.
- Central da Anna e fluxos operacionais permanecem preservados.
