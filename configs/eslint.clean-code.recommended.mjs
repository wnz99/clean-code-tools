import js from "@eslint/js";
import sonarjs from "eslint-plugin-sonarjs";
import unicorn from "eslint-plugin-unicorn";
import tseslint from "typescript-eslint";
import cleanCode from "../src/js/eslint-plugin-clean-code.mjs";

const TEST_FILE_PATTERNS = [
  "**/*.test.{js,jsx,ts,tsx}",
  "**/*.spec.{js,jsx,ts,tsx}",
  "**/__tests__/**/*.{js,jsx,ts,tsx}",
];
const TYPE_SCRIPT_FILE_PATTERNS = ["**/*.{ts,tsx,mts,cts}"];

function scopeToTypeScriptFiles(configs) {
  return configs.map((config) => ({
    ...config,
    files: TYPE_SCRIPT_FILE_PATTERNS,
  }));
}

export default tseslint.config(
  {
    ignores: [
      "**/dist/**",
      "**/build/**",
      "**/coverage/**",
      "**/.next/**",
      "**/node_modules/**",
      "**/*.d.ts",
    ],
  },
  js.configs.recommended,
  ...scopeToTypeScriptFiles(tseslint.configs.strictTypeChecked),
  ...scopeToTypeScriptFiles(tseslint.configs.stylisticTypeChecked),
  {
    files: TYPE_SCRIPT_FILE_PATTERNS,
    languageOptions: {
      parserOptions: {
        projectService: true,
      },
    },
    plugins: {
      "clean-code": cleanCode,
      sonarjs,
      unicorn,
    },
    rules: {
      // CC-033..CC-059, CC-137..CC-142, CC-206: keep units small enough to scan.
      complexity: ["warn", { max: 10 }],
      "max-depth": ["warn", 4],
      "max-lines": [
        "warn",
        {
          max: 300,
          skipBlankLines: true,
          skipComments: true,
        },
      ],
      "max-lines-per-function": [
        "warn",
        {
          max: 50,
          skipBlankLines: true,
          skipComments: true,
        },
      ],
      "max-params": ["warn", 4],
      "sonarjs/cognitive-complexity": ["warn", 15],

      // CC-043, CC-208, CC-224: discourage selector-style boolean modes.
      "@typescript-eslint/strict-boolean-expressions": [
        "warn",
        {
          allowString: false,
          allowNumber: false,
          allowNullableObject: false,
          allowNullableBoolean: false,
          allowNullableString: false,
          allowNullableNumber: false,
          allowAny: false,
        },
      ],

      // CC-018, CC-234: make policy values searchable.
      "@typescript-eslint/no-magic-numbers": [
        "warn",
        {
          ignore: [-1, 0, 1],
          ignoreArrayIndexes: true,
          ignoreDefaultValues: true,
          ignoreEnums: true,
          ignoreNumericLiteralTypes: true,
          ignoreReadonlyClassProperties: true,
        },
      ],
      "sonarjs/no-duplicate-string": ["warn", { threshold: 5 }],

      // CC-068, CC-083: use issue-tracked TODOs and do not park code in comments.
      "no-warning-comments": "off",

      // CC-071..CC-089: reduce noisy or misleading comment patterns.
      "capitalized-comments": "off",
      "lines-around-comment": "off",
      "spaced-comment": [
        "warn",
        "always",
        {
          markers: ["/"],
          exceptions: ["-", "+"],
        },
      ],
      "clean-code/no-commented-out-code": "warn",
      "clean-code/no-noisy-comments": "warn",
      "clean-code/no-redundant-comment": "warn",
      "clean-code/todo-format": "warn",

      // CC-160, CC-214: catch copy/paste branching before it becomes policy drift.
      "sonarjs/no-duplicated-branches": "warn",
      "sonarjs/no-identical-conditions": "warn",
      "sonarjs/no-identical-functions": "warn",

      // CC-237, CC-238: prefer readable predicates and positive branches.
      "no-nested-ternary": "warn",
      "no-negated-condition": "warn",
      "sonarjs/no-inverted-boolean-check": "warn",
      "unicorn/no-negated-condition": "warn",
      "clean-code/no-business-policy-literals": "warn",

      // CC-118, CC-119: avoid surprise nulls in codebases that prefer explicit absence.
      "unicorn/no-null": "warn",
      "@typescript-eslint/no-unnecessary-condition": "warn",
      "@typescript-eslint/prefer-nullish-coalescing": "warn",

      // CC-209, CC-218, CC-221: remove dead and redundant code.
      "@typescript-eslint/no-unused-vars": [
        "warn",
        {
          argsIgnorePattern: "^_",
          caughtErrorsIgnorePattern: "^_",
          varsIgnorePattern: "^_",
        },
      ],
      "no-empty": ["warn", { allowEmptyCatch: false }],
      "no-useless-return": "warn",
      "sonarjs/no-dead-store": "warn",
      "clean-code/no-boolean-flag-arguments": "warn",
      "clean-code/no-output-argument-mutation": "warn",

      // CC-246: keep imports readable and dependency lists explicit.
      "no-restricted-syntax": [
        "warn",
        {
          selector: "ImportDeclaration[specifiers.length>10]",
          message:
            "Import lists with more than 10 specifiers are hard to scan; prefer a narrower module or namespace import when it matches local conventions.",
        },
      ],
      "clean-code/no-train-wrecks": "warn",

      // CC-011, CC-025, CC-249..CC-255: enforce baseline naming consistency.
      "@typescript-eslint/naming-convention": [
        "warn",
        {
          selector: "variableLike",
          format: ["camelCase", "PascalCase", "UPPER_CASE"],
          leadingUnderscore: "allow",
        },
        {
          selector: "typeLike",
          format: ["PascalCase"],
        },
        {
          selector: "function",
          format: ["camelCase", "PascalCase"],
        },
        {
          selector: "variable",
          types: ["boolean"],
          format: ["PascalCase", "UPPER_CASE"],
          prefix: ["is", "has", "can", "should", "will", "did"],
        },
      ],

      // General precision rules that support CC-235 and reduce avoidable ambiguity.
      "@typescript-eslint/consistent-type-imports": [
        "warn",
        {
          prefer: "type-imports",
          fixStyle: "separate-type-imports",
        },
      ],
      "@typescript-eslint/no-confusing-void-expression": "warn",
      "@typescript-eslint/no-floating-promises": "error",
      "@typescript-eslint/no-misused-promises": "error",
      "@typescript-eslint/no-unnecessary-type-assertion": "warn",
      "@typescript-eslint/switch-exhaustiveness-check": "warn",
      "eqeqeq": ["error", "always", { null: "ignore" }],
      "unicorn/explicit-length-check": "warn",
    },
  },
  {
    files: TEST_FILE_PATTERNS,
    rules: {
      "@typescript-eslint/no-magic-numbers": "off",
      "max-lines": "off",
      "max-lines-per-function": "off",
      "max-params": "off",
      "sonarjs/no-identical-functions": "off",
    },
  },
);
