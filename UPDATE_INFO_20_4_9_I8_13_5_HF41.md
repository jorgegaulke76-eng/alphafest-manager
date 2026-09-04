# AlphaFest Manager 20.4.9-I8.13.5-HF41

## Preparação segura da virada do domínio

A HF41 não altera o site público, DNS, nameservers ou domínio. Ela adiciona à Central do Site uma etapa explícita de pré-virada depois da homologação externa da HF40.

### Incluído
- indicador de staging externo homologado;
- DNS ainda não alterado;
- backup DNS marcado como pendente;
- plano de rollback preparado;
- kit ZIP para registrar o DNS atual antes da virada;
- checklist com atenção especial a NS, A/AAAA, CNAME, MX e TXT.

### Regra de segurança
Nenhuma conexão de `alphafest.com.br` deve ser feita antes de copiar e conferir os registros DNS atuais. A hospedagem antiga permanece ativa durante a virada e a estabilização.
