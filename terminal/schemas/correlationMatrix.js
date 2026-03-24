/**
 * Schema for correlationMatrix panel.
 *
 * Expected shape: { tickers: string[], matrix: number[][] }
 * Optional: title (string)
 */
export const schema = {
  required: ['tickers', 'matrix'],

  coerce: {
    tickers: (val, data) => {
      if (typeof val === 'string') data.tickers = val.split(',').map(s => s.trim());
    },
  },

  defaults: {
    title: 'CORRELATION MATRIX',
  },
};
