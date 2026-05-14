"""Factor analysis submodule."""
from oskill.factor.quantile_returns import factor_quantile_returns
from oskill.factor.ic import factor_ic
from oskill.factor.fama_french import fama_french_5_factor_model
from oskill.factor.carhart import carhart_4_factor_model
from oskill.factor.barra import barra_style_decomposition
from oskill.factor.neutralization import factor_neutralization

__all__ = [
    "factor_quantile_returns",
    "factor_ic",
    "fama_french_5_factor_model",
    "carhart_4_factor_model",
    "barra_style_decomposition",
    "factor_neutralization",
]
