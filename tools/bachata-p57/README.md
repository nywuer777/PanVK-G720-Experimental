# P57 — Classificação de errno no recvmsg do BSF1

Data: 2026-10-18. Diagnóstico real `BS4-20261018-D3F91C0A`.

## Evidência de hardware

O dispositivo Android 16 `2412DPC0AG` confirmou:
- Android host encontra a pasta e `eboot.bin` do CUSA00325 via SAF.
- `BACHATA_F43DEV_R2A2_HOST_GATE_OK` (controle Host V2).
- `BACHATA_P53_EBOOT_ROOT_UNAVAILABLE` (sem arquivo físico).
- `BACHATA_P56_BSF1_HEADER_SYSCALL_ERROR` (falha de **recvmsg** antes de validar o cabeçalho).
- `CONTENT_INVALID` e nenhum primeiro quadro.
- Vida do processo FEX: 15,615 ms; timeout de recepção configurado no cliente público: 2.000 ms. O diagnóstico não contém o `errno` original, logo a causa não está provada.
- Os seis anexos do ZIP foram conferidos com o manifesto SHA-256 (sem publicar os dados da sessão).

## Auditoria local da P42 (nenhum binário privado publicado)

A inspeção read-only de `libbachata_native_runtime.so` do APK P42 fornecido mostrou o método original `SafBrokerClient::Request()` recebendo o cabeçalho por `recvmsg(fd, msg, 0)`. O núcleo público P56 usa `recvmsg(fd, msg, MSG_CMSG_CLOEXEC)`. Esta é uma diferença que pode ser relevante para compatibilidade do syscall, **mas não prova** que a flag seja responsável. A P57 **não a altera**.

Outras hipóteses ainda possíveis incluem reset pelo broker do Android, erro de permissão/seccomp, descritor inválido ou `EINVAL`. Sem o `errno`, não devemos fazer mudanças que enfraqueçam `CLOEXEC` ou as verificações de UID e token.

## O que foi implementado

- `tools/bachata-p57/patch_p57.py`, aplicado após a sequência de patches P49 → P53 → P54 → P56 no código público fixado.
- Captura `errno` imediatamente após retorno negativo de `recvmsg`, **sem imprimir o valor bruto**.
- Classifica `ECONNRESET/ENOTCONN/EPIPE` como `HEADER_PEER_RESET`; `EAGAIN/EWOULDBLOCK/ETIMEDOUT` como `HEADER_WAIT_EXPIRED`; `EPERM/EACCES` como `HEADER_POLICY_DENIED`; `ENOSYS` como `HEADER_SYSCALL_UNAVAILABLE`; `EBADF/ENOTSOCK/EFAULT` como `HEADER_BAD_DESCRIPTOR`; `EINVAL` como `HEADER_INVALID_ARGUMENT`; outros erros continuam `HEADER_SYSCALL_ERROR`.
- `PayloadSyscall` mantém sua classificação P56; só o caminho já observado do cabeçalho ganha novas categorias.
- Não altera os bytes de requisição BSF1, a função `recvmsg`, as flags, o socket, o token, a resolução da pasta do jogo ou a proteção de identidade.
- CI de pré-teste `bachata-f43dev-p57-errno-tests.yml` aprovado com C++20 e ASAN/UBSAN.
- `bachata-f43dev-p57-bsf1-arm64.yml` recompila o executável ARM64/GLIBC e verifica os marcadores no ELF; aprovação de CI **não significa** funcionalidade no Android.

## Próximo gate

Somente após compilação e APK laboratorial independente, enviar um novo diagnóstico privativo e conferir o marcador observado:

- `HEADER_PEER_RESET`: inspecionar contrato/token/caminho e logs autorizados do broker.
- `HEADER_POLICY_DENIED`: investigar seccomp/libc/permissões, sem remover controles.
- `HEADER_INVALID_ARGUMENT`: testar diferenças de flags e ABI sob um harness confiável.
- `HEADER_WAIT_EXPIRED`: verificar a entrega de resposta e timeout do serviço.
- `HEADER_BAD_DESCRIPTOR`: investigar vida útil e propriedade do socket.

Nem o carregador completo SAF/`/app0`, nem o Outlast, nem os ganhos de FPS estão homologados. P42 e PanVK Fase 3 preservados.