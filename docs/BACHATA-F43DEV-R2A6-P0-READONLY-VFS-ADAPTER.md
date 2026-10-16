# Bachata F43DEV R2A.6/P0 — integração SAF VFS read-only (staged, mount OFF)

2026-10-16 · Branch: `exp/bachata-f43dev-r2a6-vfs-readonly` · GitHub Actions: [R2A.6 #38979696311](https://github.com/nywuer777/PanVK-G720-Experimental/actions/runs/38979696311).

## O que foi implementado materialmente

- `tools/bachata-r2a6/saf_vfs_readonly.h/.cpp`: **ReadOnlyMount** com prefixo exato `/app0`, root relativo ao broker informado explicitamente, resolução sem traversal, API read-only `Stat`, `List`, `OpenRead`. Nunca cria pastas, grava, remove ou renomeia dados. Roots reais de jogos não foram inferidos a partir de nomes; usar apenas após validação no broker Android.
- `tools/bachata-r2a6/apply_r2a6.py`: patch fail-closed ancorado na revisão pública `be6bc2e9c60799e071dd2fafa6216e8d80ec619c`, preserva R2A imagem/layout, R2A2 host UID, R2A4 CLI/segredos e R2A5 BSF1. Insere métodos de aceitação segura de um descritor read-only recebido via `SCM_RIGHTS` na classe `Common::FS::IOFile` (Linux ARM64, `ENABLE_BACHATA_RUNTIME`).
- `IOFile::AdoptReadOnlyFd` toma ownership do FD em qualquer caso, usa `fcntl(F_GETFL)` e `fstat` para aceitar **somente arquivo regular O_RDONLY**, executa `fdopen(fd, "rb")`, guarda caminho guest lógico apenas para exibição e zera o flag `saf_backed_` ao fechar; `IOFile::Unlink` bloqueia remoção em handles SAF. O `Close` e operações de move preservam propriedade do FD.
- `tools/bachata-r2a6/test_saf_vfs_readonly.cpp`: 35 asserções de prefixo, root, componentes `../`, `./`, NUL, controle ASCII, e rejeição sem broker.
- CMake `shadps4` recebeu `saf_vfs_readonly.cpp/.h` somente sob `ENABLE_BACHATA_RUNTIME`; o **mount não está ligado às operações de kernel do PS4**. Não há mudança nos mounts locais existentes.
- O patch **não** reempacota nem modifica a F43DEV V2, PanVK Fase 3 ou F4.3.

## Evidências executadas

- Primeira execução #38979630244: testes passaram mas etapa de patch falhou em `git diff --check` devido a escape Python/C++; o gerador foi corrigido no commit `027e50f94705930e5508697af3a42164979e1c1c`, e foi disparada nova execução.
- Segunda execução [#38979696311](https://github.com/nywuer777/PanVK-G720-Experimental/actions/runs/38979696311):
  - `r2a6-source-vfs-preflight` **SUCCESS**, `R2A6_READONLY_VFS_PATH_TESTS_PASS count=35` tanto normal quanto ASan/UBSan; `R2A5_MOCK_BROKER_TESTS_PASS count=33`; todos os patches até R2A6 aplicados a pin exato, `git diff --check` PASS.
  - `r2a6-arm64-transport` **SUCCESS**, biblioteca experimental `libbachata_r2a6_bsf1_vfs_READONLY_TEST.so` compilada para Linux AArch64/GLIBC, não Bionic.
  - `r2a6-full-fex`: **in progress** no registro deste relatório, não confundir build iniciado com sucesso.
- Artefatos CI: diff [#12080492547](https://github.com/nywuer777/PanVK-G720-Experimental/actions/runs/38979696311/artifacts/12080492547); biblioteca ARM64 disponível nos artifacts da execução.

## Restrições / bloqueios restantes

1. **Não há integração funcional com syscalls PS4 `open`, `stat`, `getdents`, `fstat` para SAF ainda.** O core principal só compila o adaptador; nenhuma operação real do jogo é redirecionada.
2. `Kernel::fstat` ainda resolve timestamp por `stat(file->f.GetPath())`. Quando um handle SAF for habilitado, isso precisa ser convertido em `fstat(fileno(...))` e mapeamento conservador dos metadados. `getdents` exige uma `BaseDirectory` adequada; não pode reutilizar `NormalDirectory` como se a pasta estivesse em disco Linux.
3. A assinatura da sessão, o token do broker e a interoperabilidade `BSF1` real **não** foram confirmados no dispositivo. `SO_PEERCRED` não equivale a assinatura APK.
4. Todos os caminhos de escrita em `kernel/file_system.cpp`, incluindo `write`, `writev`, `pwritev`, `truncate`, `rename`, `unlink`, deverão rejeitar explicitamente SAF com `EROFS`; a proteção do FD `rb` não substitui guards de syscalls.
5. Não existe APK instalável R2A.6 neste marco, e Outlast/Minecraft seguem sem correção in vivo.

## Próximo gate R2A.6/P1

- Auditar formato real e mapeamento de raízes de jogo no broker Android (usando dados de teste, nunca tokens).
- Implementar diretório baseado em `BSF1::List`, arquivo baseado em `SCM_RIGHTS` com `IOFile::AdoptReadOnlyFd` e guards `EROFS` em TODAS as operações de escrita.
- Integrar `/app0` apenas mediante flag de laboratório e verificação de identidade, com fallback explícito e sem fallback silencioso para paths inválidos do broker.
- Validar `stat/fstat/getdents/lseek/read` e leitura real `eboot.bin` no Android, comparando V2 funcional e candidato. Gerar APK separado só depois dessa validação.

F43DEV V2 estável: `e4ec95a1ffcb33f1bf7d8e9d9587cc0af0f839de226b8ed74fb03f08e3444ded`. PanVK Fase3 congelada `3cacc2f0bcbb2333bb7742d37a3e471fd8305acb`. Não substituir nenhum deles.
