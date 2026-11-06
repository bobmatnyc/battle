// An intentionally small wire boundary shared with the Python POC.
// Copy only known fields; this is not server-side authorization.
export interface BattleCursor {
  game_id: string;
  revision: number;
}

export function readBattleCursor(input: unknown): BattleCursor {
  if (typeof input !== "object" || input === null ||
      !("game_id" in input) || typeof input.game_id !== "string" || !input.game_id ||
      !("revision" in input) || typeof input.revision !== "number" ||
      !Number.isSafeInteger(input.revision) || input.revision < 0) {
    throw new TypeError("Invalid battle cursor");
  }
  return {game_id: input.game_id, revision: input.revision};
}
