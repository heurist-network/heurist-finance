/**
 * logo.js — Brand mark for Heurist Finance.
 *
 * Candlestick-inspired mark (3 bars — bull/neutral/bear) + bold wordmark.
 * 4 rows, ~45 chars wide. Monospace-native, asymmetric.
 */

const BRAND = '\x1b[38;2;192;255;0m';    // #C0FF00 lime
const LIME_D = '\x1b[38;2;100;180;0m';   // dark lime
const LIME_M = '\x1b[38;2;155;220;0m';   // mid lime
const BOLD   = '\x1b[1m';
const DIM    = '\x1b[2m';
const RESET  = '\x1b[0m';

export const LOGO_B = [
  `${LIME_D}  ▐${RESET} ${LIME_M}▐▌${RESET} ${BRAND}█${RESET}   ${BRAND}${BOLD}HEURIST${RESET}`,
  `${LIME_D}  █${RESET} ${LIME_M}██${RESET} ${BRAND}█${RESET}   ${BRAND}${BOLD}FINANCE${RESET}`,
  `${LIME_M}  █${RESET} ${BRAND}██${RESET} ${LIME_D}▐${RESET}`,
  `${BRAND}  ▐${RESET} ${LIME_D}▐▌${RESET} ${LIME_M}▐${RESET}   ${DIM}The view that matters.${RESET}`,
];

/**
 * Render the full brand identity block.
 * @returns {string}
 */
export function brandBlock() {
  return LOGO_B.join('\n');
}
