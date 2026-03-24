/**
 * Schema for flowSankey panel.
 *
 * Expected shape: { nodes: [{label, value}], flows?: [{from, to, value?}] }
 */
export const schema = {
  required: ['nodes'],

  coerce: {
    nodes: (val, data) => {
      if (!Array.isArray(val)) data.nodes = [];
    },
    flows: (val, data) => {
      if (!Array.isArray(val)) data.flows = [];
    },
  },

  defaults: {
    flows: [],
  },
};
