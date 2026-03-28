/**
 * render.test.js — Tests for render.js pure functions.
 *
 * Covers: focusIndicator, renderHelpOverlay, buildFooter state variants.
 */

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { tui } from './state.js';
import { focusIndicator, renderHelpOverlay, buildFooter, buildHeader, paintScreen, paintWithScroll } from './render.js';

// ── Helpers ─────────────────────────────────────────────────────────────────

const strip = (s) => s.replace(/\x1b\[[0-9;]*m/g, '');

// ── focusIndicator ──────────────────────────────────────────────────────────

describe('focusIndicator', () => {
  beforeEach(() => {
    tui.focusedPanel = null;
  });

  it('returns empty string when no panel is focused', () => {
    expect(focusIndicator('quote')).toBe('');
  });

  it('returns empty string when panel name is null', () => {
    tui.focusedPanel = 'quote';
    expect(focusIndicator(null)).toBe('');
  });

  it('returns empty string for non-focused panel', () => {
    tui.focusedPanel = 'chart';
    expect(focusIndicator('quote')).toBe('');
  });

  it('returns indicator with ▶ for focused panel', () => {
    tui.focusedPanel = 'quote';
    const result = focusIndicator('quote');
    expect(strip(result)).toContain('▶');
    expect(strip(result)).toContain('Tab next');
  });
});

// ── renderHelpOverlay ───────────────────────────────────────────────────────

describe('renderHelpOverlay', () => {
  it('renders full help page for normal terminals', () => {
    const origRows = process.stdout.rows;
    process.stdout.rows = 24;
    const result = renderHelpOverlay(80);
    const text = strip(result);
    expect(text).toContain('NAVIGATION');
    expect(text).toContain('ACTIONS');
    expect(text).toContain('Scroll up / down');
    expect(text).toContain('Save report');
    expect(text).toContain('Quit terminal');
    process.stdout.rows = origRows;
  });

  it('renders single summary row for tiny terminals (<12 rows)', () => {
    const origRows = process.stdout.rows;
    process.stdout.rows = 10;
    const result = renderHelpOverlay(80);
    expect(result.split('\n').length).toBe(1);
    expect(strip(result)).toContain('scroll');
    expect(strip(result)).toContain('quit');
    process.stdout.rows = origRows;
  });

  it('includes splash screen keys', () => {
    const origRows = process.stdout.rows;
    process.stdout.rows = 24;
    const result = renderHelpOverlay(80);
    const text = strip(result);
    expect(text).toContain('SPLASH SCREEN');
    expect(text).toContain('Restore last dashboard');
    process.stdout.rows = origRows;
  });
});

// ── buildFooter state variants ──────────────────────────────────────────────

describe('buildFooter', () => {
  beforeEach(() => {
    tui.renderMeta = { model: null, tools: null, cost: null, as_of: null };
    tui.agentState = null;
  });

  it('renders standard footer with no agent state', () => {
    const result = buildFooter(80);
    expect(strip(result)).toContain('HEURIST FINANCE');
    expect(strip(result)).toContain('save');
    expect(strip(result)).toContain('quit');
  });

  it('renders gathering state footer with spinner and tool progress', () => {
    tui.agentState = {
      stage: 'gathering',
      skill: 'analyst',
      query: 'NVDA',
      tools: { called: 3, total: 8, current: 'yahoo.quote_snapshot' },
    };
    const result = buildFooter(120);
    const plain = strip(result);
    expect(plain).toContain('Gathering');
    expect(plain).toContain(':analyst');
    expect(plain).toContain('NVDA');
    expect(plain).toContain('3/8');
  });

  it('renders analyzing state footer', () => {
    tui.agentState = { stage: 'analyzing', skill: 'compare', query: 'NVDA AMD' };
    const result = buildFooter(100);
    expect(strip(result)).toContain('Analyzing');
    expect(strip(result)).toContain(':compare');
  });

  it('renders complete state footer with follow_ups hint', () => {
    tui.agentState = {
      stage: 'complete',
      follow_ups: [
        { key: '1', label: 'Drill deeper', cmd: '/heurist-finance use analyst skill. NVDA' },
        { key: '2', label: 'Compare AMD', cmd: '/heurist-finance use compare skill. NVDA AMD' },
      ],
    };
    const result = buildFooter(120);
    expect(strip(result)).toContain('1-2 drill');
  });

  it('renders meta in footer when present', () => {
    tui.renderMeta = { model: 'opus', tools: '8', cost: '$0.12', as_of: null };
    const result = buildFooter(120);
    const plain = strip(result);
    expect(plain).toContain('opus');
    expect(plain).toContain('8 tools');
    expect(plain).toContain('~$0.12');
  });
});

// ── paintScreen + paintWithScroll integration ─────────────────────────────

describe('paintScreen → paintWithScroll', () => {
  let writes;
  let origWrite, origCols, origRows;

  beforeEach(() => {
    writes = [];
    origWrite = process.stdout.write;
    origCols = process.stdout.columns;
    origRows = process.stdout.rows;
    process.stdout.write = (data) => { writes.push(data); return true; };
    process.stdout.columns = 80;
    process.stdout.rows = 24;
    tui.lastContent = '';
    tui.scrollOffset = 0;
    tui.agentState = null;
    tui.renderMeta = { model: null, tools: null, cost: null, as_of: null };
  });

  afterEach(() => {
    process.stdout.write = origWrite;
    process.stdout.columns = origCols;
    process.stdout.rows = origRows;
  });

  it('does not throw on short content (no scroll)', () => {
    expect(() => paintScreen('hello\nworld')).not.toThrow();
    expect(tui.lastContent).toContain('hello');
    expect(tui.lastContent).toContain('HEURIST FINANCE');
  });

  it('does not throw on overflowing content (scroll mode)', () => {
    const longContent = Array.from({ length: 50 }, (_, i) => `line ${i}`).join('\n');
    expect(() => paintScreen(longContent)).not.toThrow();
  });

  it('does not throw when paintWithScroll is called repeatedly', () => {
    const longContent = Array.from({ length: 50 }, (_, i) => `line ${i}`).join('\n');
    paintScreen(longContent);
    tui.scrollOffset = 5;
    expect(() => paintWithScroll()).not.toThrow();
    tui.scrollOffset = 0;
    expect(() => paintWithScroll()).not.toThrow();
  });

  it('does not throw during gathering state', () => {
    tui.agentState = { stage: 'gathering', skill: 'analyst', query: 'NVDA', tools: { called: 3, total: 8 } };
    const content = Array.from({ length: 30 }, (_, i) => `data ${i}`).join('\n');
    expect(() => paintScreen(content)).not.toThrow();
  });
});
