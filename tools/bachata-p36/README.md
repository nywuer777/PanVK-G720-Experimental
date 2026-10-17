# Bachata P36 (revisão v2) — proveniência de acesso no shader

Revisão fixada: `be6bc2e9c60799e071dd2fafa6216e8d80ec619c`. Kit SHA-256 `ca072f43d63385b62d7411bb77a80f82e8dc1aded237a07c70c91ce38340ee39`. O recurso distingue leituras comuns (`ImageRead`/`ImageSampleRaw`) de leituras implícitas de operação atômica, evitando ignorar `ImageRead+ImageAtomic` no mesmo recurso. Testes sintéticos 151 asserções C++ e 74 testes Python; compilação completa pendente de CI. Não produz APK nem muda a sincronização. Minecraft/Outlast ainda não corrigidos; P23 preservada.
