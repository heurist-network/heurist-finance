/**
 * render.js — Layout dispatch, footer construction, and direct stdout painting.
 *
 * Bypasses Ink's diff renderer — writes directly to stdout for live phase.
 * Sticky header + scrollable body + scroll indicator + footer.
 */

import { BRAND, BOLD, DIM, RESET, LIME_D, LIME_M, LABEL, REPORTS_DIR, tui } from './state.js';
import { visLen } from '../src/index.js';
import { renderBlocks, presetToBlocks } from './engine.js';
import { estimateCost } from './cost.js';
import { SPINNER_FRAMES } from './splash.js';

let _spinnerTick = 0;

// Focus indicator color — #CDF139 lime
const FOCUS_COLOR = '\x1b[38;2;205;241;57m';

// ── Header (TUI chrome) ─────────────────────────────────────────────────────

/**
 * Build the branded header line from agent session state.
 * Always present in live phase — agent doesn't need to send a header block.
 */
export function buildHeader(width) {
  const gradMark = `${LIME_D}▐${LIME_M}█${BRAND}█${RESET}`;
  const title = `${BRAND}${BOLD}HEURIST FINANCE${RESET}`;
  const sep = `${DIM} · ${RESET}`;

  const s = tui.agentState;
  let left = `  ${gradMark} ${title}`;
  if (s?.skill) left += `${sep}${LABEL}:${s.skill}${RESET}`;
  if (s?.query) left += `${sep}${BRAND}${s.query}${RESET}`;

  const fillLen = Math.max(0, width - visLen(left));
  return left + `${DIM}${'─'.repeat(fillLen)}${RESET}`;
}

// ── Focus indicator ─────────────────────────────────────────────────────────

/**
 * Render focus indicator prefix for a panel.
 * Active: ▶ [Enter] drill-down  [/] new query
 * Inactive: (empty string)
 */
export function focusIndicator(panelName) {
  if (!panelName || tui.focusedPanel !== panelName) return '';
  return `${FOCUS_COLOR}${BOLD}▶${RESET}  ${DIM}Tab next · ↑↓ scroll${RESET}`;
}

// ── Help overlay ────────────────────────────────────────────────────────────

/**
 * Render the help overlay (full-screen).
 * For terminals with <12 rows, returns a single summary row.
 */
export function renderHelpOverlay(width) {
  const rows = process.stdout.rows ?? 24;

  if (rows < 12) {
    return `${DIM}↑↓ scroll  Tab focus  s save  l load  ? close  q quit${RESET}`;
  }

  const sep = `${DIM}${'─'.repeat(width)}${RESET}`;
  const K = (key, desc) => `  ${BRAND}${key.padEnd(14)}${RESET}${DIM}${desc}${RESET}`;

  const lines = [
    '',
    `  ${BRAND}${BOLD}HEURIST FINANCE${RESET}  ${DIM}Keyboard Reference${RESET}`,
    sep,
    '',
    `  ${BRAND}${BOLD}NAVIGATION${RESET}`,
    K('↑↓  /  j k', 'Scroll up / down'),
    K('PgUp  PgDn', 'Scroll one page'),
    K('Space', 'Page down'),
    K('g', 'Jump to top'),
    K('G', 'Jump to bottom'),
    K('Tab', 'Next panel'),
    K('Shift+Tab', 'Previous panel'),
    '',
    `  ${BRAND}${BOLD}ACTIONS${RESET}`,
    K('s', 'Save report to ~/.heurist/reports/'),
    K('l', 'Load a saved report'),
    K('1-9', 'Copy follow-up command to clipboard'),
    '',
    `  ${BRAND}${BOLD}DISPLAY${RESET}`,
    K('?', 'Toggle this help'),
    K('Esc', 'Close help / cancel'),
    K('q', 'Return to splash (agent stays connected)'),
    K('Ctrl+C', 'Quit terminal'),
    '',
    `  ${BRAND}${BOLD}SPLASH SCREEN${RESET}`,
    K('Enter', 'Restore last dashboard'),
    K('l', 'Load a saved report'),
    sep,
    `  ${DIM}TUI is display-only. All queries and follow-ups happen in your agent session.${RESET}`,
  ];

  return lines.join('\n');
}

// ── Layout dispatcher ───────────────────────────────────────────────────────

export function runLayout(layoutOrBlocks, panels, width, focused) {
  try {
    if (Array.isArray(layoutOrBlocks)) {
      return renderBlocks(layoutOrBlocks, width);
    }
    const blocks = presetToBlocks(layoutOrBlocks, panels ?? {});
    return renderBlocks(blocks, width);
  } catch (err) {
    return `${DIM}⚠ Render error: ${err.message}${RESET}`;
  }
}

// ── Footer ──────────────────────────────────────────────────────────────────

export function buildFooter(width) {
  const m = tui.renderMeta;
  const s = tui.agentState;

  const gradMark = `${LIME_D}▐${LIME_M}█${BRAND}█${RESET}`;
  const meshLabel = `${BRAND}${BOLD}HEURIST FINANCE${RESET}`;

  const sep = `${DIM} · ${RESET}`;

  // Agent state: show progress during gathering/analyzing
  if (s && (s.stage === 'gathering' || s.stage === 'analyzing')) {
    _spinnerTick++;
    const spin = `${BRAND}${SPINNER_FRAMES[_spinnerTick % SPINNER_FRAMES.length]}${RESET}`;
    const parts = [
      `  ${gradMark} ${spin}`,
      s.stage === 'gathering' ? `${DIM}Gathering${RESET}` : `${DIM}Analyzing${RESET}`,
    ];
    if (s.skill) parts.push(`${LABEL}:${s.skill}${RESET}`);
    if (s.query) parts.push(`${BRAND}${s.query}${RESET}`);
    if (s.tools) {
      const { called, total, current } = s.tools;
      parts.push(`${DIM}${called ?? 0}/${total ?? '?'}${RESET}`);
      if (current) parts.push(`${DIM}${current}${RESET}`);
    }
    const left = parts.join(` ${DIM}·${RESET} `);
    const keys = `${DIM}↑↓ scroll  q quit${RESET}`;
    const leftVis = visLen(left);
    const rightVis = visLen(keys);
    const gap = Math.max(2, width - leftVis - rightVis);
    return left + ' '.repeat(gap) + keys;
  }

  // Complete or idle state: standard footer with meta
  // Cost: prefer agent-provided meta.cost; fall back to estimate from tool call count.
  // Agent provides cost without tilde prefix (e.g. "$0.12"); we add "~" to both paths.
  const toolsCalled = tui.agentState?.tools?.called;
  const costStr = m.cost
    ? `${DIM}~${m.cost}${RESET}`
    : toolsCalled != null
      ? `${DIM}${estimateCost(toolsCalled)}${RESET}`
      : null;

  const meta = [
    m.model ? `${DIM}${m.model}${RESET}` : null,
    m.tools ? `${DIM}${m.tools} tools${RESET}` : null,
    costStr,
    m.as_of ? `${DIM}${m.as_of}${RESET}` : null,
  ].filter(Boolean).join(sep);

  const left = `  ${gradMark} ${meshLabel}` + (meta ? `${sep}${meta}` : '');

  // Show follow-ups hint when complete
  let keys;
  if (s?.stage === 'complete' && s?.follow_ups?.length > 0) {
    keys = `${DIM}1-${s.follow_ups.length} drill  ↑↓ scroll  s save  q quit${RESET}`;
  } else {
    keys = `${DIM}↑↓ scroll  s save  l load  q quit${RESET}`;
  }

  const leftVis  = visLen(left);
  const rightVis = visLen(keys);
  const gap = Math.max(2, width - leftVis - rightVis);

  return left + ' '.repeat(gap) + keys;
}

// ── Load overlay ────────────────────────────────────────────────────────────

export function renderLoadOverlay(width) {
  const lines = [];
  lines.push('');
  lines.push(`  ${BRAND}▐${RESET}${DIM} Heurist Mesh${RESET}  ${LABEL}Load Report${RESET}`);
  lines.push(`  ${DIM}↑↓ navigate · Enter load · Esc cancel${RESET}`);
  lines.push('');
  if (tui.loadList.length === 0) {
    lines.push(`  ${DIM}No saved reports in ${REPORTS_DIR}${RESET}`);
  } else {
    tui.loadList.forEach((f, i) => {
      const active = i === tui.loadIdx;
      const cursor = active ? `${BRAND}▶${RESET}` : ' ';
      const label  = active ? `${LABEL}${f}${RESET}` : `${DIM}${f}${RESET}`;
      lines.push(`  ${cursor} ${label}`);
    });
  }
  return lines.join('\n');
}

// ── Shimmer animation ───────────────────────────────────────────────────────

const SHIMMER_SEQ = ['░','░','▒','▓','▒','░','░'];
let _shimmerOffset = 0;

/**
 * Apply shimmer effect to skeleton-only lines (lines that are ONLY ░ chars + whitespace).
 * Does NOT touch component content like holder bars that use ░ for empty regions.
 */
export function applyShimmer(content) {
  _shimmerOffset++;
  return content.replace(/^([ ]*)(░{20,})$/gm, (_match, prefix, run) => {
    const chars = [];
    for (let i = 0; i < run.length; i++) {
      const idx = (i + _shimmerOffset) % SHIMMER_SEQ.length;
      chars.push(SHIMMER_SEQ[idx]);
    }
    return prefix + chars.join('');
  });
}

// ── Render animation timer ──────────────────────────────────────────────────

let _animTimer = null;

/**
 * Spinner animation — calls paintWithScroll in overwrite mode (no screen clear).
 * Works for both overflow and non-overflow content.
 */
export function startRenderAnimation() {
  stopRenderAnimation();
  _animTimer = setInterval(() => {
    if (!tui.lastContent) return;
    const s = tui.agentState;
    if (!s || (s.stage !== 'gathering' && s.stage !== 'analyzing')) {
      stopRenderAnimation();
      return;
    }
    paintWithScroll(false); // false = no screen clear, overwrite in place
  }, 200);
}

export function stopRenderAnimation() {
  if (_animTimer) { clearInterval(_animTimer); _animTimer = null; }
}

// ── Direct stdout painting ──────────────────────────────────────────────────

/**
 * Build the action bar shown in COMPLETE state when follow_ups exist.
 */
function buildActionBar(width) {
  const s = tui.agentState;
  if (!s || s.stage !== 'complete' || !s.follow_ups?.length) return '';

  const lines = [];
  lines.push(`${DIM}┄┄ WHAT'S NEXT ${'┄'.repeat(Math.max(0, width - 18))}${RESET}`);
  for (const f of s.follow_ups) {
    lines.push(`  ${BRAND}${f.key}${RESET}  ${DIM}${f.label}${RESET}`);
  }
  lines.push(`  ${DIM}q${RESET}  ${DIM}Done — return to agent${RESET}`);
  lines.push(`${DIM}${'─'.repeat(width)}${RESET}`);
  return lines.join('\n');
}

export function paintScreen(content, resetScroll = true) {
  const w = process.stdout.columns ?? 80;
  const header = buildHeader(w);
  const actionBar = buildActionBar(w);
  const footer = buildFooter(w);
  // Strip duplicate headers: if agent sent a line containing "HEURIST FINANCE",
  // the TUI already renders its own header — drop the agent's to avoid wasting a row.
  const lines = content.split('\n');
  const filtered = lines.filter(l => {
    const stripped = l.replace(/\x1b\[[0-9;]*m/g, '');
    return !stripped.includes('HEURIST FINANCE');
  });
  const cleanContent = filtered.join('\n');
  tui.lastContent = header + '\n' + cleanContent + (actionBar ? '\n' + actionBar : '') + '\n' + footer;
  if (resetScroll) tui.scrollOffset = 0;
  paintWithScroll();
}

export function paintWithScroll(clear = true) {
  const rows = process.stdout.rows ?? 24;
  // Apply shimmer during gathering/analyzing
  const s = tui.agentState;
  const isAnimating = s && (s.stage === 'gathering' || s.stage === 'analyzing');
  let displayContent = isAnimating ? applyShimmer(tui.lastContent) : tui.lastContent;
  // Rebuild footer on each paint to update spinner frame
  if (isAnimating) {
    const w = process.stdout.columns ?? 80;
    const lines = displayContent.split('\n');
    lines[lines.length - 1] = buildFooter(w);
    displayContent = lines.join('\n');
  }
  const w = process.stdout.columns ?? 80;
  const allLines = displayContent.split('\n');
  const totalLines = allLines.length;

  // Always rebuild header from live agent state
  allLines[0] = buildHeader(w);
  displayContent = allLines.join('\n');

  if (totalLines <= rows) {
    if (clear) {
      process.stdout.write('\x1b[2J\x1b[H' + displayContent);
    } else {
      // Overwrite in place — pad each line to full width to cover old content
      const padded = allLines.map(l => l + ' '.repeat(Math.max(0, w - visLen(l)))).join('\n');
      process.stdout.write('\x1b[H' + padded);
      // Clear any leftover rows below
      for (let r = totalLines + 1; r <= rows; r++) {
        process.stdout.write(`\x1b[${r};1H\x1b[2K`);
      }
    }
    return;
  }

  // Content overflows — sticky header + scrollable body + indicator row
  const stickyLine = allLines[0];
  const bodyLines  = allLines.slice(1, allLines.length - 1);
  const footerLine = allLines[allLines.length - 1];
  const bodyRows   = rows - 3; // sticky(1) + footer(1) + indicator(1)

  const maxOffset = Math.max(0, bodyLines.length - bodyRows);
  tui.scrollOffset = Math.max(0, Math.min(tui.scrollOffset, maxOffset));
  const offset = tui.scrollOffset;
  const viewLines = bodyLines.slice(offset, offset + bodyRows);

  const atTop = offset === 0;
  const atBottom = offset >= maxOffset;
  const pct = maxOffset > 0 ? Math.round((offset / maxOffset) * 100) : 0;
  const indicator = `${DIM}` +
    (atTop ? ' ' : ' ▲ ') +
    `${offset + 1}–${Math.min(offset + viewLines.length, bodyLines.length)}/${bodyLines.length}` +
    (atBottom ? '' : ' ▼') +
    ` ${atBottom ? 'END' : pct + '%'}` +
    `  ↑↓/jk scroll  PgUp/Dn  g top  G end${RESET}`;

  if (clear) {
    process.stdout.write(
      '\x1b[2J\x1b[H' +
      stickyLine + '\n' +
      viewLines.join('\n') + '\n' +
      footerLine + '\n' +
      indicator,
    );
  } else {
    // Overwrite in place — pad each line to cover old content
    const pad = (l) => l + ' '.repeat(Math.max(0, w - visLen(l)));
    const output = [stickyLine, ...viewLines, footerLine, indicator].map(pad).join('\n');
    process.stdout.write('\x1b[H' + output);
  }
  // Force header at row 1 — Ink's render cycle can overwrite it
  process.stdout.write(`\x1b[1;1H\x1b[2K${stickyLine}`);
  process.stdout.write(`\x1b[${rows};1H`);
}
