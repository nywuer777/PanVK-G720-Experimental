# Bachata F43DEV V2 — P44: validação real da ImageView BCn

## Resultado executado

- Base Android funcional em hardware segundo teste do usuário: P42.
- Gate de assinatura/identidade P42 executado novamente: PASS, 397 entradas.
- Executável GLIBC analisado materialmente: `host/shadps4-arm64-fex` (privado, stripped).
- Registro da falha: `image_view.cpp:257`, `GPU BCn decoded image requires a matching sampled BC view`.
- O código `.text` GLIBC permanece inalterado frente à P43: **não está corrigido**.
- Contrato P44 em C++20: 138 casos aprovados com GCC e Clang ASan+UBSan.

## O que é novo

`p44_bcn_imageview_contract.hpp` define a política de admissão da visualização:

1. Reconhecer o guest BC1 RGB, BC1 RGBA, BC3 em UNORM/SRGB e backing real BCn/RGBA8.
2. Passar formato comprimido sem substituição quando o backing Vulkan *realmente* suporta BCn.
3. Se backing real for RGBA8, exigir conversão concluída, um upload por camada/mipmap solicitado e geração de fence concluída — nunca presumir que o buffer foi decodificado só por seu tipo.
4. Exigir formato UNORM/SRGB coerente; reinterpretação somente quando mutable format e compatibilidade Vulkan forem comprovadas.
5. Exigir aspectos de cor, uso somente para amostragem, samples=1, recursos/slices válidos e ausência de alterações posteriores ao upload.
6. Em caso de prova ausente, rejeitar e preservar diagnóstico; **não remover `assert` ou alterar cegamente instruções**.

## Pontos específicos do host privado que precisam ser portados

- `src/video_core/texture_cache/image.cpp`: registrar o formato REAL do backing alocado após fallback BCn (não o guest format).
- `src/video_core/texture_cache/texture_cache.cpp`: produzir ledger por `(mip,layer)`, com dimensões/stride/tile verificadas, geração e fence/timeline após upload.
- `src/video_core/texture_cache/image_view.cpp`: consultar o ledger e este contrato ANTES de `vkCreateImageView`; criar view do formato RGBA8 correspondente *somente* com prova positiva.
- Invalidar ledger quando imagem for sobrescrita, houver alias GPU/CPU ou troca de backing.
- Revisar o shader consumer e layout Vulkan; format alone não resolve shader atômico ou storage, nem texture decode errada.

O `p26_upload_attestation.hpp` público antigo usa máscaras de mip sem camada: não é prova suficiente para a quantidade de camadas do Outlast. Os binários da P23/P42 não contêm uma implementação desse novo ledger. Consequentemente **não será produzido APK "P44 corrigido" sem integrar e validar o código no core privado**.

## Reprodução

```sh
g++ -std=c++20 -Wall -Wextra -Werror -O2 -I. test_p44.cpp -o p44-test && ./p44-test
clang++ -std=c++20 -Wall -Wextra -Werror -fsanitize=address,undefined -fno-omit-frame-pointer -I. test_p44.cpp -o p44-san && ./p44-san
python3 audit_p44.py --apk /caminho/P42.apk --p43-json /caminho/p43-audit.json --out p44-runtime-audit.json
```

As funções de auditoria não inserem código, não alteram assinatura nem distribuem o ELF privado. O próximo gate de release exige: host compatível P42, compilação privada com patch P44, assert original mantido, vulkan validation, execução Outlast sem falha e sem erros de textura, regressão Minecraft, hash e assinatura final.