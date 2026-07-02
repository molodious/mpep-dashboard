# Revenue Forecast Model

The sales dashboard forecasts revenue from the current month through December. It is recalculated whenever `build_sales_dashboard.py` runs, including after the existing `new-order` GitHub dispatch.

## Data sources

- 2020–2025: monthly totals supplied by Dan and stored in `FORECAST_HISTORY`.
- 2026 actuals: the dashboard's existing Stripe, Thinkific, BTC/webhook, manual, and verified historical product data. These remain the authoritative current-year values.
- The model does not alter order ingestion, deduplication, transaction tables, or existing product totals.

## Baseline calculation

For each remaining calendar month:

1. Take that same month from the five latest prior years.
2. Weight the observations exponentially with a 1.25-year half-life. The latest year has the most influence; older years still contribute progressively less.
3. Calculate current-year momentum from completed months versus the same months in the prior-year supplied history.
4. Damp momentum by taking the square root of the year-over-year ratio and cap its effect to the range 0.80–1.20.
5. For the current partial month, blend its annualized run rate with the seasonal estimate according to how much of the month has elapsed. The estimate can never be lower than revenue already collected.

## Scenarios

- Conservative: baseline × 0.80.
- Baseline: recency-weighted seasonal estimate with damped momentum.
- Optimistic: baseline × 1.20.

The full-year cards combine completed current-year actuals with the forecasts for the current and remaining months. Completed months retain their product-level stacked bars; forecast months use a baseline bar with conservative and optimistic whiskers.

## Update behavior

The forecast is build-time dynamic, not hardcoded into `sales.html`. A new sale triggers the existing dashboard GitHub Action, which fetches current data and regenerates the forecast. Future-month momentum changes primarily as months close; the current-month estimate responds gradually as new revenue arrives and more of the month elapses.
