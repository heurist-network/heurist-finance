# Shape Reference  - Auto-generated

Generated from `terminal/schemas/*.js`. Do not edit manually.

Run: `node scripts/gen-shapes.js > SHAPES.md`

## MCP Tool → Component Mapping

| MCP Tool | Component | Notes |
|----------|-----------|-------|
| exa.exa_web_search | news | Web news search |
| fred.macro_regime_context | macro | Regime dashboard |
| fred.macro_release_calendar | news | Upcoming releases |
| fred.macro_series_history | chart | Macro time series |
| fred.macro_series_snapshot | gauge, gauges | Single indicator gauges |
| fred.macro_vintage_history | chart | Macro vintage data |
| sec.filing_timeline | filings | Filing history |
| sec.insider_activity | insiders | Insider transactions |
| sec.institutional_holders | holders | Institutional ownership |
| sec.xbrl_fact_trends | chart, waterfall | Financial fact trends |
| yahoo.analyst_snapshot | analyst | Ratings + price targets |
| yahoo.company_fundamentals | earnings | Earnings + financials |
| yahoo.equity_screen | treeMap | Screener results |
| yahoo.fund_snapshot | holders, treeMap | Holdings + fund data |
| yahoo.market_overview | macro | Macro market context |
| yahoo.news_search | news | News feed |
| yahoo.price_history | candlestick, chart | OHLCV time series |
| yahoo.quote_snapshot | quote | Primary price data |
| yahoo.technical_snapshot | rsi, technical | Indicators + gauges |
| yahoo.resolve_symbol |  - | internal, symbol resolution |
| sec.resolve_company |  - | internal, CIK resolution |
| fred.macro_release_context |  - | text/verdict (no dedicated schema) |
| sec.filing_diff |  - | text (no dedicated schema) |
| sec.activist_watch |  - | table (no dedicated schema) |
| exa.exa_scrape_url |  - | text/verdict (no dedicated schema) |

## Agent-Composed Panels

These panels are synthesized by the agent from multiple data sources, not mapped 1:1 from any MCP tool:

- **correlationMatrix**  - computed from multiple price_history calls
- **flowSankey**  - sector flows or XBRL segments
- **heatmap**  - cross-asset/cross-sector comparison
- **verdict**  - synthesized from ALL gathered data

## Component Reference

### analyst

**Shape:** `object with { ratings: {buy, hold, sell}, priceTarget: {current, low, median, high} }`

**MCP Tools:** `yahoo.analyst_snapshot`
**Required:** none

### candlestick

**Shape:** `object with { bars: [{open, high, low, close, volume}] }`

**MCP Tools:** `yahoo.price_history`
**Required:** none

### chart

**Shape:** `object with { values: number[] }`

**MCP Tools:** `yahoo.price_history`, `fred.macro_series_history`, `fred.macro_vintage_history`, `sec.xbrl_fact_trends`
**Required:** `values`

**Defaults:**
- `height`: `6`
- `showAxis`: `true`

**Coercions:** `values`

### correlationMatrix

**MCP Tools:** agent-composed
**Required:** `tickers`, `matrix`

**Defaults:**
- `title`: `CORRELATION MATRIX`

**Coercions:** `tickers`

### earnings

**Shape:** `object with { quarters: [{date, actual, estimate, surprise}] }`

**MCP Tools:** `yahoo.company_fundamentals`
**Required:** none

### filings

**Shape:** `object with { filings: [{date, form, description}] }`

**MCP Tools:** `sec.filing_timeline`
**Required:** none

### flowSankey

**MCP Tools:** agent-composed
**Required:** `nodes`

**Defaults:**
- `flows`: `[]`

**Coercions:** `nodes`, `flows`

### gauge

**Shape:** `object with { value: number }`

**MCP Tools:** `fred.macro_series_snapshot`
**Required:** `value`

**Defaults:**
- `showValue`: `true`
- `showLabel`: `true`

**Coercions:** `value`

### gauges

**Shape:** `object with { items: [{value, label, preset}] }`

**MCP Tools:** `fred.macro_series_snapshot`
**Required:** `items`

**Coercions:** `items`

### heatmap

**Shape:** `object with { rows: [{label, values}], columns: string[] }`

**MCP Tools:** agent-composed
**Required:** none

**Defaults:**
- `colorScale`: `diverging`

### holders

**Shape:** `object with { holders: [{name, shares, percent}] }`

**MCP Tools:** `sec.institutional_holders`, `yahoo.fund_snapshot`
**Required:** none

### insiders

**Shape:** `object with { transactions: [{date, name, type, shares, amount}] }`

**MCP Tools:** `sec.insider_activity`
**Required:** none

### macro

**Shape:** `object with { pillars: [{label, value, direction}] }`

**MCP Tools:** `fred.macro_regime_context`, `yahoo.market_overview`
**Required:** `pillars`

**Coercions:** `pillars`

### news

**Shape:** `object with { items: [{title, source, time, url}] }`

**MCP Tools:** `yahoo.news_search`, `exa.exa_web_search`, `fred.macro_release_calendar`
**Required:** none

**Defaults:**
- `items`: `[]`
- `limit`: `8`

**Coercions:** `items`, `limit`

### quote

**Shape:** `object with { ticker }`

**MCP Tools:** `yahoo.quote_snapshot`
**Required:** `ticker`

**Defaults:**
- `variant`: `full`
- `changePct`: `0`
- `volume`: `0`
- `marketCap`: `0`

**Coercions:** `symbol`

### rsi

**Shape:** `object with { value: number }`

**MCP Tools:** `yahoo.technical_snapshot`
**Required:** `value`

**Defaults:**
- `signals`: `[]`

**Coercions:** `value`, `signals`

### technical

**Shape:** `object with optional { rsi, macd, trend, signals, gauges }`

**MCP Tools:** `yahoo.technical_snapshot`
**Required:** none

**Defaults:**
- `signals`: `[]`
- `gauges`: `[]`

**Coercions:** `signals`, `gauges`, `rsi`, `macd`, `confidence`

### treeMap

**MCP Tools:** `yahoo.fund_snapshot`, `yahoo.equity_screen`
**Required:** `items`

**Defaults:**
- `height`: `10`

**Coercions:** `items`, `height`

### verdict

**Shape:** `object with { thesis, conviction, catalysts, risks, levels, timeframe }`

**MCP Tools:** agent-composed
**Required:** none

**Coercions:** `body`, `signal`

**Warn gates:**
- `thesis`: ⚠ thesis missing  - incomplete analysis
- `conviction`: ⚠ conviction missing  - no directional view
- `catalysts`: ⚠ no catalysts specified
- `risks`: ⚠ no risks specified
- `timeframe`: ⚠ no timeframe specified

### waterfall

**Shape:** `object with { items: [{label, value, previous?}] }`

**MCP Tools:** `sec.xbrl_fact_trends`
**Required:** none

## Key Coercion Patterns

| Pattern | Schema | Details |
|---------|--------|---------|
| symbol → ticker | quote | `data.ticker = val` if ticker missing |
| body → thesis | verdict | v1.0 backwards compat |
| signal → conviction | verdict | BUY→bull, SELL→bear, etc. |
| pillar → label | macro | per-item in pillars array |
| state → stateLabel + value | macro | STATE_MAP lookup |
| String → Number | many | gauge, technical, insiders, holders, etc. |
