# P60 — Consulta SAF e estágio privado de `sce_module/libc.prx`

## Evidência de entrada

No diagnóstico P59 (`BS4-20261018-3CCCD8BA`), o Host V2 concluiu
autenticação, BSF1 P58 entregou o FD e a P59 criou uma cópia privada
de `eboot.bin`. O jogo alcançou Vulkan e execução parcial no FEX.
Em seguida, o linker procurou
`<APP_DATA>/files/direct-runtime/CUSA00325/sce_module/libc.prx` e
registrou `does not exist`. A reprodução com 23 apresentações de swapchain
não demonstra primeiro quadro de jogo.

O código-fonte upstream fixado em
`be6bc2e9c60799e071dd2fafa6216e8d80ec619c` monta o diretório
físico do executável em `/app0`, e
`Core::Linker::LoadModule()` verifica `filesystem::exists()` antes de
ler o arquivo. Portanto, a biblioteca não pode ser atendida somente
pelo caminho Android SAF sem nova integração.

## Implementação segura, escopo inicial restrito

- Um único caminho relativo aprovado em tempo de compilação:
  `sce_module/libc.prx`.
- Consulta `Client::Stat` e, **somente se autorizar e indicar arquivo**,
  chama `Client::OpenRead`. Resposta remota rejeitada não significa
  necessariamente `ENOENT`; o status é registrado como rejeição.
- O descritor do broker já é validado por `SO_PEERCRED`, token da
  sessão, tipo regular e modo `O_RDONLY`. Nunca abrir
  `/proc/self/fd/N`.
- Copia diretamente com `pread` para
  `<PRIVATE_GAME_ROOT>/sce_module/libc.prx`, criado via
  `openat(O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC)` com modo `0600`.
  `sce_module` deve ser diretório privado do UID corrente,
  sem permissão de escrita para outros ou grupo.
- Rejeita caminho inseguro, symlink, arquivo preexistente (não
  sobrescreve), arquivo não regular, tamanho maior que 256 MiB,
  arquivo vazio e respostas do broker inválidas.
- Mantém o estágio vivo durante o carregamento; remove somente os
  arquivos que esta sessão criou após retorno normal. Em crash
  abrupto podem sobrar arquivos órfãos que precisam de coleta segura
  futura. Nunca apagar conteúdo original de terceiros.
- Preserva Host V2, PanVK Fase 3, BCn e as correções P53–P59.
- Não implementa acesso genérico a `/app0`, nem outros módulos,
  assets, saves, `sce_sys/param.sfo`, DLC ou listagem recursiva.
- Não distribui nem sintetiza bibliotecas do PS4 e não altera a
  P42 funcional. Dados do Outlast não são publicados em GitHub.

## Limitações que importam

O contrato `Client::Stat` foi reconstruído previamente e ainda
não foi validado com o broker real Android para
`sce_module/libc.prx`. Por isso, a P60 **não** interpreta
`BROKER_STAT_REJECTED` como arquivo ausente e não faz fallback
que contorne uma rejeição de permissão.

Mesmo com `BACHATA_P60_LIBC_SAF_PRIVATE_STAGE_READY`, isso somente
atestaria a cópia privada, não que `libc.prx` seja um módulo ELF/SELF
válido, que o linkage funcione ou que o jogo renderize corretamente.

## Gates

1. `bachata-f43dev-p60-libc-tests.yml`: testes sintéticos de
   protocolo BSF1 `Stat` e `OpenRead`, transferência de FD,
   falha remota e integridade/segurança da cópia.
2. Compilação pública ARM64/GLIBC com Host V2 + BCn + P53–P60 e
   análise estática de marcadores (somente após aprovação do gate 1).
3. APK laboratório assinado **separado** da P42 (gates próprios).
4. Diagnóstico em dispositivo real. Nenhuma alegação de FPS ou
   compatibilidade antes desse teste.

Todos os segredos, chaves privadas, APK original e dados do jogo
permanecem fora do repositório público.
