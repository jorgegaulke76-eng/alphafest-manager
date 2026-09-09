# 20.4.9-I8.13.5-HF22 — Biblioteca 3D privada do Jorge

Base funcional: **HF21 homologada**.

## Objetivo
Criar um acervo interno para preservar arquivos de impressão 3D antes que a origem externa deixe de disponibilizá-los.

## Novo módulo — somente Jorge
- Adiciona **🧊 Biblioteca 3D** na área Operação.
- Não é liberado para o perfil Anna.
- Cadastro enxuto com apenas:
  - Nome;
  - Descrição;
  - Tempo de impressão;
  - 1 imagem;
  - 1 arquivo 3D/projeto de impressão.
- Não existe campo de link externo.
- Formatos comuns aceitos: 3MF, STL, OBJ, STEP/STP, AMF, ZIP/RAR/7Z e GCODE/BGCODE.
- Pesquisa por nome, descrição ou nome do arquivo.
- O Jorge pode preparar e baixar novamente a cópia preservada diretamente no Manager.

## Preservação do arquivo
- Arquivos e imagens são gravados em bucket privado do Supabase (`biblioteca3d`).
- O bucket é criado sob demanda usando a credencial de servidor já configurada no Manager.
- Não há fallback para disco local/efêmero nesta biblioteca.
- O cadastro só é confirmado quando imagem, arquivo e metadados são persistidos.
- Se uma etapa falhar, uploads parciais são removidos para evitar falsa sensação de backup.

## Compatibilidade
- Nenhum status de pedido é alterado.
- Nenhum fluxo da Anna, THU, Agenda, Catálogo ou Orçamento é modificado.
- Metadados usam o documento `biblioteca_3d_db`; o conteúdo pesado fica no Storage privado.
