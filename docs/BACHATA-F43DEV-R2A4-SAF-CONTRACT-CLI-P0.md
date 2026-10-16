# Bachata F43DEV — R2A.4/P0: contrato SAF, parser e proteção de segredos

**Data:** 2026-10-16 · **Branch:** `exp/bachata-f43dev-r2a4-saf-contract` · **Status:** patch validado no CI pré-build; compilação ARM64/GLIBC em andamento em [#38971854990](https://github.com/nywuer777/PanVK-G720-Experimental/actions/runs/38971854990).

## Base e evidências

- APK funcional F43DEV V2 preservado, SHA-256 `e4ec95a1ffcb33f1bf7d8e9d9587cc0af0f839de226b8ed74fb03f08e3444ded`.
- Os quatro logs de diagnóstico F43DEV (Outlast, Minecraft e sessões de referência) mostram `--bachata-contract`, `--bachata-saf-socket` e `--bachata-saf-token` no lançamento.
- **Somente metadados agregados:** contrato = 32 caracteres hex em todas as 4 sessões; token = 32 caracteres hex; nome do broker = 28 caracteres `[A-Za-z0-9._-]`. Valores reais nunca copiados para a auditoria, código, relatórios ou GitHub.
- Inspeção de símbolos do runtime Bionic original revela `Core::FileSys::SafBrokerClient::{Request,Stat,List,OpenRead}`, `SafFsBackend::{Open,OpenDir,Exists,IsDirectory,ReadFile}`, `NormalizeSafGamePath` e `Platform::Bachata::IsValidContractNonce`. **O source do core Linux/GLIBC compilável, revisão fixada `be6bc2e9c60799e071dd2fafa6216e8d80ec619c`, não possui cliente/FS backend SAF correspondente.**

## Implementação material R2A.4/P0

- `tools/bachata-r2a4/saf_cli_contract.h`: valida nonce/token 32 hex e sintaxe de socket abstrato (rejeita path absoluto, controles ASCII, mais de 106 bytes). Requer obrigatoriamente todos os três parâmetros no core F43DEV Linux ARM64. Formato adotado das quatro evidências, ainda sujeito a revisão se o Android gerar novos formatos.
- `tools/bachata-r2a4/apply_r2a4.py`: aplica pin `be6bc2e9...` com ancoragem exclusiva **após** os patches R2A (acesso misto de imagens) e R2A2 (socket de controle e UID). Declara os novos parâmetros CLI11, valida antes de iniciar sessão e substitui o `LOG_INFO Run: argv` por argumentos com nonce, token e nome do broker mascarados em sintaxes `--flag value` e `--flag=value`.
- `tools/bachata-r2a4/test_saf_cli.cpp`: teste C++ nativo de casos positivos/negativos, inclusão de argumentos e redaction.
- `.github/workflows/bachata-f43dev-r2a4-saf-contract.yml`: validação do header/parser + 18 regressões R2A + unit test R2A2, checkout fixado e patch auditável, depois build C++23 ARM64/GLIBC/FEX, evidência do ELF e publicação de **candidato não instalável**.
- Na pré-validação GitHub, `R2A4_SAF_CLI_TESTS_PASS`, `Ran 18 tests`, `R2A2_HOST_GATE_TESTS_PASS`, `R2A4_CLI_PATCH_APPLIED`; o artefato [#12076583248](https://github.com/nywuer777/PanVK-G720-Experimental/actions/runs/38971854990/artifacts/12076583248) contém diff, headers e hashes. **19/19 testes locais de auditoria dos 4 registros** passaram em `audit_and_test_r2a4.py` no kit de evidências.

## Limite explícito (não mascarar)

O **formato de mensagens/handshake do broker SAF** não está disponível na revisão fonte pública. O patch **não** faz autenticação de token junto ao broker, não implementa `Stat/List/OpenRead` e não monta sistema de arquivos SAF. O marcador de build é intencionalmente `BACHATA_F43DEV_R2A4_CLI_SHAPE_OK_SAF_IO_UNIMPLEMENTED` para impedir relatórios falsos.

Validação sintática do nonce **não comprova autenticidade criptográfica** da sessão. `SO_PEERCRED` usado no socket de controle R2A2 identifica UID, mas não substitui autenticação de aplicação para o broker SAF. Uma eventual implementação exige recuperar ou documentar o protocolo, simular o broker com casos positivos/negativos, limitar tamanho de mensagens, validar todas as operações read-only e integrar a `Core::FileSys`. Qualquer formato de mensagens inventado ou falso sucesso será rejeitado.

## Liberação e próximos gates

1. Confirmar término com sucesso do build [#38971854990](https://github.com/nywuer777/PanVK-G720-Experimental/actions/runs/38971854990) e auditar ABI/marcadores no ELF.
2. Recuperar protocolo SAF do runtime original com evidência ou receber source Android/backend de leitura; testar requisições `Stat`, `List`, `OpenRead` e prevenção de travessia de diretórios.
3. Confirmar compatibilidade de handshake/contrato e identidade com os componentes Android Bionic sem reduzir assinatura ou permissões.
4. Só então gerar variante **side-by-side** com identidade assinada e testável, preservando a F43DEV V2 funcional.
5. Outlast BCn e Minecraft robust overlap permanecem pendentes e exigem validação real em G720.

**Sem alteração na PanVK Fase 3, no F4.3 Bionic ou no APK V2. Nenhum APK R2A.4 foi produzido.**
