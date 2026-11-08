// Browser entry for the command desk; served by apps/web/server/desk-server.ts.
import {createDeskApi} from "./api.ts";
import {startDesk} from "./desk.ts";

// The POC's status table (apps/poc/static/feature-sources.js), loaded by index.html as a classic
// script before this module; its top-level `const` is a global binding, not a window property.
declare const BattleFeatureSources: unknown;
const featureSources = typeof BattleFeatureSources === "undefined" ? null : BattleFeatureSources;

void startDesk(document, createDeskApi((input, init) => fetch(input, init)), featureSources);
