/**
 * version.js — Version check against Heurist Mesh registry.
 *
 * Checks for updates on startup. Updates the VERSION object in state.js.
 * Fallback: if registry is unreachable, show installed version only.
 */

import https from 'https';
import fs from 'fs';
import path from 'path';
import os from 'os';
import { VERSION } from './state.js';

const REGISTRY_URL = 'https://registry.npmjs.org/@heurist-network/skills/latest';
const VERSION_CACHE = path.join(os.homedir(), '.heurist', 'version.json');
const CACHE_TTL_MS = 3600_000; // 1 hour

/**
 * Fetch latest version from npm registry (where marketplace skills are published).
 * Returns version string or null on failure.
 */
function fetchLatestVersion() {
  return new Promise((resolve) => {
    const req = https.get(REGISTRY_URL, { timeout: 3000 }, (res) => {
      let data = '';
      res.on('data', (c) => { data += c; });
      res.on('end', () => {
        try {
          const pkg = JSON.parse(data);
          resolve(pkg.version || null);
        } catch { resolve(null); }
      });
    });
    req.on('error', () => resolve(null));
    req.on('timeout', () => { req.destroy(); resolve(null); });
  });
}

/**
 * Read cached version check result.
 */
function readCache() {
  try {
    const raw = fs.readFileSync(VERSION_CACHE, 'utf8');
    const cached = JSON.parse(raw);
    if (Date.now() - cached.checkedAt < CACHE_TTL_MS) {
      return cached;
    }
  } catch { /* cache miss */ }
  return null;
}

/**
 * Write version check result to cache.
 */
function writeCache(latest) {
  try {
    fs.mkdirSync(path.dirname(VERSION_CACHE), { recursive: true });
    fs.writeFileSync(VERSION_CACHE, JSON.stringify({
      latest,
      checkedAt: Date.now(),
    }));
  } catch { /* cache write failure is non-fatal */ }
}

/**
 * Check for updates and mutate the shared VERSION object.
 * Called at startup. Non-blocking, non-fatal.
 */
export async function checkVersion() {
  // Check cache first
  const cached = readCache();
  if (cached?.latest) {
    VERSION.latest = cached.latest;
    VERSION.upToDate = VERSION.current === cached.latest ||
      normalizeVersion(VERSION.current) >= normalizeVersion(cached.latest);
    return;
  }

  // Fetch from registry
  const latest = await fetchLatestVersion();
  if (!latest) return; // unreachable — keep defaults (upToDate: true)

  VERSION.latest = latest;
  VERSION.upToDate = VERSION.current === latest ||
    normalizeVersion(VERSION.current) >= normalizeVersion(latest);
  writeCache(latest);
}

/**
 * Strip 'v' prefix and convert to comparable number.
 */
function normalizeVersion(v) {
  const parts = String(v).replace(/^v/, '').split('.').map(Number);
  return (parts[0] || 0) * 1_000_000 + (parts[1] || 0) * 1_000 + (parts[2] || 0);
}
