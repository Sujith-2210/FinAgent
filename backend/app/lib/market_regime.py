"""
Market Regime Detection Library.

Ported from AgentQuant reference project.
Uses VIX and Momentum heuristics to classify current market state.
"""

from typing import Dict, Any, Optional

def detect_regime(market_context: Dict[str, Any]) -> str:
    """
    Detects the market regime based on simple heuristics.

    Args:
        market_context: Dict with keys 'vix_close' (float) and 'momentum_63d' (float).

    Returns:
        str: The detected market regime label.
    """
    # Defaults
    vix = market_context.get('vix_close', 20.0)
    mom63d = market_context.get('momentum_63d', 0.0)

    # Heuristic rules (from AgentQuant)
    if vix > 30:
        if mom63d < -0.10:
            return "Crisis-Bear"
        else:
            return "HighVol-Uncertain"
    elif vix > 20 and vix <= 30:
        if mom63d > 0.05:
            return "MidVol-Bull"
        elif mom63d < -0.05:
            return "MidVol-Bear"
        else:
            return "MidVol-MeanRevert"
    else: # VIX <= 20
        if mom63d > 0.05:
            return "LowVol-Bull"
        else:
            return "LowVol-MeanRevert"
