// Split and combine on the desk (docs/research/81 §6, §12): the desk refuses, in the engine's own
// words, every request the engine would refuse on what the commander view shows; the bodies pass
// the contract; the operations list shows the last notice.
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {test} from "node:test";
import {
  formationSubmission, parse, readCommanderState, type CommanderState, type FormationInstruction, type UnitReport,
} from "@battle/contracts";
import {
  combineBody, combinePartners, combineRefusal, defaultSplit, formationHelp, formationOutcome, MAX_STRENGTH, MIN_STRENGTH,
  operationsMarkup, partnerOptions, PROFILE, REFUSALS, splitBody, splitRefusal,
} from "../src/formations.ts";
import {hexDistance} from "../src/geometry.ts";
import {commander, raw} from "./fixtures.ts";

const clock = (turn: number): string => `T+${turn}`;
const unit = (view: CommanderState, id: string): UnitReport => view.units.find((u) => u.id === id)!;
// The recorded Little Round Top view: U1 (34) at 11,14 and U3 (40) at 10,13 are adjacent; U2 (40)
// at 13,15 is headquarters. U3 is a scout there; `matched` makes it a line company like U1.
const edit = (view: CommanderState, id: string, change: Partial<UnitReport>): CommanderState =>
  ({...view, units: view.units.map((u) => (u.id === id ? {...u, ...change} : u))});
const matched = (): CommanderState => edit(commander(), "U3", {recon_role: "line", recon_skill: 35});

test("hex distance is the POC's odd-row offset distance", () => {
  assert.equal(hexDistance([11, 14], [10, 13]), 1);
  assert.equal(hexDistance([11, 14], [13, 15]), 3);  // grid.distance gives 3
  assert.equal(hexDistance([13, 15], [14, 16]), 1);
  assert.equal(hexDistance([13, 15], [12, 16]), 2);
  assert.equal(hexDistance([4, 4], [4, 4]), 0);
});

test("combine partners are the adjacent own formations the engine would accept", () => {
  const view = matched();
  assert.deepEqual(combinePartners(view, unit(view, "U1")).map((u) => u.id), ["U3"]);
  assert.deepEqual(combinePartners(commander(), unit(commander(), "U1")), [], "a scout and a line company do not combine");
  assert.equal(combineRefusal(commander(), unit(commander(), "U1"), "U3"), REFUSALS.mismatch);
  assert.equal(combineRefusal(view, unit(view, "U1"), "U2"), REFUSALS.apart, "U2 is three hexes away");
  assert.equal(combineRefusal(view, unit(view, "U1"), "U1"), REFUSALS.same);
  assert.equal(combineRefusal(edit(view, "U3", {strength: 47}), unit(view, "U1"), "U3"), REFUSALS.tooStrong);
  assert.equal(combineRefusal(edit(view, "U3", {strength: 46}), unit(view, "U1"), "U3"), null, "34 + 46 is exactly 80");
  assert.equal(combineRefusal(edit(view, "U3", {status: "routed"}), unit(view, "U1"), "U3"), REFUSALS.unable);
  assert.equal(combineRefusal(edit(view, "U3", {status: "merged"}), unit(view, "U1"), "U3"), REFUSALS.unable);
  assert.equal(combineRefusal(edit(view, "U3", {captives: 3}), unit(view, "U1"), "U3"), REFUSALS.fixed);
  assert.equal(combineRefusal(view, unit(view, "U1"), "X9"), REFUSALS.outside);
  // The surviving formation may be headquarters, never the partner.
  const hq = edit(edit(view, "U2", {pos: [11, 13]}), "U1", {strength: 30});
  assert.equal(combineRefusal(hq, unit(hq, "U1"), "U2"), REFUSALS.headquarters);
  assert.equal(combineRefusal(hq, unit(hq, "U2"), "U1"), null);
});

test("a combine body passes the contract, and none is built for a partner the engine would refuse", () => {
  const view = matched();
  const body = combineBody(view, "U1", "U3");
  assert.deepEqual(body, {instruction: {kind: "combine", unit_id: "U1", partner_id: "U3"}, game_id: view.game_id, revision: view.revision});
  assert.deepEqual(parse(formationSubmission, body), body);
  assert.equal(combineBody(view, "U1", "U2"), null);
  assert.equal(combineBody(commander(), "U1", "U3"), null);
});

test("split refusals use the engine's words: count bounds, an adjacent hex, a free hex", () => {
  const view = commander();
  const u2 = unit(view, "U2");
  assert.equal(defaultSplit(u2), 20, "half the strength, as the POC desk");
  assert.equal(splitRefusal(view, u2, 20, [14, 15]), null);
  assert.equal(splitRefusal(view, u2, 11, [14, 15]), REFUSALS.count);
  assert.equal(splitRefusal(view, u2, 29, [14, 15]), REFUSALS.count, "the rest would be 11");
  assert.equal(splitRefusal(view, u2, 28, [14, 15]), null, "the rest is exactly 12");
  assert.equal(splitRefusal(view, u2, 20.5, [14, 15]), REFUSALS.count);
  assert.equal(splitRefusal(view, u2, 20, null), REFUSALS.adjacent);
  assert.equal(splitRefusal(view, u2, 20, [15, 15]), REFUSALS.adjacent);
  const crowded = edit(view, "U1", {pos: [14, 15]});
  assert.equal(splitRefusal(crowded, unit(crowded, "U2"), 20, [14, 15]), REFUSALS.occupied);
  assert.equal(splitRefusal(edit(view, "U2", {status: "routed"}), {...u2, status: "routed"}, 20, [14, 15]), REFUSALS.unable);
  assert.equal(splitRefusal(view, {...u2, captives: 2}, 20, [14, 15]), REFUSALS.fixed);
  const body = splitBody(view, "U2", 20, [14, 15]);
  assert.deepEqual(body, {instruction: {kind: "split", unit_id: "U2", count: 20, destination: [14, 15]}, game_id: view.game_id, revision: view.revision});
  assert.deepEqual(parse(formationSubmission, body), body);
  assert.equal(splitBody(view, "U2", 11, [14, 15]), null);
  assert.equal(splitBody(view, view.contacts[0]!.id, 20, [14, 15]), null);
});

// The desk repeats rules the engine owns; this pins them to apps/poc/battle (no engine change).
test("the desk's formation limits and refusal texts are the engine's own", () => {
  const formations = readFileSync(new URL("../../poc/battle/formations.py", import.meta.url), "utf8");
  const engine = readFileSync(new URL("../../poc/battle/engine.py", import.meta.url), "utf8");
  assert.match(formations, new RegExp(`^MIN_STRENGTH=${MIN_STRENGTH}$`, "m"));
  assert.match(formations, new RegExp(`^MAX_STRENGTH=${MAX_STRENGTH}$`, "m"));
  assert.ok(formations.includes(`PROFILE=(${PROFILE.map((k) => `'${k}'`).join(",")})`), "the matching keys");
  for (const [name, text] of Object.entries(REFUSALS)) {
    const quoted = (source: string): boolean => source.includes(`'${text}'`) || source.includes(`'${text.slice(0, 60)}`);
    assert.ok(quoted(formations) || quoted(engine), `${name}: "${text}" is not the engine's text`);
  }
});

test("the operations list shows each split or combine with its units, status and last notice", () => {
  const view = readCommanderState(raw("state-commander-commands"));
  const markup = operationsMarkup(view, clock);
  assert.deepEqual([...markup.matchAll(/data-operation="([^"]+)"/g)].map((m) => m[1]), ["F2", "F1"]);
  assert.match(markup, /F2 · combine U2 \+ UD1 · completed · sent T\+3/);
  assert.match(markup, /UD1 joined U2; predecessor retired\./);
  assert.match(markup, /F1 · split U2 \(20 to hex 14,15\) · completed/);
  assert.match(operationsMarkup(commander(), clock), /No split or combine sent/);
});

test("after an unknown outcome the re-read decides what the player is told about a split or combine", () => {
  const before = commander();
  const after = readCommanderState(raw("state-commander-commands"));
  const split: FormationInstruction = {kind: "split", unit_id: "U2", count: 20, destination: [14, 15]};
  assert.match(formationOutcome(before, after, split).text, /did take the split: F1, U2, completed/);
  assert.match(formationOutcome(before, before, split).text, /no new split for U2/);
});

test("the formation help says what a split and a combine need, in the engine's words", () => {
  const view = matched();
  const u1 = unit(view, "U1");
  assert.match(formationHelp(view, u1, 17, null), /^Split: click an adjacent hex for the detached troops\. Combine: the partner joins U1, which survives\./);
  assert.match(formationHelp(view, u1, 11, null), new RegExp(`^Split: ${REFUSALS.count}`));
  assert.match(formationHelp(view, u1, 17, [12, 14]), /^Split: 17 troops to hex 12,14\./);
  assert.match(formationHelp(commander(), unit(commander(), "U1"), 17, null), /Combine: no adjacent formation can join this one/);
  assert.equal(partnerOptions(combinePartners(view, u1), "U3"), "<option value=\"U3\" selected>U3 · 40 troops</option>");
});
