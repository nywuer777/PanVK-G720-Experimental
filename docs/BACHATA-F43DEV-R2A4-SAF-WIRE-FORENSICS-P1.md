# R2A.4/P1 — Protocolo SAF: análise estática da implementação Bionic original

2026-10-16. **Não é um codec de produção e não confirma interoperabilidade com o broker Android.**

## Origem autenticada

A própria F43DEV V2 assinada, APK SHA-256 `e4ec95a1ffcb33f1bf7d8e9d9587cc0af0f839de226b8ed74fb03f08e3444ded`, contém `lib/arm64-v8a/libbachata_native_runtime.so`, SHA-256 `16bd679a762ee3615bc3deb24e0945964775f267eb2f1dc0f015c2eeb030ef54`.

A biblioteca expõe, na tabela dinâmica ARM64, `Core::FileSys::SafBrokerClient::Request(uint8_t, std::string_view, bool)`, `Stat`, `List`, `OpenRead` e `SafFsBackend` com `Exists`, `IsDirectory`, `Open`, `OpenDir`, `ReadFile`.

## Observações que o disassembly sustenta

`llvm-objdump` na versão Bionic identificou estes endereços virtuais dentro da mesma biblioteca íntegra:

- `Request`: 0x0357ab10; conecta socket AF_UNIX e monta quadro de requisição.
- Sequência de magic em `Request+0x188` (0x0357ac98): `0x42534631`; helper escreve os quatro bytes **big-endian**, resultando na sequência `BSF1`.
- Após o magic, escreve o byte 0x01 localizado em `.rodata` 0x023b0cee, seguido pelo byte de operação (argumento do método).
- O seguinte `append_u32` é escrito em big-endian e precede a string de token; outro `append_u32` precede a string do caminho solicitado.
- Comprimento de caminho possui verificação de 32 bits (antes de compor pacote); ainda é necessário documentar limites superiores do caminho e da string de token.
- `Stat` usa `Request(1, path, false)` em 0x0357b660; `List` usa operação 2 em 0x0357b768; `OpenRead` usa operação 3 e `expect_fd=true` em 0x0357bc6c.
- Resposta: o código recebe um cabeçalho de **10 bytes**, verifica magic `BSF1` (comparação `rev` e `0x42534631` em 0x0357ae44), versão 1 em byte offset 4, e comprimento big-endian de 32 bits a partir do offset 6. Recusa payload superior a `0x400000` (4 MiB).
- `recvmsg` percorre ancillary messages e reconhece `SOL_SOCKET=1`, `SCM_RIGHTS=1` para obter um descritor de arquivo em `OpenRead`. A resposta mantém um byte de estado em offset 5. O significado integral dos códigos de estado ainda precisa de validação.
- `Stat` exige payload de 17 bytes ao obter sucesso (`type-byte + uint64BE + uint64BE`). Significados exatos dos dois campos u64 precisam ser verificados no Android. `List` exige ao menos 4 bytes e interpreta o primeiro como contagem big-endian, mas ainda faltam campos por entrada.

O enquadramento provisório **inferido do binário**, sujeito a ensaio com broker real, é:

```text
Request:  BSF1 (4) | version (1) | opcode (1) | token_len (u32 BE) | token |
          path_len (u32 BE) | path
Response: BSF1 (4) | version (1) | status (1) | payload_len (u32 BE) | payload
Optional response ancillary FD: SCM_RIGHTS for OpenRead
```

## Critérios antes de implementação produtiva

1. Reconstituir e testar `recv_exact`, timeouts, controle de comprimento, truncamento de CMSG, todos os códigos de status, `SCM_RIGHTS` e propriedade de FD.
2. Com broker controlado, testar `Stat` arquivos/diretórios, `List` entradas, `OpenRead` com transferência de FD e leitura parcial; comparar contra operações Bionic em dados não sensíveis.
3. Não transmitir tokens reais durante desenvolvimento ou incluí-los em logs, dumps ou artifacts.
4. Integrar `SafFsBackend` de forma read-only com `Core::FileSys`, sem substituir arquivos reais por mocks.
5. Executar handshake SAF real no dispositivo e manter assinatura/identidade do Bionic funcionando antes de um APK.

## Estado da R2A.4

O P0 (parser/validação/redação) está aplicado, com preflight CI aprovado; o ELF GLIBC está em build no [run #38971854990](https://github.com/nywuer777/PanVK-G720-Experimental/actions/runs/38971854990). Este relatório P1 **só fornece engenharia reversa estática parcial**; ainda não há cliente SAF real, nem APK liberado, nem correção comprovada dos jogos.

F43DEV V2 e PanVK F3/F4.3 permanecem imutáveis.
