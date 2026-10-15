# PanVK G720 — UMA Inteligente Fase 2

## Objetivo
Diminuir o volume de bytes submetidos à manutenção de cache CPU→GPU em buffers **internos** dos command buffers, sem mudar resolução, texturas, SSAO, shaders ou opções do Bachata.

## Alteração isolada
- Adicionado `pool_used_size` a `struct panvk_priv_bo`.
- Quando um BO interno é alocado (novo ou reutilizado da lista de buffers ociosos), seu limite utilizado é reiniciado.
- A cada subalocação o limite é aumentado para `max(valor_anterior, offset + tamanho)`, incluindo padding por alinhamento.
- Ao concluir um command buffer, `panvk_pool_flush_maps` sincroniza somente `[0, pool_used_size)` em vez de `[0, tamanho_total_do_BO)` para buffers WB_MMAP.
- `panvk_pool_invalidate_maps` mantém as invalidações completas para transferências GPU→CPU. Não elimina barreiras, flushes explícitos, ioctls necessários, nem mexe em recursos do jogo.

## Proveniência
- Base: UMA F1 compilada na execução #7 (tentativa 2) da branch `exp/uma-inteligente-fase1`.
- Fonte original reutilizada: `vendor/PanVK-G720-UMA-F1-source.zip`, SHA-256 `c0f343adcfdb6779df5642f4252308baed2c7e8b462181af79864c7471023d4a`.
- Patch F2: `patches/uma-f2-used-range.patch`.
- Workflow: `.github/workflows/build-uma-f2.yml`.
- Validação local de aplicação do patch concluída; driver Android/MediaTek ainda requer resultado CI + teste real.

## Riscos e validação
Buffers compartilhados com GPU exigem coerência correta. O patch não altera a ordem de publicação nem a sincronização pós-submissão; reduz a faixa de dados declarada como utilizada. Ainda assim, é experimental, e casos particulares de escrita fora da região subalocada podem produzir falhas gráficas.

1. **Preservar UMA F1 e E20 como retorno.** Importar F2 somente pelo Bachata, não como driver global.
2. Confirmar inicialização do jogo e consistência de texturas, partículas e sombras.
3. Comparar F1→F2→F1 na mesma cena do jogo por 3–5 min por versão, com configurações originais.
4. Anotar FPS predominante (não apenas pico), travadinhas e pressão de RAM.
5. Se houver congelamento, artefatos ou regressão persistente, interromper o teste e restaurar F1.

Um build verde é apenas validação de compilação, não evidência de FPS ou de conformidade Vulkan.
