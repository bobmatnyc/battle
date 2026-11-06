import {readBattleCursor, type BattleCursor} from "@battle/contracts";

// Point of entry for the future desk. The playable UI is still in apps/poc.
export async function loadCursor(request: typeof fetch): Promise<BattleCursor> {
  const response = await request("/api/state");
  if (!response.ok) throw new Error("Battle state unavailable");
  return readBattleCursor(await response.json());
}
