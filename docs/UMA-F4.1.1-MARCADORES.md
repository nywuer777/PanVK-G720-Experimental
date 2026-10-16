# PanVK G720 — F4.1.1: marcadores de instrumentação no Bachata

## Motivo do ciclo

O usuário confirmou que a sessão `BS4-20261016-8B4F1AA7` usou **F4.1**. O ZIP contém `shadps4.log`, mas `PANVK-F4` não aparece. `report.json` identifica o `shadps4.log` como **truncated=true**; a seção inicial e o final da sessão estão presentes. Por isso, ausência de linhas F4 não equivale a comprovação de que as submissões não foram medidas. O log registra `WARNING: panvk is not a conformant Vulkan implementation` na saída capturada.

## Base congelada

**UMA Fase 3 permanece a melhor versão experimental**, preservada integralmente. F4.1.1 deriva de F4.1 diagnóstica e continua **apenas para investigação**.

## Mudanças isoladas

Depois dos patches F2, F3, F4 e do transformador F4.1, `tools/uma-f4-1-1-markers.py` insere somente mensagens `stderr` com `fflush`:

- `PANVK-F4.1.1 READY queue_created kbase=<0|1>`: construção bem-sucedida de uma fila Vulkan, antes do primeiro quadro. Comprova entrada no módulo CSF instrumentado, não necessariamente o arquivo ZIP específico; os próprios metadados e a instalação são evidência adicional.
- `PANVK-F4.1.1 QUEUE_SUBMIT_ENTRY`: primeira entrada na função de submissão Vulkan por thread.
- `PANVK-F4.1.1 KBASE_SUBMIT_ENTER`: execução do ramo kbase por thread.
- `PANVK-F4.1.1 PROGRESS submits=N total_ns=N`: após a 1ª, 32ª e 128ª submissões concluídas em cada janela de 256 por thread.

O registro agregado da F4 `PANVK-F4 submits=...` continua inalterado e ocorrerá a cada 256 submissões bem-sucedidas por thread. Todas as mensagens F4.1.1 são diagnósticas e podem adicionar sobrecarga; nenhuma faz parte da versão F3.

**Nenhuma mudança:** código de sincronização, comandos firmware, ring CSF de 1 MiB, tiler heap, shaders, memória UMA, efeitos visuais e resolução.

## Teste móvel

1. Preservar ZIP da Fase 3 para rollback; instalar F4.1.1 via Bachata.
2. **Fazer teste curto (30–60 segundos)** para reduzir o risco de truncamento. Não é necessário aguardar falha ou jogar 9 minutos.
3. Exportar imediatamente o ZIP de diagnóstico existente no Bachata.
4. Enviar o ZIP na conversa. Verificar `shadps4.log` e procurar `PANVK-F4.1.1` e `PANVK-F4`. No `report.json`, verificar `truncated`.
5. Se `READY` aparecer sem `QUEUE_SUBMIT_ENTRY`, investigar a rota de dispatch. Se aparecer `KBASE_SUBMIT_ENTER`, mas não `PROGRESS`, investigar retornos antecipados/erros e ambiente de perfil. Se `PROGRESS` aparecer sem `PANVK-F4`, observar o limite de 256 e possível truncamento. Se nem `READY` aparecer em log não truncado, investigar captura `stderr`, cache/instalação do driver e geração de logs.

O relatório F4.1.1 continua não provando ganhos de FPS; apenas orienta o diagnóstico. A F3 é a referência de desempenho.
