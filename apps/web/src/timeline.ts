// Battlefield calendar and clock (AGENTS.md "One battlefield timeline").
// `start_local` is wall time at the battlefield. It is read as if it were UTC and
// formatted in UTC, so the browser's time zone never shifts it; UTC here is a
// neutral arithmetic frame, not a claim about the battle's zone (as apps/poc/static/timeline.js).
import type {BattleSetting} from "@battle/contracts";

export interface BattleClock { time: string; date: string; location: string }

function instant(setting: BattleSetting, elapsedSeconds: number): Date {
  return new Date(Date.parse(`${setting.start_local}Z`) + elapsedSeconds * 1000);
}

/** Local battlefield time `elapsedSeconds` after the scenario start, e.g. "16:36". */
export function timeAt(setting: BattleSetting, elapsedSeconds: number, locale = "en-GB"): string {
  const value = instant(setting, elapsedSeconds);
  return new Intl.DateTimeFormat(locale, {
    timeZone: "UTC", hour: "2-digit", minute: "2-digit", hourCycle: "h23",
    ...(value.getUTCSeconds() ? {second: "2-digit"} : {}),
  }).format(value);
}

/** Why: the desk header names place, date and local time, never a turn.
 * What: time, calendar date and location at simulation `turn`.
 * Test: `battlefield time is the scenario's local time in every browser time zone`. */
export function battleClock(setting: BattleSetting, turn: number, secondsPerTurn: number, locale = "en-GB"): BattleClock {
  const elapsed = turn * secondsPerTurn;
  const date = new Intl.DateTimeFormat(locale, {
    timeZone: "UTC", weekday: "long", day: "numeric", month: "long", year: "numeric",
  }).format(instant(setting, elapsed));
  return {time: timeAt(setting, elapsed, locale), date, location: setting.location};
}
