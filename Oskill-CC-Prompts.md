# oskill Layer 2 — 13 个 CC 实施 Prompt

**用途**：每个元 skill 一个独立 CC prompt，复制粘贴给 Claude Code 即可实施。

**前置依赖**：
- oprim 1.0 已 ship（pip install oprim）
- 31 个 atomic ops 全部可调用

**使用方式**：
- 多 CC instance 并行：每个 instance 跑一个 skill
- 单 CC instance 串行：按组依次跑
- Wiki review：每个 skill 一个独立 PR

**全局规则**（每个 prompt 都隐含）：
1. FULL AUTO MODE - 不中途问问题
2. 单 skill 单 PR - 不混合多 skill
3. 必须含：实现 + 测试 + 文档
4. **不允许 import 任何 oskill.\*（Layer 2 纪律：内部互不调用）**
5. **必须 import oprim.\* 实现核心逻辑（不允许绕过 Layer 1 直接用 scipy）**
6. 测试覆盖率 ≥ 90%
7. 学术对照测试强制
8. Pydantic v2 输入输出

---

## 共用 Prompt Header（每个 prompt 复制时都加上这段）

```
======================================================================
FULL AUTO MODE
- 不要中途问问题
- 自行决策推进
- 失败才停下来报告
- 任务全部完成后只汇报一次
======================================================================

# oskill Layer 2 元 skill 实施任务

## 项目位置
~/projects/oskill/  (独立仓库)

## 必须先读的参考
- ~/projects/oskill/docs/DESIGN.md (如已存在)
- ~/projects/oskill/ADR-062.md (本 Layer 2 spec)
- ~/projects/oprim/docs/INDEX.md (Layer 1 已实现 ops 索引)
- 本任务的 Spec (在下面 "任务" 节)

## 全局红线 (must not violate)
1. **禁止 import oskill.*** (Layer 2 纪律: 内部互不依赖)
2. **必须 import oprim.*** 实现核心逻辑 (不允许绕过 Layer 1 直接用 scipy/sklearn 重新实现已有 op)
3. 仅允许直接 import: oprim, numpy, scipy, pandas, sklearn, statsmodels, pydantic
4. 禁止读环境变量 / 文件 / 网络
5. 禁止修改输入数组 (pure function)
6. 禁止 silent fail (异常输入必须 raise ValueError + 明确消息)

## 输出标准
1. 实现代码: oskill/<group>.py 中追加该 skill
2. 测试: tests/test_<group>.py 中追加该 skill 测试
3. 文档: docs/<group>.md 中追加该 skill 文档
4. 更新 oskill/__init__.py 显式 export

## 测试要求
- 测试覆盖率 ≥ 90% (运行 pytest --cov 验证)
- happy path ≥ 3 用例
- edge cases ≥ 3 用例
- exception cases ≥ 3 用例
- **学术对照测试** (强制, 见每个 skill 具体要求)
- **集成测试**: 验证 skill 正确调用了规定的 oprim (用 mock 验证)
- 性能基准 (如适用)

## PR 提交格式
git checkout -b feat/skills-<skill_name>
git add oskill/<group>.py tests/test_<group>.py docs/<group>.md oskill/__init__.py
git commit -m "feat(skills): add skills.<skill_name>"
git push -u origin feat/skills-<skill_name>

## 完成报告
报告以下内容到 stdout:
- skill 名称
- 调用的 oprim 列表
- 文件路径 (实现 / 测试 / 文档)
- 测试覆盖率 (%)
- 学术对照测试结果
- 性能 benchmark (如适用)
- 已知限制
- PR URL (如已 push)
======================================================================
```

---

# 组 1：性能评估（Performance Evaluation）—— 4 个 prompt

---

## Prompt 1.1: `skills.bootstrap_sharpe`

```
[复用全局 Header]

任务: 实现 oskill.bootstrap_sharpe

调用的 oprim (必须用):
  - oprim.bootstrap_ci  (核心: 重采样 + CI)
  - oprim.sharpe_ratio  (统计量: Sharpe 计算)

数学逻辑:
  1. 从 returns 序列做 N 次 bootstrap 重采样
  2. 每次重采样计算 Sharpe ratio (用 oprim.sharpe_ratio)
  3. 返回 Sharpe 的分布 + 点估计 + CI

API 签名:
  def bootstrap_sharpe(
      returns: np.ndarray,
      *,
      n_bootstrap: int = 1000,
      confidence_level: float = 0.95,
      annualization_factor: float = 252.0,
      method: Literal["percentile", "bca"] = "percentile",
      risk_free_rate: float | np.ndarray = 0.0,
      random_state: int | None = None,
  ) -> dict

实现要求:
1. 内部用 oprim.bootstrap_ci, 传入 statistic=lambda x: oprim.sharpe_ratio(x, ...)
2. 不要自己写 bootstrap 重采样逻辑 (违反"调用 Layer 1"原则)
3. risk_free_rate 标量传给 sharpe_ratio
4. annualization_factor 标量传给 sharpe_ratio
5. method 透传给 bootstrap_ci

返回 schema:
  {
    "sharpe": float,                    # 原始样本 Sharpe (annualized)
    "ci_low": float,
    "ci_high": float,
    "se": float,                        # bootstrap SE
    "samples": np.ndarray,              # n_bootstrap 个 Sharpe 值
    "n_bootstrap": int,
    "confidence_level": float,
    "method": str,
  }

测试要求 (≥ 12 用例):
1. normal(0, 1) returns (mean=0, std=1) → Sharpe ≈ 0, CI 包含 0
2. mean=1%, std=1% returns → Sharpe ≈ √252 ≈ 15.87
3. n_bootstrap=1000 vs 5000 收敛性
4. method='percentile' vs 'bca' 数值差异
5. risk_free_rate 标量测试
6. risk_free_rate 时序 array 测试
7. random_state 可复现
8. annualization_factor=252 vs 365 vs 8760 对比
9. 极小样本 (n=10) raise 或 warning
10. 全 NaN raise
11. **集成测试**: mock oprim.bootstrap_ci, 验证被正确调用一次, 参数正确
12. **集成测试**: mock oprim.sharpe_ratio, 验证 statistic 参数确实是 sharpe_ratio
13. **学术对照**: 与 pyfolio.bootstrap_sharpe (如装) 对比
14. **学术对照**: 与论文 Bailey-López de Prado 2012 公式手算对比

性能要求:
- n_bootstrap=1000, n_returns=252 → < 500ms

文件位置:
- 实现: oskill/performance.py
- 测试: tests/test_performance.py
- 文档: docs/performance.md
```

---

## Prompt 1.2: `skills.psr_dsr`

```
[复用全局 Header]

任务: 实现 oskill.psr_dsr

学术参考:
- Bailey & López de Prado 2012《The Sharpe Ratio Efficient Frontier》(PSR)
- Bailey & López de Prado 2014《The Deflated Sharpe Ratio》(DSR)

调用的 oprim (必须用):
  - oprim.bootstrap_ci      (CI 估计 - 可选)
  - oprim.skew_kurt_robust  (Fisher-Pearson 校正, PSR 必需)
  - oprim.sharpe_ratio      (基础 Sharpe)

数学定义:
  PSR (Probabilistic Sharpe Ratio):
    PSR(SR*) = Φ((SR_observed - SR*) × √(T-1) / √(1 - γ_3 × SR_observed + (γ_4 - 1) / 4 × SR_observed²))
    其中 γ_3 = skewness (bias=False), γ_4 = kurtosis (bias=False, Fisher excess)
  
  DSR (Deflated Sharpe Ratio):
    SR_threshold = E[max{SR_i}] for N tested strategies
    DSR = PSR(SR_threshold)
    
  N_eff (effective sample size for DSR):
    通过 ONC clustering / Hierarchical / Spectral 估计
    本 skill 接受 N_eff 作为参数, 不实现估计 (那是 Layer 1 候选 future)

API 签名:
  def psr_dsr(
      returns: np.ndarray,
      *,
      benchmark_sharpe: float = 0.0,
      n_strategies_tested: int | None = None,  # for DSR (optional)
      n_eff: float | None = None,              # if None, use n_strategies_tested
      annualization_factor: float = 252.0,
      bootstrap_ci: bool = False,              # 可选的 CI 估计
      n_bootstrap: int = 1000,
  ) -> dict

实现要求:
1. PSR 计算:
   a. 用 oprim.sharpe_ratio 计算 Sharpe (annualized=False, raw_sharpe)
   b. 用 oprim.skew_kurt_robust(bias=False) 获取 skew + excess kurt
   c. 套 PSR 公式
2. DSR 计算 (n_strategies_tested 给定时):
   a. 计算 SR_threshold = E[max] 用近似公式: SR_threshold ≈ √(2 ln(N)) - (γ + ln(ln(N))) / (2 √(2 ln(N)))
      (γ = Euler-Mascheroni ≈ 0.5772)
   b. DSR = PSR(SR_threshold)
3. bootstrap_ci=True 时, 用 oprim.bootstrap_ci 给 PSR 提供 CI
4. T < 30 raise warning

返回 schema:
  {
    "psr": float,                       # PSR vs benchmark_sharpe
    "psr_ci": (float, float) | None,    # if bootstrap_ci=True
    "dsr": float | None,                # if n_strategies_tested given
    "sharpe_observed": float,
    "sharpe_observed_annualized": float,
    "skewness": float,
    "excess_kurtosis": float,
    "n_obs": int,
    "n_eff_used": float | None,
    "warnings": list[str],              # T<30, 等
  }

测试要求 (≥ 14 用例):
1. 正态 returns: PSR(0) → Φ(SR × √(T-1) / 1) (skew=0, kurt=0 时简化)
2. mean=0 returns + benchmark=0: PSR ≈ 0.5
3. 高 Sharpe returns + benchmark=0: PSR → 1
4. 负 Sharpe + benchmark=0: PSR → 0
5. 重尾 returns (high kurtosis) → PSR 比正态低
6. 负偏 returns (negative skew) → PSR 比正态低
7. n_strategies_tested=10 → DSR < PSR
8. n_strategies_tested=1000 → DSR << PSR (deflation 效应)
9. n_strategies_tested=1 → DSR ≈ PSR (无 deflation)
10. T<30 warning
11. bootstrap_ci=True 测试 (返回 ci 元组)
12. **集成测试**: mock oprim.skew_kurt_robust, 验证调用 bias=False
13. **集成测试**: mock oprim.sharpe_ratio, 验证调用
14. **学术对照**: Bailey-López de Prado 2012 论文 Table 1 中的具体例子
15. **学术对照**: SR_threshold 公式与论文 Eq. 8 对比

性能要求:
- bootstrap_ci=False: < 50ms
- bootstrap_ci=True (n=1000): < 500ms

文件位置: 同上 (performance.py)
```

---

## Prompt 1.3: `skills.factor_attribution`

```
[复用全局 Header]

任务: 实现 oskill.factor_attribution

学术参考:
- Fama & French 1993《Common risk factors in the returns on stocks and bonds》(3-factor)
- Fama & French 2015《A five-factor asset pricing model》(5-factor)

调用的 oprim (必须用):
  - oprim.beta_alpha_ols    (核心 OLS 回归)
  - oprim.bootstrap_ci      (bootstrap CI 估计)

数学逻辑:
  1. 输入: asset returns + factor returns DataFrame (columns = factor names)
  2. 用 oprim.beta_alpha_ols 跑 OLS: r_asset = α + β_1*F_1 + ... + β_k*F_k + ε
  3. 用 oprim.bootstrap_ci 给 α 和每个 β 估计 CI
  4. 返回完整归因结果

API 签名:
  def factor_attribution(
      asset_returns: np.ndarray,
      factor_returns: pd.DataFrame,
      *,
      bootstrap_ci_enabled: bool = True,
      n_bootstrap: int = 1000,
      confidence_level: float = 0.95,
      standard_errors: Literal["ols", "white", "newey_west"] = "newey_west",
      nw_lags: int | None = None,
      handle_nan: Literal["pairwise", "drop", "raise"] = "drop",
      random_state: int | None = None,
  ) -> dict

实现要求:
1. 先调用 oprim.beta_alpha_ols (一次性) 获得 α, β, R² 等
2. bootstrap_ci_enabled=True 时:
   a. 定义 statistic_fn(joint_data) = lambda data: beta_alpha_ols(...)
      (joint_data 是 paired (asset, factors), bootstrap 整行重采样)
   b. 调用 oprim.bootstrap_ci (paired=True)
   c. 提取 α 的 CI 和每个 β 的 CI
3. NaN 处理透传给 beta_alpha_ols
4. factor_returns columns 名作为 β 的 key

返回 schema:
  {
    "alpha": float,
    "alpha_se": float,
    "alpha_tstat": float,
    "alpha_pvalue": float,
    "alpha_ci": (float, float) | None,
    "betas": dict[str, float],          # {factor_name: beta_value}
    "betas_se": dict[str, float],
    "betas_tstat": dict[str, float],
    "betas_pvalue": dict[str, float],
    "betas_ci": dict[str, (float, float)] | None,
    "r_squared": float,
    "adj_r_squared": float,
    "n_obs": int,
    "factor_names": list[str],
    "standard_errors_method": str,
  }

测试要求 (≥ 13 用例):
1. 完全相关: r_asset = 1.5*F → β=1.5, α=0, R²=1
2. 多因子: r_asset = 0.5 + 1.0*F1 + 0.3*F2 → α/β/R² 都对
3. 独立 r_asset (无因子相关) → α 显著, 所有 β ≈ 0
4. bootstrap_ci_enabled=True 测试 (返回 ci 元组)
5. bootstrap_ci_enabled=False 测试 (ci 为 None)
6. NaN handling 'drop' / 'pairwise' / 'raise'
7. SE 三种模式 ('ols', 'white', 'newey_west')
8. factor_returns DataFrame columns 名保留
9. 单因子 (factor_returns 是 1 列 DataFrame) 测试
10. 5 因子 测试
11. n=2 raise (degenerate)
12. **集成测试**: mock oprim.beta_alpha_ols, 验证参数正确传入
13. **集成测试**: mock oprim.bootstrap_ci, 验证 paired=True
14. **学术对照**: Fama-French 5-factor 经典例子, 用真实月度因子数据 (统计 software 已知答案)
15. **学术对照**: alpha + sum(beta_i * F_i) 与 r_asset 残差检验

性能要求:
- bootstrap_ci=False: < 100ms
- bootstrap_ci=True (n=1000, 5 factor, 252 obs): < 2s

文件位置: 同上 (performance.py)
```

---

## Prompt 1.4: `skills.regime_aware_performance`

```
[复用全局 Header]

任务: 实现 oskill.regime_aware_performance

调用的 oprim (必须用):
  - oprim.regime_filter_data
  - oprim.sharpe_ratio
  - oprim.drawdown_curve
  - oprim.value_at_risk

数学逻辑:
  1. 对每个 regime, 用 regime_filter_data 提取该 regime 内的 returns
  2. 对该子集计算 Sharpe / max drawdown / VaR (用对应 ops)
  3. 输出 per-regime 性能拆解 DataFrame

API 签名:
  def regime_aware_performance(
      returns: pd.Series,
      regime_labels: pd.Series,
      *,
      metrics: list[str] = ["sharpe", "max_drawdown", "var_95", "cumulative_return"],
      annualization_factor: float = 252.0,
      var_confidence: float = 0.95,
      var_method: Literal["historical", "parametric", "cornish_fisher"] = "historical",
      include_overall: bool = True,
  ) -> pd.DataFrame

实现要求:
1. 自动识别所有 regime label
2. 对每个 regime label:
   a. 用 oprim.regime_filter_data 提取该 regime 内的数据
   b. 检查 sample size >= 30, 否则该 regime metric 标 NaN
   c. 计算请求的 metrics
3. metrics 支持的列表:
   - "sharpe": oprim.sharpe_ratio
   - "max_drawdown": oprim.drawdown_curve
   - "var_95" / "var_99": oprim.value_at_risk
   - "cumulative_return": cumulative product
   - "n_obs": sample size
4. include_overall=True 时增加一行 "OVERALL" (全部数据)

返回 schema:
  pd.DataFrame:
    index: regime labels (含 "OVERALL" 如果 include_overall=True)
    columns: metric names
    例:
                sharpe   max_drawdown   var_95   cumulative_return   n_obs
    BULL        2.15     -0.08          -0.02    1.34                120
    BEAR       -1.20     -0.32          -0.08   -0.45                 80
    NEUTRAL     0.50     -0.15          -0.04    0.05                 50
    OVERALL     0.85     -0.32          -0.05    0.94                250

测试要求 (≥ 12 用例):
1. 简单 2 regime 测试: BULL (positive returns) + BEAR (negative returns)
2. 验证 BULL Sharpe > 0, BEAR Sharpe < 0
3. 验证 BULL max_drawdown 比 BEAR 小 (绝对值)
4. metrics=["sharpe"] 仅 Sharpe
5. metrics 全部 4 个
6. include_overall=True 包含 OVERALL row
7. include_overall=False 不包含
8. 某 regime 样本 < 30: 该 regime 该 metric NaN, 不 raise
9. var_method 三种模式
10. data 与 regime_labels index 不对齐 raise
11. **集成测试**: mock 4 个 ops, 验证每个 regime 各调用一次
12. **集成测试**: 验证 regime_filter_data 用 target_regime 参数正确传入
13. **学术对照**: 验证 OVERALL Sharpe 与直接计算 returns Sharpe 一致

性能要求:
- 5 regime × 1000 obs: < 200ms

文件位置: 同上 (performance.py)
```

---

# 组 2：时序验证（Time-Series Validation）—— 3 个 prompt

---

## Prompt 2.1: `skills.walk_forward_optimization`

```
[复用全局 Header]

任务: 实现 oskill.walk_forward_optimization

学术参考: López de Prado 2018《Advances in Financial ML》Ch. 7 / Pardo 1992

调用的 oprim (必须用):
  - oprim.purge_embargo_split  (基础切分)
  - oprim.rolling_window_split (窗口管理)

数学逻辑:
  Walk-Forward Optimization 标准 IS/OOS 滚动:
  
  for each step:
    IS_window = (start, start + is_window)
    OOS_window = (start + is_window, start + is_window + oos_window)
    应用 purge + embargo (避免 label leakage)
    yield {fold_id, is_idx, oos_idx, gap, embargo}
    start += step

API 签名:
  def walk_forward_optimization(
      n_total: int,
      *,
      is_window: int,
      oos_window: int,
      step: int | None = None,
      label_horizon: int = 0,
      embargo_pct: float = 0.01,
      anchored: bool = False,
  ) -> list[dict]

实现要求:
1. step 默认 = oos_window (无重叠的 OOS)
2. anchored=True: IS 始终从 0 开始扩展 (rolling 改 expanding)
3. anchored=False (默认): rolling IS window
4. label_horizon > 0 时, IS 与 OOS 之间需要 purge gap
5. embargo: OOS 边界两侧排除部分 IS (用 oprim.purge_embargo_split 思路)
6. 内部用 oprim.rolling_window_split 生成 candidate windows
7. 内部应用 oprim.purge_embargo_split 的 purge + embargo 逻辑
8. is_window < 30 raise
9. oos_window < 1 raise
10. n_total < is_window + oos_window raise

返回 schema:
  list of dict:
  [
    {
      "fold_id": int,
      "is_start": int,
      "is_end": int (exclusive),
      "is_idx": np.ndarray,
      "oos_start": int,
      "oos_end": int,
      "oos_idx": np.ndarray,
      "purged_count": int,         # purged from IS due to label_horizon
      "embargo_count": int,         # embargoed from IS due to OOS proximity
      "gap_periods": int,
    }
  ]

测试要求 (≥ 12 用例):
1. n=1000, is=200, oos=50, step=50 → 16 个 fold
2. anchored=True 测试 (IS 持续扩展)
3. anchored=False 测试 (IS rolling)
4. step=oos_window (无重叠 OOS)
5. step < oos_window (重叠 OOS)
6. label_horizon=10 → purged_count > 0
7. embargo_pct=0.05 → embargo_count > 0
8. label_horizon=0, embargo_pct=0 → 退化为标准 IS/OOS
9. is_window<30 raise
10. n_total < is + oos raise
11. **集成测试**: mock oprim.rolling_window_split 验证调用
12. **集成测试**: mock oprim.purge_embargo_split 验证 purge/embargo 逻辑透传
13. **学术对照**: López de Prado 2018 Figure 7.4 例子手算 ground truth
14. 验证: 每个 fold 的 IS ∩ OOS = ∅
15. 验证: 每个 fold 的 IS / OOS 时间顺序正确

性能要求:
- n_total=10000: < 100ms

文件位置:
- 实现: oskill/validation.py
- 测试: tests/test_validation.py
- 文档: docs/validation.md
```

---

## Prompt 2.2: `skills.cpcv_pipeline`

```
[复用全局 Header]

任务: 实现 oskill.cpcv_pipeline

学术参考: López de Prado 2018《Advances in Financial ML》Ch. 12 (Combinatorial Purged CV)

调用的 oprim (必须用):
  - oprim.purge_embargo_split    (基础切分)
  - oprim.bootstrap_ci           (path metric CI)
  - oprim.distribution_summary   (path 分布描述)

数学逻辑:
  CPCV 核心: 通过组合多个 fold 作为 test 集, 重组出多个 OOS path
  
  Setup:
    n_folds: 总 fold 数 (e.g. 6)
    n_test_groups: 每次取多少 fold 作为 test (e.g. 2)
    
  Combinatorial:
    C(n_folds, n_test_groups) 个 test combinations
    e.g. C(6, 2) = 15 个 test 组合
    
  Path reconstruction:
    每 fold 在多少个 combinations 中出现 = (n_test_groups / n_folds) × n_combinations
    每个 fold 在不同 combinations 中作为 test 时, 模型不同
    重组成多个连续的"OOS path"
    n_paths = n_folds! / (n_test_groups! × (n_folds - n_test_groups)!) × (n_test_groups / n_folds)

API 签名:
  def cpcv_pipeline(
      n_total: int,
      *,
      n_folds: int = 6,
      n_test_groups: int = 2,
      label_horizon: int = 0,
      embargo_pct: float = 0.01,
      backtest_fn: Callable[[np.ndarray, np.ndarray], np.ndarray] | None = None,
      # backtest_fn(train_idx, test_idx) → returns array
      compute_path_statistics: bool = True,
  ) -> dict

实现要求:
1. 用 oprim.purge_embargo_split 基础切分成 n_folds
2. 生成 C(n_folds, n_test_groups) 个 combinations
3. 每个 combination 应用 purge + embargo (用 Layer 1 ops 的逻辑)
4. backtest_fn=None 时仅返回 splits 不跑 backtest
5. backtest_fn 给定时:
   a. 对每个 combination 跑 backtest_fn(train_idx, test_idx) → returns
   b. 重组多个 OOS paths (按 path reconstruction 算法)
   c. 用 oprim.bootstrap_ci 给 path metric 估 CI
   d. 用 oprim.distribution_summary 描述 path returns 分布
6. label_horizon / embargo_pct 透传

返回 schema:
  splits_only (backtest_fn=None):
    {
      "splits": list of dict,
      "n_combinations": int,
      "n_paths": int,
    }
  
  full_pipeline (backtest_fn given):
    {
      "splits": ...,
      "n_combinations": ...,
      "n_paths": ...,
      "paths_returns": np.ndarray,    # (n_paths, n_total) - some NaN where not in any test
      "paths_sharpe_distribution": dict,  # distribution_summary output
      "paths_sharpe_ci": (float, float),  # bootstrap CI
      "median_sharpe": float,
      "min_sharpe": float,
      "max_sharpe": float,
    }

测试要求 (≥ 13 用例):
1. n=1000, n_folds=6, n_test_groups=2 → 15 combinations
2. n_paths 计算正确 (验证 = C(6,2) × 2/6 = 5)
3. backtest_fn=None 仅返回 splits
4. backtest_fn 给定: 全程序跑通
5. 验证每个 combination train ∩ test = ∅ (考虑 purge + embargo 后)
6. label_horizon=0, embargo_pct=0 → 退化为标准 K-fold combinations
7. n_test_groups=1 → 退化为标准 K-fold (n_combinations = n_folds)
8. n_test_groups >= n_folds raise
9. n_folds < 2 raise
10. **集成测试**: mock oprim.purge_embargo_split 验证调用
11. **集成测试**: mock oprim.bootstrap_ci 验证调用 (compute_path_statistics=True)
12. **集成测试**: mock oprim.distribution_summary 验证调用
13. **学术对照**: López de Prado 2018 Ch. 12 Figure 12.1 路径重组例子
14. 性能: n=10000, n_folds=6, n_test=2, 简单 backtest_fn → < 5s
15. 验证: 不同 path 之间的 returns 不应完全重复

性能要求:
- n=10000, n_folds=6, n_test_groups=2, mock backtest_fn: < 2s

文件位置: 同上 (validation.py)
```

---

## Prompt 2.3: `skills.regime_aware_rolling`

```
[复用全局 Header]

任务: 实现 oskill.regime_aware_rolling

调用的 oprim (必须用):
  - oprim.regime_filter_data
  - oprim.rolling_window_split

数学逻辑:
  在同一 regime 内做 rolling window 计算, 跨 regime 边界时:
    - reset_on_regime_change=True: 重置窗口 (新 regime 开始计算)
    - reset_on_regime_change=False: carry-over (跨 regime 用 forward-fill 或保持上一窗口结果)

API 签名:
  def regime_aware_rolling(
      data: pd.Series,
      regime_labels: pd.Series,
      *,
      window: int,
      stat_fn: Callable[[np.ndarray], float],
      reset_on_regime_change: bool = True,
      min_periods: int | None = None,
  ) -> pd.Series

实现要求:
1. data 与 regime_labels index 必须对齐 (验证)
2. 自动识别所有 regime label
3. 对每个 regime:
   a. 用 oprim.regime_filter_data 提取该 regime 内的数据
   b. 用 oprim.rolling_window_split 生成滚动窗口 (在该 regime 内)
   c. 对每个窗口应用 stat_fn
   d. 把结果按原 index 拼回
4. reset_on_regime_change=True (默认):
   - 每个 regime 内独立 rolling
   - 跨 regime 边界处, regime 切换后前 (window-1) 个 NaN
5. reset_on_regime_change=False:
   - 保持前一 regime 最后窗口的结果 forward-fill
6. min_periods 默认 = window
7. window > 单个 regime 的 sample 时, 该 regime 输出全 NaN (不 raise)

返回 schema:
  pd.Series, 与 input data index 一致:
    每个 timestamp 对应该 regime 内的 rolling stat 值
    (regime 切换边界为 NaN 或 forward-fill)

测试要求 (≥ 12 用例):
1. 单 regime 测试: 退化为标准 rolling
2. 2 regime 切换: 验证切换后 reset
3. reset_on_regime_change=True vs False 对比
4. stat_fn=np.mean 测试
5. stat_fn=np.std 测试
6. stat_fn=lambda x: scipy.stats.skew(x) 测试
7. window > 单 regime sample → 该 regime 全 NaN
8. data 与 regime_labels index 不对齐 raise
9. min_periods 测试
10. 全 1 regime 测试 (退化)
11. **集成测试**: mock 2 个 ops, 验证每个 regime 各调用 regime_filter_data
12. **集成测试**: mock 验证 rolling_window_split 在每个 regime 内被调用
13. 验证 output index 与 input data index 完全一致
14. 验证 reset_on_regime_change=True 时, 跨 regime 边界前 (window-1) 个为 NaN

性能要求:
- 5 regime × 10000 obs, window=20: < 500ms

文件位置: 同上 (validation.py)
```

---

# 组 3：分布与异常（Distribution & Anomaly）—— 3 个 prompt

---

## Prompt 3.1: `skills.distribution_shift_test`

```
[复用全局 Header]

任务: 实现 oskill.distribution_shift_test

调用的 oprim (必须用):
  - oprim.kolmogorov_smirnov_test
  - oprim.wasserstein_distance
  - oprim.symmetric_kl_divergence
  - oprim.distribution_summary

数学逻辑:
  对两个样本同时跑多种分布漂移检验, 用投票决定是否 shift:
  
  - KS test: H0 = 同分布, p < alpha 拒绝 (即 shift detected)
  - Wasserstein: 距离值, 阈值 (e.g. > 0.1 × max(std)) 视为 shift
  - JSD: 距离值, 阈值 (e.g. > 0.1) 视为 shift
  
  voting:
    "majority": 多数派
    "any": 任一方法 detect 即 detect
    "all": 全部方法 detect 才 detect

API 签名:
  def distribution_shift_test(
      sample_a: np.ndarray,
      sample_b: np.ndarray,
      *,
      methods: list[Literal["ks", "wasserstein", "jsd"]] = ["ks", "wasserstein", "jsd"],
      voting: Literal["majority", "any", "all"] = "majority",
      alpha: float = 0.05,
      wasserstein_threshold_ratio: float = 0.1,  # 0.1 × max(std)
      jsd_threshold: float = 0.1,
      compute_summary: bool = True,
  ) -> dict

实现要求:
1. 对每个 method 跑对应 oprim:
   - "ks" → oprim.kolmogorov_smirnov_test
   - "wasserstein" → oprim.wasserstein_distance (1D mode)
   - "jsd" → oprim.symmetric_kl_divergence (method='jensen_shannon')
     需要先把 sample_a / sample_b 转成 histogram
2. 每个 method 输出 detected: bool
3. 用 voting 聚合最终决定
4. compute_summary=True 时, 用 oprim.distribution_summary 描述两个 sample
5. samples 长度 < 20 raise warning

返回 schema:
  {
    "shift_detected": bool,                # 最终决定
    "voting": str,
    "votes": dict[str, bool],              # {method_name: detected}
    "individual_tests": dict[str, dict],   # 每个 method 的详细结果
    "sample_a_summary": dict | None,
    "sample_b_summary": dict | None,
    "n_a": int,
    "n_b": int,
  }

测试要求 (≥ 12 用例):
1. 同分布 (两个 N(0,1) sample): shift_detected=False
2. 完全不同分布 (N(0,1) vs N(5,1)): shift_detected=True
3. 微小差异 (N(0,1) vs N(0.1,1)): 大 sample 时 detected, 小 sample 不 detected
4. methods=["ks"] 仅 KS
5. methods=["ks", "wasserstein"] 部分
6. voting="any" (一个 detect 即 detect)
7. voting="all" (全部 detect 才 detect)
8. voting="majority" (≥ 半数 detect)
9. compute_summary=True/False
10. **集成测试**: mock 3 个 oprim, 验证每个 method 调用对应 op
11. **集成测试**: mock oprim.distribution_summary, 验证 compute_summary=True 时调用
12. **学术对照**: KS test 与 scipy.stats.ks_2samp 输出一致 (透传)
13. 长度 < 20 warning
14. samples 含 NaN 处理 (透传给 oprim)

性能要求:
- n=1000 vs n=1000, all methods: < 200ms

文件位置:
- 实现: oskill/distribution.py
- 测试: tests/test_distribution.py
- 文档: docs/distribution.md
```

---

## Prompt 3.2: `skills.detect_outliers_robust`

```
[复用全局 Header]

任务: 实现 oskill.detect_outliers_robust

调用的 oprim (必须用):
  - oprim.zscore_normalize
  - oprim.distribution_summary

数学逻辑:
  用多种方法检测 outliers, 投票决定:
  
  - "zscore": |z| > threshold (默认 3.0)
  - "iqr": x < Q1 - 1.5*IQR or x > Q3 + 1.5*IQR
  - "mahalanobis": 多变量 Mahalanobis 距离 > threshold
    (本 skill 简化: 仅 1D 时与 zscore 等价, 多 D 时用 sklearn.covariance)
  
  voting:
    "any": 任一方法标 outlier 即标
    "majority": 多数派
    "all": 全部标才标

API 签名:
  def detect_outliers_robust(
      data: np.ndarray,
      *,
      methods: list[Literal["zscore", "iqr", "mahalanobis"]] = ["zscore", "iqr"],
      voting: Literal["majority", "any", "all"] = "any",
      thresholds: dict | None = None,
      return_diagnostics: bool = True,
  ) -> dict

实现要求:
1. data 1D: zscore + iqr 即可, mahalanobis 退化为 zscore
2. data 2D (n, d): 全部三种方法可用
3. zscore method:
   a. 用 oprim.zscore_normalize 计算 z (method='fixed')
   b. |z| > thresholds["zscore"] (默认 3.0) 标 outlier
4. iqr method:
   a. 用 oprim.distribution_summary 获取 Q1 (0.25), Q3 (0.75)
   b. IQR = Q3 - Q1
   c. outlier: x < Q1 - factor*IQR 或 x > Q3 + factor*IQR (factor 默认 1.5)
5. mahalanobis: 1D 等价 zscore, 2D 用 sklearn.covariance.MinCovDet (本 skill 不抽 mahalanobis 为 op, 直接 sklearn)
6. thresholds 默认: {"zscore": 3.0, "iqr_factor": 1.5, "mahalanobis": 3.0}
7. voting 聚合各 method 的 mask

返回 schema:
  {
    "outlier_mask": np.ndarray (bool, same shape as data first axis),
    "n_outliers": int,
    "n_total": int,
    "voting": str,
    "votes": dict[str, np.ndarray],     # {method: mask}
    "thresholds_used": dict,
    "diagnostics": dict | None,         # if return_diagnostics, 含每个 method 的统计
  }

测试要求 (≥ 12 用例):
1. 1D 简单测试: [1,2,3,4,5,100] → outlier_mask 最后一个为 True
2. 1D 全正常数据 → 无 outlier
3. 自定义 thresholds={"zscore": 2.0} 测试 (更严格)
4. voting="any" / "majority" / "all" 行为对比
5. methods=["zscore"] 仅 zscore
6. methods 全部三种 (1D 时 mahalanobis 等价 zscore)
7. 2D 数据测试 (n=100, d=3, 含 5 个 outlier)
8. 含 NaN 处理 (NaN 不算 outlier 但占位)
9. 全 NaN raise
10. 单元素 raise
11. **集成测试**: mock oprim.zscore_normalize, 验证 method='fixed' 调用
12. **集成测试**: mock oprim.distribution_summary, 验证 quantiles=[0.25, 0.75] 包含
13. 学术对照: 1D zscore method 与 scipy.stats.zscore + threshold 对比
14. 学术对照: 1D iqr method 与 numpy.percentile(25) / (75) 公式对比

性能要求:
- 1D, n=10000: < 100ms
- 2D, n=10000, d=10: < 500ms

文件位置: 同上 (distribution.py)
```

---

## Prompt 3.3: `skills.bootstrap_distribution`

```
[复用全局 Header]

任务: 实现 oskill.bootstrap_distribution

调用的 oprim (必须用):
  - oprim.bootstrap_ci
  - oprim.distribution_summary
  - oprim.kde_density (可选)

数学逻辑:
  对任意统计量做 bootstrap, 返回完整分布 + 描述 + 可选 density:
  
  1. 用 bootstrap_ci 重采样 + 计算 statistic, 拿到 samples
  2. 用 distribution_summary 描述 samples 分布
  3. include_density=True 时, 用 kde_density 估计平滑分布

API 签名:
  def bootstrap_distribution(
      data: np.ndarray,
      statistic: Callable[[np.ndarray], float],
      *,
      n_bootstrap: int = 1000,
      confidence_level: float = 0.95,
      method: Literal["percentile", "bca", "basic"] = "percentile",
      include_density: bool = False,
      density_n_points: int = 200,
      random_state: int | None = None,
  ) -> dict

实现要求:
1. 调用 oprim.bootstrap_ci(data, statistic, ...) 拿到 samples
2. 调用 oprim.distribution_summary(samples) 描述
3. include_density=True:
   a. 调用 oprim.kde_density(samples, n_points=density_n_points)
4. point_estimate = statistic(data) (原始样本)

返回 schema:
  {
    "point_estimate": float,
    "samples": np.ndarray,                    # n_bootstrap 长度
    "ci_low": float,
    "ci_high": float,
    "confidence_level": float,
    "method": str,
    "summary": dict,                          # distribution_summary output
    "density": dict | None,                   # kde_density output if include_density
    "n_bootstrap": int,
    "n_obs": int,
  }

测试要求 (≥ 11 用例):
1. statistic=np.mean, normal data: point_estimate ≈ 0
2. statistic=np.median, normal data: 中位数估计
3. statistic=lambda x: x.std() 测试
4. include_density=True 测试 (返回 density dict)
5. include_density=False 测试 (density=None)
6. method='percentile' / 'bca' / 'basic' 对比
7. random_state 可复现
8. samples shape == (n_bootstrap,)
9. summary schema 完整
10. **集成测试**: mock oprim.bootstrap_ci, 验证 statistic 透传
11. **集成测试**: mock oprim.distribution_summary, 验证调用 samples
12. **集成测试**: mock oprim.kde_density, include_density=True 时调用
13. **学术对照**: point_estimate = statistic(data) 直接验证
14. **学术对照**: samples mean 应接近 point_estimate (大 n_bootstrap 时)

性能要求:
- n_bootstrap=1000, n=1000, np.mean: < 500ms

文件位置: 同上 (distribution.py)
```

---

# 组 4：相似度检索（Similarity Retrieval）—— 2 个 prompt

---

## Prompt 4.1: `skills.historical_analogy_search`

```
[复用全局 Header]

任务: 实现 oskill.historical_analogy_search

调用的 oprim (必须用):
  - oprim.dtw_distance
  - oprim.wasserstein_distance
  - oprim.cosine_similarity_batch
  - oprim.euclidean_distance_matrix

数学逻辑:
  Ensemble 检索: 用多种距离 metric 各自排名, 然后融合:
  
  1. 对每个 historical sample, 用每个 method 计算 distance 到 query
  2. 每个 method 内部 rank
  3. ensemble:
     - "mean_rank": rank 的平均
     - "borda": Borda count
     - "weighted": 用户给定权重加权
  4. 取 top_k

API 签名:
  def historical_analogy_search(
      query: np.ndarray,                       # 1D or 2D (T, d)
      historical_db: list[np.ndarray] | np.ndarray,
      *,
      methods: list[Literal["dtw", "wasserstein", "cosine", "euclidean"]] = ["dtw", "wasserstein"],
      ensemble: Literal["mean_rank", "borda", "weighted"] = "mean_rank",
      weights: dict[str, float] | None = None,  # for "weighted"
      top_k: int = 10,
      sakoe_chiba_band: int | None = None,      # for dtw
  ) -> list[dict]

实现要求:
1. historical_db 可以是 list of array (variable length, dtw 友好) 或 stacked 2D array
2. 对每个 historical sample, 应用所有 methods:
   - "dtw": oprim.dtw_distance (sakoe_chiba_band 透传)
   - "wasserstein": oprim.wasserstein_distance
   - "cosine": oprim.cosine_similarity_batch (取负值变 distance: 1 - sim)
   - "euclidean": oprim.euclidean_distance_matrix
3. 每个 method 内部 rank (低 distance = 高 rank)
4. ensemble:
   - "mean_rank": rank 平均 (1 = top)
   - "borda": Borda count (n - rank, 高 = top)
   - "weighted": Σ w_method × rank_method
5. weighted 必须给 weights, 不给 raise
6. cosine 对 length 不同的 series 不可用 (raise warning)
7. dtw 性能优化: 用 sakoe_chiba_band 减少计算

返回 schema:
  list of dict (top_k 个):
  [
    {
      "rank": int,                         # 1 = top
      "historical_idx": int,               # index in historical_db
      "ensemble_score": float,             # mean_rank / borda / weighted score
      "distances_per_method": dict,        # {method_name: distance}
      "ranks_per_method": dict,            # {method_name: rank}
    },
    ...
  ]

测试要求 (≥ 12 用例):
1. query 与 historical_db[i] 完全相同: 该 i 是 rank 1
2. 简单 historical_db (5 个 series), top_k=3
3. methods=["dtw"] 仅 DTW
4. methods 全部 4 个
5. ensemble="mean_rank" 测试
6. ensemble="borda" 测试
7. ensemble="weighted" 测试
8. ensemble="weighted" 不给 weights raise
9. weights 不全 → 默认 1
10. **集成测试**: mock 4 个 oprim, 每个 method 调用对应 op
11. **集成测试**: 验证 dtw_distance 用 sakoe_chiba_band 调用
12. **集成测试**: 验证 cosine_similarity 转换为 distance (1 - sim)
13. cosine on variable-length raise warning
14. top_k > len(historical_db): top_k 调整到 len, 不 raise

性能要求:
- query length=60, historical_db 含 100 series, methods=["dtw", "wasserstein"], top_k=10:
  < 5s (DTW 是主要瓶颈)

文件位置:
- 实现: oskill/similarity.py
- 测试: tests/test_similarity.py
- 文档: docs/similarity.md
```

---

## Prompt 4.2: `skills.regime_transition_analysis`

```
[复用全局 Header]

任务: 实现 oskill.regime_transition_analysis

调用的 oprim (必须用):
  - oprim.regime_transition_matrix
  - oprim.regime_filter_data
  - oprim.distribution_summary

数学逻辑:
  完整 regime transition 分析:
  
  1. 用 regime_transition_matrix 估计转移矩阵 + 稳态
  2. 计算 expected holding period (per regime): 1 / (1 - p_stay)
  3. 计算 half-life: ln(0.5) / ln(p_stay)
  4. 如果给 data, 用 regime_filter_data 提取每 regime 内 data, 用 distribution_summary 描述

API 签名:
  def regime_transition_analysis(
      regime_labels: pd.Series,
      *,
      data_per_regime: pd.Series | None = None,  # 可选: 给 data 时计算 per-regime stats
      include_duration_stats: bool = True,
      min_duration: int = 1,
  ) -> dict

实现要求:
1. 调用 oprim.regime_transition_matrix 获取 transition_matrix + stationary_distribution + duration_distribution
2. 计算 expected_holding_period (per regime):
   regime_i 的 self-transition prob = transition_matrix[i, i]
   expected_holding = 1 / (1 - p_stay) (几何分布期望)
3. 计算 half_life (per regime):
   half_life = ln(0.5) / ln(p_stay)
   (该 regime 的 stay probability 衰减一半需要的步数)
4. data_per_regime 给定:
   a. 对每个 regime, 用 oprim.regime_filter_data 提取该 regime 内的 data
   b. 用 oprim.distribution_summary 描述
5. min_duration 透传给 regime_transition_matrix

返回 schema:
  {
    "transition_matrix": pd.DataFrame,
    "stationary_distribution": pd.Series,
    "n_transitions": int,
    "duration_distribution": dict | None,         # if include_duration_stats
    "expected_holding_period": dict,              # {regime: float}
    "half_life": dict,                            # {regime: float}
    "data_summary_per_regime": dict | None,       # {regime: distribution_summary} if data_per_regime given
  }

测试要求 (≥ 11 用例):
1. 完美 sticky regime (transition matrix diag=1): expected_holding → ∞, half_life → ∞
2. 完美随机 regime (transition matrix uniform): expected_holding 短
3. 简单 2 regime alternating: 测试 expected_holding ≈ 1
4. data_per_regime 给定: data_summary_per_regime 不为 None
5. data_per_regime=None: data_summary_per_regime=None
6. include_duration_stats=False: duration_distribution=None
7. min_duration=2 过滤短 stay
8. 单 regime raise (无 transition)
9. NaN regime 处理
10. **集成测试**: mock oprim.regime_transition_matrix
11. **集成测试**: data_per_regime 给定时, mock regime_filter_data + distribution_summary 各调用 N 次 (N = regime 数)
12. 学术对照: 简单 markov chain 手算 expected_holding_period
13. 学术对照: half_life 公式 ln(0.5)/ln(p_stay) 验证

性能要求:
- 5 regime, 10000 obs: < 500ms

文件位置: 同上 (similarity.py)
```

---

# 组 5：预测质量（Prediction Quality）—— 1 个 prompt

---

## Prompt 5.1: `skills.calibration_analysis`

```
[复用全局 Header]

任务: 实现 oskill.calibration_analysis

学术参考:
- Murphy 1973《A New Vector Partition of the Probability Score》
- Naeini, Cooper, Hauskrecht 2015《Obtaining Well Calibrated Probabilities Using Bayesian Binning》(ECE)

调用的 oprim (必须用):
  - oprim.brier_score_decomposed
  - oprim.percentile_rank
  - oprim.bayes_beta_update

数学逻辑:
  完整 calibration 分析:
  
  1. Brier Score 三分量: 用 brier_score_decomposed 直接拿
  2. Reliability diagram:
     a. 用 percentile_rank 把 predictions 分箱 (默认等频或等宽)
     b. 每 bin 计算 (avg_prediction, avg_outcome, n)
     c. 用 bayes_beta_update 给每 bin 的 outcome rate 估 posterior CI
  3. ECE (Expected Calibration Error):
     ECE = Σ_k (n_k / N) × |avg_prediction_k - avg_outcome_k|
  4. MCE (Maximum Calibration Error):
     MCE = max_k |avg_prediction_k - avg_outcome_k|

API 签名:
  def calibration_analysis(
      predictions: np.ndarray,
      outcomes: np.ndarray,
      *,
      n_bins: int = 10,
      binning: Literal["equal_width", "equal_freq"] = "equal_width",
      include_reliability_diagram: bool = True,
      include_bayesian_ci: bool = True,
      prior_alpha: float = 1.0,
      prior_beta: float = 1.0,
  ) -> dict

实现要求:
1. 调用 oprim.brier_score_decomposed (传入 n_bins, binning 参数)
2. include_reliability_diagram=True 时:
   a. 用 oprim.percentile_rank 帮助分箱 (equal_freq 时)
      或 numpy.linspace 直接分箱 (equal_width)
   b. per-bin: avg_prediction, avg_outcome, n_bin
3. include_bayesian_ci=True:
   每 bin 用 oprim.bayes_beta_update(prior_alpha, prior_beta, successes=sum(outcomes_in_bin), failures=n-sum):
     - 拿 ci_95
4. ECE = Σ (n_k / N) × |p_k - o_k|
5. MCE = max |p_k - o_k|
6. predictions 范围 [0, 1] 检查
7. outcomes 范围 {0, 1} 检查
8. 长度不一致 raise

返回 schema:
  {
    "brier_score": float,
    "reliability": float,
    "resolution": float,
    "uncertainty": float,
    "skill_score": float,
    "ece": float,
    "mce": float,
    "n_bins": int,
    "binning": str,
    "reliability_diagram": pd.DataFrame | None,
    # columns: bin_id, bin_min, bin_max, n, avg_prediction, avg_outcome, ci_low, ci_high
    "n_obs": int,
  }

测试要求 (≥ 13 用例):
1. 完美校准 (predictions == outcomes): brier=0, ece=0, mce=0
2. 完全不校准 (predictions=0.5, outcomes random): ECE 大
3. 全 0.5 prediction, 50% outcome: reliability=0, resolution=0
4. binning="equal_width" vs "equal_freq" 对比
5. include_reliability_diagram=True 测试
6. include_reliability_diagram=False 测试
7. include_bayesian_ci=True 测试 (CI 列存在)
8. include_bayesian_ci=False 测试 (CI 列 None)
9. predictions 范围外 raise
10. outcomes 非 0/1 raise
11. predictions 和 outcomes 长度不同 raise
12. **集成测试**: mock 3 个 oprim, 验证调用
13. **集成测试**: include_bayesian_ci=True 时, bayes_beta_update 被调用 n_bins 次
14. **学术对照**: ECE 公式与 Naeini 2015 论文对照
15. **学术对照**: brier 三分量恒等式 BS = R - Res + U 验证

性能要求:
- n=10000, n_bins=10, full calibration: < 500ms

文件位置:
- 实现: oskill/prediction.py
- 测试: tests/test_prediction.py
- 文档: docs/prediction.md
```

---

# 总结

```yaml
total_prompts: 13
组_1_performance: 4 个 prompt
组_2_validation: 3 个 prompt
组_3_distribution: 3 个 prompt
组_4_similarity: 2 个 prompt
组_5_prediction: 1 个 prompt

dependency_graph_validation:
  每个 prompt 显式列出调用的 oprim
  没有任何 prompt 调用其它 oskill (Layer 2 纪律)
  每个 prompt 必须用 oprim 实现核心逻辑 (不允许绕过)

usage:
  - 每个 skill 一个 prompt, 复制粘贴给 CC
  - 推荐多 CC instance 并行 (3-5 个)
  - 每个 prompt 跑 1.5-3 天完成 (含测试 + 文档 + 集成测试)
  - 总周期: 3-4 周 (并行)

prerequisites:
  oprim 1.0 已 ship, pip install oprim 可用
  31 个 atomic ops 全部 import 可用

next_steps:
  1. Wiki 创建 oskill 仓库基础结构
  2. 设置 CI/CD (lint + test + coverage gate + Layer 2 纪律 lint)
  3. 分发 13 prompt 给 CC instance
  4. 每完成 1 PR Wiki review + merge
  5. oskill 1.0 ship
```

---

## 关键纪律提醒（每个 prompt 都强调）

```yaml
layer_2_disciplines_summary:

  discipline_1_must_use_oprim:
    每个 skill 内部必须 import oprim.* 实现核心逻辑
    不允许绕过 Layer 1 直接用 scipy.stats.bootstrap 等
    PR review 关注点: 是否走了 Layer 1 还是绕过

  discipline_2_no_layer_2_internal_calls:
    oskill 内部 skill 互不 import
    PR lint check 强制

  discipline_3_neutral_design:
    API 设计基于"金融分析通用需求"
    文档示例用通用场景, 不绑特定项目
    任何项目都可调用

  discipline_4_test_includes_integration:
    单元测试 + 集成测试 (用 mock 验证调用了规定的 oprim)
    集成测试必须验证: 调用了哪些 ops, 参数透传是否正确
```

---

**END OF 13 CC IMPLEMENTATION PROMPTS**
