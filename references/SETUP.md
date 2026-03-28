# First-Time Setup

## Get key and credits
If no key provided, you should pause and tell the user to do:

Option 1. Visit https://heurist.ai/credits to manage API keys.

Option 2. Claim 100 free credits by posting a verification tweet (only once per user allowed):

1. Call `POST https://mesh.heurist.xyz/claim_credits/initiate` — returns a `verification_code` and `tweet_text`.
2. Post the tweet text on X (must include `@heurist_ai` and `verification: <code>`).
3. Call `POST https://mesh.heurist.xyz/claim_credits/verify` with:
   ```json
   {"tweet_url": "https://x.com/<user>/status/<id>", "verification_code": "<code>"}
   ```
4. Returns success status. One claim per Twitter handle. Code expires in 10 minutes.

---

## First Install

When the Setup Check returns `LIB_MISSING` or `DEPS_MISSING`, run:

```bash
cd ~/.agents/skills/heurist-finance && HEURIST_API_KEY="$HEURIST_API_KEY" TERMINAL_AGENT="$TERMINAL_AGENT" bash setup.sh
```

`setup.sh` is fully headless — it outputs a single JSON line:
```json
{"status":"ok","errors":[],"agent":"claude-code","api_key":true,"deps_ok":true,"mcp_configured":true,"hf_command":true,"mcp_reachable":true}
```
On error:
```json
{"status":"error","errors":["api_key_missing","mcp_unreachable"],"agent":"claude-code"}
```

If `status` is `error`, inspect the `errors` array:
- `node_missing` — Node.js >= 18 required. Tell user to install from https://nodejs.org/
- `api_key_missing` — No key found. See **Get Credits** above.
- `npm_install_failed` — `npm install --production` failed. Check network.
- `mcp_unreachable` — MCP endpoint timed out. Check network.

If `status` is `ok`, proceed silently.

---

## First-Run Welcome

On the very first session (`~/.heurist/.telemetry-prompted` does not exist),
give the user a warm welcome before anything else:

> Welcome to **Heurist Finance** - your AI-powered research desk.
>
> You have a full team of analysts at your command. Ask about any stock,
> sector, or macro regime and get a conviction note - thesis, evidence,
> falsifiers, and a verdict. Every query produces a position, not a summary.
>
> **Your desk:**
> - `/heurist-finance NVDA` - deep-dive on any ticker
> - `/heurist-finance how's the market` - market pulse
> - `/heurist-finance NVDA vs AMD` - side-by-side conviction
>
> Research renders on `hf` - a live Bloomberg-style dashboard that runs in a
> separate terminal window. Panels build in real time as data arrives: quotes,
> charts, technicals, filings, macro overlays, news, and your verdict - all
> on one dense canvas. Works great in a tmux split next to this conversation.
>
> Let's get you set up.

Then ask about telemetry:

> One quick thing before we start. Help us make Heurist Finance better?
>
> Community mode shares anonymous usage data (which skills you use, how long
> queries take, tool success rates) so we can track trends and fix issues.
> No portfolio data, no tickers, no query text - ever.
> Change anytime: `hf-config set telemetry off`

Options:
- A) Sure, happy to help (Recommended)
- B) No thanks

If A: run `~/.agents/skills/heurist-finance/bin/hf-config set telemetry community`

If B: ask a follow-up:

> How about anonymous mode? We just learn that *someone* used HF - no unique ID,
> no way to connect sessions. Just a counter.

Options:
- A) Anonymous is fine
- B) No thanks, fully off

If B→A: run `~/.agents/skills/heurist-finance/bin/hf-config set telemetry anonymous`
If B→B: run `~/.agents/skills/heurist-finance/bin/hf-config set telemetry off`

Always run after consent is resolved:
```bash
touch ~/.heurist/.telemetry-prompted
```
