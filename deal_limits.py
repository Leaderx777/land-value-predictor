"""User-editable screening rules, separate from prices and available cash."""
from dataclasses import asdict, dataclass
import math

PROPERTY_TYPES = ("Land", "House", "Condo / townhouse", "Multifamily", "Manufactured / mobile home", "Commercial", "Other real estate")
STATES = tuple('AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY'.split())


@dataclass(frozen=True)
class Limits:
    max_purchase_price: float | None = None
    max_upfront_cash: float | None = None
    max_total_cash: float | None = None
    max_monthly_outflow: float | None = None
    min_roi_pct: float | None = 30.
    min_profit: float | None = None
    max_holding_months: int | None = None
    states: tuple[str, ...] | None = None
    property_types: tuple[str, ...] | None = None
    financing: str = "Either"

    def __post_init__(self):
        for name in ['max_purchase_price', 'max_upfront_cash', 'max_total_cash', 'max_monthly_outflow',
                     'min_roi_pct', 'min_profit', 'max_holding_months']:
            value = getattr(self, name)
            if value is not None and (not math.isfinite(value) or value < 0):
                raise ValueError(f"{name} must be nonnegative or disabled")
        if self.max_holding_months is not None and int(self.max_holding_months) != self.max_holding_months:
            raise ValueError("Holding-month limit must be a whole month")
        if self.states is not None and not set(self.states).issubset(STATES):
            raise ValueError("Unknown state")
        if self.property_types is not None and not set(self.property_types).issubset(PROPERTY_TYPES):
            raise ValueError("Unknown property type")
        if self.financing not in {"Either", "Cash purchase", "Seller-financed purchase"}:
            raise ValueError("Unknown purchase financing filter")

    def to_dict(self):
        return asdict(self)

    def check(self, deal, result, *, state, property_type):
        upfront = deal.purchase_down + deal.buying_costs + deal.improvements
        # Regular monthly payment plus holding, excluding the separately disclosed balloon/payoff.
        monthly = result['regular_purchase_payment'] + deal.monthly_holding
        rows = []
        for label, actual, limit, minimum in [
            ("Purchase price", deal.purchase_price, self.max_purchase_price, False),
            ("Upfront cash", upfront, self.max_upfront_cash, False),
            ("Peak deal cash", max(upfront, result['peak_funding']), self.max_total_cash, False),
            ("Regular monthly payment + holding", monthly, self.max_monthly_outflow, False),
            ("Net project ROI (%)", result['project_roi_pct'], self.min_roi_pct, True),
            ("Net profit", result['profit'], self.min_profit, True),
            ("Holding months", deal.resale_month, self.max_holding_months, False),
        ]:
            if limit is not None:
                rows.append(dict(rule=label, actual=actual, limit=limit,
                                 passed=bool(actual >= limit if minimum else actual <= limit)))
        if self.states is not None:
            rows.append(dict(rule="State", actual=state, limit=", ".join(self.states) or "No states selected", passed=state in self.states))
        if self.property_types is not None:
            rows.append(dict(rule="Property type", actual=property_type, limit=", ".join(self.property_types) or "No types selected", passed=property_type in self.property_types))
        if self.financing != "Either":
            actual = "Seller-financed purchase" if deal.purchase_down < deal.purchase_price else "Cash purchase"
            rows.append(dict(rule="Purchase financing", actual=actual, limit=self.financing, passed=actual == self.financing))
        return rows
