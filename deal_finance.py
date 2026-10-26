"""Deterministic, pre-tax deal cash flows; no model-estimated resale values."""

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class Note:
    principal: float
    annual_rate: float
    amortization_months: int
    balloon_month: int = 0  # 0 means fully amortizing

    def schedule(self):
        if not math.isfinite(self.principal) or self.principal < 0:
            raise ValueError("Principal must be finite and nonnegative")
        if self.principal == 0:
            return []
        if not math.isfinite(self.annual_rate) or not 0 <= self.annual_rate <= 1:
            raise ValueError("Annual rate must be between 0 and 100 percent")
        if type(self.amortization_months) is not int or not 1 <= self.amortization_months <= 600:
            raise ValueError("Amortization must be 1–600 whole months")
        if type(self.balloon_month) is not int or not 0 <= self.balloon_month <= self.amortization_months:
            raise ValueError("Balloon must be 0 or no later than amortization month")
        monthly = self.annual_rate / 12
        payment = (self.principal / self.amortization_months if monthly == 0 else
                   self.principal * monthly / -math.expm1(-self.amortization_months * math.log1p(monthly)))
        payment = round(payment, 2)
        balance = round(self.principal, 2)
        rows = []
        for month in range(1, (self.balloon_month or self.amortization_months) + 1):
            interest = round(balance * monthly, 2)
            regular = min(payment, round(balance + interest, 2))
            principal_paid = round(regular - interest, 2)
            balance = round(balance - principal_paid, 2)
            balloon = balance if month == (self.balloon_month or self.amortization_months) else 0.
            balance = round(balance - balloon, 2)
            rows.append(dict(month=month, payment=round(regular + balloon, 2), regular_payment=regular,
                             interest=interest, principal=round(principal_paid + balloon, 2),
                             balloon=balloon, balance=balance))
        return rows


@dataclass(frozen=True)
class Deal:
    purchase_price: float
    purchase_down: float
    purchase_rate: float
    purchase_term: int
    purchase_balloon: int
    sale_price: float
    resale_month: int
    buying_costs: float = 0
    improvements: float = 0
    selling_cost_pct: float = 0
    selling_cost_fixed: float = 0
    monthly_holding: float = 0

    def analyze(self):
        for name in ['purchase_price', 'purchase_down', 'sale_price', 'buying_costs',
                     'improvements', 'selling_cost_fixed', 'monthly_holding']:
            value = getattr(self, name)
            if not math.isfinite(value) or value < 0:
                raise ValueError(f"{name} must be finite and nonnegative")
        if self.purchase_price <= 0 or self.sale_price <= 0:
            raise ValueError("Enter positive purchase and resale prices")
        if self.purchase_down > self.purchase_price:
            raise ValueError("Purchase down payment cannot exceed purchase price")
        if type(self.resale_month) is not int or not 0 <= self.resale_month <= 600:
            raise ValueError("Resale month must be a whole month from 0 to 600")
        if not math.isfinite(self.selling_cost_pct) or not 0 <= self.selling_cost_pct <= 1:
            raise ValueError("Selling cost percentage must be between 0 and 100 percent")
        debt = Note(self.purchase_price - self.purchase_down, self.purchase_rate,
                    self.purchase_term, self.purchase_balloon).schedule()
        flows = [dict(month=i, sale_receipts=0., purchase_debt=0., costs=0.)
                 for i in range(self.resale_month + 1)]
        flows[0]['costs'] = self.purchase_down + self.buying_costs + self.improvements
        interest = 0.
        for row in debt:
            if row['month'] > self.resale_month:
                break
            flows[row['month']]['purchase_debt'] += row['payment']
            interest += row['interest']
        payoff = (debt[self.resale_month - 1]['balance'] if self.resale_month else
                  self.purchase_price - self.purchase_down) if self.resale_month < len(debt) else 0.
        flows[-1]['purchase_debt'] += payoff
        flows[-1]['sale_receipts'] = self.sale_price
        selling_cost = self.sale_price * self.selling_cost_pct + self.selling_cost_fixed
        flows[-1]['costs'] += selling_cost
        for month in range(1, self.resale_month + 1):
            flows[month]['costs'] += self.monthly_holding
        cumulative = 0.
        for row in flows:
            row['net'] = round(row['sale_receipts'] - row['purchase_debt'] - row['costs'], 2)
            cumulative = round(cumulative + row['net'], 2)
            row['cumulative'] = cumulative
        total_cost = (self.purchase_price + self.buying_costs + self.improvements + selling_cost
                      + interest + self.monthly_holding * self.resale_month)
        equity_contributions = sum(max(0, -r['net']) for r in flows)
        denominator = 1 - self.selling_cost_pct
        break_even = ((total_cost - self.sale_price * self.selling_cost_pct) / denominator
                      if denominator > 0 else None)
        return dict(profit=cumulative, total_cost=round(total_cost, 2),
                    project_roi_pct=cumulative / total_cost * 100,
                    cash_roi_pct=cumulative / equity_contributions * 100 if equity_contributions else None,
                    cash_contributions=round(equity_contributions, 2),
                    peak_funding=max(0., -min(r['cumulative'] for r in flows)),
                    break_even_resale=round(break_even, 2) if break_even is not None else None,
                    purchase_payoff_at_resale=payoff,
                    regular_purchase_payment=debt[0]['regular_payment'] if debt else 0.,
                    purchase_balloon=debt[-1]['balloon'] if debt else 0.,
                    balloon_before_resale=bool(self.purchase_balloon and self.purchase_balloon < self.resale_month and debt),
                    purchase_interest_paid=round(interest, 2), flows=flows, purchase_schedule=debt)
