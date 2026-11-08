// Browser entry for the command desk; served by apps/web/server/desk-server.ts.
import {createDeskApi} from "./api.ts";
import {startDesk} from "./desk.ts";

void startDesk(document, createDeskApi((input, init) => fetch(input, init)));
