# Shape Reference — Auto-generated

Generated from `terminal/schemas/*.js`. Do not edit manually.

Run: `npx vite-node scripts/gen-shapes.js > SHAPES.md`

## analyst

**Required:** none

## chart

**Required:** `values`

**Defaults:**
- `height`: `6`
- `showAxis`: `true`

**Coercions:** `values`

## correlationMatrix

**Required:** `tickers`, `matrix`

**Defaults:**
- `title`: `CORRELATION MATRIX`

**Coercions:** `tickers`

## flowSankey

**Required:** `nodes`

**Defaults:**
- `flows`: `[]`

**Coercions:** `nodes`, `flows`

## gauge

**Required:** `value`

**Defaults:**
- `showValue`: `true`
- `showLabel`: `true`

**Coercions:** `value`

## gauges

**Required:** `items`

**Coercions:** `items`

## macro

**Required:** `pillars`

**Coercions:** `pillars`

## news

**Required:** none

**Defaults:**
- `items`: `[]`
- `limit`: `8`

**Coercions:** `items`, `limit`

## quote

**Required:** `ticker`

**Defaults:**
- `variant`: `full`
- `changePct`: `0`
- `volume`: `0`
- `marketCap`: `0`

**Coercions:** `symbol`

## rsi

**Required:** `value`

**Defaults:**
- `signals`: `[]`

**Coercions:** `value`, `signals`

## technical

**Required:** none

**Defaults:**
- `signals`: `[]`
- `gauges`: `[]`

**Coercions:** `signals`, `gauges`, `rsi`, `macd`, `confidence`

## treeMap

**Required:** `items`

**Defaults:**
- `height`: `10`

**Coercions:** `items`, `height`

## verdict

**Required:** none

**Coercions:** `body`, `signal`

**Warn gates:**
- `thesis`: ⚠ thesis missing — incomplete analysis
- `conviction`: ⚠ conviction missing — no directional view
- `catalysts`: ⚠ no catalysts specified
- `risks`: ⚠ no risks specified
- `timeframe`: ⚠ no timeframe specified
