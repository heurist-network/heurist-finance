/**
 * splash.js — Splash screen renderer.
 *
 * Three responsive layouts: wide (≥82 cols), medium (≥48), narrow.
 * Figlet wordmark + desk grid + MCP agents + version + pulse animation.
 */

import { BRAND, BOLD, DIM, RESET, LABEL, VERSION } from './state.js';
import { LOGO_B } from './logo.js';

// Pulse: ▐██ breathes lime → bright-white → lime → dim → recover
export const PULSE_COLORS = [
  '\x1b[38;2;192;255;0m',
  '\x1b[38;2;215;255;40m',
  '\x1b[38;2;240;255;90m',
  '\x1b[38;2;215;255;40m',
  '\x1b[38;2;192;255;0m',
  '\x1b[38;2;155;210;0m',
  '\x1b[38;2;192;255;0m',
];

export const SPINNER_FRAMES = ['⠋','⠙','⠹','⠸','⠼','⠴','⠦','⠧','⠇','⠏'];

export const DESK = [
  ['/analyst',     'deep-dives, SEC filings, and the view that matters'],
  ['/compare',     'side-by-side conviction · 2–5 names, one winner'],
  ['/macro',       'rates, inflation, growth — the regime behind the trade'],
  ['/sector',      'rotations, thematics, and the names moving money'],
  ['/desk',        'market pulse · 3 seconds · everything that matters'],
  ['/risk',        'event impact · catalyst timing · what could go wrong'],
  ['/options',     'chains, OI skew, positioning — where smart money leans'],
  ['/futures',     'commodities, rates futures — the cross-asset tape'],
  ['/watch',       'watchlist · what moved · conviction logged'],
];

export const MCP_AGENTS = ['yahoo', 'fred', 'sec', 'exa'];

/**
 * Render the splash screen as an ANSI string.
 * @param {string} msg - Status message
 * @param {number} width - Terminal width
 * @param {number} pulseFrame - Animation frame counter
 * @param {number} maxRows - Max terminal rows available
 * @returns {string} ANSI splash screen
 */
export function renderSplash(msg, width, pulseFrame = 0, maxRows = 999) {
  const pc = PULSE_COLORS[pulseFrame % PULSE_COLORS.length];
  const mark  = `${pc}${BOLD}▐██${RESET}`;
  const spin  = `${pc}${SPINNER_FRAMES[pulseFrame % SPINNER_FRAMES.length]}${RESET}`;
  const vStr  = VERSION.upToDate
    ? `${BRAND}${VERSION.current}${RESET} ${DIM}✓ up to date${RESET}`
    : `${BRAND}${VERSION.current}${RESET} ${LABEL}↑ ${VERSION.latest} available${RESET}`;

  const pad = (s) => {
    const vis = s.replace(/\x1b\[[0-9;]*m/g, '').length;
    return ' '.repeat(Math.max(0, Math.floor((width - vis) / 2))) + s;
  };
  const sep = (ch = '─') => `${DIM}${ch.repeat(width)}${RESET}`;
  const L = (left, right, w = width) => {
    const lv = left.replace(/\x1b\[[0-9;]*m/g, '').length;
    const rv = right.replace(/\x1b\[[0-9;]*m/g, '').length;
    return left + ' '.repeat(Math.max(1, w - lv - rv)) + right;
  };

  const lines = [];

  // ── WIDE: brand mark + two-column desk ──────────────────────────────────
  if (width >= 82 && maxRows >= 22) {
    lines.push('');
    // Custom brand mark — compact 4-row logo (Direction B)
    // Logo row 4 already contains "The view that matters."
    for (const row of LOGO_B) {
      lines.push(`  ${row}`);
    }
    lines.push(sep());
    lines.push('');

    // Two-column: desk left, MCP + version right
    const colW = Math.floor(width / 2) - 2;
    lines.push(L(
      `  ${BRAND}${BOLD}THE DESK${RESET}  ${DIM}every seat takes a position${RESET}`,
      `${DIM}MCP AGENTS${RESET}  `,
    ));
    const mcpW = 'MCP AGENTS'.length; // match header width
    lines.push(L(
      `  ${DIM}${'─'.repeat(colW - 2)}${RESET}`,
      `${DIM}${'─'.repeat(mcpW)}${RESET}  `,
    ));

    const mcpLines = [
      ...MCP_AGENTS.map(a => `  ${BRAND}●${RESET} ${DIM}${a.padEnd(8)}${RESET} ${DIM}connected${RESET}`),
      '',
      `  ${vStr}`,
    ];

    DESK.forEach(([ name, desc ], i) => {
      const left  = `  ${BRAND}${BOLD}${name.padEnd(12)}${RESET}  ${DIM}${desc}${RESET}`;
      const right = mcpLines[i] ? `${mcpLines[i]}  ` : '';
      lines.push(L(left, right));
    });

    lines.push('');
    lines.push(sep());

    // Pad to push hints + spinner to fixed bottom rows
    while (lines.length < maxRows - 2) lines.push('');
    lines.push(`  ${DIM}l${RESET} ${DIM}load${RESET}  ${DIM}?${RESET} ${DIM}help${RESET}  ${DIM}q${RESET} ${DIM}quit${RESET}`);
    lines.push(L(
      `  ${spin} ${DIM}${msg}${RESET}`,
      `${DIM}heurist.ai  ·  ${RESET}${mark}  `,
    ));

  // ── MEDIUM: compact header + desk list ───────────────────────────────────
  } else if (width >= 48 && maxRows >= 16) {
    lines.push('');
    lines.push(L(`  ${mark}  ${BRAND}${BOLD}HEURIST FINANCE${RESET}`, `  ${vStr}  `));
    lines.push(`  ${DIM}heurist.ai  ·  Agent-Driven Financial Intelligence${RESET}`);
    lines.push(sep());
    lines.push(`  ${BRAND}${BOLD}THE DESK${RESET}`);
    DESK.forEach(([name, desc]) => {
      lines.push(`  ${BRAND}${name.padEnd(13)}${RESET}${DIM}${desc}${RESET}`);
    });
    lines.push(`  ${DIM}MCP: ${MCP_AGENTS.join(' · ')}  ·  25 tools${RESET}`);
    lines.push(sep());

    while (lines.length < maxRows - 2) lines.push('');
    lines.push(`  ${DIM}l${RESET} ${DIM}load${RESET}  ${DIM}?${RESET} ${DIM}help${RESET}  ${DIM}q${RESET} ${DIM}quit${RESET}`);
    lines.push(`  ${spin} ${DIM}${msg}${RESET}`);

  // ── SMALL: brand + desk names only ─────────────────────────────────────
  } else if (maxRows >= 10) {
    lines.push(`  ${mark}  ${BRAND}${BOLD}HEURIST FINANCE${RESET}  ${DIM}The view that matters.${RESET}`);
    lines.push(sep());
    // Show desk names without descriptions to save rows
    const deskNames = DESK.map(([name]) => `${BRAND}${name}${RESET}`).join(`${DIM} · ${RESET}`);
    lines.push(`  ${deskNames}`);
    lines.push(`  ${DIM}MCP: ${MCP_AGENTS.join(' · ')}${RESET}`);
    lines.push(sep());

    while (lines.length < maxRows - 2) lines.push('');
    lines.push(`  ${DIM}l load  ? help  q quit${RESET}`);
    lines.push(`  ${spin} ${DIM}${msg}${RESET}`);

  // ── TINY: just brand + spinner ─────────────────────────────────────────
  } else {
    lines.push(`  ${mark}  ${BRAND}${BOLD}HEURIST FINANCE${RESET}`);
    while (lines.length < maxRows - 1) lines.push('');
    lines.push(`  ${spin}  ${DIM}${msg}${RESET}`);
  }

  return lines.join('\n');
}
