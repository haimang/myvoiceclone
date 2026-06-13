# myvoiceclone first-test action-plan index

> 来源基线：[proposed-planning.md](../../eval/first-test/proposed-planning.md)
> reference-anchor：[reference-anchor.md](../../eval/first-test/reference-anchor.md)
> 输出目录：`myvoiceclone/docs/plan/first-test/`
> 路径说明：本目录按用户本轮要求输出至 `docs/plan/first-test/`，取代 proposed 派生图中的 `docs/action-plan/first-test/` 目标路径。
> 状态：`draft`

## 执行顺序

```text
FT1 -> FT2 -> FT3 -> FT5 -> FT7 -> FT8
       ├──────────────▶ FT4 adapter/contract spike 可在 FT2 后并行；formal pass 依赖 FT3 artifact
       └──────────────▶ FT6 API skeleton 可在 FT1 后并行；成功语义依赖 FT2/FT4/FT5
```

## Phase action-plans

| Phase | 文件 | 主要目标 | 依赖 | 状态 |
|-------|------|----------|------|------|
| FT1 | [FT1-preflight.md](FT1-preflight.md) | 准入收敛、命令/config/job 入口统一 | proposed/reference | Draft |
| FT2 | [FT2-schema-observability.md](FT2-schema-observability.md) | schema drift、job events、trace 与 mock/real separation | FT1 | Draft |
| FT3 | [FT3-real-preprocess.md](FT3-real-preprocess.md) | 真实音频预处理与 dataset/reference artifact contract | FT1/FT2 | Draft |
| FT4 | [FT4-real-inference.md](FT4-real-inference.md) | 真实推理 substrate、model manifest、artifact metadata | spike: FT2；formal pass: FT3 artifact | Draft |
| FT5 | [FT5-real-evaluation.md](FT5-real-evaluation.md) | smoke/proxy/manual 真实评估与 release gate | FT4 | Draft |
| FT6 | [FT6-fastapi-e2e.md](FT6-fastapi-e2e.md) | FastAPI run/upload/start/status/report/trace surface | skeleton: FT1；success semantics: FT2/FT4/FT5 | Draft |
| FT7 | [FT7-live-capstone.md](FT7-live-capstone.md) | live marker、capstone、evidence pack 与 validator | FT1-FT6 | Draft |
| FT8 | [FT8-closure-deferred.md](FT8-closure-deferred.md) | closure、deferred reconciliation、final input pack | FT7 | Draft |

## 共同硬闸

- 每份 AP 必须消费 `proposed-planning.md` 的对应 FT 工作项与测试项。
- 每份 AP 必须绑定 `reference-anchor.md` 的业务轴、反例和 trust rules。
- `MOCK_ADAPTERS=false` 的真实路径禁止 silent fallback 到 mock。
- live/gpu/slow tests 必须 gated，缺依赖时 skip with reason，并计入 evidence denominator。
- 目标硬闸：真实音频、模型和 run evidence 不进入 repo；FT1 必须修 config/env/API artifact root 后，真实 run 统一落 `/mnt/usb/workspace/myvoiceresearch` 路径族。
- FT7 未产生真实 capstone evidence 时，FT8 不得 full-close。
