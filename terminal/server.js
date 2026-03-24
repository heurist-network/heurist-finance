/**
 * TUI Server — HTTP bridge between agents and Ink React app.
 *
 * Agents POST render commands to /render.
 * An EventEmitter singleton bridges those commands to the Ink app.
 * State is persisted to ~/.heurist/tui.json for PID/port tracking.
 */

import http from 'http';
import net from 'net';
import fs from 'fs';
import path from 'path';
import os from 'os';
import { EventEmitter } from 'events';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const DEFAULT_PORT = 7707;
const STATE_DIR = path.join(os.homedir(), '.heurist');
const STATE_FILE = path.join(STATE_DIR, 'tui.json');
const VALID_ACTIONS = new Set(['render', 'focus', 'layout', 'clear']);
import { createRequire } from 'module';
// __PKG_VERSION__ is replaced by esbuild at bundle time (scripts/build.js define).
// When running from source (vite-node / tests), fall back to reading package.json.
const _require = createRequire(import.meta.url);
function _resolveVersion() {
  if (typeof __PKG_VERSION__ !== 'undefined') return __PKG_VERSION__;
  try { return _require('../package.json').version; } catch { return '0.0.0'; }
}
const VERSION = _resolveVersion();

// ── Session lock — one agent per TUI ────────────────────────────────────────
let _agentSession = null; // { agent: string, connectedAt: number } or null

// Valid theme names from src/themes.js
const VALID_THEMES = new Set([
  'terminal-cyan',
  'bloomberg',
  'monochrome',
  'solarized-dark',
  'dracula',
  'heurist',
]);

// ---------------------------------------------------------------------------
// EventEmitter singleton
// ---------------------------------------------------------------------------

export const emitter = new EventEmitter();
emitter.setMaxListeners(20);


// ---------------------------------------------------------------------------
// Server state
// ---------------------------------------------------------------------------

let _server = null;
let _handlersRegistered = false;
let _shuttingDown = false;
let _port = null;
let _startedAt = null;
let _layout = 'default';
let _panelCount = 0;

// ---------------------------------------------------------------------------
// Port management
// ---------------------------------------------------------------------------

/**
 * Test whether a port is available by attempting to bind to it.
 * Returns a Promise<boolean>.
 */
export function isPortAvailable(port) {
  return new Promise((resolve) => {
    const tester = net.createServer();
    tester.once('error', () => resolve(false));
    tester.once('listening', () => {
      tester.close(() => resolve(true));
    });
    tester.listen(port, '127.0.0.1');
  });
}

/**
 * Find an available port.
 * Tries DEFAULT_PORT first, then up to 5 random ports in [10000, 60000).
 */
export async function findPort() {
  if (await isPortAvailable(DEFAULT_PORT)) {
    return DEFAULT_PORT;
  }

  for (let attempt = 0; attempt < 5; attempt++) {
    const candidate = Math.floor(Math.random() * 50000) + 10000;
    if (await isPortAvailable(candidate)) {
      return candidate;
    }
  }

  throw new Error('Could not find an available port after 5 attempts');
}

// ---------------------------------------------------------------------------
// State file
// ---------------------------------------------------------------------------

/**
 * Write state file atomically (tmp → rename) with mode 0o600.
 */
export function writeStateFile(data) {
  fs.mkdirSync(STATE_DIR, { recursive: true });

  const tmp = STATE_FILE + '.tmp';
  fs.writeFileSync(tmp, JSON.stringify(data, null, 2), { mode: 0o600 });
  fs.renameSync(tmp, STATE_FILE);
}

/**
 * Delete the state file if it exists.
 */
export function deleteStateFile() {
  try {
    fs.unlinkSync(STATE_FILE);
  } catch {
    // ignore — file may not exist
  }
}

// ---------------------------------------------------------------------------
// CORS helpers
// ---------------------------------------------------------------------------

function setCorsHeaders(res) {
  res.setHeader('Access-Control-Allow-Origin', 'http://localhost');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
}

// ---------------------------------------------------------------------------
// Request body parser
// ---------------------------------------------------------------------------

const MAX_BODY_BYTES = 1_048_576; // 1 MB

function readBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    let totalBytes = 0;
    let limitExceeded = false;
    req.on('data', (chunk) => {
      if (limitExceeded) return;
      totalBytes += chunk.length;
      if (totalBytes > MAX_BODY_BYTES) {
        limitExceeded = true;
        const err = new Error('Payload too large');
        err.code = 'PAYLOAD_TOO_LARGE';
        reject(err);
        // Drain remaining data so the socket can be reused cleanly
        req.resume();
        return;
      }
      chunks.push(chunk);
    });
    req.on('end', () => {
      if (limitExceeded) return;
      const body = Buffer.concat(chunks).toString('utf8');
      try {
        resolve(JSON.parse(body));
      } catch {
        reject(new Error('Invalid JSON'));
      }
    });
    req.on('error', reject);
  });
}

// ---------------------------------------------------------------------------
// HTTP request handler
// ---------------------------------------------------------------------------

function handleRequest(req, res) {
  setCorsHeaders(res);

  // Pre-flight
  if (req.method === 'OPTIONS') {
    res.writeHead(204);
    res.end();
    return;
  }

  const { method, url } = req;

  // GET /health — capability negotiation handshake
  if (method === 'GET' && url === '/health') {
    const now = Date.now();
    const uptime = _startedAt ? Math.floor((now - _startedAt) / 1000) : 0;
    const { columns, rows } = process.stdout;
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({
      status: 'ok',
      pid: process.pid,
      port: _port,
      version: VERSION,
      uptime,
      layout: _layout,
      panelCount: _panelCount,
      startedAt: _startedAt,
      width: columns ?? 80,
      height: rows ?? 24,
      theme: 'heurist',
      capabilities: ['patch', 'sections', 'focus', 'state', 'memory', 'connect'],
      agent: _agentSession,
    }));
    return;
  }

  // POST /connect — agent claims this TUI session
  if (method === 'POST' && url === '/connect') {
    readBody(req)
      .then((payload) => {
        const agentId = payload?.agent || 'unknown';

        // If another agent holds the session, reject
        if (_agentSession && _agentSession.agent !== agentId) {
          res.writeHead(409, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({
            error: 'occupied',
            agent: _agentSession.agent,
            connectedAt: _agentSession.connectedAt,
            message: `TUI occupied by ${_agentSession.agent}. Disconnect first or use Research mode.`,
          }));
          return;
        }

        const modelId = payload?.model || null;
        _agentSession = {
          agent: agentId,
          model: modelId,
          query: payload?.query || null,
          connectedAt: Date.now(),
        };
        // Update splash with connection status
        const label = modelId ? `${agentId} · ${modelId}` : agentId;
        emitter.emit('_splash', {
          msg: `Connected · ${label}`,
          agent: _agentSession,
        });
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ status: 'connected', agent: agentId, model: modelId }));
      })
      .catch((err) => {
        if (err?.code === 'PAYLOAD_TOO_LARGE') {
          res.writeHead(413, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ error: 'Payload too large', maxBytes: MAX_BODY_BYTES }));
        } else {
          res.writeHead(400, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ error: 'Invalid JSON' }));
        }
      });
    return;
  }

  // POST /disconnect — agent releases this TUI session
  if (method === 'POST' && url === '/disconnect') {
    readBody(req)
      .then((payload) => {
        const agentId = payload?.agent;

        // Require the agent field
        if (!agentId) {
          res.writeHead(403, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ error: 'Agent ID mismatch' }));
          return;
        }

        // No active session
        if (!_agentSession) {
          res.writeHead(409, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ error: 'No agent connected' }));
          return;
        }

        // Agent ID must match the connected session
        if (_agentSession.agent !== agentId) {
          res.writeHead(403, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ error: 'Agent ID mismatch' }));
          return;
        }

        _agentSession = null;
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ status: 'disconnected' }));
      })
      .catch((err) => {
        if (err?.code === 'PAYLOAD_TOO_LARGE') {
          res.writeHead(413, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ error: 'Payload too large', maxBytes: MAX_BODY_BYTES }));
        } else {
          res.writeHead(400, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ error: 'Invalid JSON' }));
        }
      });
    return;
  }

  // POST /render — requires active session via /connect + agent identity match
  if (method === 'POST' && url === '/render') {
    if (!_agentSession) {
      res.writeHead(403, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'No agent connected. POST /connect first.' }));
      return;
    }
    readBody(req)
      .then((payload) => {
        // Verify caller matches connected agent
        const callerId = payload?.agent;
        if (callerId && callerId !== _agentSession.agent) {
          res.writeHead(403, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ error: 'Agent ID mismatch', connected: _agentSession.agent }));
          return;
        }
        const action = payload?.action;
        if (!VALID_ACTIONS.has(action)) {
          res.writeHead(400, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({
            error: `Invalid action "${action}". Must be one of: ${[...VALID_ACTIONS].join(', ')}`,
          }));
          return;
        }

        // ── File-based enforcement for render action ─────────────────────────
        // The render action requires blocks to be in a file, not inline.
        // Other actions (focus, layout, clear) still accept inline payloads.
        if (action === 'render') {
          // Reject if blocks are sent inline
          if (payload.blocks !== undefined) {
            res.writeHead(400, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({
              error: 'Inline blocks not accepted. Write blocks to a file and POST {"action":"render","file":"/path/to/file.json"}',
            }));
            return;
          }

          // Require a file path
          if (!payload.file) {
            res.writeHead(400, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({
              error: 'Missing "file" field. Write blocks to a file and POST {"action":"render","file":"/path/to/file.json"}',
            }));
            return;
          }

          const filePath = payload.file;

          // Security: only allow files under /tmp/
          if (!filePath.startsWith('/tmp/')) {
            res.writeHead(400, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({
              error: 'File path must be under /tmp/. Got: ' + filePath,
            }));
            return;
          }

          // Read the file
          let fileContents;
          try {
            const stat = fs.statSync(filePath);
            if (stat.size > MAX_BODY_BYTES) {
              res.writeHead(413, { 'Content-Type': 'application/json' });
              res.end(JSON.stringify({ error: 'File too large', maxBytes: MAX_BODY_BYTES }));
              return;
            }
            fileContents = fs.readFileSync(filePath, 'utf8');
          } catch (readErr) {
            if (readErr.code === 'ENOENT') {
              res.writeHead(404, { 'Content-Type': 'application/json' });
              res.end(JSON.stringify({ error: `File not found: ${filePath}` }));
            } else {
              res.writeHead(500, { 'Content-Type': 'application/json' });
              res.end(JSON.stringify({ error: `Could not read file: ${readErr.message}` }));
            }
            return;
          }

          let filePayload;
          try {
            filePayload = JSON.parse(fileContents);
          } catch {
            res.writeHead(400, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ error: `Invalid JSON in file: ${filePath}` }));
            return;
          }

          // Merge file contents into payload (blocks, _state, meta, theme, patch, layout, panels)
          if (filePayload.blocks !== undefined) payload.blocks = filePayload.blocks;
          if (filePayload._state !== undefined) payload._state = filePayload._state;
          if (filePayload.meta !== undefined) payload.meta = filePayload.meta;
          if (filePayload.theme !== undefined) payload.theme = filePayload.theme;
          if (filePayload.patch !== undefined) payload.patch = filePayload.patch;
          if (filePayload.layout !== undefined) payload.layout = filePayload.layout;
          if (filePayload.panels !== undefined) payload.panels = filePayload.panels;
        }
        // ────────────────────────────────────────────────────────────────────

        // Accept optional theme in payload — validate if present
        if (payload.theme !== undefined && !VALID_THEMES.has(payload.theme)) {
          res.writeHead(400, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({
            error: `Unknown theme "${payload.theme}". Valid: ${[...VALID_THEMES].join(', ')}`,
          }));
          return;
        }

        // Update tracked server state from layout/panel/blocks hints
        if (payload.layout) _layout = payload.layout;
        if (Array.isArray(payload.blocks)) _layout = 'blocks';
        if (typeof payload.panelCount === 'number') _panelCount = payload.panelCount;

        try {
          emitter.emit(action, payload);
        } catch (emitErr) {
          res.writeHead(500, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ error: `Render error: ${emitErr.message}` }));
          return;
        }

        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ ok: true }));
      })
      .catch((err) => {
        if (err?.code === 'PAYLOAD_TOO_LARGE') {
          res.writeHead(413, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ error: 'Payload too large', maxBytes: MAX_BODY_BYTES }));
        } else {
          res.writeHead(400, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ error: 'Invalid JSON in request body' }));
        }
      });
    return;
  }

  // 404 for everything else
  res.writeHead(404, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify({ error: 'Not found' }));
}

// ---------------------------------------------------------------------------
// Lifecycle
// ---------------------------------------------------------------------------

/**
 * Start the HTTP server.
 * Finds an available port, binds, writes state file, registers signal handlers.
 * Returns {server, port}.
 */
export async function startServer() {
  const port = await findPort();
  _port = port;
  _startedAt = Date.now();

  const server = http.createServer(handleRequest);
  _server = server;

  await new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(port, '127.0.0.1', () => resolve());
  });

  writeStateFile({
    pid: process.pid,
    port,
    startedAt: new Date(_startedAt).toISOString(),
    version: VERSION,
  });

  // Only register signal handlers once (module-level flag, not listenerCount)
  if (!_handlersRegistered) {
    process.on('SIGTERM', shutdown);
    process.on('SIGINT', shutdown);
    _handlersRegistered = true;
  }

  return { server, port };
}

/**
 * Graceful shutdown: delete state file, close server, exit.
 */
export function shutdown() {
  if (_shuttingDown) return;
  _shuttingDown = true;
  deleteStateFile();
  if (_server) {
    // closeAllConnections() force-drains keep-alive sockets (Node 18.2+)
    if (typeof _server.closeAllConnections === 'function') {
      _server.closeAllConnections();
    }
    _server.close(() => process.exit(0));
    // Force exit if server doesn't close within 3s
    setTimeout(() => process.exit(0), 3000).unref();
  } else {
    process.exit(0);
  }
}

// ---------------------------------------------------------------------------
// Health check utility (for bin scripts / orchestrators)
// ---------------------------------------------------------------------------

/**
 * Read tui.json, verify the process is alive, and HTTP-ping /health.
 * Returns one of:
 *   {alive: true, port, pid}
 *   {alive: false, reason: 'stale'|'no_state', port?, pid?}
 */
export async function checkHealth(stateFilePath = STATE_FILE) {
  let state;
  try {
    const raw = fs.readFileSync(stateFilePath, 'utf8');
    state = JSON.parse(raw);
  } catch {
    return { alive: false, reason: 'no_state' };
  }

  const { pid, port } = state;

  // Check if PID is alive
  try {
    process.kill(pid, 0);
  } catch {
    return { alive: false, reason: 'stale', pid, port };
  }

  // HTTP health check
  try {
    await httpGet(`http://127.0.0.1:${port}/health`);
    return { alive: true, port, pid };
  } catch {
    return { alive: false, reason: 'stale', pid, port };
  }
}

/**
 * Minimal HTTP GET helper (no external deps).
 */
function httpGet(url) {
  return new Promise((resolve, reject) => {
    const req = http.get(url, { timeout: 2000 }, (res) => {
      let body = '';
      res.on('data', (chunk) => { body += chunk; });
      res.on('end', () => resolve({ statusCode: res.statusCode, body }));
    });
    req.on('error', reject);
    req.on('timeout', () => {
      req.destroy();
      reject(new Error('timeout'));
    });
  });
}
