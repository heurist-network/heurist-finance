/**
 * io.js — HTTP helpers, MCP auto-fetch, report save/load.
 *
 * No React dependencies. Pure I/O and network functions.
 */

import http from 'http';
import fs from 'fs';
import path from 'path';
import { BRAND, BOLD, DIM, RESET, REPORTS_DIR, tui } from './state.js';
import { emitter } from './server.js';

// ── HTTP helpers (no external deps) ─────────────────────────────────────────

export function httpGet(url) {
  return new Promise((resolve, reject) => {
    const req = http.get(url, { timeout: 3000 }, (res) => {
      let data = '';
      res.on('data', (c) => { data += c; });
      res.on('end', () => {
        try { resolve(JSON.parse(data)); } catch { resolve(data); }
      });
    });
    req.on('error', reject);
    req.on('timeout', () => { req.destroy(); reject(new Error('timeout')); });
  });
}

export function httpPost(url, body) {
  return new Promise((resolve, reject) => {
    const payload = JSON.stringify(body);
    const parsed = new URL(url);
    const req = http.request({
      hostname: parsed.hostname,
      port: parsed.port,
      path: parsed.pathname,
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(payload) },
      timeout: 10000,
    }, (res) => {
      let data = '';
      res.on('data', (c) => { data += c; });
      res.on('end', () => {
        try { resolve(JSON.parse(data)); } catch { resolve(data); }
      });
    });
    req.on('error', reject);
    req.on('timeout', () => { req.destroy(); reject(new Error('timeout')); });
    req.write(payload);
    req.end();
  });
}

/**
 * Health check on startup — probe MCP endpoint, update splash status.
 * Never auto-fetches data or transitions to live. TUI stays on splash
 * until an agent connects via POST /render.
 */
export async function healthCheck() {
  const MCP_URL = 'https://mesh.heurist.xyz/mcp/heurist-finance';
  let mcpUp = false;
  try {
    // Streamable HTTP health: POST a JSON-RPC initialize and check for a valid response
    const https = await import('https');
    mcpUp = await new Promise((resolve) => {
      const payload = JSON.stringify({ jsonrpc: '2.0', id: 1, method: 'initialize', params: { protocolVersion: '2025-03-26', capabilities: {}, clientInfo: { name: 'hf-tui', version: '1.0.0' } } });
      const req = https.request(MCP_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Accept': 'application/json, text/event-stream', 'Content-Length': Buffer.byteLength(payload) },
        timeout: 5000,
      }, (res) => {
        let data = '';
        res.on('data', (c) => { data += c; });
        res.on('end', () => resolve(res.statusCode >= 200 && res.statusCode < 300));
      });
      req.on('error', () => resolve(false));
      req.on('timeout', () => { req.destroy(); resolve(false); });
      req.write(payload);
      req.end();
    });
  } catch {
    mcpUp = false;
  }

  if (mcpUp) {
    emitter.emit('_splash', { msg: 'Waiting for agent · MCP ready' });
  } else {
    emitter.emit('_splash', { msg: 'Waiting for agent · MCP offline' });
  }
}

// ── Report save/load ────────────────────────────────────────────────────────

export function saveReport() {
  if (!tui.lastBlocks) return null;
  try {
    fs.mkdirSync(REPORTS_DIR, { recursive: true });
    const ts = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 16);
    const textBlock = tui.lastBlocks.find(b => b.text);
    const ticker = textBlock?.text?.match(/·\s+([A-Z/]+)/)?.[1]?.replace(/\s/g, '-') ?? 'report';
    const filename = `${ts}-${ticker}.json`;
    fs.writeFileSync(
      path.join(REPORTS_DIR, filename),
      JSON.stringify({ blocks: tui.lastBlocks, meta: tui.renderMeta, saved_at: new Date().toISOString() }, null, 2),
    );
    return filename;
  } catch { return null; }
}

export function listReports() {
  try {
    if (!fs.existsSync(REPORTS_DIR)) return [];
    return fs.readdirSync(REPORTS_DIR)
      .filter(f => f.endsWith('.json'))
      .sort()
      .reverse()
      .slice(0, 20);
  } catch { return []; }
}
