// ESLint flat config for the static frontend (plain ES modules in the browser, no bundler).
import js from "@eslint/js";
import globals from "globals";

export default [
  js.configs.recommended,
  {
    files: ["static/js/**/*.js"],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: "module",
      globals: globals.browser,
    },
    rules: {
      eqeqeq: ["error", "always"],
      "no-var": "error",
      "prefer-const": "error",
      "no-unused-vars": ["error", { argsIgnorePattern: "^_" }],
      "no-shadow": "error",
      "object-shorthand": "error",
      "prefer-template": "error",
      curly: ["error", "multi-line"],
      // The UI builds the DOM with createElement/textContent only (see format.js `el`).
      "no-restricted-properties": [
        "error",
        { property: "innerHTML", message: "Use el()/textContent so model text can never inject HTML." },
        { property: "outerHTML", message: "Use el()/textContent so model text can never inject HTML." },
      ],
    },
  },
  {
    // theme.js is a classic script loaded in <head> so the theme applies before first paint.
    files: ["static/js/theme.js"],
    languageOptions: { sourceType: "script" },
  },
];
