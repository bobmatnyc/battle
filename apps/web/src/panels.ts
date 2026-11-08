// Side-panel markup for slice 2 (docs/research/71): the unit card, the order form,
// dispatches, the mission brief and the scenario choice. Drawn from the commander
// view and the scenario catalog only; every server string passes through `esc`.
import type {CommanderView, OrderTemplate, ScenarioList, UnitReport} from "@battle/contracts";
import {esc} from "./render.ts";

const percent = (value: unknown): string =>
  typeof value === "number" && Number.isFinite(value) ? `${Math.round(value)}%` : "?";

const row = (field: string, label: string, value: string): string =>
  `<div data-field="${field}"><dt>${esc(label)}</dt><dd>${esc(value)}</dd></div>`;

const templateLabel = (view: CommanderView, id: unknown): string =>
  view.order_templates.find((t) => t.id === id)?.label ?? String(id ?? "?");

/** Why: the player commands from reported condition, not ground truth (AGENTS.md "Unit counters").
 * What: the selected own unit's card: strength / initial, type, skill, energy (100 - fatigue),
 * morale, ammunition, suppression, fatigue, tools and fire posture when reported, status,
 * mission and its last reported result, local judgment, and the report's battlefield time.
 * Test: `the unit card shows the commander view's report, with energy as 100 - fatigue`. */
export function unitCardMarkup(view: CommanderView, unit: UnitReport, clock: (turn: number) => string): string {
  const fatigue = typeof unit.fatigue === "number" ? unit.fatigue : null;
  const rows = [
    row("strength", "Strength", `${unit.strength} / ${unit.initial}`),
    row("type", "Type", String(unit["unit_type"] ?? "not reported")),
    row("skill", "Skill", percent(unit["skill"])),
    row("energy", "Energy", fatigue === null ? "?" : percent(100 - fatigue)),
    row("morale", "Morale", percent(unit.morale)),
    row("ammo", "Ammunition", String(unit.ammo)),
    row("suppression", "Suppression", percent(unit.suppression)),
    row("fatigue", "Fatigue", percent(unit.fatigue)),
  ];
  if (unit["tools"] !== undefined) rows.push(row("tools", "Entrenching tools", String(unit["tools"])));
  if (unit["fire_posture"] !== undefined) rows.push(row("posture", "Fire posture", templateLabel(view, unit["fire_posture"])));
  rows.push(row("status", "Status", unit.status));
  rows.push(row("mission", "Mission", templateLabel(view, unit.stance)));
  if (unit.target) rows.push(row("target", "Toward", `hex ${unit.target.join(",")}`));
  const result = unit["mission_result"] as {status?: unknown; reason?: unknown} | undefined;
  const judgment = [
    result ? `${String(result.status ?? "").toUpperCase()} · ${String(result.reason ?? "")}` : "",
    typeof unit["local_reason"] === "string" ? unit["local_reason"] : "",
  ].filter(Boolean).join(" ");
  const headquarters = unit.id === view.command.unit_id ? " · with your headquarters" : "";
  return `<h3 id="unit-title">${esc(unit.id)} · ${esc(unit.name)}</h3>`
    + `<p class="unit-age">Reported ${esc(clock(unit.observed_turn))}${headquarters} · ${esc(String(unit["weapon_class"] ?? "weapons not reported"))}</p>`
    + `<dl class="unit-stats">${rows.join("")}</dl>`
    + (judgment ? `<p class="unit-judgment">${esc(judgment)}</p>` : "");
}

/** The order kinds this battle offers, as `<option>`s, with `chosen` selected. */
export function templateOptions(view: CommanderView, chosen: string): string {
  return view.order_templates.map((t) =>
    `<option value="${esc(t.id)}"${t.id === chosen ? " selected" : ""}>${esc(t.label)}</option>`).join("");
}

/** Why: the player should know what an order kind asks for before sending it.
 * What: the template's intent and effect, what input it needs, and for resupply the
 * briefed ammunition points (positions only; stocks are not in the commander view).
 * Test: `the order form offers the catalog with its intent and effect, and resupply names the briefed point`. */
export function templateHelp(view: CommanderView, template: OrderTemplate): string {
  const need = template.destination === "hex" ? "Click a destination hex on the map, then send."
    : template.destination === "supply" ? "The unit goes to the nearest compatible ammunition point; no hex is needed."
      : "No destination; the order applies where the unit stands.";
  const sites = template.destination === "supply"
    ? `<p>${view.supply_sites.map((s) => `${esc(s.name)} · hex ${s.pos.join(",")}`).join("<br>") || "No ammunition point is briefed."}</p>` : "";
  return `<strong>${esc(template.intent)}</strong><p>${esc(template.effect)}</p><p class="order-need">${esc(need)}</p>${sites}`;
}

/** Why: dispatches are the commander's main information channel.
 * What: received dispatches, newest first, each with its battlefield receipt time.
 * Test: `dispatches are listed newest first with battlefield times, and the order list shows delivery`. */
export function dispatchesMarkup(view: CommanderView, clock: (turn: number) => string): string {
  if (!view.dispatches.length) return "<li>No dispatches received.</li>";
  return [...view.dispatches].reverse().map((d) =>
    `<li data-dispatch-kind="${esc(d.kind)}"><small>received ${esc(clock(d.turn))} · ${esc(d.kind)}</small> ${esc(d.display_text)}</li>`).join("");
}

/** Why: a codeword is news headquarters learns only when its report arrives (docs/research/53);
 * the player reads it as the commander did (docs/research/81 §4).
 * What: null when the battle has no authored codeword (no `signals` in the view); else the
 * received codewords, newest first, each with its meaning, bridge (by the name the view gives
 * it), sender and battlefield arrival time.
 * Test: `a delivered codeword is listed with its meaning, bridge, sender and arrival time`,
 * `a battle with no authored codeword has no panel; one awaiting its codeword says so`,
 * `signal text is escaped and the newest codeword comes first`. */
export function signalsMarkup(view: CommanderView, clock: (turn: number) => string): string | null {
  if (!view.signals) return null;
  if (!view.signals.length) return "<li>No codeword received.</li>";
  const name = (id: string): string => view.map_features.find((f) => f.id === id)?.name ?? id;
  return [...view.signals].reverse().map((s) =>
    `<li data-codeword="${esc(s.codeword)}"><strong>${esc(s.codeword)}</strong> · ${esc(s.meaning)}`
    + `<br><small>${esc(name(s.bridge))} · received ${esc(clock(s.delivered_turn))} · from ${esc(s.sender_id)}</small></li>`).join("");
}

/** The brief's mission text: escaped, with its `**bold**` marks as <b>. */
export function missionMarkup(view: CommanderView): string {
  const brief = view.scenario_brief;
  if (!brief) return "No briefing is available for this saved battle.";
  const text = esc(brief.mission.text).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>");
  return `<strong>${esc(brief.mission.title)}</strong><p>${text}</p><p>${esc(brief.subhead)}</p>`;
}

/** Why: a finished battle must say who won in the scenario's own words, as the POC desk does
 * (docs/research/74). What: null while the battle is active; else the brief's win, loss or draw
 * headline for the viewing side (by `winner`) and the server's `reason`; "Battle complete." when
 * the saved battle has no brief.
 * Test: `a finished battle shows the brief's headline for the player's side, with the reason`. */
export function outcomeText(view: CommanderView): {headline: string; reason: string} | null {
  if (view.status === "active") return null;
  const outcomes = view.scenario_brief?.outcomes;
  const headline = !outcomes ? "Battle complete."
    : view.winner === view.side ? outcomes.win : view.winner === "draw" ? outcomes.draw : outcomes.loss;
  return {headline, reason: view.reason ?? ""};
}

/** Why: the player picks a scenario from the POC's own player-facing catalog.
 * What: one `<option>` per catalog entry (title and calendar date), `current` selected.
 * Test: `the scenario choice lists the catalog and marks the battle being played`. */
export function scenarioOptions(list: ScenarioList, current: string | null): string {
  return list.scenarios.map((s) =>
    `<option value="${esc(s.id)}"${s.id === current ? " selected" : ""}>${esc(s.title)} · ${esc(s.date)}</option>`).join("");
}
