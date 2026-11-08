// Standing orders on the desk (docs/research/81 §5, §12): templates from the view, the request
// body, cancel as a superseding instruction, and the list with status.
import assert from "node:assert/strict";
import {test} from "node:test";
import {parse, readCommanderState, standingOrderSubmission, type CommanderState, type StandingOrder} from "@battle/contracts";
import {
  cancelBody, standingBody, standingCurrent, standingHelp, standingListMarkup, standingOptions, standingOutcome,
} from "../src/standing.ts";
import {commander, raw} from "./fixtures.ts";

const commanded = (): CommanderState => readCommanderState(raw("state-commander-commands"));
const clock = (turn: number): string => `T+${turn}`;
const values = (options: string): string[] => [...options.matchAll(/value="([^"]*)"/g)].map((m) => m[1]!);
const pending = (view: CommanderState, profile: string, version: number): StandingOrder => ({
  id: `SO${version + 1}`, side: view.side, unit_id: "U1", profile_id: profile, version, sent_turn: view.turn,
  arrival_turn: view.turn + 3, status: "awaiting_ack", template_version: "standing-orders-v1",
});

test("the desk offers exactly the view's standing templates, with the chosen one's intent", () => {
  const view = commander();
  assert.deepEqual(values(standingOptions(view, "cautious")), view.standing_templates.map((t) => t.id));
  assert.match(standingOptions(view, "cautious"), /<option value="cautious" selected>Preserve the force<\/option>/);
  // A battle with a gate adds its own template (standing.templates); the desk offers it because the view does.
  const gated = {...view, standing_templates: [...view.standing_templates,
    {...view.standing_templates[2]!, id: "close_on_breach", label: "Close the gate <on> a breach", version: "standing-orders-v2",
      message_key: "standing.template.close_on_breach", intent: "Close & bar the gate."}]};
  assert.deepEqual(values(standingOptions(gated, "balanced")), ["balanced", "cautious", "firm", "screen", "close_on_breach"]);
  assert.match(standingOptions(gated, "balanced"), /Close the gate &lt;on&gt; a breach/);
  assert.equal(standingHelp(gated, "close_on_breach"), "Close &amp; bar the gate.");
  assert.equal(standingHelp(view, "unknown"), "");
});

test("a standing order body names the unit, template and cursor; none for an unknown template or a unit that cannot take orders", () => {
  const view = commander();
  const body = standingBody(view, "U1", "screen");
  assert.deepEqual(body, {instruction: {unit_id: "U1", profile_id: "screen"}, game_id: view.game_id, revision: view.revision});
  assert.deepEqual(parse(standingOrderSubmission, body), body);
  assert.equal(standingBody(view, "U1", "close_on_breach"), null, "a template this battle does not offer");
  assert.equal(standingBody(view, view.contacts[0]!.id, "screen"), null, "an enemy contact");
  assert.equal(standingBody(view, null, "screen"), null);
  const routed = {...view, units: view.units.map((u) => (u.id === "U1" ? {...u, status: "routed"} : u))};
  assert.equal(standingBody(routed, "U1", "screen"), null);
});

test("cancel sends the battle's first template, and only while the unit's last instruction differs from it", () => {
  const plain = commander();
  assert.equal(cancelBody(plain, "U1"), null, "U1 still holds the battle's default doctrine");
  const view = commanded();
  assert.deepEqual(cancelBody(view, "U1"), {instruction: {unit_id: "U1", profile_id: "balanced"}, game_id: view.game_id, revision: view.revision});
  const cancelled = {...view, standing_orders: [...view.standing_orders, pending(view, "balanced", 2)]};
  assert.equal(cancelBody(cancelled, "U1"), null, "a cancel already on its way");
  const enRoute = {...plain, standing_orders: [pending(plain, "firm", 1)]};
  assert.equal(cancelBody(enRoute, "U1")?.instruction.profile_id, "balanced", "an instruction still on its way can be superseded");
  assert.equal(cancelBody(view, "U2"), null);
});

test("the unit's doctrine line names the reported template and any instruction still on its way", () => {
  const view = commanded();
  const u1 = view.units.find((u) => u.id === "U1")!;
  assert.equal(standingCurrent(view, u1), "Reported: Preserve the force (version 1).");
  const enRoute = {...view, standing_orders: [...view.standing_orders, pending(view, "firm", 2)]};
  assert.equal(standingCurrent(enRoute, u1), "Reported: Preserve the force (version 1). On its way: SO3 Hold ground firmly, awaiting ack.");
});

test("the standing orders list shows each instruction's unit, template, battlefield time and status, newest first", () => {
  const view = commanded();
  const two = {...view, standing_orders: [...view.standing_orders, pending(view, "firm", 2)]};
  const markup = standingListMarkup(two, clock);
  assert.deepEqual([...markup.matchAll(/data-standing="([^"]+)"/g)].map((m) => m[1]), ["SO3", "SO1"]);
  assert.match(markup, /U1 · Preserve the force · sent T\+0 · delivered/);
  assert.match(markup, /U1 · Hold ground firmly · sent T\+6 · awaiting ack/);
  assert.match(standingListMarkup(commander(), clock), /No standing orders sent/);
});

test("after an unknown outcome the re-read decides what the player is told about a standing order", () => {
  const before = commander();
  const after = commanded();
  assert.match(standingOutcome(before, after, "U1", "cautious").text, /did take the standing order: SO1, U1 Preserve the force, delivered/);
  assert.match(standingOutcome(before, before, "U1", "cautious").text, /no new standing order for U1/);
  assert.equal(standingOutcome(before, after, "U1", "cautious").kind, "unknown");
});
