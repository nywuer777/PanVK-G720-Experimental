# P60 — Bloqueio de inicialização GitHub Actions (18/10/2026)

**Status: gate não aprovado; NÃO produzir APK P60**.

## Evidências verificadas via GitHub REST

| Run | Workflow | Resultado |
| --- | --- | --- |
| [39150292966](https://github.com/nywuer777/PanVK-G720-Experimental/actions/runs/39150292966) | P60 mock, ubuntu-24.04 | failure, `steps=null` |
| [39150468409](https://github.com/nywuer777/PanVK-G720-Experimental/actions/runs/39150468409) | P60 mock, ubuntu-24.04 | failure, `steps=null` |
| [39150561039](https://github.com/nywuer777/PanVK-G720-Experimental/actions/runs/39150561039) | P60 mock, ubuntu-22.04 | failure, `steps=null` |
| [39150718327](https://github.com/nywuer777/PanVK-G720-Experimental/actions/runs/39150718327) | P60 mock, ubuntu-22.04 | failure, `steps=null` |
| [39151141916](https://github.com/nywuer777/PanVK-G720-Experimental/actions/runs/39151141916) | mínimo `echo`, ubuntu-24.04 | failure, sem runner, nenhuma etapa executada, segunda tentativa também falhou |

O workflow mínimo contém apenas `echo P60_RUNNER_EXECUTED_STEP=YES`. Não usa `checkout`, código, bibliotecas, caches, segredos, containers ou rede. Sua execução inicial resultou em:

- `runner_id=0`, `runner_name=""`, `steps=[]`;
- duração do run: ~2 s;
- `billable.UBUNTU.total_ms=0`;
- `annotations_count=1` no check run (a anotação completa deverá ser consultada no GitHub UI ou API autorizada).

O log do job P60 inexistente em armazenamento retornou `BlobNotFound`; isso não demonstra erro do compilador.
Uma reexecução do job mínimo foi requisitada e também falhou sem executar etapas.

## Limites da conclusão

As evidências comprovam que os **jobs da P60 não chegaram à execução**, inclusive com um workflow mínimo. Não estabelecem ainda a causa administrativa/operacional exata. Possibilidades a conferir pelo proprietário: GitHub Actions usage/budget, políticas de conta/repositório, provisioning e anotações do workflow. Não presumir qualquer erro de faturamento.

## Gates de retomada

1. O proprietário confere a anotação do run mínimo #39151141916 no GitHub, e `Settings > Billing and licensing > Usage / Budgets` se necessário.
2. Verificar que um workflow mínimo **realmente executa pelo menos uma etapa**.
3. Executar o CI `bachata-f43dev-p60-libc-tests.yml`: testes Python de patch + C++ GCC/Clang/ASAN/UBSAN, incluindo broker sintético (Stat→OpenRead, FD, rejeição).
4. Apenas após o CI aprovado, executar manualmente `bachata-f43dev-p60-arm64.yml` (GLIBC ARM64).
5. Somente após hashes/ELF aprovados, montar LAB CLONE e assinar APK. P42 funcional e PanVK Fase 3 devem ser preservados.

## Implementação separada e não homologada

A branch `exp/bachata-f43dev-p60-libc-saf-preflight` contém:
`p60_saf_libc_stage.h` (escopo exato `sce_module/libc.prx`, SAF Stat/OpenRead, cópia privada 0600 e não sobrescrita),
`patch_p60.py` (integração ao P59),
`test_stage_libc.cpp`, `test_broker_libc.cpp`,
`test_patch.py`. Houve auditoria estática de âncoras e controles, porém
**nenhum teste de execução P60 aprovado e nenhum APK P60 gerado**.


## Diagnóstico conclusivo comunicado pelo proprietário

O GitHub exibiu na execução \`runner-startup\`:
> O serviço não foi iniciado porque houve falhas nos pagamentos recentes da sua conta ou porque seu limite de gastos precisa ser aumentado. Verifique a seção "Faturamento e planos" nas suas configurações.

**Causa do bloqueio da CI: restrição de cobrança/orçamento da conta.**
O aviso aponta duas condições possíveis (pagamentos recentes com falha **ou**
limite de gastos insuficiente). Sem acesso às preferências privadas de
faturamento da conta, não é possível determinar qual das duas se aplica.

Medida necessária pelo proprietário da conta GitHub: conferir
Settings → Billing and licensing → Payment information e Budgets and alerts,
regularizar pendência ou elevar orçamento se apropriado, depois reexecutar
\`runner-startup\` e somente em seguida o gate \`P60 SAF libc.prx exact-path staging\`.

Nenhum alteração do código P60, do PanVK ou de autenticação do BSF1 resolve um
bloqueio administrativo do Actions. A compilação ARM64 e a distribuição do APK
P60 continuam **bloqueadas até testes executados de fato**.
