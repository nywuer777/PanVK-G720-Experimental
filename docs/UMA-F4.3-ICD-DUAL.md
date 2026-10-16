# PanVK F4.3 — Android HAL + Vulkan direct-ICD

Data: 2026-10-16
Branch: exp/uma-inteligente-fase4-3-icd-dual
Base: exp/uma-inteligente-fase4-2-logcat (3e3ca9ff326850779879583ad39f201b9dd755f4)

## Evidência inicial

O APK Bachata S4 0.2.5 contém dois runtimes separados (Android/Bionic e Linux/GLIBC/FEX). O loader Bionic possui mecanismo direct-icd que requer funções vk_icd*. O binário F4.2 exportava apenas HMI; suas funções ICD existiam, mas estavam LOCAL (não disponíveis para dlsym). O mapa Android do Mesa continha apenas HMI no bloco global, ao contrário do mapa GLIBC.

Os processos vistos em 10:10:43 e 10:14:05 nos logs antigos iniciaram shadps4-arm64-fex (caminho GLIBC). O log de 10:54 não discrimina qual runtime foi usado; a seleção de driver na aba Native Bionic não comprova runtime efetivo.

## Implementação mínima e com guardas

Ferramenta: tools/uma-f4-3-icd-exports.py. Executada após F4.2 e antes do configure do Mesa.

1. src/vulkan/vulkan-android.sym: mantém HMI; e exporta vk_icdGetInstanceProcAddr, vk_icdGetPhysicalDeviceProcAddr, vk_icdNegotiateLoaderICDInterfaceVersion; mantém local: * para demais símbolos.
2. src/vulkan/vulkan-icd-android-symbols.txt: atualiza conjunto permitido pelo symbols-check opcional para as mesmas quatro entradas.
3. src/panfrost/vulkan/csf/panvk_vX_gpu_queue.c: somente substitui o identificador diagnóstico por PANVK-F4.3 LIB_LOADED, build G720-UMA-F4.3-ICD-DUAL-20261016 e Logcat PanVK_F43. Nenhuma mudança funcional de sincronização, cache UMA, ring CSF ou agendamento.

A ferramenta exige uma ocorrência exata de cada âncora e contém testes negativos de proteção contra reaplicação. O workflow exige ELF ARM64, liblog.so e as quatro exportações com nm -D --defined-only; recusa dependências GLIBC indevidas.

## Critérios de validação

- Teste local do contrato do linker script (fixture ELF) PASSOU, mas é apenas host Linux.
- Pipeline CI Android ARM64: resultado deve ser lido diretamente da execução GitHub Actions.
- Runtime real Bionic no aparelho: pendente; não afirmar que o driver foi carregado com base apenas na aba de seleção.
- Carregamento válido exige linha Bachata.Vulkan direct-icd loaded=..., hash e interface; idealmente também PanVK_F43 LIB_LOADED.
- Nenhuma comparação de FPS sem comprovação de driver real.

## Preservação

Branch estável Fase 3 intocada. Branch F4.2 inalterada. APK do Bachata não foi modificado nem assinado. Não gerar crash proposital. Não reutilizar o pacote Bionic em um slot GLIBC.
