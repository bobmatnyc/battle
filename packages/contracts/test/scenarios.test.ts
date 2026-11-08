// Contract test for GET /api/scenarios against the recorded fixture (docs/research/71).
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {test} from "node:test";
import {ContractError, parse, scenarioList} from "../src/index.ts";

type Doc = Record<string, any>;

const recorded: Doc = JSON.parse(readFileSync(new URL("../fixtures/scenarios.json", import.meta.url), "utf8"));

function rejects(edit: (doc: Doc) => void, path: string): void {
  const doc = structuredClone(recorded);
  edit(doc);
  assert.throws(() => parse(scenarioList, doc), (error: unknown) => {
    assert.ok(error instanceof ContractError, String(error));
    assert.equal(error.path, path, error.message);
    return true;
  });
}

test("scenario list fixture validates and names the player-facing scenarios", () => {
  assert.deepEqual(parse(scenarioList, recorded), recorded);
  assert.deepEqual(recorded["scenarios"].map((s: Doc) => s.id),
    ["little-round-top", "hougoumont-north-gate", "concord-north-bridge", "pegasus-bridge", "hill-223-patrol"]);  // docs/research/74, 75
});

test("scenario list refuses a bad field with its path", () => {
  rejects((d) => { d["default"] = "gergovia-recall"; }, "$.default");  // headless only, not in the list
  rejects((d) => { d["scenarios"] = []; }, "$.scenarios");
  rejects((d) => { d["scenarios"][1].id = ""; }, "$.scenarios[1].id");
  rejects((d) => { d["scenarios"][1].date = "18 June 1815"; }, "$.scenarios[1].date");
  rejects((d) => { d["scenarios"][1].id = "little-round-top"; }, "$.scenarios[1].id");
  rejects((d) => { d["scenarios"][0].god = true; }, "$.scenarios[0].god");
});
