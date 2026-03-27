/**
 * version.js — Version check against Heurist Mesh registry.
 *
 * Checks for updates on startup. Updates the VERSION object in state.js.
 * Fallback: if registry is unreachable, show installed version only.
 */

import https from 'https';
import { VERSION } from './state.js';

const REGISTRY_URL = 'https://registry.npmjs.org/@heurist-network/skills/latest';

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
 * Check for updates and mutate the shared VERSION object.
 * Called at startup. Non-blocking, non-fatal.
 */
export async function checkVersion() {
  const latest = await fetchLatestVersion();
  if (!latest) return; // unreachable — keep defaults (upToDate: true)

  VERSION.latest = latest;
  VERSION.upToDate = VERSION.current === latest ||
    normalizeVersion(VERSION.current) >= normalizeVersion(latest);
}

/**
 * Strip 'v' prefix and convert to comparable number.
 */
function normalizeVersion(v) {
  const parts = String(v).replace(/^v/, '').split('.').map(Number);
  return (parts[0] || 0) * 1_000_000 + (parts[1] || 0) * 1_000 + (parts[2] || 0);
}
