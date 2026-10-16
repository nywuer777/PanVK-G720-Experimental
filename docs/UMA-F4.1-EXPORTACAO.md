# PanVK G720 — Fase 4.1: diagnóstico exportável sem LADB

## Decisão de arquitetura
Base **F4-DIAG** (que, por sua vez, preserva E20 + UMA F1 + F2 + F3). A versão de melhor desempenho continua sendo **UMA F3**. F4.1 é **instrumentação de investigação**, não otimização de FPS.

## Evidência material do Bachata
ZIP analisado: `bachata-diagnostic-BS4-20261016-60C1C3EE.zip`.
Seu `shadps4.log` inclui a linha crua:
`WARNING: panvk is not a conformant Vulkan implementation, testing use only.`
O código Mesa de `src/vulkan/util/vk_util.c`, função `vk_warn_non_conformant_implementation`, emite essa mensagem usando `fprintf(stderr, ...)`.

Isso evidencia que o `stderr` do processo onde o driver é carregado chega ao `shadps4.log`. **Não há necessidade de escrever em diretórios privados ou acessar Logcat** para testar esse caminho. Contudo, a coleta F4.1 precisa ser confirmada em hardware, pois buffers e rotatividade dos logs podem alterar a exportação.

## Alteração única na F4.1
`tools/uma-f4-1-stderr-relay.py` transforma apenas a linha agregada `PANVK-F4` já emitida a cada 256 submissões por thread:
1. Importa `<stdio.h>` explicitamente no arquivo CSF.
2. Substitui `mesa_logi("PANVK-F4 ...")` por `fprintf(stderr, "PANVK-F4 ...\n")`.
3. Usa `fflush(stderr)` após uma janela.
4. Preserva todos os nomes e valores dos contadores; não altera emissão, espera, sincronização, renovação de heap, shaders, efeitos, resolução ou ring.

A execução tem guardas estritas para todos os quatro trechos. O workflow executa o teste do transformador e o analisador F4; exporta um diff para a auditoria antes de compilar.

## Teste no Android (sem PC)
1. Guarde o ZIP da UMA F3 como rollback. Importe **F4.1 DIAG** somente no Bachata.
2. Entre numa cena reproduzível por 2 a 3 minutos com as configurações usuais.
3. Use o botão já existente do Bachata para exportar seu diagnóstico ZIP (o mesmo procedimento anterior). Envie-o nesta conversa.
4. Procure em `shadps4.log` por `PANVK-F4 submits=`. O analisador em `tools/analyze-uma-f4.py` já reconhece a mesma linha em arquivos .log e em ZIPs de diagnóstico.

**Critério de sucesso:** existir ao menos uma janela válida `PANVK-F4` em `shadps4.log`. Se não existir, documentar a falha de coleta; nunca deduzir CPU/GPU limitantes a partir de ausência de linhas.

## Limitações e riscos
- `shadps4.log` pode ser truncado pela exportação. Jogar durante período curto para aumentar as chances de incluir os eventos recentes.
- `stderr` adiciona IO de texto na thread de submissão a cada 256 operações. A latência e o FPS da F4.1 **não** são diretamente comparáveis à F3.
- Campos medem a duração de CPU e esperas host-side, **não** utilização da GPU ou FPS.
- Medições são thread-local e podem estar divididas em várias janelas.
- Só a F3 está designada melhor versão; manter F4.1 exclusivamente para medição e restaurar F3 depois do teste.
