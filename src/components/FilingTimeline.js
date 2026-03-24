/**
 * FilingTimeline — vertical chronological timeline for SEC filings.
 *
 * Renders each filing with date, form badge, and description,
 * color-coded by form type (10-K, 10-Q, 8-K, etc.).
 *
 * Pure function: (opts) → string (ANSI-colored, multi-line)
 */
import { c, pc, BOLD, RESET, padRight, padLeft, visLen, ansiTrunc } from '../ansi.js';
import { palette } from '../themes.js';
import { fmtDate } from '../formatters.js';

// Timeline drawing characters
const TL_TOP    = '┬';
const TL_MID    = '│';
const TL_LAST   = '└';
const TL_DOT    = '●';
const TL_LINE   = '─';

// Color roles by form type
const FORM_ROLES = {
  '10-K':  'positive',   // annual — green
  '10-Q':  'accent',     // quarterly — cyan/accent
  '8-K':   'warning',    // current events — amber
  'S-1':   'highlight',  // registration — highlight
  'S-1/A': 'highlight',
  '6-K':   'accent',
  '20-F':  'positive',
  '424B5': 'warning',
  'DEF 14A': 'muted',
  'SC 13G': 'muted',
  'SC 13D': 'negative',
};

function formRole(form) {
  return FORM_ROLES[String(form).toUpperCase()] || FORM_ROLES[String(form)] || 'data';
}

/**
 * Render a SEC filing timeline.
 *
 * @param {Object} opts
 * @param {Array<{date, form, description}>} opts.filings - Filing records (newest first or oldest first)
 * @param {number} [opts.width=80] - Total output width
 * @returns {string} Multi-line ANSI string
 */
export function filingTimeline(opts = {}) {
  const {
    filings = [],
    width = 80,
  } = opts;

  if (!filings.length) {
    return pc('muted', 'No filings');
  }

  const lines = [];

  // Column layout:
  // [connector] [date] [form badge] [description]
  const connW = 2;  // "│ " or "└─"
  const dateW = 8;
  const formW = 10; // badge like "[10-K]" or "[DEF 14A]"
  const descW = Math.max(10, width - connW - dateW - formW - 4);

  // Header
  lines.push(
    ' '.repeat(connW) +
    padRight(pc('label', 'DATE'), dateW) + ' ' +
    padRight(pc('label', 'FORM'), formW) + ' ' +
    pc('label', 'DESCRIPTION')
  );
  lines.push(pc('muted', '─'.repeat(Math.min(width, connW + dateW + formW + descW + 3))));

  for (let i = 0; i < filings.length; i++) {
    const filing = filings[i];
    const isLast = i === filings.length - 1;
    const role   = formRole(filing.form);
    const color  = palette(role);

    // Connector column
    const connector = isLast
      ? c(palette('muted'), `${TL_LAST}${TL_LINE}`)
      : c(palette('muted'), `${TL_MID} `);

    // Date
    const date = padRight(pc('muted', fmtDate(filing.date)), dateW);

    // Form badge — fixed width, colored
    const formStr  = String(filing.form || '?');
    const badge    = padRight(c(color, `[${formStr}]`), formW);

    // Description — truncate to available width
    const descRaw  = String(filing.description || '');
    const descFull = pc('data', descRaw);
    const desc     = ansiTrunc(descFull, descW);

    lines.push(`${connector} ${date} ${badge} ${desc}`);
  }

  return lines.join('\n');
}
