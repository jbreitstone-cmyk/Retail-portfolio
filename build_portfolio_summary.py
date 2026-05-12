#!/usr/bin/env python3
"""Build a portfolio summary page rolling up all 6 properties.

Reads each property's analysis/valuation.json and config.json + GL distributions,
then renders portfolio.html with totals and a per-property table.
"""
from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent

PROJECTS_ROOT = Path("/Users/jasonbreitstone/Documents/Claude/Projects")

# (project folder name, display name, city, slug, headline tenants)
PROPERTIES = [
    {
        "folder": "68-100 Old riverhead Road ",
        "name": "68-100 Old Riverhead Rd",
        "city": "Westhampton Beach, NY",
        "slug": "68-100",
        "appfolio_ids": "179",
        "headline": "Hamptons retail — multi-unit renovation almost complete; Hamptons Endoscopy, Gluckmans, BJJ signed",
        "units": 15, "sqft": 25433,
    },
    {
        "folder": "Commack Road Combined",
        "name": "193 + 231 Commack Rd",
        "city": "Commack, NY",
        "slug": "commack",
        "appfolio_ids": "172 + 173",
        "headline": "Steady-state Long Island retail — 95% leased; ETS Bagels + Atelier + Guac Time step-ups in flight",
        "units": 21, "sqft": 29200,
    },
    {
        "folder": "350 e Main St Patchogue ",
        "name": "350 E Main St",
        "city": "Patchogue, NY",
        "slug": "patchogue",
        "appfolio_ids": "142",
        "headline": "Patchogue Main Street mixed-use retail",
        "units": 15, "sqft": 27338,
    },
    {
        "folder": "476 Montauk Highway",
        "name": "476 Montauk Highway",
        "city": "East Hampton, NY",
        "slug": "476-montauk",
        "appfolio_ids": "182",
        "headline": "East Hampton retail — 100% leased; Chen's Garden + EH Vacuum repricing 7/1/2026",
        "units": 5, "sqft": 10423,
    },
    {
        "folder": "Amagansett Combined",
        "name": "136 Main St + 11 Indian Wells",
        "city": "Amagansett, NY",
        "slug": "amagansett",
        "appfolio_ids": "109 + 114",
        "headline": "Amagansett village mixed-use — Sett Coffee, Cosmic Studios, La Parlour anchor",
        "units": 13, "sqft": 17371,
    },
    {
        "folder": "107 E Mount Pleasant",
        "name": "107 E Mount Pleasant Ave",
        "city": "Livingston, NJ",
        "slug": "107-mt-pleasant",
        "appfolio_ids": "112",
        "headline": "Livingston retail + car wash + 13 office suites — 100% leased",
        "units": 19, "sqft": 27065,
    },
]


def _read_json(p: Path) -> dict:
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text())
    except Exception:
        return {}


def _gl_account_sum(gl: Path, prefix: str, sign: str = "credit_minus_debit") -> float:
    """Sum GL account by prefix. sign='credit_minus_debit' for liability/equity
    (mortgage, owner contribution); 'debit_minus_credit' for asset/expense
    (distribution = positive debits)."""
    if not gl.exists():
        return 0.0
    total = 0.0
    with gl.open() as fh:
        for r in csv.DictReader(fh):
            nm = (r.get("account_name") or "").strip()
            if not nm.startswith(prefix):
                continue
            debit = float(r.get("debit") or 0)
            credit = float(r.get("credit") or 0)
            if sign == "credit_minus_debit":
                total += credit - debit
            else:
                total += debit - credit
    return total


def fetch(p: dict) -> dict:
    proj = PROJECTS_ROOT / p["folder"]
    val = _read_json(proj / "analysis" / "valuation.json")
    cfg = _read_json(proj / "config.json")
    gl = proj / "normalized" / "general_ledger.csv"

    equity = float(cfg.get("owner_equity_invested") or 0)
    if equity == 0:
        equity = _gl_account_sum(gl, "3000")
    distributions = _gl_account_sum(gl, "3250", sign="debit_minus_credit")

    mortgage = val.get("mortgage_principal_outstanding") or 0
    value_mid = val.get("value_mid") or 0
    value_low = val.get("value_low") or 0
    value_high = val.get("value_high") or 0
    cap_mid = val.get("cap_rates", {}).get("mid", 0)
    cap_low = val.get("cap_rates", {}).get("low", 0)
    cap_high = val.get("cap_rates", {}).get("high", 0)
    t12_noi = val.get("t12_noi") or 0
    t12_rev = val.get("t12_revenue") or 0
    stab_noi = val.get("stabilized_noi") or 0
    stab_rev = val.get("stabilized_revenue") or 0

    implied_equity = value_mid - mortgage if value_mid else 0
    dpi = (distributions / equity) if equity > 0 else 0
    rvpi = (implied_equity / equity) if equity > 0 else 0
    tvpi = dpi + rvpi
    unrealized = implied_equity + distributions - equity

    return {
        **p,
        "equity": equity,
        "distributions": distributions,
        "mortgage": mortgage,
        "value_low": value_low,
        "value_mid": value_mid,
        "value_high": value_high,
        "cap_low": cap_low * 100,
        "cap_mid": cap_mid * 100,
        "cap_high": cap_high * 100,
        "t12_noi": t12_noi,
        "t12_revenue": t12_rev,
        "stab_noi": stab_noi,
        "stab_revenue": stab_rev,
        "implied_equity": implied_equity,
        "dpi": dpi, "rvpi": rvpi, "tvpi": tvpi,
        "unrealized": unrealized,
    }


def m(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return "—"
    if f == 0:
        return "—"
    if abs(f) >= 1_000_000:
        return f"${f/1_000_000:,.2f}M"
    if abs(f) >= 10_000:
        return f"${f/1_000:,.0f}K"
    return f"${f:,.0f}"


def m_full(v):
    try:
        return f"${float(v):,.0f}"
    except (TypeError, ValueError):
        return "—"


def main():
    rows = [fetch(p) for p in PROPERTIES]

    # Portfolio totals
    total_equity = sum(r["equity"] for r in rows)
    total_mortgage = sum(r["mortgage"] for r in rows)
    total_value_mid = sum(r["value_mid"] for r in rows)
    total_value_low = sum(r["value_low"] for r in rows)
    total_value_high = sum(r["value_high"] for r in rows)
    total_distributions = sum(r["distributions"] for r in rows)
    total_t12_noi = sum(r["t12_noi"] for r in rows)
    total_t12_rev = sum(r["t12_revenue"] for r in rows)
    total_stab_noi = sum(r["stab_noi"] for r in rows)
    total_stab_rev = sum(r["stab_revenue"] for r in rows)
    total_implied_equity = total_value_mid - total_mortgage
    total_units = sum(r["units"] for r in rows)
    total_sqft = sum(r["sqft"] for r in rows)
    total_unrealized = total_implied_equity + total_distributions - total_equity
    portfolio_tvpi = (total_implied_equity + total_distributions) / total_equity if total_equity else 0
    portfolio_dpi = total_distributions / total_equity if total_equity else 0
    portfolio_rvpi = total_implied_equity / total_equity if total_equity else 0

    # Build HTML
    today = date.today().strftime("%B %d, %Y")

    property_rows = []
    for r in rows:
        property_rows.append(f"""
<tr class="border-b border-slate-200 hover:bg-slate-50">
  <td class="py-3 px-3">
    <a href="/{r['slug']}/" class="font-semibold text-blue-700 hover:underline">{r['name']}</a>
    <div class="text-xs text-slate-500">{r['city']} · AppFolio {r['appfolio_ids']}</div>
  </td>
  <td class="py-3 px-3 text-right text-xs text-slate-600">{r['units']} units<br>{r['sqft']:,} SF</td>
  <td class="py-3 px-3 text-right font-mono">{m(r['t12_revenue'])}</td>
  <td class="py-3 px-3 text-right font-mono font-semibold">{m(r['t12_noi'])}</td>
  <td class="py-3 px-3 text-right font-mono">{m(r['stab_revenue'])}</td>
  <td class="py-3 px-3 text-right font-mono font-bold text-emerald-700">{m(r['stab_noi'])}</td>
  <td class="py-3 px-3 text-right text-xs">{r['cap_low']:.2f}% – {r['cap_high']:.2f}%</td>
  <td class="py-3 px-3 text-right font-mono font-bold text-blue-700">{m(r['value_mid'])}</td>
  <td class="py-3 px-3 text-right font-mono text-slate-600">({m(r['mortgage'])})</td>
  <td class="py-3 px-3 text-right font-mono">{m(r['equity'])}</td>
  <td class="py-3 px-3 text-right font-mono text-emerald-700">{m(r['distributions']) if r['distributions'] else '—'}</td>
  <td class="py-3 px-3 text-right font-bold text-emerald-700">{r['tvpi']:.2f}x</td>
</tr>""")

    property_rows_html = "".join(property_rows)

    totals_row = f"""
<tr class="bg-slate-100 font-bold border-t-2 border-slate-400">
  <td class="py-3 px-3">PORTFOLIO TOTAL</td>
  <td class="py-3 px-3 text-right text-xs">{total_units} units<br>{total_sqft:,} SF</td>
  <td class="py-3 px-3 text-right font-mono">{m(total_t12_rev)}</td>
  <td class="py-3 px-3 text-right font-mono">{m(total_t12_noi)}</td>
  <td class="py-3 px-3 text-right font-mono">{m(total_stab_rev)}</td>
  <td class="py-3 px-3 text-right font-mono text-emerald-700">{m(total_stab_noi)}</td>
  <td class="py-3 px-3 text-right text-xs">—</td>
  <td class="py-3 px-3 text-right font-mono text-blue-700">{m(total_value_mid)}</td>
  <td class="py-3 px-3 text-right font-mono">({m(total_mortgage)})</td>
  <td class="py-3 px-3 text-right font-mono">{m(total_equity)}</td>
  <td class="py-3 px-3 text-right font-mono text-emerald-700">{m(total_distributions)}</td>
  <td class="py-3 px-3 text-right text-emerald-700">{portfolio_tvpi:.2f}x</td>
</tr>"""

    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>HREA Retail Portfolio — Summary</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Helvetica Neue', Arial, sans-serif; }}
    .kpi {{ background: linear-gradient(135deg, #f8fafc 0%, #f0f9ff 100%); }}
  </style>
</head>
<body class="bg-slate-50 text-slate-900">
  <div class="max-w-7xl mx-auto p-6">
    <header class="mb-8 pb-6 border-b-2 border-slate-300">
      <h1 class="text-4xl font-bold text-slate-900">HREA Retail Portfolio — Summary</h1>
      <p class="text-slate-500 mt-2">Hildreth Real Estate Advisors · 6 commercial properties across Long Island &amp; Northern NJ · {today}</p>
      <p class="mt-3"><a href="/" class="text-blue-700 hover:underline">← Back to property tiles</a></p>
    </header>

    <!-- Portfolio KPI tiles -->
    <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
      <div class="kpi p-5 rounded-xl shadow-sm border border-slate-200">
        <div class="text-xs uppercase text-slate-500 font-semibold tracking-wide">Stabilized NOI</div>
        <div class="text-3xl font-bold text-emerald-700 mt-1">{m(total_stab_noi)}</div>
        <div class="text-xs text-slate-500 mt-1">T12 actual: {m(total_t12_noi)}</div>
      </div>
      <div class="kpi p-5 rounded-xl shadow-sm border border-slate-200">
        <div class="text-xs uppercase text-slate-500 font-semibold tracking-wide">Mid Valuation</div>
        <div class="text-3xl font-bold text-blue-700 mt-1">{m(total_value_mid)}</div>
        <div class="text-xs text-slate-500 mt-1">Range: {m(total_value_low)} – {m(total_value_high)}</div>
      </div>
      <div class="kpi p-5 rounded-xl shadow-sm border border-slate-200">
        <div class="text-xs uppercase text-slate-500 font-semibold tracking-wide">Implied Equity (mid)</div>
        <div class="text-3xl font-bold text-blue-700 mt-1">{m(total_implied_equity)}</div>
        <div class="text-xs text-slate-500 mt-1">Net of {m(total_mortgage)} in mortgages</div>
      </div>
      <div class="kpi p-5 rounded-xl shadow-sm border border-slate-200">
        <div class="text-xs uppercase text-slate-500 font-semibold tracking-wide">Portfolio TVPI (MOIC)</div>
        <div class="text-3xl font-bold text-emerald-700 mt-1">{portfolio_tvpi:.2f}x</div>
        <div class="text-xs text-slate-500 mt-1">DPI {portfolio_dpi:.2f}x + RVPI {portfolio_rvpi:.2f}x</div>
      </div>
    </div>

    <!-- Sources of capital -->
    <div class="bg-white rounded-xl shadow-sm border border-slate-200 p-6 mb-8">
      <h2 class="text-lg font-bold mb-4">Sources of Capital · Returns to Date</h2>
      <div class="grid grid-cols-2 md:grid-cols-4 gap-6 text-sm">
        <div>
          <div class="text-xs uppercase text-slate-500 font-semibold">Equity Contributed</div>
          <div class="text-2xl font-bold mt-1">{m(total_equity)}</div>
        </div>
        <div>
          <div class="text-xs uppercase text-slate-500 font-semibold">1st Mortgage Balances</div>
          <div class="text-2xl font-bold mt-1">{m(total_mortgage)}</div>
        </div>
        <div>
          <div class="text-xs uppercase text-slate-500 font-semibold">Total All-In Basis</div>
          <div class="text-2xl font-bold mt-1">{m(total_equity + total_mortgage)}</div>
        </div>
        <div>
          <div class="text-xs uppercase text-slate-500 font-semibold">Distributions Paid</div>
          <div class="text-2xl font-bold mt-1 text-emerald-700">{m(total_distributions)}</div>
        </div>
      </div>
      <div class="mt-5 pt-5 border-t border-slate-200 grid grid-cols-3 gap-6 text-sm">
        <div>
          <div class="text-xs uppercase text-slate-500 font-semibold">Unrealized Gain (vs. all-in)</div>
          <div class="text-xl font-bold mt-1 text-emerald-700">{m(total_unrealized)}</div>
          <div class="text-xs text-slate-500 mt-1">Implied equity {m(total_implied_equity)} + distributions {m(total_distributions)} − equity {m(total_equity)}</div>
        </div>
        <div>
          <div class="text-xs uppercase text-slate-500 font-semibold">Stabilized NOI / Total Basis</div>
          <div class="text-xl font-bold mt-1">{(total_stab_noi/(total_equity+total_mortgage)*100):.2f}%</div>
          <div class="text-xs text-slate-500 mt-1">Yield-on-cost (stabilized basis)</div>
        </div>
        <div>
          <div class="text-xs uppercase text-slate-500 font-semibold">Properties · Units · SF</div>
          <div class="text-xl font-bold mt-1">{len(rows)} props · {total_units} units · {total_sqft:,} SF</div>
        </div>
      </div>
    </div>

    <!-- Per-property table -->
    <div class="bg-white rounded-xl shadow-sm border border-slate-200 p-6 mb-8 overflow-x-auto">
      <h2 class="text-lg font-bold mb-4">Per-Property Detail</h2>
      <table class="w-full text-sm">
        <thead class="bg-slate-100 text-slate-600">
          <tr class="border-b-2 border-slate-300">
            <th class="py-2 px-3 text-left">Property</th>
            <th class="py-2 px-3 text-right">Size</th>
            <th class="py-2 px-3 text-right">T12 Revenue</th>
            <th class="py-2 px-3 text-right">T12 NOI</th>
            <th class="py-2 px-3 text-right">Stab. Revenue</th>
            <th class="py-2 px-3 text-right">Stab. NOI</th>
            <th class="py-2 px-3 text-right">Cap Range</th>
            <th class="py-2 px-3 text-right">Mid Value</th>
            <th class="py-2 px-3 text-right">Mortgage</th>
            <th class="py-2 px-3 text-right">Equity In</th>
            <th class="py-2 px-3 text-right">Distrib.</th>
            <th class="py-2 px-3 text-right">TVPI</th>
          </tr>
        </thead>
        <tbody>
          {property_rows_html}
          {totals_row}
        </tbody>
      </table>
    </div>

    <!-- Property highlights cards -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
"""

    for r in rows:
        gain = r["implied_equity"] + r["distributions"] - r["equity"]
        gain_pct = (gain / r["equity"] * 100) if r["equity"] else 0
        html += f"""
      <a href="/{r['slug']}/" class="bg-white rounded-xl shadow-sm border border-slate-200 p-5 hover:shadow-md transition-shadow">
        <div class="flex justify-between items-start mb-2">
          <div>
            <h3 class="text-lg font-bold text-slate-900">{r['name']}</h3>
            <p class="text-xs text-slate-500">{r['city']}</p>
          </div>
          <div class="text-right">
            <div class="text-2xl font-bold text-emerald-700">{r['tvpi']:.2f}x</div>
            <div class="text-xs text-slate-500">TVPI</div>
          </div>
        </div>
        <p class="text-xs text-slate-600 mb-3">{r['headline']}</p>
        <div class="grid grid-cols-3 gap-2 text-xs">
          <div class="bg-slate-50 p-2 rounded">
            <div class="text-slate-500">Stab. NOI</div>
            <div class="font-bold">{m(r['stab_noi'])}</div>
          </div>
          <div class="bg-slate-50 p-2 rounded">
            <div class="text-slate-500">Value</div>
            <div class="font-bold">{m(r['value_mid'])}</div>
          </div>
          <div class="bg-slate-50 p-2 rounded">
            <div class="text-slate-500">Equity</div>
            <div class="font-bold">{m(r['implied_equity'])}</div>
          </div>
        </div>
      </a>"""

    html += f"""
    </div>

    <footer class="text-center text-xs text-slate-400 mt-12 pb-8 border-t border-slate-200 pt-6">
      <p>Each property has its own dashboard, investor PDF, and live data feed from AppFolio.</p>
      <p class="mt-2">Valuations are internal management estimates based on stabilized NOI and prevailing market cap rates. Numbers are illustrative, not appraisals.</p>
      <p class="mt-2 text-slate-300">Generated {today}</p>
    </footer>
  </div>
</body>
</html>
"""

    out = REPO / "portfolio.html"
    out.write_text(html)
    print(f"Wrote {out}")
    print()
    print("=== Portfolio totals ===")
    print(f"  Stabilized NOI:    {m(total_stab_noi)}")
    print(f"  Mid Valuation:     {m(total_value_mid)}")
    print(f"  Mortgages:         {m(total_mortgage)}")
    print(f"  Equity Contrib'd:  {m(total_equity)}")
    print(f"  Distributions:     {m(total_distributions)}")
    print(f"  Implied Equity:    {m(total_implied_equity)}")
    print(f"  TVPI:              {portfolio_tvpi:.2f}x  (DPI {portfolio_dpi:.2f}x + RVPI {portfolio_rvpi:.2f}x)")
    print(f"  Yield-on-cost:     {(total_stab_noi/(total_equity+total_mortgage)*100):.2f}%")


if __name__ == "__main__":
    main()
