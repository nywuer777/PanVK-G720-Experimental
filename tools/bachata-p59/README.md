# P59 — Materialização temporária privada do eboot autenticado

Data: 2026-10-18. Continuação do diagnóstico P58 enviado pelo usuário
`BS4-20261018-7CB0793C`.

## Evidência do Android real (ZIP privado: não publicar)

- Conferidos seis arquivos contra `manifest.json` (tamanho e SHA-256).
- Android Host V2: `BACHATA_F43DEV_R2A2_HOST_GATE_OK`.
- Protocolo corrigido: `BACHATA_P58_BSF1_REQUEST_ANDROID_WIRE_BE16_BE32`.
- Broker SAF autenticado devolveu o FD inicial:
  `BACHATA_P54_BSF1_EBOOT_AUTHENTICATED_FD_READY`.
- Novo bloqueio do Outlast: `fopen("/proc/self/fd/6", "rb")` devolveu
  `Permission denied`; `Elf::Open` não conseguiu ler o SELF header e
  retornou `CONTENT_INVALID`. Nenhum primeiro quadro.
- Duração do processo FEX ~60 ms. Esse incidente não testa o PanVK/BCn.
- O reset subsequente do control socket após o erro de backend não é
  evidência de novo reset BSF1: a conexão com o broker havia funcionado.

## Confirmação por auditoria das fontes públicas pinadas

O carregador de `src/core/loader/elf.cpp` executa
`m_f.Open(file_name, FileAccessMode::Read)`, e `Common::FS::IOFile::Open`
usa `std::fopen(path.c_str(), ...)`. Portanto, a ponte P54 original
`/proc/self/fd/<n>` demanda uma **nova operação open**, sujeita às regras
do arquivo subjacente e do Android, mesmo que o FD recebido por
`SCM_RIGHTS` já seja autenticado e válido.

A correção P59 permite ao leitor usar uma cópia temporária privada
consistente: `pread(fd)` diretamente sobre o descritor recebido;
`mkstemp` cria um arquivo temporário 0600 dentro do diretório privado
do jogo, com verificação de UID/permissões/tipo do diretório; o carregador
recebe o caminho normal desse arquivo privado. RAII tenta apagar a cópia
em saída normal. Em desligamento abrupto, a cópia pode permanecer; uma
fase posterior deverá implementar coleta segura de arquivos órfãos.

## Segurança e limites

- O protocolo BSF1 P58, a autenticação da sessão, `SO_PEERCRED`,
  `MSG_CMSG_CLOEXEC` e o FD original são preservados.
- Não acessa descritores novos via `/proc/self/fd`.
- Nenhum arquivo de jogo, APK privado, token, certificado, socket ou
  caminho privado é publicado no GitHub.
- A cópia está restrita ao diretório privado já fornecido e validado,
  rejeitando diretórios com escrita para grupo/outros, donos incorretos,
  links simbólicos e FD não regular.
- Máximo 2 GiB; copia em blocos de 256 KiB. Escreve apenas arquivo
  exclusivo 0600 e não substitui `eboot.bin` original.
- Não habilita `/app0` nem fornece acesso a `param.sfo`, DLC,
  arquivos do jogo, bibliotecas ou saves. Também não comprova
  carregamento do Outlast no Android.
- O diretório privado precisa permitir criação de arquivo pela própria
  identidade do processo. Se não, a P59 retorna `CREATE_FAILED` ou
  `UNSAFE_ROOT`, sem contornar permissões.
- Fontes públicas upstream fixadas em
  `be6bc2e9c60799e071dd2fafa6216e8d80ec619c`.

## Indicadores esperados em novo diagnóstico

```
BACHATA_P54_BSF1_EBOOT_AUTHENTICATED_FD_READY
BACHATA_P59_EBOOT_PRIVATE_STAGE_READY
```

O segundo marcador atesta cópia concluída, mas NÃO confirma que o SELF
tenha sido aceito ou que a montagem virtual esteja completa. Os marcadores
de erro P59 distinguem raiz insegura, FD inválido, fonte grande demais,
falha de criação, falha de leitura, falha de escrita e arquivo vazio.

## Gates

`bachata-f43dev-p59-private-stage-tests.yml`: testes sintéticos C++20
em Linux, clang ASAN/UBSAN e Python, com validação de conteúdo, permissões,
rejeições e limpeza.

`bachata-f43dev-p59-arm64.yml`: compila publicamente Host V2 + BCn +
P53–P59 para Linux ARM64/GLIBC e verifica os marcadores efetivamente
presentes no ELF. Não compila o APK; o empacotamento e a homologação
Android são gates distintos.

A P42 funcional e o PanVK Fase 3 permanecem preservados.
