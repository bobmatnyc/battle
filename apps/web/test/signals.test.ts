// Slice 4a (docs/research/81 §4): the signals panel lists the codewords the commander's
// headquarters has received, from the commander view's `signals` only, in battlefield time.
import assert from "node:assert/strict";
import {test} from "node:test";
import {readCommanderReplay} from "@battle/contracts";
import {signalsMarkup} from "../src/panels.ts";
import {commander, raw} from "./fixtures.ts";

const clock = (turn: number): string => `T${turn}`;
// A recorded Pegasus Bridge commander view (guard-only entry) after Ham arrived (record.py).
const pegasus = () => readCommanderReplay(raw("replay-commander-pegasus"));

test("a delivered codeword is listed with its meaning, bridge, sender and arrival time", () => {
  const view = pegasus();
  assert.equal(view.side, "british");
  assert.deepEqual(view.signals?.map((s) => [s.codeword, s.delivered_turn]), [["Ham", 12]]);
  const markup = signalsMarkup(view, clock)!;
  assert.match(markup, /<li data-codeword="Ham">/);
  assert.match(markup, /<strong>Ham<\/strong>/);
  assert.match(markup, /Canal bridge taken intact\./);
  assert.match(markup, /Caen Canal bridge/, "the bridge by the name the commander view gives it");
  assert.match(markup, /received T12 · from D25/);
  assert.doesNotMatch(markup, /\bturn\b|revision|sent_turn/i, "battlefield time only, no turn");
});

test("a battle with no authored codeword has no panel; one awaiting its codeword says so", () => {
  assert.equal(commander().signals, undefined);
  assert.equal(signalsMarkup(commander(), clock), null);
  assert.equal(signalsMarkup({...pegasus(), signals: []}, clock), "<li>No codeword received.</li>");
});

test("signal text is escaped and the newest codeword comes first", () => {
  const view = pegasus();
  const ham = view.signals![0]!;
  const markup = signalsMarkup({...view, signals: [ham, {...ham, codeword: "<b>Jack</b>", delivered_turn: 20, bridge: "unknown-bridge"}]}, clock)!;
  assert.ok(markup.indexOf("Jack") < markup.indexOf(">Ham<"), "newest first");
  assert.match(markup, /&lt;b&gt;Jack&lt;\/b&gt;/);
  assert.match(markup, /unknown-bridge/, "a bridge the view does not name is shown by its id");
});
