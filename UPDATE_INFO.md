# AlphaFest Manager — HF53.3-HF8-HF37

## HF37 — Motor de materiais indexado

O HF37 otimiza consumo, reserva, falta de material, necessidades de compra e risco de produção sem alterar nenhuma regra operacional.

### Alterações
- movimentos de estoque são indexados uma única vez por cálculo em lote;
- resumos de vários pedidos compartilham o mesmo índice;
- Central reaproveita os resumos de consumo no mesmo ciclo;
- tela de Compras/Estoque calcula reserva e pendência de todos os materiais em uma única passagem;
- Necessidades de Compra usa resumos em lote;
- Previsão/Risco de Produção usa os mesmos resumos indexados;
- reserva, baixa, estorno, FIFO e status permanecem inalterados.

### Proteções
- Template Mestre HF7 preservado;
- Template Anna preservado;
- Marketing Engine preservado;
- nenhuma migração de dados.
