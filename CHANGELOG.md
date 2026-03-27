# Changelog

All notable changes to Heurist Finance are documented here.

## [0.9.14] - 2026-03-27

### Engineering
- **Release**: version bump to `0.9.14`.

## [0.9.13] - 2026-03-26

### Added
- **Sub-skill: options** — single-ticker options analysis (chains, OI skew, put/call ratio, max pain, suggested structures). MCP tools: `options_expirations`, `options_chain`.
- **Sub-skill: futures** — futures & commodities regime analysis (energy, metals, rates, equity index). MCP tool: `futures_snapshot`.
- **MCP tools deployed**: `futures_snapshot`, `options_expirations`, `options_chain`. Known bug: `limit`/`limit_contracts` params cause type error when passed explicitly — use defaults.

### Changed
- **Skill renames**: `pm` → `compare`, `strategist` → `macro`, `sector-head` → `sector`. Routing table, sub-skill files, and all references updated.
- **SKILL.md**: table block format corrected from `columns`/`rows` to `headers`/`rows[].cells` to match `terminal/engine.js` implementation.
- **terminal/splash.js**: desk grid updated with new skill names + options/futures entries.
- **README.md**: skill table updated — 9 research modes (was 7).
- **ARCHITECTURE.md**: directory tree updated with renamed + new skill dirs.
- **MARKETING.md**: skill table updated with new names + options/futures.
- **gtm/**: research prompts and positioning updated from 7 to 9 modes, old names replaced.

### Fixed
- **package-lock.json**: regenerated to match current `package.json` after dependency cleanup (removed stale `@modelcontextprotocol/sdk`, `ink`, `react` lockfile entries).

### Engineering
- **terminal/render.test.js**: test fixtures updated from `pm` to `compare`.

## [0.9.1] - 2026-03-23

### Hardening

Post-review fixes from 5 review reports (CEO, Eng, CMO, Design, YC Garry Tan).

#### Bug Fixes
- **Schema coerce try/catch**: Throwing coerce functions no longer crash `validate()` and silently drop panels - errors are caught, logged, and the panel renders with uncoerced data
- **BrailleChart NaN/Infinity guard**: Non-finite values from bad agent input are filtered before plotting - gaps are skipped cleanly instead of corrupting the chart
- **CandlestickChart bull/bear chars**: `BODY_BULL` now correctly uses `░` (hollow) vs `BODY_BEAR` `█` (filled) - constants match their names and the rendering references them correctly
- **`/render` agent identity verification**: Endpoint now checks the optional `agent` field against the connected session - mismatched agent IDs get 403

#### Engineering (from v0.9.0 post-tag)
- OSC8 hyperlink support in `ansiTrunc` (11 new tests)
- 1MB payload size limit on all POST endpoints
- `/disconnect` auth - agent ID verification, 403 on mismatch
- Clipboard `execSync` → async `spawn`
- Word-wrap deduplication - extracted to shared utility in `ansi.js` (-24 lines)
- CorrelationMatrix hardcoded hex → theme palette
- Bridge port configurable via `HEURIST_BRIDGE_PORT` env var
- 10 untested panel formatters now covered (113 panel tests total)
- `renderPanel()` 440-line switch → handler registry pattern
- HeatMap hardcoded neutral color → theme-derived value
- News limit capped to prevent unbounded array rendering
- `render.js` inline ANSI strip replaced with `visLen()`
- Non-Negotiable Rules embedded in all 7 sub-skill SKILL.md files
- README hero rewrite, `.npmignore` for internal docs
- **741 tests passing** (14 pre-existing bridge/port infra failures)

## [0.9.0] - 2026-03-23

### The View That Matters

v0.9.0 is the dog-food release. 27 commits, 20+ bugs fixed from live testing
with 15 MCP tools. Every surface polished: splash, research mode, TUI rendering,
brand identity, and codebase quality.

### Brand

- **Tagline**: "The view that matters." replaces feature-count spec sheet
- **Logo**: Committed to Direction B (candlestick mark). Direction A removed.
- **SKILL.md frontmatter**: "Conviction-driven financial research desk" - trigger-focused, not architecture
- **Sub-skill names**: `/analyst` not `/heurist-finance:analyst`
- **Splash**: "every seat takes a position" thesis. Desk descriptors polished.
- **Persona-first architecture**: SKILL.md restructured - identity is immersive character brief, all setup is silent, voice gates at every stage, ASK blocks voiced across all 7 sub-skills

### Research Mode

- **First dog-food test**: Full crypto stocks sector analysis via Research mode
- **`hf-chart` CLI**: Plain-text braille charts for markdown code blocks
- **No `---` dividers**: Claude Code doesn't render horizontal rules - documented and fixed in all examples
- **Sparklines**: sector-head pipeline now fetches price_history per ticker

### TUI Fixes (Dog-Food)

- **Load overlay**: `l` on splash no longer shows skeleton blocks
- **Column alignment**: InsiderTimeline nameW uses full width, EarningsSurprise epsW bumped to 18
- **Session lifecycle**: splash → connect → render → save → quit → restore flow polished
- **Help overlay**: Removed unimplemented keybind labels (Enter/r/c//)
- **Animation**: Footer-only 200ms repaint (was full-screen 60ms causing shaking)
- **News**: OSC 8 hyperlinks + visLen strips OSC 8 for alignment
- **Splash**: waiting → connected → live → q → restore with Enter/l

### Engineering

- **Version**: Single source of truth from package.json (was 3 different values)
- **Dead code removed**: extractQuote, mcpCall, mcpInit, clipboardFlash, 5 unused constants
- **DRY**: SPINNER_FRAMES, PANEL_NAMES deduplicated; figlet + zod phantom deps removed
- **Edge cases**: WaterfallChart previous=0, NewsStream invalid dates, HeatMap all-null guard
- **Defensive defaults**: 9 components now have `opts = {}` default
- **`hf` symlink**: resolves correctly through ~/.local/bin
- **tmux**: setup.sh shows hyperlink config tip when running inside tmux
- **598 tests passing** (14 pre-existing bridge/port infra failures)

## [0.8.0] - 2026-03-22

### Added
- Markdown→ANSI renderer (`src/markdown.js`) - converts agent markdown output to styled ANSI for Research mode
- Wire 3 remaining components: CorrelationMatrix, TreeMap, FlowSankey now connected to panels.js
- 5 research mode examples added to SKILL.md covering deep-dive, compare, macro, sector, pulse
- Version scheme retag - pre-release series: v0.7.0/v0.7.1 historical, v0.8.0 current, v0.9.0 internal review gate, v1.0.0 public distribution

## [0.7.1] - 2026-03-22

### Added - Phase 0 (Foundation)
- AGENTS.md - agent-agnostic project config for Claude Code, Codex CLI, OpenCode
- Schema quality gates - verdict warns on missing thesis/conviction/catalysts/risks/timeframe
- Conviction unification - strong_bull/bull/neutral/bear/strong_bear enum, signal→conviction coercion
- Brand palette: #C0FF00 lime, #374EFF blue, #6100FF purple, #FF5C30 orange-red
- setup.sh registers `hf` shell command via ~/.local/bin/hf symlink

### Added - Phase 1 (Intelligence Layer)
- Sections API - verdict renders sections[] in agent-controlled order, flat→sections coercion
- Universal annotations - summary/footnote on all components, _annotations passthrough
- Shape catalog - data shape→component mapping documented in SKILL.md
- Thinking protocol - 6-stage state machine (context load → gather → analyze → render → follow-up → save)
- Personality spec - terse, opinionated, jargon-native voice (Damodaran/Soros/Druckenmiller/Burry)
- Research/Terminal two-mode architecture - Research (markdown) is primary experience

### Added - Phase 2 (Agent Memory)
- Session persistence - ~/.heurist/sessions/{date}-{NNN}.json
- Memory section in verdict - "Prior (Mar 15): bullish at $168 - conviction changed"
- 90-day session cleanup

### Added - Phase 3 (TUI Architecture)
- app.jsx split into state.js, splash.jsx, render.js, scroll.js, io.js
- Agent→TUI state protocol (_state in POST payload)
- Shimmer + spinner animations (footer-only, 200ms cycle)

### Added - Phase 4 (Marketing & Brand)
- MARKETING.md - brand kit with thesis, taglines, marketplace copy
- logo.js - candlestick mark + HEURIST FINANCE wordmark
- version.js - npm registry version check with 1-hour cache

### Added - Phase 5 (TUI Controls)
- Tab focus cycling with ▶ indicator
- Help overlay (? key) with keybind reference
- Number key clipboard copy

## [0.7.0] - 2026-03-21

Initial release. 20 components, 6 themes, free-form block engine, Heurist Mesh MCP integration.
