// Fails loudly when Node is older than the desk needs (docs/research/71, review #5).
// Plain JavaScript, so any Node can run it, including one without type stripping.
// The desk server uses `import.meta.main` (Node >= 24.2); package.json `engines` says the same.
// Usage: node scripts/check-node.mjs [version]   (the argument exists for the test)
const NEED = [24, 2];
const version = process.argv[2] || process.versions.node;
const [major, minor] = version.split(".").map(Number);
if (!(major > NEED[0] || (major === NEED[0] && minor >= NEED[1]))) {
  console.error(`The TypeScript desk needs Node >= ${NEED.join(".")} (import.meta.main); found ${version}.`);
  process.exit(1);
}
