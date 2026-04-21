"""
Financial analytics for FRIP properties.

Risk scoring:
    Each factor returns a float in [0.0, 1.0] where 1.0 = maximum risk.
    Composite score is a weighted average scaled to 0-100.

    Thresholds:  < 30 = Low   30-55 = Medium   > 55 = High

Time-Weighted Return:
    Modified Dietz method — industry-standard approximation when daily
    valuations are unavailable. Removes the distortion caused by the
    timing of capital additions.
"""
import math
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# Risk scoring
# ---------------------------------------------------------------------------

def calculate_risk_score(prop, investors, valuations):
    """
    Args:
        prop:        raw MongoDB property document
        investors:   list of investment documents (need 'ownership_share')
        valuations:  list of valuation documents sorted by date (need 'market_value')

    Returns:
        {
            "score":   float 0-100,
            "label":   "Low" | "Medium" | "High",
            "factors": {
                "volatility":    float 0-100,
                "concentration": float 0-100,
                "funding":       float 0-100,
                "cap_rate":      float 0-100,
                "depreciation":  float 0-100,
            }
        }
    """
    vol  = _volatility(valuations)
    conc = _concentration(investors)
    fund = _funding(prop)
    capr = _cap_rate(prop)
    depr = _depreciation(prop)

    composite = (
        0.25 * vol  +
        0.20 * conc +
        0.20 * fund +
        0.20 * capr +
        0.15 * depr
    )

    score = round(composite * 100, 1)

    if score < 30:
        label = "Low"
    elif score <= 55:
        label = "Medium"
    else:
        label = "High"

    return {
        "score": score,
        "label": label,
        "factors": {
            "volatility":    round(vol  * 100, 1),
            "concentration": round(conc * 100, 1),
            "funding":       round(fund * 100, 1),
            "cap_rate":      round(capr * 100, 1),
            "depreciation":  round(depr * 100, 1),
        },
    }


def _volatility(valuations):
    """
    Annualised standard deviation of month-over-month returns.
    Normalised so 10%+ annual vol maps to 1.0.
    Falls back to 0.3 (moderate unknown) with < 2 data points.
    """
    if len(valuations) < 2:
        return 0.3

    values = [v["market_value"] for v in valuations]
    returns = [
        (values[i] - values[i - 1]) / values[i - 1]
        for i in range(1, len(values))
        if values[i - 1] != 0
    ]

    if not returns:
        return 0.3

    mean = sum(returns) / len(returns)
    variance = sum((r - mean) ** 2 for r in returns) / len(returns)
    monthly_std = math.sqrt(variance)
    annual_vol = monthly_std * math.sqrt(12)

    return min(1.0, annual_vol / 0.10)


def _concentration(investors):
    """
    Herfindahl-Hirschman Index of ownership shares.
    HHI = Σ(share²).  Range: (0, 1].  Higher = more concentrated.
    No investors yet = 0.65 (unvalidated, high concentration risk).
    """
    if not investors:
        return 0.65

    hhi = sum(inv["ownership_share"] ** 2 for inv in investors)
    return min(1.0, hhi)


def _funding(prop):
    """Proportion of the property that is unfunded."""
    total  = prop.get("total_value", 0) or 0
    pooled = prop.get("total_pooled_capital", 0) or 0

    if total <= 0:
        return 0.5

    funded_ratio = min(1.0, pooled / total)
    return 1.0 - funded_ratio


def _cap_rate(prop):
    """
    Cap rate = annual rental income / current market value.
    Benchmark 6%. Below benchmark scales to 1.0 risk.
    """
    market_val     = prop.get("current_market_value") or prop.get("total_value") or 0
    monthly_income = prop.get("rental_income", 0) or 0

    if market_val <= 0 or monthly_income <= 0:
        return 0.5

    cap = (monthly_income * 12) / market_val
    benchmark = 0.06

    if cap >= benchmark:
        return 0.0

    return min(1.0, (benchmark - cap) / benchmark)


def _depreciation(prop):
    """
    Negative price movement from purchase value is a direct risk signal.
    -10% or worse maps to 1.0.
    """
    purchase = prop.get("total_value", 0) or 0
    current  = prop.get("current_market_value") or purchase

    if purchase <= 0:
        return 0.0

    change = (current - purchase) / purchase
    if change >= 0:
        return 0.0

    return min(1.0, -change / 0.10)


# ---------------------------------------------------------------------------
# Time-Weighted Return  (Modified Dietz method)
# ---------------------------------------------------------------------------

def compute_twr(investments, current_portfolio_value, total_distributions):
    """
    Approximate Time-Weighted Return using the Modified Dietz method.

    Removes the distortion caused by the *timing* of new capital additions,
    giving a fairer view of investment performance than simple ROI.

    Formula (with BMV = 0, since users start with nothing):
        MDR = (EMV - CF) / Σ(CF_i × W_i)

    Where:
        EMV  = End market value = current holdings value + distributions received
        CF   = Total invested capital (sum of all investments)
        W_i  = Time weight of cash flow i
               = (days_remaining_after_cf_i) / total_period_days

    A weight close to 1.0 means capital was deployed early (had more time
    to work); a weight near 0 means capital was deployed late.

    Returns: percentage float (e.g. 8.3 means 8.3%)
    """
    if not investments:
        return 0.0

    now = datetime.now(timezone.utc)

    sorted_invs = sorted(investments, key=lambda x: x["timestamp"])
    period_start = sorted_invs[0]["timestamp"]

    # Ensure timezone-aware comparison
    if period_start.tzinfo is None:
        period_start = period_start.replace(tzinfo=timezone.utc)

    total_days = max(1, (now - period_start).days)

    emv      = current_portfolio_value + total_distributions
    cf_total = sum(inv["amount"] for inv in investments)

    weighted_cf = 0.0
    for inv in sorted_invs:
        ts = inv["timestamp"]
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        days_in       = max(0, (ts - period_start).days)
        days_remaining = total_days - days_in
        weight         = days_remaining / total_days
        weighted_cf   += inv["amount"] * weight

    if weighted_cf <= 0:
        return 0.0

    return round(((emv - cf_total) / weighted_cf) * 100, 2)
