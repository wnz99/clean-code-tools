import cleanCode from "clean-code-tools/configs/eslint.clean-code.recommended.mjs";

export default [
  {
    ignores: [
      ".codex/**",
      ".venv/**",
      "build/**",
      "dist/**",
      "node_modules/**",
      "sample-apps/**",
    ],
  },
  ...cleanCode,
];
