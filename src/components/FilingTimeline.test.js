import { describe, it, expect, beforeEach } from 'vitest';
import { filingTimeline } from './FilingTimeline.js';
import { setTheme } from '../themes.js';
import { strip } from '../ansi.js';

const SAMPLE_FILINGS = [
  { date: '2024-02-15', form: '10-K',  description: 'Annual report for fiscal year 2023' },
  { date: '2024-01-10', form: '8-K',   description: 'Earnings release Q4 2023' },
  { date: '2023-11-05', form: '10-Q',  description: 'Quarterly report Q3 2023' },
  { date: '2023-08-07', form: '10-Q',  description: 'Quarterly report Q2 2023' },
  { date: '2023-05-09', form: '10-Q',  description: 'Quarterly report Q1 2023' },
];

beforeEach(() => setTheme('terminal-cyan'));

describe('filingTimeline', () => {
  it('renders a basic filing timeline snapshot', () => {
    const result = filingTimeline({ filings: SAMPLE_FILINGS, width: 80 });
    expect(result).toMatchSnapshot();
  });

  it('shows form types in brackets', () => {
    const result = filingTimeline({ filings: SAMPLE_FILINGS });
    const stripped = strip(result);
    expect(stripped).toContain('[10-K]');
    expect(stripped).toContain('[10-Q]');
    expect(stripped).toContain('[8-K]');
  });

  it('shows formatted dates', () => {
    const result = filingTimeline({ filings: SAMPLE_FILINGS });
    const stripped = strip(result);
    expect(stripped).toContain('Feb 15');
    expect(stripped).toContain('Jan 10');
    expect(stripped).toContain('Nov 5');
  });

  it('shows descriptions', () => {
    const result = filingTimeline({ filings: SAMPLE_FILINGS });
    const stripped = strip(result);
    expect(stripped).toContain('Annual report');
    expect(stripped).toContain('Earnings release');
  });

  it('renders timeline connector characters', () => {
    const result = filingTimeline({ filings: SAMPLE_FILINGS });
    const stripped = strip(result);
    // Should contain the timeline vertical bar and closing connector
    expect(stripped).toContain('│');
    expect(stripped).toContain('└');
  });

  it('last entry uses └─ connector', () => {
    const result = filingTimeline({ filings: SAMPLE_FILINGS });
    const lines = result.split('\n');
    // last line (after header + divider) = lines[lines.length - 1]
    const lastLine = strip(lines[lines.length - 1]);
    expect(lastLine.startsWith('└')).toBe(true);
  });

  it('non-last entries use │ connector', () => {
    const result = filingTimeline({ filings: SAMPLE_FILINGS });
    const lines = result.split('\n');
    // first data row is lines[2]
    const firstDataLine = strip(lines[2]);
    expect(firstDataLine.startsWith('│')).toBe(true);
  });

  it('handles a single filing', () => {
    const result = filingTimeline({
      filings: [{ date: '2024-03-01', form: 'S-1', description: 'IPO registration statement' }],
      width: 80,
    });
    const stripped = strip(result);
    expect(stripped).toContain('[S-1]');
    expect(stripped).toContain('IPO registration');
    expect(result).toMatchSnapshot();
  });

  it('handles empty filings', () => {
    const result = filingTimeline({ filings: [] });
    expect(strip(result)).toContain('No filings');
  });

  it('handles unknown form types gracefully', () => {
    const result = filingTimeline({
      filings: [{ date: '2024-01-01', form: 'DEF 14A', description: 'Proxy statement' }],
    });
    const stripped = strip(result);
    expect(stripped).toContain('[DEF 14A]');
    expect(stripped).toContain('Proxy statement');
  });

  it('handles SC 13D form with negative color', () => {
    const result = filingTimeline({
      filings: [{ date: '2024-01-01', form: 'SC 13D', description: 'Activist stake filing' }],
    });
    expect(result).toMatchSnapshot();
  });

  it('renders with narrow width', () => {
    const result = filingTimeline({ filings: SAMPLE_FILINGS, width: 60 });
    expect(result).toMatchSnapshot();
  });

  it('renders in dracula theme', () => {
    setTheme('dracula');
    const result = filingTimeline({ filings: SAMPLE_FILINGS, width: 80 });
    expect(result).toMatchSnapshot();
  });

  it('renders in bloomberg theme', () => {
    setTheme('bloomberg');
    const result = filingTimeline({ filings: SAMPLE_FILINGS, width: 80 });
    expect(result).toMatchSnapshot();
  });

  it('renders in monochrome theme', () => {
    setTheme('monochrome');
    const result = filingTimeline({ filings: SAMPLE_FILINGS, width: 80 });
    expect(result).toMatchSnapshot();
  });
});
