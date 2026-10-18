# P46 — Relatório material de fechamento

## Evidência binária e verificação contra falsos positivos

**Fonte:** APKs P23, P31 e P42 originais disponíveis no projeto. Arquivos privados foram lidos localmente, NÃO foram anexados ao pacote de testes ou publicados no GitHub.

| Alvo | Identidade V2 | Marcador fallback BCn | Código `.text` | Resultado |
|---|---|---|---|---|
| P23 privado | Presente | Presente | `f71b3ac83bb350f7de2835e3f4037b9d95d3fc080f1d9781e2271549f7964157` | Gate identidade **PASS**, BCn privado **não provado** |
| P42 privado | Presente | Presente | `f71b3ac83bb350f7de2835e3f4037b9d95d3fc080f1d9781e2271549f7964157` | Gate identidade **PASS**, mesma `.text` que P23 |
| P31 público | Ausente | Ausente | `e1e9613c5fae9a4d6c30950b1167ad8e4ef57b04ff3f7ce76836edb5f7d52586` | Gate identidade **REJECT**, core não intercambiável |

A presença de `bachata-s4` em ambos os executáveis é **falso positivo**: não pode comprovar o contrato host V2 nem compatibilidade Vulkan.

**Build-ID P42:** `b505e6d4f2dbf557e2d9577ca9029281d685fb96`. O literal `GPU BCn decoded image requires a matching sampled BC view` permanece na `.rodata` privada, como no diagnóstico do Outlast em `image_view.cpp:257`.

## Regressões executadas

- 12 testes Python (ELF64 little-endian AArch64, bounds, PT_INTERP, contrato V2, falsos positivos, text não alterado) — PASS.
- 14 casos C++ BC3 sRGB de 1024×1024/11 mips — PASS, **GCC + Clang/ASan/UBSan**. Trata-se de ensaio do contrato, não de acesso Vulkan real.
- Gate Android assinatura/identidade V2 **P23 PASS**, **P42 PASS**, **P31 REJECT**, todos verificados com os arquivos reais.
- `p46_private_glibc_gate.py` contra P42/P42: `REJECT_BCN_FIX_NOT_IN_PRIVATE_EXECUTABLE_CODE` (esperado).
- Contra P31/P42: `REJECT_PUBLIC_OR_INCOMPATIBLE_HOST` (esperado).

## Bloqueio remanescente

A fonte completa do executável GLIBC/FEX privado F43DEV não está disponível entre os artefatos. O P45 aprovado no CI compilou o core **público**; não prova uma modificação do binário **privado** da P42. Sem implementação direta no runtime privado, não foi gerado um novo APK. Para retomar: obter fontes privadas ou uma porta ABI comprovada, aplicar P45 nos callsites `Image::Upload` / `ImageView`, compilar ARM64/GLIBC, executar gate de assinatura/identidade e validar no Outlast. **OUTLAST_FIXED=NO**, **APK_P46_BUILT=NO**.