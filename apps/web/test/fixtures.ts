// Reads the fixtures recorded from the Python app (packages/contracts/fixtures).
import {readFileSync} from "node:fs";
import vm from "node:vm";
import {readCommanderState, readMapDocument, type CommanderState, type MapDocument} from "@battle/contracts";

export type Doc = Record<string, any>;

export function raw(name: string): Doc {
  const url = new URL(`../../../packages/contracts/fixtures/${name}.json`, import.meta.url);
  return JSON.parse(readFileSync(url, "utf8"));
}

export const commander = (): CommanderState => readCommanderState(raw("state-commander"));
export const map = (): MapDocument => readMapDocument(raw("map"));

// docs/research/73: the POC's status table, loaded as the desk page loads it (a classic script).
export function pocFeatureSources(): unknown {
  const context = vm.createContext({});
  vm.runInContext(readFileSync(new URL("../../poc/static/feature-sources.js", import.meta.url), "utf8"), context);
  return vm.runInContext("BattleFeatureSources", context);
}
