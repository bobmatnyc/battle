// Reads the fixtures recorded from the Python app (packages/contracts/fixtures).
import {readFileSync} from "node:fs";
import {readCommanderState, readMapDocument, type CommanderState, type MapDocument} from "@battle/contracts";

export type Doc = Record<string, any>;

export function raw(name: string): Doc {
  const url = new URL(`../../../packages/contracts/fixtures/${name}.json`, import.meta.url);
  return JSON.parse(readFileSync(url, "utf8"));
}

export const commander = (): CommanderState => readCommanderState(raw("state-commander"));
export const map = (): MapDocument => readMapDocument(raw("map"));
