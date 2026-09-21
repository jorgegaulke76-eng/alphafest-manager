# HF65.18 — Importação em lote do Google Fotos para a Galeria

- Novo bloco `☁️ Importar fotos do Google Fotos` dentro da Galeria de Trabalhos.
- Importa um ou vários ZIPs baixados do Google Fotos e ignora automaticamente os JSONs de metadados.
- Deduplicação por SHA-256: fotos já importadas não entram novamente.
- Classificação do lote por produto, categoria, subcategoria e Datas & Ocasiões antes da gravação.
- Opção de criar um registro por foto (melhor para lotes mistos) ou agrupar todo o lote em um único trabalho.
- Fotos entram no armazenamento privado da Galeria e não são publicadas automaticamente.
- Limite operacional de 200 novas fotos por execução; o mesmo ZIP pode ser reenviado para continuar apenas com as restantes.
- Observação técnica: desde 31/03/2025 o Google Photos Library API não permite a aplicativos de terceiros varrer automaticamente álbuns/bibliotecas antigos; o fluxo oficial de acesso direto passou a ser o Google Photos Picker com seleção explícita do usuário. Esta versão usa o caminho zero-custo e estável por lote/ZIP, sem credenciais Google.
