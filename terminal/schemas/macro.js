/**
 * Schema for the "macro" panel.
 *
 * Component: macroDashboard({ pillars: [{label, value, direction, indicators}], width, title })
 *
 * Agents often send { pillar, state, direction } (per SKILL.md).
 * Coercion normalizes to { label, value, stateLabel, direction }.
 */

// Map common state strings to a 0-100 gauge value
const STATE_MAP = {
  sticky:       65,
  hot:          80,
  accelerating: 75,
  rising:       70,
  elevated:     60,
  resilient:    55,
  stable:       50,
  mixed:        50,
  neutral:      50,
  normalizing:  45,
  cooling:      40,
  slowing:      35,
  weakening:    30,
  contracting:  20,
  restrictive:  70,
  tight:        65,
  tightening:   60,
  loose:        30,
  easing:       35,
};

function stateToValue(state) {
  if (state == null) return null;
  const key = String(state).toLowerCase().trim();
  return STATE_MAP[key] ?? 50;
}

export const schema = {
  type: 'object',
  required: ['pillars'],
  defaults: {},
  coerce: {
    pillars: (val, data) => {
      if (Array.isArray(val)) {
        data.pillars = val.map(item => {
          if (typeof item === 'string') {
            return { label: item, value: 0, direction: '' };
          }
          const out = { ...item };
          // pillar → label
          if (out.pillar && !out.label) {
            out.label = out.pillar;
            delete out.pillar;
          }
          // state → stateLabel + numeric value
          if (out.state != null && out.value == null) {
            out.stateLabel = String(out.state).toUpperCase();
            out.value = stateToValue(out.state);
            delete out.state;
          }
          return out;
        });
      }
    },
  },
  validate: (data) => {
    if (!Array.isArray(data.pillars) || data.pillars.length === 0) return null;
    return data;
  },
  shape: 'object with { pillars: [{label, value, direction}] }',
};
