// Contract test for GET /api/map against the recorded fixture (docs/research/70).
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {test} from "node:test";
import {ContractError, mapDocument, parse} from "../src/index.ts";

type Doc = Record<string, any>;

const recorded: Doc = JSON.parse(readFileSync(new URL("../fixtures/map.json", import.meta.url), "utf8"));

function rejects(edit: (doc: Doc) => void, path: string): void {
  const doc = structuredClone(recorded);
  edit(doc);
  assert.throws(() => parse(mapDocument, doc), (error: unknown) => {
    assert.ok(error instanceof ContractError, String(error));
    assert.equal(error.path, path, error.message);
    return true;
  });
}

test("map fixture validates", () => {
  assert.deepEqual(parse(mapDocument, recorded), recorded);
  assert.equal(recorded["cells"].length, recorded["cols"] * recorded["rows"]);
});

test("map refuses a bad field with its path", () => {
  rejects((d) => { delete d["setting"].start_local; }, "$.setting.start_local");
  // An offset would let a browser shift the battle's local time.
  rejects((d) => { d["setting"].start_local = "1863-07-02T16:30:00Z"; }, "$.setting.start_local");
  rejects((d) => { d["setting"].start_local = "1863-07-02T16:30:00-05:00"; }, "$.setting.start_local");
  rejects((d) => { d["cells"][3].pos = [d["cols"], 0]; }, "$.cells[3].pos");
  rejects((d) => { d["cells"][3].terrain = 7; }, "$.cells[3].terrain");
  rejects((d) => { d["radius"] = 0; }, "$.radius");
  rejects((d) => { d["debug"] = true; }, "$.debug");
});

test("map accepts a null source url and extra cell keys", () => {
  const doc = structuredClone(recorded);
  doc["source_url"] = null;
  doc["cells"][0].area = "orchard";
  assert.deepEqual(parse(mapDocument, doc), doc);
});
