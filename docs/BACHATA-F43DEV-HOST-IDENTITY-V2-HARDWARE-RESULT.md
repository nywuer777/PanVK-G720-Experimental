# Bachata F43DEV — Host Identity V2: feedback de dispositivo

Data: 2026-10-16.

## Retorno do teste real

Após receber o APK experimental `Bachata-S4-F43DEV-HOST-IDENTITY-V2-SIGNED.apk`, o usuário confirmou: **"Deu certinho"**.

Contexto: a V1 exibia `IllegalStateException: host identity check failed` na tela de execução. Na V2, a identidade do runtime Linux/GLIBC foi reconciliada com o pacote e certificado experimentais; a verificação foi mantida (não removida) e os manifests internos atualizados.

**Estado:** correção da falha de host identity reportada como funcional em hardware pelo usuário. Não foram fornecidos novos logs nesta confirmação; não extrapolar para estabilidade prolongada, desempenho, ou validação do ICD.

## Próximo gate técnico

Identificar o runtime efetivamente selecionado e confirmar carregamento da F4.3 (marcadores `PanVK_F43` e mensagem de loader `direct-icd loaded=... sha256=...`, com sessão delimitada antes/depois de lançamento do jogo). O driver Bionic embalado no APK não é necessariamente o driver usado pelo host GLIBC.

## Preservação

Bachata oficial não modificado. PanVK Fase 3 estável `3cacc2f0bcbb` preservado. Evitar novas mudanças no CSF/UMA sem confirmação de driver carregado.
