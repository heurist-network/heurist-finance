# Trades

One row per fill. A receipt image, if any, goes under `receipts/` as `YYYY-MM-DD-<ticker>-<n>.png`. `plan` is the plan file stem; `level` is the level `id` from that plan's frontmatter, or `unplanned` when no plan level covers the fill.

| Date | Broker | Ticker | Side | Qty | Price | Fee | Plan | Level | Note |
|---|---|---|---|---|---|---|---|---|---|
