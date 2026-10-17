# P39 — layout Vulkan coerente para o mesmo ImageId

Fonte pública fixada: `be6bc2e9c60799e071dd2fafa6216e8d80ec619c`. Novo delta SHA-256: `9614c70a68c7257c8ba6c64ebfeaf3aeb2bc25878397714539621886761d0eb2`.

Este experimento exige que os dois descritores referenciem o **mesmo** `VideoCore::ImageId`, um como amostragem e outro como storage, excluindo depth, attachment e rebind. Com `BACHATA_P39_SAME_IMAGE_LAYOUT=1`, marca a imagem `force_general` antes da criação das views e inclui o acesso `eShaderWrite` nas transições gerais. DESLIGADO por padrão.

Não corrige alias entre IDs diferentes, conflitos intra-shader, robust-image ou os jogos Outlast/Minecraft; não desativa asserts e não altera a P23. O workflow recompila o core público AArch64/GLIBC, não gera APK.
