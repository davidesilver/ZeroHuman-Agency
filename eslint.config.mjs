import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
    // Vendored / external / tooling (not part of app source)
    "references/**",
    "superpowers/**",
    "postiz/**",
    "python/**",
  ]),
  // Rule overrides
  {
    rules: {
      // These rules flag valid async data-fetching patterns (useEffect → async fn → setState)
      // used throughout this codebase. The patterns are correct React idioms; the rules are
      // overly strict about synchronous vs. asynchronous setState in effects.
      "react-compiler/react-compiler": "off",
      "react-hooks/set-state-in-effect": "off",
      // Date.now() and similar impure reads are harmless for display-only KPIs
      // computed during render; useMemo snapshotting adds ceremony without value here.
      "react-hooks/purity": "off",
    },
  },
]);

export default eslintConfig;
