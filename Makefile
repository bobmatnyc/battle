PYTHON ?= python3
NODE ?= node
POC_ARGS ?=

.PHONY: poc poc-offline test-poc smoke-poc headless-poc web smoke-web
WEB_ARGS ?=

# TypeScript desk (docs/research/70) against a POC already running on 8874.
web:
	cd apps/web && $(NODE) --disable-warning=ExperimentalWarning server/desk-server.ts $(WEB_ARGS)

# Real-browser click test on its own POC, SQLite file and ports; exit 3 = no browser (blocked).
smoke-web:
	cd apps/web && $(NODE) --disable-warning=ExperimentalWarning scripts/smoke-browser.ts

poc:
	cd apps/poc && $(PYTHON) -m battle $(POC_ARGS)

poc-offline:
	cd apps/poc && $(PYTHON) -m battle --offline $(POC_ARGS)

test-poc:
	cd apps/poc && $(PYTHON) -m unittest discover -s tests -q
	cd apps/poc && $(NODE) scripts/smoke_ui.mjs
	cd apps/poc && $(NODE) scripts/check_map_geometry.mjs
	cd apps/poc && $(NODE) scripts/check_map_features.mjs

smoke-poc:
	cd apps/poc && $(PYTHON) scripts/smoke_http.py

headless-poc:
	@run_dir=$$(mktemp -d "$${TMPDIR:-/tmp}/battle-headless.XXXXXX") && \
	  echo "Headless artifacts: $$run_dir" && \
	  cd apps/poc && $(PYTHON) -m battle --headless --db "$$run_dir/battle.sqlite"

# Prepare the designated Evo target without transferring secrets or local saves.
.PHONY: package-evo
package-evo:
	$(PYTHON) apps/poc/scripts/package_evo.py
