# UMA F4.2 — PANVK G720 Logcat Diagnostic (não otimização)

Deriva da F4.1.1; preserva F2/F3 e toda sincronização, ring CSF,
heap, shaders e políticas UMA. F3 continua referência de desempenho.
Esta versão não é considerada validada em dispositivo até teste.

Emitimos PANVK-F4.2 LIB_LOADED build=G720-UMA-F4.2-LOGCAT-20261016
em stderr e Logcat (tag PanVK_F42). F4.1.1 e perfis F4 são
espelhados em Logcat via liblog.so, já vinculado ao driver anterior.
O identificador de build não equivale a um SHA do binário em RAM.
O hash do binário empacotado está em meta.json. O logging adiciona overhead.

## Teste no LADB / ADB shell sem root e sem provocar crash

1. Preserve e mantenha disponível o ZIP F3 para rollback.
2. Importe apenas no Bachata e selecione F4.2.
3. No terminal ADB shell execute: logcat -c
4. Abra o jogo por 30–60 segundos; saia normalmente.
5. Execute: logcat -d -v threadtime -b main > /sdcard/Download/panvk-f42-logcat.txt
6. Envie o arquivo txt. Procure LIB_LOADED, READY, QUEUE_SUBMIT_ENTRY,
   KBASE_SUBMIT_ENTER, PROGRESS e PANVK-F4 submits=.
7. Opcional: python3 tools/analyze-uma-f4-2.py panvk-f42-logcat.txt
   e python3 tools/analyze-uma-f4.py panvk-f42-logcat.txt

Sem LIB_LOADED não é possível confirmar carga F4.2 pelo Logcat;
verifique seleção, sessão, buffer Logcat e o stderr capturado.
Nenhuma modificação no app Bachata. Não comparar FPS da F4.2 contra F3.
