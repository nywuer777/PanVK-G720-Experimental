# P46 — Gate contra falsa integração do BCn no F43DEV privado

O objetivo deste ciclo é **não atribuir a correção BCn P45 pública ao ELF GLIBC privado**, sem perder a correção de identidade da P42.

## Escopo e resultados

- [x] ELF privado real P42, AArch64/GLIBC: `host/shadps4-arm64-fex` (75.323.616 bytes), `.text` SHA-256 `f71b3ac83bb350f7de2835e3f4037b9d95d3fc080f1d9781e2271549f7964157`.
- [x] `.text` dos APKs privados assinados P23 e P42 **idêntica**; diferença de assinatura/identidade não incorpora BCn.
- [x] ELF público P31: contrato privado `--bachata-contract` ausente e marcador `GPU BCn fallback admitted` ausente. A presença do caminho textual `bachata-s4` **não prova** equivalência.
- [x] Gate de identidade da P42 reexecutado: **P23 PASS**, **P42 PASS**, **P31 REJECT** (o último tem identidade privada ausente).
- [x] `test_p46.py`: **12 testes** em ELF sintéticos (nenhum binário privado distribuído).
- [x] `test_p46_outlast.cpp`: **14 cenários** do contrato BC3 sRGB 1024×1024 11 mipmaps; GCC + Clang ASan/UBSan aprovados. Esses cenários são **simulados, não acessam a GPU**.
- [ ] Alterar e recompilar **código-fonte do GLIBC privado** correspondente à P42 com o caminho completo P45; fonte privada não está presente.
- [ ] Testes de integração Vulkan em dispositivo Android e revalidação do Outlast.

## Executar localmente (com arquivos que você possui legitimamente)

```bash
python3 -m unittest -v test_p46.py
# Compilar na pasta do pacote, sem desativar asserções:
g++ -std=c++20 -O2 -Wall -Wextra -Werror -pedantic -I. test_p46_outlast.cpp -o /tmp/p46-outlast
/tmp/p46-outlast
clang++ -std=c++20 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer -Wall -Wextra -Werror -pedantic -I. test_p46_outlast.cpp -o /tmp/p46-outlast-san
ASAN_OPTIONS=detect_leaks=1 UBSAN_OPTIONS=halt_on_error=1 /tmp/p46-outlast-san
# Gate estático (código de saída 3 = bloqueio):
python3 p46_private_glibc_gate.py --baseline Bachata-P42.apk --candidate APK-candidato.apk --report p46-report.json
```

O gate verifica a seção **`.text`** real, o contrato privado V2 e o caminho BCn. **Não permite aprovar um APK apenas com novo Build-ID, novas strings, nova assinatura ou o executável público recompilado.** Mesmo uma seção `.text` alterada permanece BLOQUEADA até rastreabilidade da fonte privada, build e prova de funcionalidade no Android. Ele não desativa asserts nem faz patch na P42.

**Importante:** o P44/P45 resolve condições de admissão da `ImageView` em código C++ público. O F43DEV privado ainda precisa conectar: (1) decodificação BC1/BC3; (2) VkImage de RGBA8 sRGB/UNORM; (3) upload com fence sinalizado por mip/camada; (4) ledger invalidado após escrita; (5) criação de view amostrada com formato da imagem real. Apenas existir uma string no ELF não comprova esse percurso.

## Gates para um APK posterior

1. Possuir e modificar legalmente o **código-fonte correspondente ao runtime GLIBC privado da P42** ou mecanismo equivalente de integração comprovado, não apenas o APK.
2. Demonstrar diff C++ ativo, build ARM64/GLIBC reproduzível e mudança pertinente na `.text` privada.
3. Executar `tools/bachata-hostid/host_identity_release_gate.py` no **APK final assinado** e verificar os 397 manifestos.
4. Provar em Vulkan que cada subrecurso `(mip, layer)` recebeu o formato final RGBA8 correto, o upload foi concluído e a view usa o formato compatível.
5. Testar em Android/Outlast e coletar diagnóstico sem informações privadas para declarar o jogo corrigido.

Nenhum APK P46 foi criado: produzir outro APK com o mesmo `.text` não testaria P45 no Outlast. O P42 funcional permanece preservado.