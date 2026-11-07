# Simulation clock and replay

Date: 2026-11-05. **User requirement:** replace the Advance button with a clock that can start, stop, speed up, slow down and replay. This document specifies the local POC behavior; it is not historical research or historical calibration.

## Implemented local behavior

The Python server owns one clock per running application. Browsers observe it; extra tabs do not generate extra ticks. New battles and server restarts are paused. Reset also returns the rate to the 10× default; the previous battle's speed does not carry over. The clock resumes the newest committed battle, with no offline catch-up. Default rate is 10×; supported rates are 0.5×, 1×, 2×, 5×, 10×, 30× and 60×. At 10×, a 30-second simulation interval becomes eligible after three wall-clock seconds. The top command-map clock shows committed simulation time, while the control panel shows remaining time until the next interval.

The existing simultaneous 30-second resolution remains unchanged. Speed affects pacing, never movement distance, weapon effects, communications latency, model cadence or outcome rules. Accepted decisions and resulting state still commit atomically to SQLite. An interval may take longer than its pacing delay when inference or persistence is slow; the clock shows that it is resolving. It schedules the next interval after completion rather than performing a catch-up burst.

Pause immediately prevents another interval from starting. An interval already in progress finishes and saves normally, with a visible “finishing current interval” state. Pausing/resuming and rate changes preserve the elapsed fraction of the waiting interval. A calculation or save error stops the clock. Completion stops it as well.

For this local single-player demo, submitting an order, staff message, mode change or reset pauses the clock and waits for an in-progress interval before applying the command to the latest revision. The game stays paused afterward. This is a player planning aid, not an in-world communications capability: dispatch arrival still requires simulation time and the scenario's normal delivery rules. Direct API callers must pause before issuing these mutations. The old `/api/advance` endpoint remains a paused-only debugging/testing adapter; the player UI has no Advance button.

Start, pause, speed changes and reset controls are recorded separately in SQLite `clock_events`, with battle ID, committed revision and wall-clock timestamp. Canonical simulation events, decisions and snapshots remain the source of deterministic replay. Pacing records do not change the world-state hash. Process shutdown/restart is deliberately fail-paused; these control records are not a durable scheduler or a complete crash telemetry stream. No new inference happens merely because a browser polls the clock.

## Replay

Opening Replay pauses live simulation and waits for the current interval to finish. It captures the available history for that battle and opens revision zero. Play/pause and slower/faster controls then operate on the recorded knowledge of the player's side. Since 2026-11-07 a selector in the replay bar also shows God view and, once the battle is complete, the opponent's commander view, in every player scenario ([65](65-replay-by-side-and-god-view.md)). The slider can seek to any recorded revision; seeking pauses playback. Playback delay follows the difference in simulation time between revisions, divided by playback speed. Same-time order/chat revisions have a minimum 100 ms display interval so their sequence remains inspectable. Playback stops at the final recorded revision.

Replay makes no simulation mutations or inference calls and exposes no enemy ground truth. Returning to live reloads current saved state; it does not automatically restart time. Replay is review-only, with no branching or alternate-history edits. An existing second tab can still control the shared live clock: this loopback POC has no session ownership or multiplayer permissions. A future networked game must settle pause/speed authority, synchronized command deadlines and whether active participants can review history without stopping everyone.

## Verification and limits

Focused tests use a fake monotonic clock to verify pause/resume, fractional progress across speed changes, long stalls, one in-flight interval, immediate pause during a blocked interval, completion, sanitized failure and audit-write failure. Application tests verify saved replay equivalence, restart-paused behavior and mutation exclusion while running. Offline HTTP checks exercise automatic clock stepping, speed/pause controls, polling and non-mutating historical reads. The UI harness checks clock requests and dialog-free reset; browser verification is recorded separately.

This clock is a pacing layer over a coarse simulation, not continuous movement animation, higher-resolution physics, a calibrated historical tempo, or multiplayer synchronization. Slow model calls can make actual throughput lower than the selected rate. The server continues running when a browser is closed; use Pause or stop the Python server to stop live progression.

### Local verification record — 2026-11-05

- 39 Python component tests passed; offline HTTP and JavaScript DOM smoke checks passed.
- Existing saved battles retained exact replay equivalence. The clock-driven browser run also verified identical replay across four revisions / three intervals.
- In the actual browser, selected the scripted commander, raised live speed from 10× to 30×, started and paused after three intervals, played replay from revision zero to its automatic stop at revision three, sought revision one, and reduced replay speed to 10×. Returned to live, restored 10× and OpenRouter selection, and left the clock paused. No provider calls were needed for these checks.
- Browser console contained no errors. Screenshot: `artifacts/battle-clock.jpg`. This is local evidence only; no Evo run or deployment was performed.

## One battlefield timeline — 2026-11-05

User clarification: show location and day/date beside the clock, with no player-facing turns. The command desk now shows Little Round Top · Gettysburg, Pennsylvania and Thursday, 2 July 1863. Replay labels and accessible slider values use the same scenario-local calendar and clock; dispatches and assessments use that time basis. Replay no longer labels storage revisions. Clock controls show running/paused time rather than an interval countdown.

The catalog supplies the local start timestamp and location. The existing NPS provenance for the date is in [16](16-playable-poc.md); 16:30 remains an authored scenario start. Formatting uses a neutral calendar arithmetic frame, independent of the viewer's timezone, and supports midnight/date rollover and locale formatting. This does not assign a modern timezone offset to 1863.

Simulation still commits fixed 30-second steps internally. Existing `turn` and revision fields remain compatibility/audit identifiers; there is no player turn-taking or new rules edition. Multiple command records can share the same battlefield time. Replay retains their ordering. No time is interpolated ahead of committed battlefield state. Raw God Mode event details and exported audit records retain canonical technical fields. Existing saved battles require no Reset.

Verification: 180 Python component tests, UI regression checks (including calendar/midnight rollover), map geometry and HTTP smoke passed. Live browser inspection confirmed the saved battle at 16:32 with location/date and replay at 16:30 using the same calendar, then returned to paused live view. [Display capture](../../apps/poc/artifacts/battle-calendar-timeline.png).
