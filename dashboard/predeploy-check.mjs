/** Refuse to deploy a wrangler.toml that still holds template placeholders.
 *
 *  wrangler.toml is COMMITTED with placeholders on purpose — ACCESS_AUD, ACCESS_TEAM_DOMAIN
 *  and the D1 id are infrastructure identifiers that do not belong in a public repo. But
 *  `wrangler deploy` pushes [vars] verbatim, so running `npm run deploy` from a clean
 *  checkout OVERWRITES the live values with the literal string "REPLACE": Access JWT
 *  verification fails closed, the DB binding points at nothing, every request 403s or 500s —
 *  and wrangler prints a successful deploy. The failure is total, silent, and one command away.
 *
 *  Fill the real values in locally (the file is git-tracked, so do NOT commit them), or
 *  deploy with --var overrides.
 */
import { readFileSync } from "node:fs";

const toml = readFileSync(new URL("./wrangler.toml", import.meta.url), "utf8");
const bad = [...toml.matchAll(/^\s*([A-Za-z_]+)\s*=\s*"(REPLACE[^"]*)"/gm)];
if (bad.length) {
  console.error("\n  ✘ refusing to deploy: wrangler.toml still has template placeholders\n");
  for (const [, k, v] of bad) console.error(`      ${k} = "${v}"`);
  console.error("\n    Deploying these would push them to PRODUCTION as literal strings:");
  console.error("      ACCESS_* -> Access JWT verification fails closed -> the dashboard 403s");
  console.error("      database_id -> the DB binding resolves to nothing -> every query 500s");
  console.error("    and wrangler would report success. Fill the real values in locally");
  console.error("    (do NOT commit them), then re-run.\n");
  process.exit(1);
}
