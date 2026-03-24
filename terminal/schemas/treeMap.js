/**
 * Schema for treeMap panel.
 *
 * Expected shape: { items: [{label, weight, value?, color?}] }
 * Optional: height (number, default 10)
 */
export const schema = {
  required: ['items'],

  coerce: {
    items: (val, data) => {
      if (!Array.isArray(val)) data.items = [];
    },
    height: (val, data) => {
      data.height = Number(val) || 10;
    },
  },

  defaults: {
    height: 10,
  },
};
