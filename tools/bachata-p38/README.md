# Bachata P38 — sincronização entre despachos (experimental)

Core público fixado `be6bc2e9c60799e071dd2fafa6216e8d80ec619c`.

P38 acrescenta um `vk::MemoryBarrier2` entre operações de shader de despachos/desenhos sucessivos para ordenar escritas de imagem anteriores contra acessos posteriores. A função é **desligada por padrão**, ativada apenas com `BACHATA_P38_INTERDISPATCH_BARRIER=1`. Não assegura sincronização intra-despacho, não elimina corridas de operações atômicas dentro do shader e não remove os bloqueios de robust image/alias; no momento, Outlast e Minecraft **não estão homologados como corrigidos**. A P23, os drivers PanVK e a resolução dos jogos não são modificados.

Delta P38 SHA256: `a74edea8081197971d30505ce89caf50dbcd1be6c47d81a9338a0b839bf6ea14`, composto com os kits P36.2 e P37 existentes na branch. O workflow valida o portador e testa a compilação real do core público ARM64/GLIBC; não publica APK nem código/credenciais privados.
