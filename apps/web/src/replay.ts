// Commander replay of the current battle (docs/research/73), apart from the DOM so it can be
// tested with a fake DeskApi. It reads the POC's own /api/history and /api/replay (the POC
// desk's replay, apps/poc/static/app.js), always for the player's side: the relay forwards
// no `side` or `view`, and a replayed view of any other side is refused here as well.
import type {BattleSetting, CommanderState, CommanderView, HistoryEntry} from "@battle/contracts";
import type {DeskApi} from "./api.ts";
import {battleClock} from "./timeline.ts";

/** A replay of `gameId`: its recorded revisions and the view at `entries[index]`. */
export interface Replay {
  readonly gameId: string; readonly side: string;
  readonly entries: readonly HistoryEntry[]; readonly index: number; readonly view: CommanderView;
}

async function load(api: DeskApi, replay: Omit<Replay, "view" | "index">, index: number): Promise<Replay> {
  const view = await api.replay(replay.gameId, replay.entries[index]!.revision);
  if (view.side !== replay.side) throw new Error(`The recorded view is not your commander view (side ${view.side}).`);
  return {...replay, index, view};
}

/** Why: the player replays the battle as their commander saw it, from the most recent record back.
 * What: reads the live game's history and loads its latest revision's commander view.
 * Test: `opening a replay reads the live game's history and shows its latest recorded commander view`,
 * `a replay that is not the player's own commander view is refused`. */
export async function openReplay(api: DeskApi, live: CommanderState): Promise<Replay> {
  const entries = await api.history(live.game_id);
  return load(api, {gameId: live.game_id, side: live.side, entries}, entries.length - 1);
}

/** What: the replay at `index` (a step or a scrub); `replay` itself when `index` is outside the record.
 * Test: `stepping back loads an earlier revision, whose header time is earlier; the ends are clamped`. */
export async function replayAt(api: DeskApi, replay: Replay, index: number): Promise<Replay> {
  if (!Number.isInteger(index) || index < 0 || index >= replay.entries.length || index === replay.index) return replay;
  return load(api, replay, index);
}

/** Why: a recorded view is read only; orders go to the live battle alone.
 * What: true only live, not busy, in an active battle whose headquarters can command.
 * Test: `orders are closed while replaying and open again live`. */
export function ordersOpen(live: CommanderState, replay: Replay | null, busy: boolean): boolean {
  return replay === null && !busy && live.status === "active" && live.command.operational;
}

/** The replay bar's text: the recorded view's calendar date and battlefield time, never a revision. */
export function replayLabel(replay: Replay, setting: BattleSetting): string {
  const at = battleClock(setting, replay.view.turn, replay.view.seconds_per_turn, replay.view.display_locale);
  return `Recorded commander view · ${at.date} · ${at.time}`;
}
