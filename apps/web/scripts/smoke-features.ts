// Browser checks for desk slice 3 (docs/research/73): the map features the commander view
// holds, drawn at the map's scale with a legend and a status on every mark; the grid toggle
// that hides hex outlines and keeps the features; and the commander replay, stepped and
// scrubbed through the POC's recorded revisions with orders closed, then back to live.
import assert from "node:assert/strict";
import {timeAt} from "../src/timeline.ts";
import type {Page} from "./cdp.ts";
import {choose, clickOn, header, openHex, poc, screenshot, until, type Doc} from "./smoke-page.ts";

const LABELS: Record<string, string> = {sourced: "Sourced", reconstructed: "Reconstructed", illustrative: "Illustrative"};

// Every drawn mark (key, status, state, kind, tooltip, label, size) and every legend line.
const DRAWN = `(() => ({
  marks: [...document.querySelectorAll("#map .battle-features [data-feature]")].map(g => {
    const b = g.getBoundingClientRect();
    return {key: g.dataset.feature, status: g.dataset.status, state: g.dataset.state ?? null,
      kind: [...g.classList].find(c => c.startsWith("feature-") && c !== "feature-mark"),
      title: g.querySelector("title")?.textContent ?? "", label: g.querySelector("text")?.textContent ?? "",
      width: b.width, height: b.height};
  }),
  legend: [...document.querySelectorAll("#feature-legend li[data-feature]")].map(li =>
    ({key: li.dataset.feature, status: li.querySelector(".legend-status")?.textContent ?? ""})),
}))()`;
const attribute = (selector: string, name: string): string =>
  `document.querySelector(${JSON.stringify(selector)})?.getAttribute(${JSON.stringify(name)}) ?? null`;

/** Why: the player must see the roads, buildings, walls and gate the engine moves and sees by, and
 * whether each is sourced. What: checks the drawn layer and legend against the POC's own commander
 * view and the status table the page loaded. Returns a one-line summary. */
export async function checkFeatures(page: Page, pocPort: number): Promise<string> {
  const state = await poc(pocPort, "/api/state");
  const map = await poc(pocPort, "/api/map");
  const id = state["scenario_brief"].id as string;
  const table = await page.evaluate<Doc>(`BattleFeatureSources.forScenario(${JSON.stringify(id)})`);
  const drawn = await until("the feature layer", async () => {
    const found = await page.evaluate<Doc>(DRAWN);
    return found["marks"].length ? found : null;
  });
  const marks = new Map<string, Doc>(drawn["marks"].map((m: Doc) => [m["key"], m]));
  const features: Doc[] = state["map_features"];
  for (const road of features.filter((f) => f["kind"] === "road")) {
    const mark = marks.get(road["id"]);
    assert.equal(mark?.["kind"], "feature-road", `${road["id"]} is drawn as a road`);
    const d = await page.evaluate<string>(attribute(`[data-feature="${road["id"]}"] .road-casing`, "d"));
    assert.equal(d.split(/[ML]/).filter((s) => s.trim()).length, road["points"].length, `${road["id"]}: one line through its points`);
    assert.ok(mark!["width"] > 20 || mark!["height"] > 20, `${road["id"]} is visible`);
  }
  const spacing = Math.sqrt(3) * map["radius"];
  for (const building of features.filter((f) => f["kind"] === "building")) {
    const metres: number[] = table[building["id"]]?.["footprint_m"];
    assert.ok(metres, `${building["id"]} has a footprint size in the status table`);
    const width = Number(await page.evaluate<string>(attribute(`[data-feature="${building["id"]}"] rect.footprint`, "width")));
    assert.ok(Math.abs(width - Math.max(6, metres[0]! * spacing / map["metres_per_hex"])) < 1e-6, `${building["id"]}: footprint scaled from metres_per_hex`);
    const tip = await page.evaluate<string>(`document.querySelector('.hex[data-c="${building["pos"][0]}"][data-r="${building["pos"][1]}"] title').textContent`);
    assert.ok(tip.includes(`${building["name"]} (${LABELS[table[building["id"]].status]}: `), `${building["id"]}: the hex tooltip names it and its status`);
  }
  assert.deepEqual(drawn["legend"].map((l: Doc) => l["key"]), drawn["marks"].map((m: Doc) => m["key"]), "one legend line per drawn mark");
  for (const line of drawn["legend"] as Doc[]) {
    const status = table[line["key"]]?.["status"];
    assert.ok(status, `${line["key"]} is in the POC's status table`);
    assert.equal(line["status"], LABELS[status], `${line["key"]}: legend status`);
    assert.equal(marks.get(line["key"])!["status"], status, `${line["key"]}: drawn status`);
    assert.match(marks.get(line["key"])!["title"], new RegExp(`— ${LABELS[status]}: `), `${line["key"]}: tooltip status`);
  }
  let extra = "";
  if (id === "hougoumont-north-gate") {
    const wall = await page.evaluate<string>(attribute(`[data-feature="hougoumont#walls"] .compound-wall`, "d"));
    assert.equal(wall.split("M").filter(Boolean).length, 17, "the compound wall: 17 outward edges, the gate edge left open");
    const gate = marks.get("hougoumont#north-gate");
    assert.deepEqual([gate?.["state"], gate?.["status"], gate?.["label"]], ["open", "sourced", "North gate · open"], "the gate in its known state");
    extra = `; compound wall 17 edges; gate ${gate!["label"]} (${LABELS[gate!["status"]]})`;
  }
  const summary = (drawn["legend"] as Doc[]).map((l) => `${l["key"]} ${l["status"]}`).join(", ");
  return `${id}: ${drawn["marks"].length} marks drawn, legend ${summary}${extra}`;
}

/** What: Hex grid off hides hex outlines only; every mark stays drawn and visible. */
export async function checkGridToggle(page: Page, artifacts: string, shot: string): Promise<string> {
  const stroke = `getComputedStyle(document.querySelector(".hex")).strokeOpacity`;
  const before = await page.evaluate<Doc>(DRAWN);
  assert.equal(await page.evaluate<string>(stroke), "1");
  await clickOn(page, "#grid-toggle");
  await until("hex outlines to hide", async () => (await page.evaluate<string>(stroke)) === "0");
  assert.equal(await page.evaluate<string>(attribute("#grid-toggle", "aria-pressed")), "false");
  const after = await page.evaluate<Doc>(DRAWN);
  assert.deepEqual(after["marks"].map((m: Doc) => m["key"]), before["marks"].map((m: Doc) => m["key"]), "every mark stays");
  for (const mark of after["marks"] as Doc[]) assert.ok(mark["width"] > 0 && mark["height"] > 0, `${mark["key"]} still visible`);
  assert.equal(await page.evaluate<string>(`getComputedStyle(document.querySelector(".battle-features")).display`), "inline");
  await screenshot(page, artifacts, shot);
  await clickOn(page, "#grid-toggle");
  await until("hex outlines to return", async () => (await page.evaluate<string>(stroke)) === "1");
  return `grid off: hex stroke-opacity 0, ${after["marks"].length} marks kept; grid on again`;
}

const disabled = (page: Page, ids: string[]): Promise<boolean[]> =>
  page.evaluate<boolean[]>(`${JSON.stringify(ids)}.map(id => document.getElementById(id).disabled)`);

/** Why: the player replays the current battle as their commander saw it, never as God or the enemy.
 * What: opens the replay, steps back to an earlier interval (an earlier header time, the POC's
 * recorded units), scrubs to the start, steps forward, checks orders stay closed and the POC is
 * untouched, then returns to live. Returns a one-line summary. */
export async function checkReplay(page: Page, pocPort: number, artifacts: string): Promise<string> {
  const live = await poc(pocPort, "/api/state");
  const history = await poc(pocPort, `/api/history?game_id=${live["game_id"]}`) as unknown as Doc[];
  const setting = (await poc(pocPort, "/api/map"))["setting"];
  const at = (turn: number): string => timeAt(setting, turn * live["seconds_per_turn"], live["display_locale"]);
  const time = async (): Promise<string> => (await header(page))["time"];
  assert.equal(await time(), at(live["turn"]), "the desk shows the live battle");
  await clickOn(page, "#replay-toggle");
  await until("the replay bar", () => page.evaluate<boolean>(`!document.getElementById("replay-bar").hidden`));
  const index = async (): Promise<number> => Number(await page.evaluate<string>(`document.getElementById("replay-slider").value`));
  assert.equal(await index(), history.length - 1, "the replay opens at the latest record");
  assert.equal(await time(), at(live["turn"]));
  assert.match(await page.evaluate<string>(`document.getElementById("replay-label").textContent`), /^Recorded commander view · /);
  assert.deepEqual(await disabled(page, ["send-order", "order-kind", "clock-toggle", "new-battle", "scenario-select"]),
    [true, true, true, true, true], "orders, the clock and new battles are closed while replaying");
  let i = history.length - 1;
  while (history[i]!["turn"] >= live["turn"]) {
    assert.ok(i > 0, "the record holds an earlier interval");
    await clickOn(page, "#replay-back");
    await until("a step back", async () => (await index()) === i - 1);
    i -= 1;
    await until(`header ${at(history[i]!["turn"])}`, async () => (await time()) === at(history[i]!["turn"]));
  }
  const recorded = await poc(pocPort, `/api/replay?game_id=${live["game_id"]}&revision=${history[i]!["revision"]}`);
  const units = await page.evaluate<string[]>(`[...document.querySelectorAll("[data-unit]")].map(n => n.dataset.unit)`);
  assert.deepEqual(units, recorded["units"].map((u: Doc) => u.id), "the counters are the recorded commander view's");
  assert.doesNotMatch((await header(page))["text"], /\bturn\b|revision/i, "no turn counter or revision label");
  const hex = await until("an open hex", () => page.evaluate<Doc | null>(openHex(recorded["units"][0].pos)));
  await page.click(hex["x"], hex["y"]);
  assert.match(await page.evaluate<string>(`document.getElementById("notice").textContent`), /Orders are disabled/);
  assert.equal(await page.evaluate<number>(`document.querySelectorAll(".hex.destination").length`), 0, "no destination while replaying");
  await screenshot(page, artifacts, "desk-replay.png");
  const earlier = await time();
  await choose(page, "replay-slider", "0", ["input", "change"]);
  await until("the scrub to the start", async () => (await index()) === 0 && (await time()) === at(history[0]!["turn"]));
  await clickOn(page, "#replay-forward");
  await until("a step forward", async () => (await index()) === 1);
  await clickOn(page, "#replay-live");
  await until("the live battle", () => page.evaluate<boolean>(`document.getElementById("replay-bar").hidden`));
  await until("the live header", async () => (await time()) === at(live["turn"]));
  assert.deepEqual(await disabled(page, ["clock-toggle", "new-battle"]), [false, false], "live controls return");
  const after = await poc(pocPort, "/api/state");
  assert.deepEqual([after["revision"], after["orders"].length, after["clock"]["running"]], [live["revision"], live["orders"].length, false],
    "replaying changed nothing in the battle");
  return `replay: opened at ${at(live["turn"])} (${history.length} records), stepped back to ${earlier}, `
    + `scrubbed to ${at(history[0]!["turn"])}, stepped forward, orders closed throughout; back to live at ${at(live["turn"])}`;
}
