# myvoiceclone first-build action-plan index

> 来源基线：[final-execution-plan.md](../../eval/first-build/final-execution-plan.md)
> 输出目录：`myvoiceclone/docs/plan/first-build/`
> 状态：`draft`

## 执行顺序

```text
P0 -> P1 -> P2 -> P3 -> P4 -> P5 -> P6 -> P7 -> P8
              └──────────────▶ P8 docs/scripts 可并行预备
```

## Phase action-plans

| Phase | 文件 | 主要目标 | 依赖 |
|-------|------|----------|------|
| P0 | [00-scope-architecture.md](00-scope-architecture.md) | scope、分层、测试分类冻结 | final plan |
| P1 | [01-storage-vec0-skeleton.md](01-storage-vec0-skeleton.md) | repo skeleton、SQLite、vec0、artifact store | P0 |
| P2 | [02-preprocess-pipeline.md](02-preprocess-pipeline.md) | ingest/diarize/slice/clean/transcribe/score | P1 |
| P3 | [03-corpus-dataset-freeze.md](03-corpus-dataset-freeze.md) | review、dedupe、split、manifest、corpus report | P2 |
| P4 | [04-quick-baselines.md](04-quick-baselines.md) | RVC/TTS quick baseline、eval pack、long-train gate | P3 |
| P5 | [05-long-train-sovits.md](05-long-train-sovits.md) | So-VITS-SVC adapter、feature cache、resume、registry | P3/P4 |
| P6 | [06-eval-inference-api.md](06-eval-inference-api.md) | FastAPI、CLI、inference、eval、audit trace | P4；P5 后补长训评估 |
| P7 | [07-security-governance-retrofit.md](07-security-governance-retrofit.md) | policy feature flag、release gate、synthetic metadata | P6 |
| P8 | [08-ops-handoff.md](08-ops-handoff.md) | README、scripts、Docker、capstone、handoff | P8-prep after P0/P1；P8-closeout after P7 |

## 共同硬闸

- 每份 AP 必须消费 `final-execution-plan.md` 的对应 phase 台账、文件定位矩阵、冻结 Q 和测试要求。
- 每份 AP 必须包含 §7 内置锚区、§8 测试台账、§10 收口映射。
- 默认测试不得依赖真实音频、真实模型、GPU、网络。
- P0-P6 不实现授权/安全拦截；P7 后置启用治理。
