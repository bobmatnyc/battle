// Contract tests for the standing-order and formation commands (docs/research/81 §5, §6, §12):
// the request bodies the POC accepted, the commander view after them, and malformed bodies.
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {test} from "node:test";
import {
  commanderState, ContractError, formationSubmission, parse, readFormationSubmission, readStandingOrderSubmission,
  standingOrderSubmission, standingTemplate, type Check,
} from "../src/index.ts";

type Doc = Record<string, any>;

const fixture = (name: string): Doc =>
  JSON.parse(readFileSync(new URL(`../fixtures/${name}.json`, import.meta.url), "utf8"));
const standing = fixture("standing-request");
const split = fixture("formation-request-split");
const combine = fixture("formation-request-combine");
const after = fixture("state-commander-commands");

function fails(check: Check<unknown>, input: unknown, path: string): void {
  assert.throws(() => parse(check, input), (error: unknown) => {
    assert.ok(error instanceof ContractError, `expected ContractError, got ${String(error)}`);
    assert.equal(error.path, path, error.message);
    return true;
  });
}

const edited = (doc: Doc, edit: (copy: Doc) => void): Doc => {
  const copy = structuredClone(doc);
  edit(copy);
  return copy;
};

test("the recorded standing-order, split and combine bodies validate unchanged", () => {
  assert.deepEqual(readStandingOrderSubmission(standing), standing);
  assert.deepEqual(readFormationSubmission(split), split);
  assert.deepEqual(readFormationSubmission(combine), combine);
  assert.equal(split["instruction"].kind, "split");
  assert.equal(combine["instruction"].kind, "combine");
});

test("the commander view after a standing order, a split and a combine validates with typed items", () => {
  const view = parse(commanderState, after);
  assert.deepEqual(view, after);
  const [order] = view.standing_orders;
  assert.deepEqual([order?.unit_id, order?.profile_id, order?.version, order?.status], ["U1", "cautious", 1, "delivered"]);
  assert.deepEqual(view.formation_ops.map((o) => [o.kind, o.unit_id, o.partner_id ?? null, o.status]),
    [["split", "U2", null, "completed"], ["combine", "U2", "UD1", "completed"]]);
  assert.match(view.formation_ops[1]?.reason ?? "", /UD1 joined U2/);
  assert.deepEqual(view.standing_templates.map((t) => t.id), ["balanced", "cautious", "firm", "screen"]);
  assert.equal(typeof view.standing_templates[0]?.intent, "string");
});

test("a standing template is typed: every recorded template passes and a mistyped one is rejected", () => {
  for (const template of after["standing_templates"]) assert.deepEqual(parse(standingTemplate, template), template);
  fails(commanderState, edited(after, (d) => { d["standing_templates"][0].label = 3; }), "$.standing_templates[0].label");
  fails(commanderState, edited(after, (d) => { delete d["standing_templates"][1].intent; }), "$.standing_templates[1].intent");
});

test("standing orders and formation operations in the view are typed", () => {
  fails(commanderState, edited(after, (d) => { delete d["standing_orders"][0].profile_id; }), "$.standing_orders[0].profile_id");
  fails(commanderState, edited(after, (d) => { d["standing_orders"][0].version = "1"; }), "$.standing_orders[0].version");
  fails(commanderState, edited(after, (d) => { d["formation_ops"][1].partner_id = 7; }), "$.formation_ops[1].partner_id");
  fails(commanderState, edited(after, (d) => { d["formation_ops"][0].kind = "merge"; }), "$.formation_ops[0].kind");
  fails(commanderState, edited(after, (d) => { delete d["formation_ops"][0].unit_id; }), "$.formation_ops[0].unit_id");
});

const malformed: [string, Check<unknown>, Doc, (d: Doc) => void, string][] = [
  ["standing: extra instruction key", standingOrderSubmission, standing, (d) => { d["instruction"].priority = 1; }, "$.instruction.priority"],
  ["standing: missing profile", standingOrderSubmission, standing, (d) => { delete d["instruction"].profile_id; }, "$.instruction.profile_id"],
  ["standing: empty unit id", standingOrderSubmission, standing, (d) => { d["instruction"].unit_id = ""; }, "$.instruction.unit_id"],
  ["standing: no cursor", standingOrderSubmission, standing, (d) => { delete d["revision"]; }, "$.revision"],
  ["standing: side named", standingOrderSubmission, standing, (d) => { d["side"] = "confederate"; }, "$.side"],
  ["standing: instruction as text", standingOrderSubmission, standing, (d) => { d["instruction"] = "cautious"; }, "$.instruction"],
  ["formation: unknown kind", formationSubmission, split, (d) => { d["instruction"].kind = "merge"; }, "$.instruction.kind"],
  ["formation: no instruction", formationSubmission, split, (d) => { delete d["instruction"]; }, "$.instruction"],
  ["split: partner given", formationSubmission, split, (d) => { d["instruction"].partner_id = "U1"; }, "$.instruction.partner_id"],
  ["split: count as text", formationSubmission, split, (d) => { d["instruction"].count = "20"; }, "$.instruction.count"],
  ["split: fractional count", formationSubmission, split, (d) => { d["instruction"].count = 20.5; }, "$.instruction.count"],
  ["split: no destination", formationSubmission, split, (d) => { delete d["instruction"].destination; }, "$.instruction.destination"],
  ["split: destination as text", formationSubmission, split, (d) => { d["instruction"].destination = "14,15"; }, "$.instruction.destination"],
  ["combine: count given", formationSubmission, combine, (d) => { d["instruction"].count = 20; }, "$.instruction.count"],
  ["combine: no partner", formationSubmission, combine, (d) => { delete d["instruction"].partner_id; }, "$.instruction.partner_id"],
  ["combine: with itself", formationSubmission, combine, (d) => { d["instruction"].partner_id = d["instruction"].unit_id; }, "$.instruction.partner_id"],
  ["formation: wrong game id type", formationSubmission, combine, (d) => { d["game_id"] = 7; }, "$.game_id"],
];

test("a malformed standing-order or formation request is rejected with the path of the bad field", async (t) => {
  for (const [name, check, source, edit, path] of malformed) {
    await t.test(name, () => {
      parse(check, source);  // the recorded body passes
      fails(check, edited(source, edit), path);
    });
  }
});
