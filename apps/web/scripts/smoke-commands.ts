// Smoke steps for standing orders and split/combine (docs/research/81 §12, bt-T20): real clicks on
// the desk's forms, then a direct POC read that the battle holds what the desk said it sent.
import assert from "node:assert/strict";
import type {Page} from "./cdp.ts";
import {choose, clickOn, nextNotice, noticeText, poc, selectUnit, until, type Doc} from "./smoke-page.ts";

type Hex = [number, number];

// grid.neighbors: odd-row offset hexes.
const neighbours = ([c, r]: Hex): Hex[] => {
  const side = r & 1 ? 1 : -1;
  return [[c + 1, r], [c - 1, r], [c, r + 1], [c, r - 1], [c + side, r + 1], [c + side, r - 1]];
};

// A point inside hex c,r that hit-tests to the hex itself (no counter or label on top), scrolled into view.
const hexPoint = (c: number, r: number): string => `(() => {
  const hex = document.querySelector('.hex[data-c="${c}"][data-r="${r}"]');
  if (!hex) return null;
  hex.scrollIntoView({block: "center", inline: "center"});
  const b = hex.getBoundingClientRect();
  for (const fy of [0.5, 0.35, 0.65, 0.25, 0.75]) for (const fx of [0.5, 0.35, 0.65, 0.25, 0.75]) {
    const x = b.x + b.width * fx, y = b.y + b.height * fy;
    if (document.elementFromPoint(x, y) === hex) return {x, y};
  }
  return null; })()`;

async function clickHex(page: Page, [c, r]: Hex): Promise<boolean> {
  const point = await page.evaluate<{x: number; y: number} | null>(hexPoint(c, r));
  if (!point) return false;
  await page.click(point.x, point.y);
  await until(`hex ${c},${r} marked`, () => page.evaluate<boolean>(`!!document.querySelector('.hex.destination[data-c="${c}"][data-r="${r}"]')`));
  return true;
}

const text = (page: Page, id: string): Promise<string> => page.evaluate<string>(`document.getElementById(${JSON.stringify(id)}).textContent`);
const enabled = (page: Page, id: string): Promise<boolean> => page.evaluate<boolean>(`!document.getElementById(${JSON.stringify(id)}).disabled`);

/** D: send `profile` to `unitId`, see it listed on its way, then cancel it; the POC holds both. */
export async function checkStanding(page: Page, pocPort: number, unitId: string, profile: string): Promise<string> {
  await selectUnit(page, unitId);
  const templates = (await poc(pocPort, "/api/state"))["standing_templates"].map((t: Doc) => t.id);
  const offered = await page.evaluate<string[]>(`[...document.getElementById("standing-profile").options].map(o => o.value)`);
  assert.deepEqual(offered, templates, "the desk offers the view's standing templates");
  await choose(page, "standing-profile", profile);
  const before = await noticeText(page);
  await clickOn(page, "#send-standing");
  const sent = await nextNotice(page, before);
  assert.equal(sent["kind"], "accepted", sent["text"]);
  let state = await poc(pocPort, "/api/state");
  const order = state["standing_orders"].find((o: Doc) => o.unit_id === unitId && o.profile_id === profile);
  assert.ok(order, "the POC holds the standing order");
  const label = state["standing_templates"].find((t: Doc) => t.id === profile).label;
  assert.match(await page.evaluate<string>(`document.querySelector('[data-standing="${order.id}"]')?.textContent ?? ""`),
    new RegExp(`^${unitId} · ${label} · sent .* · awaiting ack`), "the list shows it");
  assert.match(await text(page, "standing-current"), new RegExp(`On its way: ${order.id} ${label}`));
  await until("cancel to be offered", () => enabled(page, "cancel-standing"));
  await clickOn(page, "#cancel-standing");
  const cancelled = await nextNotice(page, sent["text"]);
  assert.equal(cancelled["kind"], "accepted", cancelled["text"]);
  state = await poc(pocPort, "/api/state");
  const first = state["standing_templates"][0];
  const cancel = state["standing_orders"].find((o: Doc) => o.unit_id === unitId && o.version > order.version);
  assert.equal(cancel?.profile_id, first.id, "cancel sends the battle's first template, which supersedes the order");
  await until("cancel to be withdrawn once sent", async () => !(await enabled(page, "cancel-standing")));
  return `${unitId} ${profile} (${order.id}): "${sent["text"]}"; cancelled by ${cancel.id} ${first.id}: "${cancelled["text"]}"`;
}

/** E: split `unitId` to a free adjacent hex with the default count; the POC holds the operation. */
export async function checkSplit(page: Page, pocPort: number, unitId: string): Promise<string> {
  await selectUnit(page, unitId);
  const state = await poc(pocPort, "/api/state");
  const unit = state["units"].find((u: Doc) => u.id === unitId);
  const taken = new Set(state["units"].map((u: Doc) => String(u.pos)));
  const count = Math.floor(unit.strength / 2);
  assert.equal(Number(await page.evaluate<string>(`document.getElementById("split-count").value`)), count, "half the strength by default");
  assert.match(await text(page, "formation-help"), /^Split: click an adjacent hex/);
  let target: Hex | null = null;
  for (const hex of neighbours(unit.pos).filter((h) => !taken.has(String(h)))) {
    if (await clickHex(page, hex)) { target = hex; break; }
  }
  assert.ok(target, "a free adjacent hex can be clicked");
  assert.match(await text(page, "formation-help"), new RegExp(`^Split: ${count} troops to hex ${target.join(",")}\\.`));
  const before = await noticeText(page);
  await clickOn(page, "#send-split");
  const sent = await nextNotice(page, before);
  assert.equal(sent["kind"], "accepted", sent["text"]);
  const op = (await poc(pocPort, "/api/state"))["formation_ops"].find((o: Doc) => o.kind === "split" && o.unit_id === unitId);
  assert.deepEqual([op?.count, op?.destination], [count, target], "the POC holds the split");
  assert.match(await page.evaluate<string>(`document.querySelector('[data-operation="${op.id}"]')?.textContent ?? ""`),
    new RegExp(`^${op.id} · split ${unitId} \\(${count} to hex ${target.join(",")}\\) · awaiting report`));
  return `${unitId} ${count} → ${target.join(",")} (${op.id}): "${sent["text"]}"`;
}

/** E: a split the desk cannot judge (a wall it does not draw) is refused by the engine, whose text is shown. */
export async function checkEngineRefusal(page: Page, pocPort: number, unitId: string, count: number, across: Hex): Promise<string> {
  await selectUnit(page, unitId);
  await choose(page, "split-count", String(count), ["input"]);
  assert.ok(await clickHex(page, across), `hex ${across.join(",")} can be clicked`);
  const ops = (await poc(pocPort, "/api/state"))["formation_ops"].length;
  const before = await noticeText(page);
  await until("split to be offered", () => enabled(page, "send-split"));
  await clickOn(page, "#send-split");
  const refused = await nextNotice(page, before);
  assert.equal(refused["kind"], "refusal", refused["text"]);
  assert.equal(refused["text"], "A wall or shut gate separates that hex from the formation.");
  assert.equal((await poc(pocPort, "/api/state"))["formation_ops"].length, ops, "the refused split changed nothing");
  return `${unitId} ${count} → ${across.join(",")}: "${refused["text"]}"`;
}
