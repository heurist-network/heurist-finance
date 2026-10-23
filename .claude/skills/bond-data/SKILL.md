---
name: bond-data
description: "How to get corporate bond data here: terms at issue (SEC term sheets), current price/yield per bond (TradingView's FINRA TRACE feed), Treasuries and spread indexes (FRED), corporate-bond market breadth (FINRA API), CDS (news only), and what each can't do. Use when asked how a company's bonds are trading, whether its spreads are widening, or to compare a bond now vs at issue. Trigger: `use bond skill`."
---

# Bond data

There is no single bond feed. Combine the five sources below. Run from the repo root.

## 1. Terms at issue: SEC term sheets (primary)

The coupon, yield, spread and size at sale are in the pricing term sheet, form FWP (sometimes a 424B2 instead).

```bash
# list FWPs (10-digit zero-padded CIK; META=1326801, GOOGL=1652044, AMZN=1018724, MSFT=789019, ORCL=1341439)
curl -sS -H "User-Agent: research you@example.com" https://data.sec.gov/submissions/CIK0001326801.json \
 | python3 -c "import json,sys;d=json.load(sys.stdin)['filings']['recent'];[print(d['filingDate'][i],d['accessionNumber'][i],d['primaryDocument'][i]) for i,f in enumerate(d['form']) if f in('FWP','424B2')]"
# read one: URL = https://www.sec.gov/Archives/edgar/data/<cik>/<accession without dashes>/<primaryDocument>
p=$(uv run python scripts/hf_tool.py document "<url>" | python3 -c "import json,sys;print(json.load(sys.stdin)['full_text_path'])")
tr -s ' \n' ' ' < "$p" | grep -oE "(Trade Date|Yield to Maturity|Spread to Benchmark Treasury|Aggregate Principal Amount)[^|]{0,40}\|[^|]{0,20}\|[^|]{0,500}"
```

## 2. Price and yield now: TradingView bond scanner (FINRA TRACE, 4h delay)

Keep the rows where `exchange` is `FINRA`. Their prices are TRACE trades, delayed 4 hours (`update_mode` = `delayed_streaming_14400`). `last_bar_update_time` is a Unix timestamp. Other exchanges are European listings of the same bond.

```bash
curl -sS -X POST https://scanner.tradingview.com/bond/scan -H "Content-Type: application/json" -H "Origin: https://www.tradingview.com" \
 -d '{"filter":[{"left":"bond_issuer","operation":"match","right":"Oracle"},{"left":"exchange","operation":"equal","right":"FINRA"},{"left":"maturity_date","operation":"greater","right":20450101}],
      "columns":["description","isin","close","yield_to_worst","volume","last_bar_update_time"],
      "sort":{"sortBy":"maturity_date","sortOrder":"asc"},"range":[0,50]}'
```

- The issuer name must match TradingView's spelling: "Meta Platforms", "Alphabet", "Amazon.com", "Microsoft", "Oracle". `range` pages through results 50 at a time.
- Non-USD bonds (for example Alphabet's sterling 2126) carry no FINRA row. Use the row without `FINRA` and note the venue.

## 3. Treasuries and spread indexes: FRED

```bash
uv run python scripts/hf_tool.py fred DGS30 DGS20 DGS10 BAMLC0A2CAA BAMLC8A0C15PY BAMLC0A0CM BAMLH0A0HYM2
```

Series:
- `DGS30`, `DGS20`, `DGS10`: Treasury yields.
- `BAMLC0A2CAA`: AA OAS.
- `BAMLC8A0C15PY`: 15y+ IG OAS.
- `BAMLC0A0CM`: all-IG OAS.
- `BAMLH0A0HYM2`: HY OAS.

All are in percent and lag about one day.

**Spread now** ≈ yield to worst minus the CMT matching the benchmark named in the term sheet: `DGS30` for 2050+ maturities, `DGS20` for 2045/46. Treat it as ±10bp. Spread change minus yield change gives the Treasury part of the move.

## 4. Market breadth: FINRA API (public credentials)

Needs `FINRA_CLIENT_ID` and `FINRA_CLIENT_SECRET` in `.env`. The datasets are `corporateMarketBreadth` (advances, declines, 52-week highs and lows, volume) and `corporateMarketSentiment` (customer buy vs sell volume). Both split by investment grade, high yield and convertibles, daily.

```bash
set -a; . ./.env; set +a
T=$(curl -sS -u "$FINRA_CLIENT_ID:$FINRA_CLIENT_SECRET" -X POST "https://ews.fip.finra.org/fip/rest/ews/oauth2/access_token?grant_type=client_credentials" | python3 -c "import json,sys;print(json.load(sys.stdin)['access_token'])")
curl -sS -X POST -H "Authorization: Bearer $T" -H "Content-Type: application/json" -H "Accept: application/json" \
 https://api.finra.org/data/group/fixedIncomeMarket/name/corporateMarketBreadth \
 -d '{"limit":10,"compareFilters":[{"compareType":"EQUAL","fieldName":"tradeReportDate","fieldValue":"2026-10-22"}]}'
```

Sorting needs an EQUAL filter on `tradeReportDate`, so query one date at a time.

## 5. CDS: news only

There is no CDS feed here. Use `uv run python scripts/hf_tool.py web "<issuer> credit default swap"`, or WebSearch. Prefer articles that name the data source (S&P Global Market Intelligence, ICE, LSEG) and a date, and label the number secondary.

## Limitations

- **No per-bond trade history.** TradingView gives the latest delayed print. The FINRA API platform excludes TRACE trade data, which needs a paid TRACE licence. For a few bonds, the free FINRA Data Bond Watchlist (website login) shows trades by hand.
- **No bond data in Yahoo or Databento.** Databento's datasets are equities, options and futures. CME Treasury futures are the only bond-related feed it has.
- **TradingView's scanner is an unofficial endpoint.** It can change or block without notice. Save what you pull with the timestamp.
- **Thin bonds have stale prints.** Check `volume` and `last_bar_update_time` before quoting a price.
- **Spreads are approximate.** CMT vs the on-the-run benchmark, plus yield to worst vs yield to maturity, together give about ±10bp. OAS indexes and spread-to-benchmark are not the same measure.
- **Bloomberg and bondblox return 403.** Their figures reach us only through search snippets.
