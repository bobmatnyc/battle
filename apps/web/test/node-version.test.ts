// The desk's Node requirement is declared and checked before `make web` serves.
import assert from "node:assert/strict";
import {spawnSync} from "node:child_process";
import {readFileSync} from "node:fs";
import {fileURLToPath} from "node:url";
import {test} from "node:test";

const check = fileURLToPath(new URL("../scripts/check-node.mjs", import.meta.url));
const run = (version: string) => spawnSync(process.execPath, [check, version], {encoding: "utf8"});

test("an older Node fails the check with a reason; 24.2 and later pass", () => {
  for (const old of ["22.6.0", "24.1.9", "23.11.0"]) {
    const result = run(old);
    assert.equal(result.status, 1, old);
    assert.match(result.stderr, /needs Node >= 24\.2/);
  }
  for (const ok of ["24.2.0", "24.10.1", "26.12.1"]) assert.equal(run(ok).status, 0, ok);
});

test("the Node requirement is declared in engines and checked by make web and smoke-web", () => {
  for (const file of ["../package.json", "../../../package.json"]) {
    const manifest = JSON.parse(readFileSync(new URL(file, import.meta.url), "utf8"));
    assert.equal(manifest.engines?.node, ">=24.2", file);
  }
  const makefile = readFileSync(new URL("../../../Makefile", import.meta.url), "utf8");
  for (const target of ["web", "smoke-web"]) {
    const rule = makefile.match(new RegExp(`^${target}:[^\\n]*\\n((?:\\t[^\\n]*\\n)+)`, "m"));
    assert.ok(rule, target);
    assert.match(rule[1]!.split("\n")[0]!, /check-node\.mjs/, `${target} checks Node first`);
  }
});
