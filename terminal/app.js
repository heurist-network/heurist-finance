/**
 * app.js — Heurist Finance Terminal.
 *
 * Full-screen TUI with branded splash → auto-fetch market pulse → agent takeover.
 * Agents POST commands to localhost:7707/render → EventEmitter → direct stdout.
 *
 * Rendering strategy:
 * - Splash phase: plain timer + process.stdout.write
 * - Live phase: direct stdout write via paintScreen/paintWithScroll
 * - No React/Ink — single stdout owner eliminates ghost footer, header clobber,
 *   and spinner freeze bugs.
 *
 * Architecture:
 *   server emitter → tui state mutation → paintScreen() → stdout
 *   stdin keypress  → tui state mutation → paintWithScroll() → stdout
 *   animation timer → paintWithScroll(false) → stdout
 *
 * Module split (#10):
 *   state.js   — shared constants, mutable TUI state, block type resolver
 *   splash.js  — splash screen renderer (figlet, desk grid, pulse animation)
 *   render.js  — layout dispatch, footer, direct stdout painting
 *   scroll.js  — scroll state, mouse wheel handler
 *   io.js      — HTTP helpers, MCP auto-fetch, report save/load
 */

import fs from 'fs';
import path from 'path';
import readline from 'readline';
import { startServer, emitter } from './server.js';
import { setTheme } from '../src/index.js';

// ── Module imports ──────────────────────────────────────────────────────────

import { BRAND, DIM, RESET, REPORTS_DIR, tui, getBlockType, applyPatch } from './state.js';
import { renderSplash, PULSE_COLORS, SPINNER_FRAMES } from './splash.js';
import { runLayout, buildFooter, renderLoadOverlay, renderHelpOverlay, focusIndicator, paintScreen, paintWithScroll, startRenderAnimation, stopRenderAnimation } from './render.js';
import { setupMouseWheel, isMouseRecent } from './scroll.js';
import { healthCheck, saveReport, listReports } from './io.js';
import { checkVersion } from './version.js';
import { spawn } from 'child_process';

// ── Helpers ──────────────────────────────────────────────────────────────────

const getWidth  = () => Math.min(process.stdout.columns ?? 80, 200);
const getHeight = () => process.stdout.rows ?? 24;

// ── Phase state ──────────────────────────────────────────────────────────────
// These replace React's useState. They live in module scope so all handlers
// can read/write them directly.

tui.phase     = 'splash';
tui.splashMsg = 'Starting...';
tui.layout    = 'pulse';
tui.panels    = {};
tui.blocks    = null;   // null = use legacy layout+panels
tui.focused   = null;
tui.isPatch   = false;

// ── Repaint helper ───────────────────────────────────────────────────────────

function repaint() {
  if (tui.phase === 'splash') return; // splash has its own animation
  if (tui.loadMode) return;
  const w = getWidth();
  const output = runLayout(tui.blocks ?? tui.layout, tui.blocks ? null : tui.panels, w, tui.focused);
  paintScreen(output, !tui.isPatch);
  tui.isPatch = false;
}

// ── Server event handlers ────────────────────────────────────────────────────

function onRender(payload) {
  if (tui.phase === 'splash') {
    process.stdout.write('\x1b[2J\x1b[H');
  }
  tui.phase = 'live';

  // Capture meta (model, tools, cost, as_of) for dynamic footer
  if (payload.meta && typeof payload.meta === 'object') {
    tui.renderMeta = { ...tui.renderMeta, ...payload.meta };
  }

  // Capture _state for agent→TUI state protocol (#15)
  if (payload._state && typeof payload._state === 'object') {
    const prev = tui.agentState?.stage;
    tui.agentState = payload._state;
    // Start/stop render animation based on stage transitions (#16)
    const stage = payload._state.stage;
    if (stage === 'gathering' || stage === 'analyzing') {
      startRenderAnimation();
    } else {
      stopRenderAnimation();
      // Scroll to top when render completes
      if (stage === 'complete' && prev !== 'complete') {
        tui.scrollOffset = 0;
      }
    }
  }

  // Track if this render is a patch (for scroll preservation)
  tui.isPatch = !!payload.patch;
  tui.loadMode = false;
  tui.helpVisible = false;

  // Extract panel IDs for focus cycling (#3)
  if (Array.isArray(payload.blocks)) {
    const ids = payload.blocks
      .map(b => getBlockType(b))
      .filter(t => t && t !== 'text' && t !== 'divider' && t !== 'spacer' && t !== 'row' && t !== 'stack');
    tui.panelIds = ids;
    if (!ids.includes(tui.focusedPanel)) tui.focusedPanel = ids[0] ?? null;
  }

  // New blocks API: payload.blocks is the full render spec
  if (Array.isArray(payload.blocks)) {
    if (!payload.patch) tui.lastBlocks = payload.blocks;
    if (payload.patch) {
      const base = Array.isArray(tui.blocks) ? [...tui.blocks] : [];
      tui.blocks = applyPatch(base, payload.blocks);
    } else {
      tui.blocks = payload.blocks;
    }
    tui.layout = null;
  } else if (payload.layout) {
    if (tui.layout !== payload.layout) tui.panels = payload.panels ?? {};
    else if (payload.panels && typeof payload.panels === 'object') {
      tui.panels = { ...tui.panels, ...payload.panels };
    }
    tui.layout = payload.layout;
    tui.blocks = null;
  } else if (payload.panels && typeof payload.panels === 'object') {
    tui.panels = { ...tui.panels, ...payload.panels };
  }

  if (payload.theme) {
    setTheme(payload.theme);
  }

  repaint();
}

function onFocus(payload) {
  tui.focused = payload?.panel ?? null;
  repaint();
}

function onLayout(payload) {
  if (payload?.layout) {
    tui.layout = payload.layout;
    repaint();
  }
}

function onClear() {
  tui.panels = {};
  repaint();
}

function onSplash(payload) {
  tui.splashMsg = payload?.msg ?? '';
  if (payload?.agent) tui.agentState = { ...tui.agentState, ...payload.agent };
  // Restart splash animation to reflect new message
  if (tui.phase === 'splash') {
    startSplashAnimation();
  }
}

function onLive() {
  tui.phase = 'live';
  repaint();
}

// ── Splash animation ─────────────────────────────────────────────────────────

let _splashRevealTimer = null;
let _splashPulseTimer  = null;

function stopSplashAnimation() {
  if (_splashRevealTimer) { clearInterval(_splashRevealTimer); _splashRevealTimer = null; }
  if (_splashPulseTimer)  { clearInterval(_splashPulseTimer);  _splashPulseTimer  = null; }
}

function startSplashAnimation() {
  stopSplashAnimation();

  const width    = getWidth();
  const termRows = getHeight();
  const allLines = renderSplash(tui.splashMsg, width, 0, termRows).split('\n');
  let revealCount = 0;
  let pulseFrame  = 0;

  const spinnerSet = new Set(SPINNER_FRAMES);
  const animLineIndices = allLines.reduce((acc, line, i) => {
    const stripped = line.replace(/\x1b\[[0-9;]*m/g, '');
    if (stripped.includes('▐') || [...stripped].some(c => spinnerSet.has(c))) acc.push(i);
    return acc;
  }, []);

  // Find last non-blank content line (skip bottom padding)
  let lastContentIdx = allLines.length - 1;
  while (lastContentIdx > 0 && allLines[lastContentIdx].replace(/\x1b\[[0-9;]*m/g, '').trim() === '') lastContentIdx--;
  // The spinner line is the last non-blank line — include it but skip padding above it
  const spinnerIdx = lastContentIdx;
  // Content ends at the separator before padding
  let contentEnd = spinnerIdx;
  for (let i = spinnerIdx - 1; i >= 0; i--) {
    if (allLines[i].replace(/\x1b\[[0-9;]*m/g, '').trim() !== '') { contentEnd = i + 1; break; }
  }

  _splashRevealTimer = setInterval(() => {
    if (tui.phase !== 'splash') {
      stopSplashAnimation();
      return;
    }
    revealCount++;
    if (revealCount <= contentEnd) {
      // Reveal content lines progressively, but always show spinner at fixed bottom
      process.stdout.write('\x1b[2J\x1b[H' + allLines.slice(0, revealCount).join('\n'));
      process.stdout.write(`\x1b[${spinnerIdx + 1};1H${allLines[spinnerIdx]}`);
    } else {
      // Content done — show full splash
      revealCount = allLines.length;
      process.stdout.write('\x1b[2J\x1b[H' + allLines.join('\n'));
    }
    if (revealCount >= allLines.length) {
      clearInterval(_splashRevealTimer);
      _splashRevealTimer = null;
      _splashPulseTimer = setInterval(() => {
        if (tui.phase !== 'splash') {
          stopSplashAnimation();
          return;
        }
        pulseFrame++;
        const currentWidth = getWidth();
        const currentRows  = getHeight();
        const newLines = renderSplash(tui.splashMsg, currentWidth, pulseFrame, currentRows).split('\n');
        for (const i of animLineIndices) {
          if (i >= currentRows) continue;
          process.stdout.write(`\x1b[${i + 1};1H\x1b[2K${newLines[i] ?? ''}`);
        }
      }, 110);
    }
  }, 16);
}

// ── Keyboard input ────────────────────────────────────────────────────────────

function handleKeypress(ch, key) {
  // Safety: ignore if no key object (can happen with raw data)
  if (!key) key = {};

  // Ctrl+C: always exit
  if (key.ctrl && key.name === 'c') {
    process.exit(0);
  }

  // ── Help overlay (works from any phase) ────────────────────────
  if (ch === '?') {
    tui.helpVisible = !tui.helpVisible;
    if (tui.helpVisible) {
      stopSplashAnimation();
      const w = getWidth();
      const overlay = renderHelpOverlay(w);
      process.stdout.write('\x1b[2J\x1b[H' + overlay);
    } else {
      if (tui.phase === 'splash') {
        startSplashAnimation();
      } else {
        paintWithScroll();
      }
    }
    return;
  }

  // Esc dismisses help overlay from any phase
  if (key.name === 'escape' && tui.helpVisible) {
    tui.helpVisible = false;
    if (tui.phase === 'splash') {
      startSplashAnimation();
    } else {
      paintWithScroll();
    }
    return;
  }

  // ── Splash-phase inputs ────────────────────────────────────────
  if (tui.phase === 'splash') {
    // q on splash: exit the TUI entirely
    if (ch === 'q') {
      process.stdout.write('\x1b[?1049l\x1b[?25h\x1b[?1000l\x1b[?1006l');
      process.exit(0);
    }
    // Enter/r: restore last dashboard if available
    if ((key.name === 'return' || ch === 'r') && tui.lastBlocks) {
      tui.blocks = tui.lastBlocks;
      tui.phase = 'live';
      // Paint immediately so tui.lastContent is set (enables q and scroll)
      const output = runLayout(tui.lastBlocks, null, getWidth());
      paintScreen(output);
      return;
    }
    // l: load saved report
    if (ch === 'l') {
      tui.loadList = listReports();
      if (tui.loadList.length === 0) return;
      tui.loadIdx = 0;
      tui.loadMode = true;
      tui.phase = 'live';
      const overlay = renderLoadOverlay(getWidth());
      tui.lastContent = overlay;
      process.stdout.write('\x1b[2J\x1b[H' + overlay);
      return;
    }
    return;
  }

  if (!tui.lastContent) return;
  const pageSize = Math.max(1, getHeight() - 2);
  let changed = false;

  // ── Load overlay navigation ──────────────────────────────────────
  if (tui.loadMode) {
    if (key.name === 'escape') {
      tui.loadMode = false;
      if (tui.lastBlocks) {
        paintWithScroll();
      } else {
        stopSplashAnimation();
        tui.phase = 'splash';
        startSplashAnimation();
      }
    } else if (key.name === 'up' || ch === 'k') {
      tui.loadIdx = Math.max(0, tui.loadIdx - 1);
      process.stdout.write('\x1b[2J\x1b[H' + renderLoadOverlay(getWidth()));
    } else if (key.name === 'down' || ch === 'j') {
      tui.loadIdx = Math.min(tui.loadList.length - 1, tui.loadIdx + 1);
      process.stdout.write('\x1b[2J\x1b[H' + renderLoadOverlay(getWidth()));
    } else if (key.name === 'return' && tui.loadList.length > 0) {
      try {
        const file = path.join(REPORTS_DIR, tui.loadList[tui.loadIdx]);
        const saved = JSON.parse(fs.readFileSync(file, 'utf8'));
        tui.loadMode = false;
        if (saved.meta) tui.renderMeta = { ...tui.renderMeta, ...saved.meta };
        if (Array.isArray(saved.blocks)) {
          tui.lastBlocks = saved.blocks;
          tui.blocks = saved.blocks;
          repaint();
        }
      } catch { tui.loadMode = false; paintWithScroll(); }
    }
    return;
  }

  // ── Save ──────────────────────────────────────────────────────────
  if (ch === 's') {
    const filename = saveReport();
    if (filename) {
      const msg = `${BRAND}✓${RESET} ${DIM}Saved: ${filename}${RESET}`;
      const w = getWidth();
      const savedFooter = buildFooter(w);
      const confirmFooter = `  ${msg}`;
      tui.lastContent = tui.lastContent.replace(savedFooter, confirmFooter);
      paintWithScroll();
      setTimeout(() => { tui.lastContent = tui.lastContent.replace(confirmFooter, savedFooter); paintWithScroll(); }, 2000);
    }
    return;
  }

  // ── Load ──────────────────────────────────────────────────────────
  if (ch === 'l') {
    tui.loadList = listReports();
    tui.loadIdx = 0;
    tui.loadMode = true;
    process.stdout.write('\x1b[2J\x1b[H' + renderLoadOverlay(getWidth()));
    return;
  }

  // (? and Esc for help handled above, before phase checks)

  // ── Tab focus cycling ────────────────────────────────────────────
  if (key.name === 'tab' && tui.panelIds.length > 0) {
    const ids = tui.panelIds;
    const cur = ids.indexOf(tui.focusedPanel);
    if (key.shift) {
      // Shift+Tab: backwards
      tui.focusedPanel = ids[(cur - 1 + ids.length) % ids.length];
    } else {
      // Tab: forwards (circular)
      tui.focusedPanel = ids[(cur + 1) % ids.length];
    }
    paintWithScroll();
    return;
  }

  // ── Number keys: clipboard copy follow_up (only when complete) ───
  // Guard: ignore digits from mouse SGR sequences — check both escape prefix and recent mouse activity
  const num = parseInt(ch, 10);
  if (num >= 1 && num <= 9 && !key.sequence?.startsWith('\x1b[') && !isMouseRecent() && tui.agentState?.stage === 'complete' && tui.agentState?.follow_ups?.length) {
    const fu = tui.agentState.follow_ups.find(f => f.key === String(num));
    if (fu?.cmd) {
      try {
        // Copy to clipboard (pbcopy on macOS, xclip/xsel on Linux)
        const [clipBin, ...clipArgs] = process.platform === 'darwin'
          ? ['pbcopy']
          : ['xclip', '-selection', 'clipboard'];
        const proc = spawn(clipBin, clipArgs, { stdio: ['pipe', 'ignore', 'ignore'] });
        proc.stdin.end(fu.cmd);
        proc.on('error', () => { /* clipboard unavailable — silent fail */ });
        // Flash confirmation in footer
        const w = getWidth();
        const flash = `  ${BRAND}✓${RESET} ${DIM}Copied: ${fu.cmd}${RESET}`;
        const currentFooter = buildFooter(w);
        tui.lastContent = tui.lastContent.replace(currentFooter, flash);
        paintWithScroll();
        setTimeout(() => {
          tui.lastContent = tui.lastContent.replace(flash, buildFooter(w));
          paintWithScroll();
        }, 2000);
      } catch { /* clipboard unavailable — silent fail */ }
      return;
    }
  }

  // ── Quit — return to splash ────────────────────────────────────────
  if (ch === 'q') {
    stopRenderAnimation();
    tui.lastContent = '';
    // Keep lastBlocks so Enter can restore from splash
    const connectedAgent = tui.agentState?.agent;
    const connectedModel = tui.agentState?.model;
    // Preserve connection info — agent stays connected, only clear render state
    tui.agentState = connectedAgent ? { agent: connectedAgent, model: connectedModel } : null;
    tui.renderMeta = { model: null, tools: null, cost: null, as_of: null };
    // Agent stays connected — q is visual reset only
    tui.blocks = null;
    tui.phase = 'splash';
    const hint = tui.lastBlocks ? 'Enter restore · l load' : 'l load';
    // Show connected status if agent is still connected, not "Waiting for agent"
    const connLabel = connectedAgent
      ? `Connected · ${connectedModel ? `${connectedAgent} · ${connectedModel}` : connectedAgent}`
      : 'Waiting for agent';
    tui.splashMsg = `${connLabel} · ${hint}`;
    startSplashAnimation();
    return;
  }

  // ── Scroll ────────────────────────────────────────────────────────
  if (key.name === 'up' || ch === 'k') { tui.scrollOffset = Math.max(0, tui.scrollOffset - 1); changed = true; }
  else if (key.name === 'down' || ch === 'j') { tui.scrollOffset += 1; changed = true; }
  else if (key.name === 'pageup' || (key.sequence === '\x1b[5~')) { tui.scrollOffset = Math.max(0, tui.scrollOffset - pageSize); changed = true; }
  else if (key.name === 'pagedown' || (key.sequence === '\x1b[6~') || ch === ' ') { tui.scrollOffset += pageSize; changed = true; }
  else if (ch === 'g') { tui.scrollOffset = 0; changed = true; }
  else if (ch === 'G') { tui.scrollOffset = Infinity; changed = true; }

  if (changed) paintWithScroll();
}

function setupKeyboard() {
  readline.emitKeypressEvents(process.stdin);
  if (process.stdin.isTTY) process.stdin.setRawMode(true);
  process.stdin.resume();
  process.stdin.on('keypress', (ch, key) => {
    handleKeypress(ch, key);
  });
}

// ── Resize handling ──────────────────────────────────────────────────────────

function setupResize() {
  process.stdout.on('resize', () => {
    if (tui.phase === 'splash') {
      // Restart splash animation with new dimensions
      startSplashAnimation();
    } else {
      repaint();
    }
  });
}

// ── Entry point ──────────────────────────────────────────────────────────────

async function main() {
  try {
    const { port } = await startServer();
    process.stderr.write(`Heurist Finance Terminal on port ${port}\n`);
  } catch (err) {
    process.stderr.write(`Failed to start: ${err.message}\n`);
    process.exit(1);
  }

  // Enter alt screen
  process.stdout.write('\x1b[?1049h\x1b[2J\x1b[3J\x1b[H\x1b[?25l\x1b[?1000h\x1b[?1006h');

  const restoreScreen = () => {
    process.stdout.write('\x1b[?1006l\x1b[?1000l\x1b[?25h\x1b[?1049l');
  };
  process.on('exit', restoreScreen);
  process.on('SIGINT', () => { restoreScreen(); process.exit(0); });
  process.on('SIGTERM', () => { restoreScreen(); process.exit(0); });
  process.on('uncaughtException', (err) => {
    restoreScreen();
    process.stderr.write(`\nUncaught: ${err.message}\n${err.stack}\n`);
    process.exit(1);
  });
  process.on('unhandledRejection', (err) => {
    restoreScreen();
    process.stderr.write(`\nUnhandled rejection: ${err}\n`);
    process.exit(1);
  });

  // Setup mouse BEFORE keyboard — scroll.js data handler must fire before
  // readline's keypress emitter so isMouseRecent() is set when digits arrive
  setupMouseWheel();
  setupKeyboard();
  setupResize();

  // Subscribe to server events
  emitter.on('render', onRender);
  emitter.on('focus', onFocus);
  emitter.on('layout', onLayout);
  emitter.on('clear', onClear);
  emitter.on('_splash', onSplash);
  emitter.on('_live', onLive);

  // Start splash
  startSplashAnimation();

  // Non-blocking checks
  checkVersion().catch(() => {});
  healthCheck().catch(() => {});

  // Keep alive — process stays running via stdin (raw mode) + HTTP server
}

main().catch(err => {
  process.stderr.write(`Fatal: ${err.message}\n${err.stack}\n`);
  process.exit(1);
});
