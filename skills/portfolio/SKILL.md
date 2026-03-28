---
name: portfolio
description: Use when the user asks about their portfolio, holdings, positions, what they own, allocation, concentration risk, portfolio health, or says "my portfolio" / "show positions" / "what do I hold". Also handles broker connection via "/portfolio connect" and "/portfolio disconnect".
---

> **PREREQUISITE:** Read `../../SKILL.md` (two directories up from this file) first. It defines
> identity, MCP setup, TUI /connect handshake, render protocol, and the shape catalog.
> This file handles only the sub-skill-specific flow.

# Portfolio - Brokerage Dashboard

*Your positions. Your risk. No sugar-coating.*

Read-only portfolio view. All brokers use token-based auth. No daemons, no gateways.
Uses existing TUI panels. Zero new components.

## Supported Brokers

| Broker | What you need | Data | Setup |
|--------|--------------|------|-------|
| **IBKR** | Token + Query ID | End-of-day positions, balances, P&L | 5 min |
| **Moomoo** | Moomoo desktop app running | Real-time US + HK + SG + JP | 0 min (auto-detect) |

---

## Entry Logic

```
args contain "connect" or "disconnect"?
  YES -> Broker Connection
  NO  -> Portfolio Dashboard
```

---

## Broker Connection

All CLI commands use:
```bash
SKILL_DIR=$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]:-$0}")")" && cd ../.. && pwd)
```

### `/portfolio connect ibkr`

Walk the user through step by step:

1. "IBKR Flex Query gives you portfolio data with just a token. 5 minutes to set up."
2. Tell them exactly what to do (paste these, don't just link):
   - Log into portal.interactivebrokers.com
   - Go to Performance & Reports -> Flex Queries
   - Click "Create" next to Activity Flex Query
   - Check: **Open Positions** and **Cash Report**
   - Set period to "Last Business Day", format XML
   - Save. Note the **Query ID** (number next to query name)
   - Scroll to "Flex Web Service Configuration"
   - Click "Create Token". Note the **Token**
3. Ask for both values
4. Connect and test:
```bash
node "$SKILL_DIR/lib/portfolio-cli.js" connect ibkr <TOKEN> <QUERY_ID>
node "$SKILL_DIR/lib/portfolio-cli.js" test ibkr
```
5. Success: "Connected! Run `/portfolio` to see your positions."
6. Common errors:
   - Token expired -> "Regenerate in IBKR portal"
   - Invalid Query ID -> "Double-check the number"
   - Rate limited -> "Wait 10 minutes"

### `/portfolio connect moomoo`

**Level 1: Auto-detect (0 min)**

Probe for running Moomoo desktop app or OpenD:
```bash
node "$SKILL_DIR/lib/portfolio-cli.js" probe moomoo
```
If `detected: true`: connect immediately:
```bash
node "$SKILL_DIR/lib/portfolio-cli.js" connect moomoo
node "$SKILL_DIR/lib/portfolio-cli.js" test moomoo
```
Done. No setup needed.

**Level 2: Start desktop app**

If not detected but user has Moomoo desktop installed:
"Open the Moomoo app, I'll wait for it to start."
Poll every 5 seconds:
```bash
for i in $(seq 1 12); do
  node "$SKILL_DIR/lib/portfolio-cli.js" probe moomoo 2>/dev/null | grep -q '"detected":true' && echo "DETECTED" && break
  sleep 5
done
```
Once detected, connect and test.

**Level 3: Agent installs OpenD**

If user doesn't have the desktop app, offer to set up OpenD:
"I can install Moomoo's API gateway for you. It runs in the background. You just need your Moomoo login."

Use `bin/setup-opend.sh` — it handles download, config generation, and startup:

```bash
node "$SKILL_DIR/lib/portfolio-cli.js" setup download
```

**Credentials: never handle directly.** Tell the user to run the configure step themselves:
"Type this in your terminal — it will ask for your password securely (I won't see it):"
```
! bash ~/.agents/skills/heurist-finance/bin/setup-opend.sh configure <MOOMOO_ID>
```
The `!` prefix runs it in the user's terminal. The script prompts for the password with hidden input.

Then start:
```bash
node "$SKILL_DIR/lib/portfolio-cli.js" setup start
```

OpenD listens on WebSocket port **33333** by default.

Wait for startup, then connect:
```bash
for i in $(seq 1 12); do
  node "$SKILL_DIR/lib/portfolio-cli.js" probe moomoo 2>/dev/null | grep -q '"detected":true' && echo "DETECTED" && break
  sleep 5
done
node "$SKILL_DIR/lib/portfolio-cli.js" connect moomoo
node "$SKILL_DIR/lib/portfolio-cli.js" test moomoo
```

If first-time login triggers a verification code, tell the user:
"Moomoo sent a verification code to your phone/email. Enter it here."
Then pass it to OpenD via: `node "$SKILL_DIR/lib/portfolio-cli.js" setup verify-2fa <CODE>`

On success: "Moomoo connected! OpenD is running in the background. Run `/portfolio` to see your positions."

### `/portfolio connect` (no broker)

> Which broker?
>
> 1. **IBKR** -- token + query ID, 5 min setup
> 2. **Moomoo** -- auto-detect or I'll set it up for you
>
> All free, read-only, credentials stay on your machine.

### `/portfolio disconnect <broker>`

```bash
node "$SKILL_DIR/lib/portfolio-cli.js" disconnect <broker>
```

---

## Portfolio Dashboard

### Phase 1: Check Brokers

```bash
node "$SKILL_DIR/lib/portfolio-cli.js" brokers
```

No brokers? Show connection options. **STOP.**

### Phase 2: Fetch

```bash
node "$SKILL_DIR/lib/portfolio-cli.js" status
```

Returns normalized JSON: `holdings[]`, `accounts[]`, `totals`, `concentration`, `_cached`, `_errors`.

### Phase 3: Enrich

```
mcp__heurist-finance__yahoofinanceagent_quote_snapshot
  symbols: "NVDA,AAPL,MSFT,..."
```

Update holdings with fresh prices. 1-3 MCP calls.

### Phase 4: Render

Single POST. Write to `/tmp/hf-render.json`, then: `hf-post /tmp/hf-render.json`

Minimum 4 panels:

| Data | Panel | When |
|------|-------|------|
| Holdings | `table` | Always |
| Allocation | `heatmap` | > 3 holdings |
| Daily P&L | `waterfall` | If data available |
| Concentration | `gauge` | > 3 holdings |
| Verdict | `verdict` | Always |

#### Payload

```json
{
  "blocks": [
    { "divider": "PORTFOLIO" },
    {
      "panel": "table",
      "data": {
        "title": "Holdings",
        "headers": ["Ticker", "Qty", "Avg Cost", "Price", "Mkt Val", "P&L", "P&L%", "Weight"],
        "rows": [
          { "cells": ["NVDA", "400", "$150.00", "$172.70", "$69,080", "+$9,080", "+15.1%", "40.2%"] }
        ],
        "align": ["left", "right", "right", "right", "right", "right", "right", "right"]
      }
    },
    {
      "row": [
        { "panel": "heatmap", "data": { "title": "Sector Allocation", "items": [{ "label": "Tech", "value": 65.1, "color": "accent" }] } },
        { "panel": "gauge", "data": { "title": "Concentration", "value": 40.2, "max": 100, "label": "Top Position", "thresholds": [{ "value": 20, "color": "positive" }, { "value": 35, "color": "warning" }, { "value": 100, "color": "negative" }] } }
      ]
    },
    {
      "panel": "verdict",
      "data": {
        "variant": "boxed",
        "sections": [
          { "type": "thesis", "content": "65% in semis with NVDA at 40% weight. That's a bet, not a portfolio." },
          { "type": "risks", "items": ["NVDA at 40% (threshold: 20%)", "Tech at 65% (S&P: 31%)"] },
          { "type": "catalysts", "items": ["Trim NVDA to 20%", "Add non-tech exposure"] }
        ]
      }
    }
  ],
  "_state": {
    "stage": "complete",
    "agent": "<your-agent>",
    "model": "<your-model>",
    "skill": "portfolio",
    "query": "portfolio",
    "tools": { "called": 2, "total": 2, "current": null, "completed": ["portfolio-cli", "quote_snapshot"] },
    "follow_ups": [
      { "key": "1", "label": "Deep dive on top holding" },
      { "key": "2", "label": "Sector rotation analysis" }
    ]
  }
}
```

---

## Research Mode (TUI not running)

```
▐██ **HEURIST FINANCE** . portfolio

## Portfolio -- $171,778 (+$9,078 / +5.6%)

> 65% tech, 40% in one name. Conviction bet, not a portfolio.

| Ticker | Qty | Avg | Price | Value | P&L% | Wt% |
|--------|-----|-----|-------|-------|------|-----|
| NVDA | 400 | $150 | $172.70 | $69,080 | +15.1% | 40.2% |
| AAPL | 200 | $165 | $213.49 | $42,698 | +29.4% | 24.9% |

**Concentration** HHI 0.28 . Top-5: 87% . **HIGH RISK**

---
*Claude Opus 4 . 2 tools . ~$0.02*
```

---

## Error Handling

- No brokers -> guide to connect
- Partial data (`_errors`) -> render what's available, note gaps
- Token expired -> "Regenerate in IBKR portal"
- Moomoo not detected -> offer to install OpenD (Level 3 setup)
- MCP fails -> use broker prices, note staleness

## Constraints

- Max 3 MCP calls. Portfolio data comes from CLI.
- **Read-only. No orders. No trades. Ever.**
- Never expose tokens or API keys in output.
- Holdings sorted by weight descending.
- Concentration: green < 20%, yellow 20-35%, red > 35%.
- HHI: < 0.10 diversified, 0.10-0.18 moderate, > 0.18 concentrated.
- Recommend IBKR Flex first (simplest token-based setup).
