# oskill

Composite financial analysis workflows built on [oprim](https://github.com/helios-plat/oprim) atomic operations.

## Installation

```bash
pip install oskill
```

## Quick Start

```python
from oskill import bootstrap_sharpe, cpcv_pipeline, calibration_analysis
import numpy as np

returns = np.random.normal(0.001, 0.02, 252)
result = bootstrap_sharpe(returns, n_bootstrap=1000)
print(f"Sharpe: {result['sharpe']:.2f} [{result['ci_low']:.2f}, {result['ci_high']:.2f}]")
```

## Skills (13)

| Group | Skills |
|-------|--------|
| Performance | `bootstrap_sharpe`, `psr_dsr`, `factor_attribution`, `regime_aware_performance` |
| Validation | `walk_forward_optimization`, `cpcv_pipeline`, `regime_aware_rolling` |
| Distribution | `distribution_shift_test`, `detect_outliers_robust`, `bootstrap_distribution` |
| Similarity | `historical_analogy_search`, `regime_transition_analysis` |
| Prediction | `calibration_analysis` |

## Architecture

```
oskill (Layer 2) → oprim (Layer 1) → numpy/scipy/pandas (Layer 0)
```

## License

MIT
