/**
 * MCP Bridge — SSE → Streamable HTTP
 *
 * Proxies the Heurist Mesh MCP server (SSE transport) into Streamable HTTP
 * at localhost:3100 (configurable via HEURIST_BRIDGE_PORT), so agents that only support Streamable HTTP can use
 * Heurist Mesh tools (Codex CLI, OpenCode, etc.).
 *
 * Architecture:
 *   [Local HTTP client] → POST /mcp → [Bridge] → SSEClientTransport → [Upstream SSE]
 *
 * Endpoints:
 *   POST /mcp     — Streamable HTTP endpoint (main)
 *   GET  /sse     — Legacy SSE passthrough (for SSE-preferring agents)
 *   GET  /health  — Status: {status, upstream, uptime, pid, port}
 *
 * State file: ~/.heurist/bridge.json  {pid, port, startedAt}
 */

import http from 'http';
import net from 'net';
import fs from 'fs';
import path from 'path';
import os from 'os';
import { fileURLToPath } from 'url';
import { SSEClientTransport } from '@modelcontextprotocol/sdk/client/sse.js';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const BRIDGE_PORT = parseInt(process.env.HEURIST_BRIDGE_PORT, 10) || 3100;
const UPSTREAM_URL = process.env.HEURIST_MCP_URL || 'https://mcp.mesh.heurist.xyz/toolaac6abd2/sse';
const STATE_DIR = path.join(os.homedir(), '.heurist');
const STATE_FILE = path.join(STATE_DIR, 'bridge.json');
const RECONNECT_DELAY_MS = 3000;
const REQUEST_TIMEOUT_MS = 30000;

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const SKILL_DIR = path.resolve(__dirname, '..');

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
 * Find an available port for the bridge.
 * Tries BRIDGE_PORT first; if occupied, falls back to port 0 (OS-assigned).
 */
export async function findBridgePort(preferredPort = BRIDGE_PORT) {
  if (await isPortAvailable(preferredPort)) {
    return preferredPort;
  }
  // Port occupied — let the OS assign a free one
  return 0;
}

// ---------------------------------------------------------------------------
// Local MCP resources (served by bridge, not upstream)
// ---------------------------------------------------------------------------

const LOCAL_RESOURCES = [
  {
    uri: 'heurist://skill',
    name: 'Heurist Finance Skill Guide',
    description: 'Complete skill instructions — routing, panel shapes, data mapping, follow-up patterns',
    mimeType: 'text/markdown',
  },
  {
    uri: 'heurist://tools',
    name: 'Heurist Finance Tool Reference',
    description: '25 MCP tools across 4 agents (Yahoo Finance, FRED, SEC EDGAR, Exa Search)',
    mimeType: 'text/markdown',
  },
  {
    uri: 'heurist://layouts',
    name: 'Heurist Finance TUI Layouts',
    description: 'Available layouts (deep-dive, compare, macro, pulse) and their expected panel schemas',
    mimeType: 'text/markdown',
  },
];

function readResource(uri) {
  switch (uri) {
    case 'heurist://skill': {
      const fp = path.join(SKILL_DIR, 'SKILL.md');
      return fs.existsSync(fp) ? fs.readFileSync(fp, 'utf8') : '# Heurist Finance\n\nSKILL.md not found.';
    }
    case 'heurist://tools': {
      const fp = path.join(SKILL_DIR, 'SKILL.md');
      if (!fs.existsSync(fp)) return '# Tools\n\nSKILL.md not found.';
      const content = fs.readFileSync(fp, 'utf8');
      const start = content.indexOf('## Available MCP Tools');
      const end = content.indexOf('## Render Dispatch Protocol');
      if (start === -1) return '# Tools\n\nTool section not found in SKILL.md.';
      return content.slice(start, end === -1 ? undefined : end).trim();
    }
    case 'heurist://layouts': {
      return [
        '# Heurist Finance Layouts',
        '',
        '## deep-dive',
        'Single-ticker analysis. Panels: quote, chart, technical, analyst, macro, news, verdict',
        '',
        '## compare',
        'Multi-ticker side-by-side (2-5 tickers). Panels: tickers[], {TICKER: {quote, analyst, chart}}',
        '',
        '## macro',
        'Economic regime dashboard. Panels: macro (pillars), gauges[]',
        '',
        '## pulse',
        'Broad market snapshot. Panels: quote, chart, news',
      ].join('\n');
    }
    default:
      return null;
  }
}

/**
 * Handle MCP methods locally before forwarding to upstream.
 * Returns a response object if handled, or null to forward upstream.
 */
function handleLocalMethod(msg) {
  const { method, id, params } = msg;

  switch (method) {
    case 'resources/list':
      return { jsonrpc: '2.0', id, result: { resources: LOCAL_RESOURCES } };

    case 'resources/templates/list':
      return { jsonrpc: '2.0', id, result: { resourceTemplates: [] } };

    case 'resources/read': {
      const uri = params?.uri;
      const content = uri ? readResource(uri) : null;
      if (content === null) {
        return { jsonrpc: '2.0', id, error: { code: -32602, message: `Unknown resource: ${uri}` } };
      }
      return {
        jsonrpc: '2.0', id,
        result: { contents: [{ uri, mimeType: 'text/markdown', text: content }] },
      };
    }

    case 'prompts/list':
      return { jsonrpc: '2.0', id, result: { prompts: [] } };

    default:
      return null; // forward to upstream
  }
}

// ---------------------------------------------------------------------------
// Tool name remapping: strip verbose agent prefixes, use dot namespaces
// ---------------------------------------------------------------------------

const AGENT_PREFIXES = [
  { prefix: 'yahoofinanceagent_', ns: 'yahoo.' },
  { prefix: 'fredmacroagent_macro_', ns: 'fred.' },
  { prefix: 'secedgaragent_', ns: 'sec.' },
  { prefix: 'exasearchdigestagent_exa_', ns: 'exa.' },
];

function toCleanName(upstreamName) {
  for (const { prefix, ns } of AGENT_PREFIXES) {
    if (upstreamName.startsWith(prefix)) {
      return ns + upstreamName.slice(prefix.length);
    }
  }
  return upstreamName;
}

function toUpstreamName(cleanName) {
  for (const { prefix, ns } of AGENT_PREFIXES) {
    if (cleanName.startsWith(ns)) {
      return prefix + cleanName.slice(ns.length);
    }
  }
  return cleanName;
}

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

let _server = null;
let _port = null;
let _startedAt = null;
let _upstreamConnected = false;
let _upstreamTransport = null;
let _reconnectTimer = null;
let _handlersRegistered = false;
let _shuttingDown = false;

/**
 * Map of JSON-RPC request IDs to pending response resolvers.
 * Keyed by the string representation of the request ID.
 * @type {Map<string, {resolve: Function, reject: Function, timer: NodeJS.Timeout}>}
 */
const _pendingRequests = new Map();

/**
 * Set of active SSE response objects for legacy GET /sse connections.
 * @type {Set<http.ServerResponse>}
 */
const _sseClients = new Set();

// ---------------------------------------------------------------------------
// State file helpers (same pattern as terminal/server.js)
// ---------------------------------------------------------------------------

export function writeStateFile(data) {
  fs.mkdirSync(STATE_DIR, { recursive: true });
  const tmp = STATE_FILE + '.tmp';
  fs.writeFileSync(tmp, JSON.stringify(data, null, 2), { mode: 0o600 });
  fs.renameSync(tmp, STATE_FILE);
}

export function deleteStateFile() {
  try {
    fs.unlinkSync(STATE_FILE);
  } catch {
    // ignore — file may not exist
  }
}

// ---------------------------------------------------------------------------
// Upstream SSE connection
// ---------------------------------------------------------------------------

/**
 * Connect to the upstream Heurist SSE server.
 * Sets up message routing: all upstream messages are dispatched to pending
 * request resolvers or broadcast to legacy SSE clients.
 */
export async function connectUpstream(upstreamUrl = UPSTREAM_URL) {
  if (_upstreamTransport) {
    try {
      await _upstreamTransport.close();
    } catch {
      // ignore close errors
    }
    _upstreamTransport = null;
  }

  _upstreamConnected = false;

  const transport = new SSEClientTransport(new URL(upstreamUrl));

  transport.onmessage = (message) => {
    _dispatchUpstreamMessage(message);
  };

  transport.onerror = (error) => {
    console.error('[bridge] upstream error:', error.message);
    _upstreamConnected = false;
    _scheduleReconnect(upstreamUrl);
  };

  transport.onclose = () => {
    console.error('[bridge] upstream closed, scheduling reconnect');
    _upstreamConnected = false;
    _upstreamTransport = null;
    _scheduleReconnect(upstreamUrl);
  };

  try {
    await transport.start();
    _upstreamTransport = transport;
    _upstreamConnected = true;
    console.log('[bridge] upstream connected:', upstreamUrl);
  } catch (err) {
    console.error('[bridge] upstream connect failed:', err.message);
    _upstreamConnected = false;
    _upstreamTransport = null;
    _scheduleReconnect(upstreamUrl);
  }
}

function _scheduleReconnect(upstreamUrl) {
  if (_reconnectTimer) return; // already scheduled
  _reconnectTimer = setTimeout(async () => {
    _reconnectTimer = null;
    console.log('[bridge] reconnecting to upstream...');
    await connectUpstream(upstreamUrl);
  }, RECONNECT_DELAY_MS);
  _reconnectTimer.unref?.(); // don't prevent process exit
}

/**
 * Dispatch an upstream message to the right pending request or SSE clients.
 * Handles both responses (with id) and notifications (no id).
 */
function _dispatchUpstreamMessage(message) {
  // Broadcast to all legacy SSE clients
  _broadcastSse(message);

  // If the message has an id, it's a response — resolve the pending request
  if (message.id !== undefined && message.id !== null) {
    const key = String(message.id);
    const pending = _pendingRequests.get(key);
    if (pending) {
      clearTimeout(pending.timer);
      _pendingRequests.delete(key);
      pending.resolve(message);
    }
  }
}

/**
 * Send a JSON-RPC message to the upstream SSE server.
 * Returns a Promise that resolves with the upstream response (matched by id).
 * For notifications (no id), resolves immediately after send.
 */
export async function sendToUpstream(message) {
  if (!_upstreamTransport || !_upstreamConnected) {
    throw new Error('upstream not connected');
  }

  // Notifications and responses have no id — fire and forget
  if (message.id === undefined || message.id === null) {
    await _upstreamTransport.send(message);
    return null;
  }

  const key = String(message.id);

  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      _pendingRequests.delete(key);
      reject(new Error(`request ${key} timed out after ${REQUEST_TIMEOUT_MS}ms`));
    }, REQUEST_TIMEOUT_MS);

    _pendingRequests.set(key, { resolve, reject, timer });

    _upstreamTransport.send(message).catch((err) => {
      clearTimeout(timer);
      _pendingRequests.delete(key);
      reject(err);
    });
  });
}

// ---------------------------------------------------------------------------
// Legacy SSE broadcast helpers
// ---------------------------------------------------------------------------

function _broadcastSse(message) {
  if (_sseClients.size === 0) return;
  const data = `data: ${JSON.stringify(message)}\n\n`;
  for (const res of _sseClients) {
    try {
      res.write(data);
    } catch {
      _sseClients.delete(res);
    }
  }
}

// ---------------------------------------------------------------------------
// HTTP request body helper
// ---------------------------------------------------------------------------

function readBody(req) {
  return new Promise((resolve, reject) => {
    let body = '';
    req.on('data', (chunk) => { body += chunk; });
    req.on('end', () => {
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

async function handleRequest(req, res) {
  const { method, url } = req;

  // GET /health
  if (method === 'GET' && url === '/health') {
    const uptime = _startedAt ? Math.floor((Date.now() - _startedAt) / 1000) : 0;
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({
      status: 'ok',
      upstream: _upstreamConnected ? 'connected' : 'disconnected',
      uptime,
      pid: process.pid,
      port: _port,
      startedAt: _startedAt,
    }));
    return;
  }

  // POST /mcp — Streamable HTTP endpoint
  if (method === 'POST' && url === '/mcp') {
    let message;
    try {
      message = await readBody(req);
    } catch {
      res.writeHead(400, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'Invalid JSON in request body' }));
      return;
    }

    if (!_upstreamConnected) {
      res.writeHead(503, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({
        jsonrpc: '2.0',
        id: message?.id ?? null,
        error: { code: -32603, message: 'Bridge upstream not connected' },
      }));
      return;
    }

    // Handle batch (array) vs single message
    const isBatch = Array.isArray(message);
    const messages = isBatch ? message : [message];

    try {
      const responses = await Promise.all(
        messages.map(async (msg) => {
          // Handle locally-served methods (resources, prompts)
          const local = handleLocalMethod(msg);
          if (local) return local;

          try {
            // Remap clean tool names → upstream names on tools/call
            let outMsg = msg;
            if (msg.method === 'tools/call' && msg.params?.name) {
              outMsg = { ...msg, params: { ...msg.params, name: toUpstreamName(msg.params.name) } };
            }

            let resp = await sendToUpstream(outMsg);

            // Augment initialize response to include resources capability
            if (msg.method === 'initialize' && resp?.result?.capabilities) {
              resp = JSON.parse(JSON.stringify(resp));
              resp.result.capabilities.resources = { listChanged: false };
            }

            // Remap upstream tool names → clean names on tools/list response
            if (msg.method === 'tools/list' && resp?.result?.tools) {
              resp = JSON.parse(JSON.stringify(resp));
              resp.result.tools = resp.result.tools.map(t => ({
                ...t,
                name: toCleanName(t.name),
              }));
            }

            return resp; // null for notifications
          } catch (err) {
            // If the message has an id, return a JSON-RPC error response
            if (msg.id !== undefined && msg.id !== null) {
              return {
                jsonrpc: '2.0',
                id: msg.id,
                error: { code: -32603, message: err.message },
              };
            }
            return null;
          }
        })
      );

      // Filter out nulls (notifications produce no response)
      const validResponses = responses.filter((r) => r !== null);

      if (validResponses.length === 0) {
        // Notifications only — 202 Accepted with no body
        res.writeHead(202);
        res.end();
        return;
      }

      const body = isBatch ? validResponses : validResponses[0];
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify(body));
    } catch (err) {
      res.writeHead(500, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({
        jsonrpc: '2.0',
        id: message?.id ?? null,
        error: { code: -32603, message: err.message },
      }));
    }
    return;
  }

  // GET /sse — legacy SSE passthrough
  if (method === 'GET' && url === '/sse') {
    res.writeHead(200, {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
    });
    res.write(': connected\n\n');

    _sseClients.add(res);

    req.on('close', () => {
      _sseClients.delete(res);
    });

    // Keep alive ping every 30s
    const keepAlive = setInterval(() => {
      try {
        res.write(': ping\n\n');
      } catch {
        clearInterval(keepAlive);
        _sseClients.delete(res);
      }
    }, 30000);
    keepAlive.unref?.();

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
 * Start the bridge HTTP server and connect to upstream SSE.
 * Returns {server, port}.
 */
export async function startBridge({ upstreamUrl = UPSTREAM_URL, skipUpstream = false } = {}) {
  _startedAt = Date.now();

  const server = http.createServer((req, res) => {
    handleRequest(req, res).catch((err) => {
      console.error('[bridge] unhandled handler error:', err);
      if (!res.headersSent) {
        res.writeHead(500);
        res.end();
      }
    });
  });

  _server = server;

  // Find an available port: try BRIDGE_PORT, fall back to OS-assigned (port 0)
  const listenPort = await findBridgePort(BRIDGE_PORT);

  await new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(listenPort, '127.0.0.1', () => resolve());
  });

  // Use the actual port the OS assigned (important when listenPort was 0)
  const actualPort = server.address().port;
  _port = actualPort;

  writeStateFile({
    pid: process.pid,
    port: actualPort,
    startedAt: new Date(_startedAt).toISOString(),
  });

  if (!skipUpstream) {
    // Connect to upstream in background — don't block server start
    connectUpstream(upstreamUrl).catch((err) => {
      console.error('[bridge] initial upstream connect error:', err.message);
    });
  }

  if (!_handlersRegistered) {
    process.on('SIGTERM', shutdown);
    process.on('SIGINT', shutdown);
    _handlersRegistered = true;
  }

  console.log(`[bridge] listening on http://127.0.0.1:${actualPort}`);
  return { server, port: actualPort };
}

/**
 * Graceful shutdown: close upstream, drain connections, clean up state file.
 */
export async function shutdown() {
  if (_shuttingDown) return;
  _shuttingDown = true;

  if (_reconnectTimer) {
    clearTimeout(_reconnectTimer);
    _reconnectTimer = null;
  }

  // Reject all pending requests
  for (const [key, pending] of _pendingRequests) {
    clearTimeout(pending.timer);
    pending.reject(new Error('bridge shutting down'));
    _pendingRequests.delete(key);
  }

  // Close legacy SSE clients
  for (const res of _sseClients) {
    try { res.end(); } catch { /* ignore */ }
  }
  _sseClients.clear();

  // Close upstream transport
  if (_upstreamTransport) {
    try {
      await _upstreamTransport.close();
    } catch { /* ignore */ }
    _upstreamTransport = null;
  }

  deleteStateFile();

  if (_server) {
    if (typeof _server.closeAllConnections === 'function') {
      _server.closeAllConnections();
    }
    _server.close(() => process.exit(0));
    setTimeout(() => process.exit(0), 3000).unref();
  } else {
    process.exit(0);
  }
}

// ---------------------------------------------------------------------------
// Exported test helpers (for unit tests to inspect/set state)
// ---------------------------------------------------------------------------

export function _getState() {
  return {
    upstreamConnected: _upstreamConnected,
    pendingRequests: _pendingRequests,
    sseClients: _sseClients,
    server: _server,
    port: _port,
    startedAt: _startedAt,
  };
}

export function _setUpstreamConnected(val) {
  _upstreamConnected = val;
}

export function _setUpstreamTransport(transport) {
  if (!transport) {
    // Reject any pending requests when disconnecting
    for (const [key, pending] of _pendingRequests) {
      clearTimeout(pending.timer);
      pending.reject(new Error('upstream disconnected'));
      _pendingRequests.delete(key);
    }
  }
  _upstreamTransport = transport;
  _upstreamConnected = transport !== null;
  // Wire up message dispatch so mock transports work in tests
  if (transport) {
    transport.onmessage = (message) => {
      _dispatchUpstreamMessage(message);
    };
  }
}

// ---------------------------------------------------------------------------
// Entrypoint (run as script)
// ---------------------------------------------------------------------------

// ESM: detect if this file is the entry point
const _thisFile = fileURLToPath(import.meta.url);
if (process.argv[1] && path.resolve(process.argv[1]) === _thisFile) {
  startBridge().catch((err) => {
    console.error('[bridge] fatal:', err);
    process.exit(1);
  });
}
