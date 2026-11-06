# Unit counters and readiness

Date: 2026-11-05. Source: direct user request to split/combine units and show force strength, type, skill, energy and morale in their icons. Status: implemented POC presentation; existing formation rules retained.

## Display contract

Map counters show identity, troop count, type (INF infantry; scout role additionally marked SC), and S/E/M ratings with numeric values and bars. S means the existing aggregate skill score; E means 100 minus fatigue; M means morale. Energy is a derived display value, not a new resource or stamina rule. Ratings are authored POC values, not calibrated historical measurements. The legend explains symbols. Unit cards and the selected-unit panel show spelled-out ratings.

Counters connect by leader lines to the unit's reported hex. A deterministic presentation layout separates nearby labels and avoids covering unit anchors where space allows. Label positions never change simulation positions. Zoom in for detail on small screens; cards remain readable independently of map zoom. Very dense formations may still crowd labels; clustering/level-of-detail is future work.

Normal own-unit icons use headquarters reports, including stale condition. Contacts show estimated strength and identified type; skill, energy and morale remain unknown (`?`). Even if unexpected numeric fields arrive on a contact object, the icon adapter excludes them. God Mode can show exact observer values, without granting command authority. Titles/accessibility labels include report time or estimate age. Replay uses the selected recorded observation.

Early poc-1/2/3 summaries omitted static type/proficiency fields after updates. The query adapter fills only pre-briefed, immutable own-unit traits from that edition's snapshot. Those editions have no training/remixing; current strength, fatigue, morale, position and enemy state are never filled from truth. This is read-only projection enrichment, with no changes to frozen transitions or saved snapshots.

## Split and combine

Select a counter or unit card to use the existing Split/Combine panel. Instructions still require authority, communication delivery, compatible adjacent formations and safe regrouping; troop and ammunition accounting remain deterministic. New or absorbed formations update counters when their reports reach headquarters, immediately only in God Mode. The current old saved battle predates formation actions and requires Reset to start a current-rules battle; it is preserved rather than silently migrated.

## Code and verification

`apps/poc/static/unit-icons.js` owns observer-only counter descriptions, SVG markup, layout and card metrics. It receives escaping as a dependency and has no data-fetch or mutation capability. Existing app click/keyboard routing invokes the original unit actions.

Checks cover numeric energy derivation, enemy attribute exclusion, counter creation/removal after visible formation changes, and legacy trait enrichment without refreshing remote condition. Existing formation tests and HTTP smoke exercise delivered split/combine and conservation. The 181 Python tests and UI/HTTP smoke checks passed. The browser showed the ratings on the saved battle; its final pointer-target fix was applied after that inspection. A later live click recheck was unavailable because local browser use was disabled in Work settings. No historical sources or coefficients are added by this display change.
