# P58 — Corrigir enquadramento da solicitação BSF1 ao broker Android

Data: 2026-10-18. Evidência real: diagnóstico privado
`BS4-20261018-D85BCE48`, cujo manifesto (seis arquivos) foi conferido
com SHA-256.

## Achado material

A P57 detectou `BACHATA_P57_BSF1_HEADER_PEER_RESET`.
Uma inspeção **read-only**, local e autorizada do `classes.dex` do APK
P42 encontrou o método Android do broker SAF, que recebe dados por
`DataInputStream` nesta ordem:

1. `readInt()` — magic `0x42534631` (`BSF1`);
2. `readUnsignedByte()` — versão 1;
3. `readUnsignedByte()` — operação (3 = OpenRead);
4. `readUnsignedShort()` — comprimento do token, **16 bits BE**;
5. `readInt()` — comprimento do caminho, **32 bits BE**;
6. `readFully()` — bytes do token;
7. `readFully()` — bytes do caminho;
8. o token é comparado usando `MessageDigest.isEqual`; após validação
   de escopo, o broker pode devolver um arquivo via
   `LocalSocket.setFileDescriptorsForSend`.

Essa sequência também é corroborada pela montagem da requisição na
biblioteca privada P42 `SafBrokerClient::Request()`: um campo
`BE16`, depois `BE32`, antes dos bytes do token/caminho.

**Defeito no cliente público R2A5 (P54–P57):**

```
BSF1 | U8(version) | U8(opcode) | BE32(tokenLen) |
tokenBytes | BE32(pathLen) | pathBytes
```

**P58 aplica o formato aceito pelo lado Android:**

```
BSF1 | U8(version) | U8(opcode) | BE16(tokenLen) |
BE32(pathLen) | tokenBytes | pathBytes
```

Para `OpenRead("eboot.bin")` e token hexadecimal com 32 bytes:
- pacote público anterior: **55 bytes**;
- formato P58: **53 bytes**;
- cabeçalho de 12 bytes:
  `42 53 46 31 01 03 00 20 00 00 00 09`.

Com o framing antigo, o broker interpretava os campos de comprimento
incorretamente e podia encerrar a conexão antes de responder, consistente
com `HEADER_PEER_RESET` observado. Isso constitui **uma causa concreta de
incompatibilidade**, mas não comprova que seja a única.

## Implementação e verificações

- `patch_p58.py`: substitui **apenas** a serialização da solicitação BSF1
  em `saf_bsf1_client.cpp`, usando âncoras estritas; adiciona marcador
  constante `BACHATA_P58_BSF1_REQUEST_ANDROID_WIRE_BE16_BE32`.
- `test_patch.py`: valida sequência, tamanhos, bytes dourados e
  preservação do protocolo Host V2/UID/token/descritores.
- `test_android_bsf1_wire.cpp`: servidor sintético compatível com o
  `DataInputStream` Android aceita a solicitação e devolve um FD de
  arquivo regular somente leitura via Unix `SCM_RIGHTS`.
- `bachata-f43dev-p58-bsf1-protocol-tests.yml`: testes Linux C++20,
  Python e sanitizadores sem qualquer binário privado em CI.
- `bachata-f43dev-p58-bsf1-arm64.yml`: compilação ARM64/GLIBC do core
  com Host V2, correções BCn e P53–P57 preservadas.

## Limitações

A P42 original **não** foi alterada, recompilada, distribuída nem usada
em GitHub Actions. Nenhuma chave de assinatura, token de sessão, socket,
arquivo de jogo, classes.dex privado ou biblioteca nativa privada foi
incluída neste repositório público.

O teste simulado demonstra correção do framing e passagem de FD, não
comprova que o Android autorizará o acesso ao arquivo do Outlast após a
instalação do LAB CLONE. A montagem completa do diretório virtual PS4
`/app0` e leitura de todos os recursos via SAF continuam fora do escopo
desta alteração. A P42 funcional e o PanVK Fase 3 devem permanecer
preservados. FPS e texturas BCn só poderão ser testados após alcançar a
renderização efetiva.

**Próxima evidência:** reconstruir um APK LAB CLONE com o núcleo P58,
instalar sem substituir a P42, iniciar o Outlast e analisar os marcadores
`BACHATA_P58_BSF1_REQUEST_ANDROID_WIRE_BE16_BE32` e
`BACHATA_P54_BSF1_EBOOT_AUTHENTICATED_FD_READY`.
