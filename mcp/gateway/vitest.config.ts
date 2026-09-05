import { cloudflareTest } from "@cloudflare/vitest-plugin";
import { defineConfig } from "vitest/config";

const testSecret = Array.from({ length: 8 }, (_, index) => `test-part-${index}`).join("-");

export default defineConfig({
  plugins: [
    cloudflareTest({
      wrangler: { configPath: "./wrangler.jsonc" },
      miniflare: {
        bindings: {
          EDITOR_SHARED_SECRET: testSecret,
          REPORT_SHARED_SECRET: testSecret,
        },
        serviceBindings: {
          SCORER: async () => Response.json({ ok: true, scorerVersion: "2.8.11" }),
        },
      },
    }),
  ],
  test: {
    include: ["test/**/*.spec.ts"],
    testTimeout: 15_000,
  },
});
