import { ESLint } from "eslint";
import assert from "node:assert/strict";
import { mkdtemp, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { describe, it } from "node:test";

describe("eslint clean-code recommended config", () => {
  it("is importable through the package export path", async () => {
    const cleanCodeConfig = await import("clean-code-tools/configs/eslint.clean-code.recommended.mjs");

    assert.ok(Array.isArray(cleanCodeConfig.default));
  });

  it("does not apply project-service parsing to ordinary mjs files", async () => {
    const { default: cleanCodeConfig } = await import("clean-code-tools/configs/eslint.clean-code.recommended.mjs");
    const cwd = await mkdtemp(path.join(tmpdir(), "clean-code-eslint-"));
    await writeFile(path.join(cwd, "config.mjs"), "export default [];\n");

    const eslint = new ESLint({
      cwd,
      overrideConfig: cleanCodeConfig,
      overrideConfigFile: true,
    });
    const [result] = await eslint.lintFiles(["config.mjs"]);

    assert.equal(result.fatalErrorCount, 0);
    assert.equal(result.parseErrors?.length ?? 0, 0);
  });

  it("runs the exported config and reports custom clean-code rules on TypeScript files", async () => {
    const { default: cleanCodeConfig } = await import("clean-code-tools/configs/eslint.clean-code.recommended.mjs");
    const cwd = await mkdtemp(path.join(tmpdir(), "clean-code-eslint-"));
    await writeFile(
      path.join(cwd, "tsconfig.json"),
      JSON.stringify(
        {
          compilerOptions: {
            module: "ESNext",
            moduleResolution: "Bundler",
            strict: true,
            target: "ES2022",
          },
          include: ["sample.ts"],
        },
        null,
        2,
      ),
    );
    await writeFile(
      path.join(cwd, "sample.ts"),
      "function sendInvoice(invoice: Invoice): void {\n  send(invoice, true);\n}\n",
    );

    const eslint = new ESLint({
      cwd,
      overrideConfig: cleanCodeConfig,
      overrideConfigFile: true,
    });
    const [result] = await eslint.lintFiles(["sample.ts"]);
    const ruleIds = result.messages.map((message) => message.ruleId);

    assert.ok(ruleIds.includes("clean-code/no-boolean-flag-arguments"));
  });
});
