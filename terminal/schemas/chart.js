/**
 * Schema for the "chart" panel.
 *
 * Component: brailleChart({ values, width, height, showAxis, volume, label })
 */
export const schema = {
  type: 'object',
  required: ['values'],
  defaults: {
    height: 6,
    showAxis: true,
  },
  coerce: {
    // Ensure values is an array of numbers
    values: (val, data) => {
      if (typeof val === 'string') {
        try { data.values = JSON.parse(val); } catch { /* leave as-is */ }
      }
    },
  },
  validate: (data) => {
    // values must be a non-empty array
    if (!Array.isArray(data.values) || data.values.length === 0) return null;
    return data;
  },
  shape: 'object with { values: number[] }',
  mcpTools: ['yahoofinanceagent_price_history', 'fredmacroagent_macro_series_history', 'fredmacroagent_macro_vintage_history', 'secedgaragent_xbrl_fact_trends'],
};
