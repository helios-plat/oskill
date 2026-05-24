# SELF_CHECK_P6_B4.md — 2 扩展 oskill MINOR

## Commit

`cdd925e` — `feat(p6-b4): script_writer template_prompt + storyboard_planner motion`

## 变更

| 模块 | 变更 | 向后兼容 |
|------|------|----------|
| `script_writer` | `template_prompt: str \| None = None` 已存在,新增测试验证注入 | ✅ None = 旧行为 |
| `storyboard_planner` | LLM prompt 加 `motion` 字段请求 | ✅ Shot.motion 默认 None |
| `_schemas.Shot` | `motion: str \| None = None` 已存在 | ✅ 缺省 None |

## 5 红线验收

| 红线 | 结果 |
|------|------|
| 覆盖率 ≥90% | ✅ **100%** (combined with existing tests) |
| 新增测试 ≥3 each | ✅ **4 + 4 = 8 new tests** |
| Pydantic + docstring + Raises | ✅ 无变更,已满足 |
| mypy --strict + ruff 0 | ✅ Success: no issues in 3 files |
| 现有测试不破坏 | ✅ **65 existing tests still pass** |

## 测试结果

```
73 passed in 2.81s (8 new + 65 existing)
Coverage: 100% (script_writer + storyboard_planner)
```
