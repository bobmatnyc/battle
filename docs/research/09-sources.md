# Source register and evidence limits

Access/research date for all entries: **2026-11-04**. Source publication dates below are taken from the document/page where identified; search-engine crawl or inferred publication dates are not treated as edition dates. These notes summarize only the mechanisms used in our design discussion, not complete rulesets. Linked works remain with their publishers; no manuals or proprietary tables have been copied into this project.

## Game systems

### S01

**Battlefront / Matrix Games — Combat Mission: Shock Force 2 base-game manual.** [Publisher-hosted PDF](https://ftp.matrixgames.com/pub/CombatMissionShockForce2/CMShockForce2BaseGameManual.pdf).

Read: tutorial discussion of play modes, printed pp. 15–16. Supports the observed 60-second WEGO order/resolution/replay cycle and distinction from real-time play. Does not establish battle's tick length, Combat Mission's internal equations, or current engine behavior across all titles. Used in the [survey](01-game-survey.md).

### S02

**NorbSoftDev — Scourge of War: Gettysburg manual**, developer manual distributed through the game's Steam asset host. [PDF](https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/3136610/manuals/71098d1b4813f3642baca457694dd14819c87f1e/SoW_Gettysburg_Manual.pdf?t=1746575587).

Read: command organization; multiplayer sections listed at pp. 28–40; command-level courier settings pp. 44–46; order screen pp. 61–64. Supports command hierarchy and configurable communication delay. This is an older manual with legacy system requirements; current service availability was not tested. Used in [survey](01-game-survey.md) and [agents](04-command-and-agents.md).

### S03

**WarfareSims / Matrix Games — Command: Modern Operations online manual.** [Introduction](https://command.matrixgames.com/manual/03-introduction/), [doctrine and context controls](https://command.matrixgames.com/manual/05-8-context-menus-and-info-panel/), [missions](https://command.matrixgames.com/manual/06-missions/).

Read: platform/components description, unit/group/mission doctrine and engagement settings, and mission definitions including patrol behavior. Supports mission-based control and domain-specific platforms. A changing online manual, not a pinned numerical model; no modern weapon coefficients are imported. Used in [survey](01-game-survey.md) and [domains](06-domains-and-campaigns.md).

### S04

**The Battle for Wesnoth project — Defense and resistance.** [Official project wiki](https://wiki.wesnoth.org/Defense_and_resistance).

Read: distinction between terrain-dependent hit avoidance and damage resistance. Useful as a clarity precedent, not historical evidence. Wiki material is project-hosted and community-maintained. Main homepage retrieval was blocked by an anti-bot page; no current service/version claim is based on that page. Used in the [survey](01-game-survey.md).

### S05

**Chad Jensen / GMT — Combat Commander rulebook v1.1.** [Publisher PDF](https://www.gmtgames.com/living_rules/CC_Rulebook_v1.1.pdf).

Read: introduction and sequence; section 13 on suppression; order listings for recovery and rout. Supports separating recoverable suppression from unit destruction and using constrained activation. Older edition; not asserted to be the latest living rules. Used in the [survey](01-game-survey.md).

### S06

**Chad Jensen / GMT — Fighting Formations series rulebook v1.1; US 29th Infantry Division product description.** [Series rules](https://www.gmtgames.com/living_rules/FF-GD_Rulebook_FINAL.pdf), [publisher description](https://www.gmtgames.com/p-1005-fighting-formations-us-29th-infantry-division.aspx).

Read: introduction, initiative/order structure and command concept; product sections on initiative, scale and units. Supports platoon/squad granularity, activation costs, reactive fire, and the cited 75 m/five-minute scale for the US 29th entry. Series and product-specific material are distinguished; these are not recommended constants for battle.

### S07

**Richard Borg / GMT — Commands & Colors: Napoleonics, second-edition rules, 2012.** [Publisher PDF](https://www.gmtgames.com/living_rules/CCN-RULES-2012.pdf).

Read: introduction and overview of command cards, loss/retreat and combined-arms mechanisms. Source explicitly permits variable scenario unit scale. Used as an abstraction/readability precedent, not a platoon-scale historical model. Used in the [survey](01-game-survey.md).

### S08

**TooFatLardies publisher administrator — Chain of Command v2 development discussion, 2024-09-09.** [Publisher forum post](https://toofatlardies.co.uk/forum/viewtopic.php?t=57).

Read: opening publisher post describing command-dice continuity and additional reactions. This is a primary development statement, **not** inspection of the final v2 rulebook. Exact command-dice probabilities, shock thresholds and final release changes remain unverified. Used narrowly in the [survey](01-game-survey.md).

### S09

**GMT — Musket & Pike Battle Series rules v6.0, 2012.** [Publisher PDF](https://www.gmtgames.com/tacw/master_rules.pdf). [Dual Pack page listing v7.0](https://www.gmtgames.com/p-626-musket-pike-dual-pack.aspx).

Read: rule organization and sections on initiative, leaders/orders, facing/formation, reactions, morale and reform. V6 is the inspected document; the publisher listing shows a newer v7. Do not imply current-edition completeness. Early-modern subject matter must not be confused with an American Civil War equipment source.

### S10

**Mike Nagel / GMT — Flying Colors Deluxe series rules, version 01.01.2023.** [Publisher asset PDF](https://gmtwebsiteassets.s3.us-west-2.amazonaws.com/nnfc/Flying_Colors_SeriesRules_v01012023.pdf).

Read: command/wind/movement structure, section 3.7 on fire and damage, hull/rigging effects and striking colors, section 5's ship-duel scope. Supports distinct naval mobility and damage channels. Used in the [survey](01-game-survey.md) and [domain design](06-domains-and-campaigns.md); no combat tables reproduced.

### S11

**Warlord Games / designer Gabrio — Black Seas FAQ, 2019-09-03.** [Designer FAQ](https://www.warlordgames.com/frequently-asked-questions-black-seas/).

Read: scale, wind/movement design and land-campaign linkage. Broad design evidence only; the complete rulebook was not inspected. Used in the [survey](01-game-survey.md).

## Algorithms and simulation architecture

### S12

**Amit Patel / Red Blob Games — Hexagonal Grids**, maintained guide, page marked March 2013–April 2026. [Guide](https://www.redblobgames.com/grids/hexagons/).

Read: axial/cube coordinates, neighbors, distance, line drawing, field of view, map storage and pathfinding topics. Provides the grid mathematics used in [simulation methods](03-simulation-methods.md). Tactical LOS, physical scale and formation exposure are additional battle design proposals, not claims made by this guide.

### S13

**Amit Patel / Red Blob Games — Introduction to the A* Algorithm**, created 2014, page lists updates through 2023. [Guide](https://www.redblobgames.com/pathfinding/a-star/introduction.html).

Read: graph representation and BFS/Dijkstra/A* distinctions. Supports route/reachability algorithm choices. Terrain capability, congestion and risk costs are our proposed modeling decisions. No pathfinding library selected.

### S14

**Glenn Fiedler — Fix Your Timestep!, 2004-06-10.** [Author's article](https://gafferongames.com/post/fix_your_timestep/).

Read: fixed versus variable delta time and simulation/render timing concerns. Used for the fixed-step principle. It does not validate a one-second combat timestep or prescribe a language/framework.

### S15

**Glenn Fiedler — Deterministic Lockstep, 2014-11-29.** [Author's article](https://gafferongames.com/post/deterministic_lockstep/).

Read: definition of exact determinism and floating-point/platform difficulties. Supports explicit replay guarantees and caution about cross-runtime equality. Networking by shared input is discussed in the source; battle proposes an authoritative simulator to preserve hidden information rather than selecting client lockstep.

### S16

**Farama Foundation — PettingZoo Parallel API.** [Official documentation](https://pettingzoo.farama.org/api/parallel/).

Read: simultaneous actions/observations, per-agent mappings and termination/truncation interface. Used as a conceptual test-harness precedent in [agents](04-command-and-agents.md). No package dependency, programming language, or training method has been selected.

### S17

**D. E. Shaw Research — Random123.** [Maintainer repository and documentation entry](https://github.com/DEShawResearch/random123). Associated original work: Salmon, Moraes, Dror and Shaw, *Parallel Random Numbers: As Easy as 1, 2, 3*, SC11 (2011), [paper](https://www.thesalmons.org/john/random123/papers/random123sc11.pdf).

Read: maintainer description of counter-based generators and parallel use; paper identified through its abstract/search record. Supports independent keyed random draws. The proposed battle key format and replay contract are original design suggestions; library adoption remains open.

### S18

**Iovino et al. — A Survey of Behavior Trees in Robotics and AI**, arXiv:2005.05842, revised 2020-05-13. [Author paper record and abstract](https://arxiv.org/abs/2005.05842).

Read: abstract describing hierarchical state-transition structure, reuse, and FSM scaling motivation. Supports behavior trees as a candidate control structure, not proof they outperform utility policies for battle. Full-paper reproduction or implementation was not performed.

### S19

**David Silver and Joel Veness — Monte-Carlo Planning in Large POMDPs**, NeurIPS/NIPS 2010. [Original proceedings abstract and paper link](https://papers.nips.cc/paper_files/paper/2010/hash/edfbe1afcf9246bb0d40eb4d8027d90f-Abstract.html).

Read: original abstract explaining belief-state sampling and Monte Carlo tree search with a black-box simulator. Supports POMCP as a future planning research direction. It does not directly solve multiplayer adversarial command. The author's old direct PDF URL returned 404; an MIT repository route returned 429. The proceedings record was successfully retrieved.

### S20

**David L. I. Kirkpatrick — How Important are Superior Numbers?**, Cambridge University Press, 2021, DOI 10.1017/9781108973458. [Publisher record and summary](https://www.cambridge.org/core/elements/abs/how-important-are-superior-numbers/400D403E02FF938651B9CD362F69857E).

Read: public summary discussing American Civil War loss/engagement ratios and limits of indiscriminate square-law application. Full monograph not read. Used narrowly to justify treating Lanchester models as baselines rather than universal combat laws. Author/date should be retained as bibliographic metadata, not as proof of general consensus.

### S21

**Microsoft Azure Architecture Center — Event Sourcing pattern.** [Official architecture guidance](https://learn.microsoft.com/en-us/azure/architecture/patterns/event-sourcing).

Read: append-only state reconstruction, auditability, and complexity/schema tradeoffs. Supports the replay/event discussion in [state and outcomes](05-state-events-outcomes.md). Page text was available despite a generic authorization banner. This is architecture research, not an Azure or database selection.

## Historical context and validation

### S22

**The National WWII Museum — D-Day Doctrine: Six Elements for a Successful Landing, 2024-05-28.** [Museum article](https://www.nationalww2museum.org/war/articles/d-day-doctrine-six-elements-successful-landing).

Read: coordinated command, ship-to-shore movement, naval/air support, beachhead and logistics framework. Institutional historical synthesis, not an original 1944 operations order or quantitative calibration dataset. Supports treating amphibious scale as coupled systems; no battle probabilities derived.

### S23

**U.S. Army Center of Military History — Gettysburg Staff Ride Briefing Book**, government-hosted edition. [GovInfo PDF](https://www.govinfo.gov/content/pkg/GOVPUB-D114-PURL-gpo92542/pdf/GOVPUB-D114-PURL-gpo92542.pdf).

Read: contents and indexed small-arms excerpt; relevant printed sections are Organization p. 30, Logistics p. 32, Small Arms p. 35, Tactics p. 42, and weather p. 44. A later targeted retrieval timed out. Government historical compilation, not direct measurement of this prototype's effective fire. Used as a starting source pointer for future content research. No proposed 30-person fixture count or casualty coefficient is attributed to it.

### S24

**National Research Council — Representing Human Behavior in Military Simulations: Interim Report**, 1997, chapter 3, *A Methodology for Creating Human Behavior Representations*. [Full chapter](https://www.nationalacademies.org/read/5714/chapter/5), DOI 10.17226/5714.

Read: validation/calibration and intended-use discussion, especially printed pp. 30–31. Supports distinguishing model credibility from code correctness and caution about predictive use of simple models. Historical methodology reference, not a current certification standard or validation of battle.

### S25

**U.S. Marine Corps — MCDP 1, Warfighting**, chapter 1, sections on friction and uncertainty. [Official training-command PDF](https://www.trngcmd.marines.mil/Portals/207/Docs/SOI-W/MCTB/Student-Resources/Reference-1_MCDP-1_Warfighting.pdf?ver=2018-10-12-135248-037). Research date: 2026-11-04.

Read: official search-index excerpts from chapter 1, not the full PDF. Both the main marines.mil publication PDF and the training-command PDF returned 403. Used for the qualitative distinction between friction, incomplete information and chance in [friction and uncertainty](11-friction-and-uncertainty.md). Doctrine provides conceptual grounding, not empirical failure rates, universal historical coefficients or a validated game algorithm. Specific game mechanisms and acceptance tests are our proposals.

## Specialist units follow-up

### S26

**Firaxis / 2K — Civilization VI base-game manual.** [Publisher PDF](https://downloads.2kgames.com/civilization/vi/manuals/eu/CIV_VI_25TH_ONLINE_MANUAL_ENG.pdf). Read p. 59 on recon units and p. 37 on the espionage overview. The web reader rejected the file size; downloaded from the publisher and extracted locally. No precise spy mission claims are based on this manual. Inspected PDF SHA-256: `c172805eb222ed4b5af2ddf1226d9d4590857a7c67845efffc104e6d72aff1d0`. Used in [specialist research](13-specialist-units.md).

### S27

**David Thompson and Trevor Benjamin / Osprey — Undaunted: Normandy rulebook.** [Publisher PDF](https://www.ospreypublishing.com/media/nb5javdo/lr_undaunted_normandy_rulebook.pdf). Read pp. 11–13, Fog of War, Move/Scout and Recon actions. Supports scouts' movement-enabling and deck-management roles. No edition/version identifier established from the inspected text; do not treat its Fog of War cards as evidence of hidden map state. Used in [specialist research](13-specialist-units.md).

### S28

**Creative Assembly — Total War: Rome II official encyclopedia, Spies.** [Developer-hosted manual entry](https://r2enc.totalwar.com/en/manual/single-player/0048_enc_page_campaign_play_characters_agents_spies/). Read introduction, Military Intelligence, Counter-intelligence and Intercept Orders. Supports independent/embedded assignments and intelligence actions. Legacy online manual, no patch equivalence verified; political and character systems are excluded from battle's recommendation. Used in [specialist research](13-specialist-units.md).

### S29

**VR Designs / Matrix Games — Shadow Empire manual**, publisher-hosted snapshot retrieved 2026-11-04. [PDF](https://ftp.matrixgames.com/pub/ShadowEmpire/Shadow%20Empire%20manual%20EBOOK.pdf). Read p. 54 supply reporting, p. 142 operational logistics, p. 331 §5.11 and pp. 379–382 §5.14 recon. Network capacity, pickup reach and graduated intelligence support the comparison; exact rules are not historical coefficients. This retrieved manual contains expansion sections; no stable edition number asserted. Web retrieval hit timeout/size limits; publisher download and local text extraction succeeded. SHA-256: `262e2ecdc0cd7c8531e9980ac9c093ba9b288477b80b78ea107274f1a45cfed7`. Used in [specialist research](13-specialist-units.md).

### S30

**Dean N. Essig / Multi-Man Publishing — Operational Combat Series rules v3.1.** [Publisher archive PDF](https://mmpgamers.com/support/gamersarchive/ocs/OCS3-1SeriesRules.pdf). Read §§13.1b and 13.2, PDF pages 26–27, on HQ supply functions and transport capacity. Archival edition, not claimed current. Supports separating distribution authority/range from supply stock and transport, not a universal logistical model. Used in [specialist research](13-specialist-units.md).

### S31

**Impressions Games — Lords of the Realm III manual**, publisher-distributed Steam asset. [Manual PDF](https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/254860/manuals/Manual.pdf?t=1579791576), [store identity](https://store.steampowered.com/app/254860/). Read p. 29 special-ability text identifying Quartermaster as an army supply-state modifier; introductory text identifies Lords III. A PDF table screenshot request timed out; extracted text and indexed table text support only that broad claim. No numerical effect or current-runtime verification asserted. Used as a contrasting trait abstraction in [specialist research](13-specialist-units.md).

## Period command tools follow-up

### S32

**Susan Thompson, Command Historian / U.S. Army — Signal Corps in World War II, 2020-06-26.** [Army article](https://www.army.mil/article/236799/). Read discussion of field radio, relay, radar, photography and continued pigeon use. Used narrowly as institutional evidence of mixed WWII capabilities in [period command tools](14-period-command-tools.md), not as a detailed equipment establishment, numerical reliability source or endorsement of every broad comparative claim in the article.

### S33

**Imperial War Museums — Duxford Operations Block large-print interpretation, Fighter Command Group Layout / The Dowding System.** [Museum PDF](https://www.iwm.org.uk/sites/default/files/files/2020-09/OPS_BLOCK_Largeprint.pdf). Read official search-index excerpt on radar reports to Fighter Command and Observer Corps reports through the command system; full PDF returned 403. Supports only the broad report-processing precedent, not a reconstructed plotting procedure or a numerical delay. Air-defense organization must not be generalized to all field headquarters. Used in [period command tools](14-period-command-tools.md).

### S34

**U.S. Army Communicator — Signal Corps Support of Amphibious Operations, Spring 2024.** [Official article](https://www.lineofdeparture.army.mil/Journals/Army-Communicator/Spring-2024/Signal-Corps-Support-of-Amphibious-Operations/). Read official indexed excerpts discussing WWII radio, switchboards, field wire and damaged circuits; full page returned 403. Used only for qualitative amphibious communication dependencies in [period command tools](14-period-command-tools.md). No equipment ranges, exact establishment or timing constants adopted.

## Real-map preparation follow-up

### S35

**U.S. Geological Survey — Historical Topographic Maps: Preserving the Past.** [Official collection overview](https://www.usgs.gov/programs/national-geospatial-program/historical-topographic-maps-preserving-past). Read official indexed description of the historical collection, its 1884–2006 printed-map coverage and scanning/georeferencing; full-page retrieval timed out. Used as a candidate-source example in [real-map design](03-simulation-methods.md#real-maps-grid-overlays-and-terrain-interpretation), not a claim that a specific battle map or its historical accuracy has been verified.

### S36

**GDAL project — Geotransform Tutorial.** [Official documentation](https://gdal.org/en/stable/tutorials/geotransforms_tut.html). Read pixel/line-to-world affine transformation, six coefficients, rotation and pixel-center conventions. Supports coordinate alignment principles in [real-map design](03-simulation-methods.md#real-maps-grid-overlays-and-terrain-interpretation). Does not perform semantic terrain recognition, validate historical source accuracy or select GDAL as the project stack. Accessed 2026-11-04.

## Retrieval gaps and follow-up evidence

- **Warzone browser game:** attempted `https://www.warzone.com/wiki/Turn_structure` and `https://www.warzone.com/wiki/Fog`; inaccessible/redirected to an unavailable transfer endpoint. No gameplay claim relies on these failed retrievals.
- **Wesnoth homepage:** anti-bot access denial; official mechanics wiki remained readable. No live multiplayer-service test performed.
- **POMCP:** two failed routes noted under S19; original proceedings abstract successfully read.
- **Chain of Command:** final second-edition rulebook not inspected; development discussion only.
- **Historical validation:** no matched platoon-level casualty/exposure dataset, validated mutiny model, civilian behavior dataset, naval damage calibration, or detailed WWII establishment/weapon pack assembled.
- **Evo:** no host inspection or execution; no claimed benchmark results.

Search discovery also surfaced community discussions and secondary summaries. They helped locate primary material but are not relied upon for exact rules or algorithm claims. The source register is intentionally bounded to the material used in these notes.

## Playable POC follow-up — accessed 2026-11-05

### S37

**National Park Service — 20th Maine Infantry Regiment Monument.** [Official account](https://www.nps.gov/places/20th-maine-monument.htm). Read the account identifying the July 2 Little Round Top defense and opposing 15th/47th Alabama formations. Supplies historical setting and parent unit names only. The POC's detachments, strengths, ammunition, timing and placements are authored abstractions. See [POC record](16-playable-poc.md).

### S38

**John B. Bachelder / Library of Congress — Map of the battle field of Gettysburg. July 1st, 2nd, 3rd, 1863.** [Official resource and metadata](https://www.loc.gov/resource/g3824g.cw0325000a/), item 99447491. Indexed official metadata inspected; direct HTML returned 403. Publication field says 1876; generated citation/date fields say 1879. The first-day sheet's topography is used as a static backdrop, not as second-day unit positions. The 1600-pixel image was downloaded from LOC and visually inspected; crop coordinates and rights credit are recorded in [POC provenance](16-playable-poc.md). Higher-resolution requests failed with 403. No GIS registration or historical terrain extraction claimed.

### S39

**OpenRouter — API reference overview.** [Official documentation](https://openrouter.ai/docs/api_reference/overview). Read the chat-completions request/response, authorization header and JSON response-format contract. Used for the server-side inference adapter. A live computer-command request and staff-chat request succeeded using `openai/gpt-4.1-mini`; this verifies those calls, not continuous provider availability or tactical quality.

## User requirement follow-up — 2026-11-05

The user requested era-appropriate unit speech in the specs/demo, i18n as a default product intent, internal messaging between players, and cooperative, antagonistic and terrain-control multiplayer scenarios. This primary product direction is recorded in [language, localization and multiplayer](17-language-localization-and-multiplayer.md). Its speech examples are original illustrative text; its proposed data contracts are design work, not sourced historical findings. No additional external research was needed for this update.

The user further clarified the campaign direction with a “Risk-like” example: armies/units deployed across multiple fronts. The [campaign specification](17-language-localization-and-multiplayer.md#campaign-play-across-multiple-fronts) records that product intent and distinguishes it from an adoption or researched account of Risk rules.

### User clock requirement — 2026-11-05

Direct project instruction: replace Advance with a stoppable, startable, faster/slower clock and replay. Source: this conversation; no external factual claims. Local implementation and verification boundaries are documented in [18](18-simulation-clock-and-replay.md).

### User map-style reference — 2026-11-05

The user supplied a Google Maps screenshot of the Gettysburg area and requested stylized rather than photographic maps. The image is a visual reference for flat land colors, readable labels and clean cartography, not evidence for 1863 terrain, routes or building locations. The POC renderer creates original SVG from existing authored scenario terrain and does not copy the screenshot or use Google map tiles. See the [map update](16-playable-poc.md#stylized-map-update--2026-11-05).

### Open-source cartography — 2026-11-05

User preference: use an OSS map tiler/renderer. Primary sources: [MapLibre repository/license](https://github.com/maplibre/maplibre-gl-js), [GeoJSONSource](https://maplibre.org/maplibre-gl-js/docs/API/classes/GeoJSONSource/), [style sources](https://maplibre.org/maplibre-style-spec/sources/), [introduction/CSP](https://maplibre.org/maplibre-gl-js/docs/), [PMTiles integration](https://docs.protomaps.com/pmtiles/maplibre), [PMTiles project](https://github.com/protomaps/PMTiles), [MapLibre data guide](https://makewithmaplibre.com/data/), [Leaflet reference](https://leafletjs.com/reference). Accessed 2026-11-05. Software capabilities only, not historical terrain evidence. See [comparison, implemented scope and limitations](19-open-source-map-rendering.md). Vendored npm release 5.12.0 integrity and origin are recorded alongside its license.

### Reconnaissance and standing reactions — 2026-11-05

Direct user requirement: improve enemy composition estimates through sightings, give scouts/spies estimation advantages, and make unit commanders defend/retreat and react to contact without orders. [Implementation contract](20-reconnaissance-and-standing-reactions.md). Thresholds, estimation bands and local doctrine are authored POC choices, not sourced historical measurements. Existing specialist research remains in [13](13-specialist-units.md).

### God Mode and command location — 2026-11-05

Direct user requirement: an omniscient observation mode, and a player physically located in a command unit using period communications. [Contract and implementation](21-god-mode-and-command-location.md).

**NPS, Antietam National Battlefield — The Signal Corps**, updated September 15, 2023. [Official page](https://www.nps.gov/anti/learn/historyculture/signal.htm). **NPS, Harpers Ferry — Information Panel: Flag Talk**, updated March 8, 2023. [Official page](https://www.nps.gov/places/000/information-panel-flag-talk.htm). Both accessed 2026-11-05. Evidence for Civil War signaling, equipment, terrain/visibility constraints and technology-dependent delay. They do not establish particular equipment for the POC detachments or validate the courier rate, automatic friendly forwarding, or U2/C2 commander attachments. Those are authored abstractions.

User control clarification (2026-11-05): explicit God Mode toggle and Reset. Implemented UI semantics are recorded in [21](21-god-mode-and-command-location.md#control-clarification--2026-11-05); no additional historical claims.

### Unit details and actions — 2026-11-05

Direct user requirement: clicking a unit shows strength and options including move, give an order, split and combine. [Implementation contract](22-unit-panel-and-formation-actions.md). The 12/80-person bounds, 60-second regrouping time and condition restrictions are authored POC design decisions, not historical measurements. No additional external historical claims.

### Common order templates — 2026-11-05

Direct user requirement: a reusable catalog including rest, retreat and resupply. [Implementation and limits](23-common-order-templates.md). The six template contracts, fatigue rate, ammunition quantities, loading limits and depot positions are authored POC design choices. No external historical measurements or quotations are claimed.

### Map features and Dig in — 2026-11-05

Direct user requirement: roads, fortifications and buildings on the map, plus a “dig in” order. [Implementation and limitations](24-map-features-and-digging-in.md). Locations, obstacle heights, road costs, initial tool inventories and construction coefficients are original authored POC choices, not external historical findings.

### Commander recommendations — 2026-11-05

Direct user requirement: unit commanders recommend actions, indicated by a flag or moving runner. [Implemented contract](25-commander-recommendations.md) uses delivered UI flags and existing courier transport. Recommendation priorities, thresholds, cooldown and expiry are authored POC choices, with no historical measurement claims.

### Standing orders and troop analysis — 2026-11-05

Direct user requirement: set or recommend standing orders and analyze units/troops before starting or at any time. [Implemented contract](26-standing-orders-and-troop-analysis.md). Doctrine thresholds, readiness concerns and recommendation priorities are authored deterministic POC choices. This entry adds no external historical claims or copied game rules.

### Structured demo architecture — 2026-11-05

Direct user requirement: structured code, DI, SOA and separation of concerns to simplify later conversion. [Implemented architecture](27-service-architecture-and-dependency-injection.md) records original project design choices and local verification. No new external-source or historical claims are introduced.

### Monorepo and full-stack direction — 2026-11-05

Direct user requirement: keep the POC in its own monorepo subdirectory; likely Vercel/TypeScript/Next.js for the future application, with recommendations requested. [Layout, proposal and limitations](28-monorepo-and-stack-direction.md).

Official sources, accessed 2026-11-05:

- [Next.js Server and Client Components](https://nextjs.org/docs/app/getting-started/server-and-client-components): server/client responsibility boundaries; current App Router documentation.
- [Vercel monorepos](https://vercel.com/docs/monorepos): project root selection and workspace-aware build dependencies.
- [Vercel Daemons](https://vercel.com/docs/daemons): continuous container processes, public-beta status and production-only restriction.
- [Vercel background workers](https://vercel.com/docs/background-workers): worker/queue/workflow choices, ephemeral local storage and external persistence.
- [Vercel function duration](https://vercel.com/docs/functions/configuring-functions/duration): generally available and beta invocation bounds; page reports updated August 24, 2026.
- [Vercel WebSockets](https://vercel.com/docs/functions/websockets): native support, bounded connection lifetime, reconnect and shared-state requirements.

These sources establish software capabilities only. Hosting suitability, cost, latency and production recovery remain unmeasured. Proposed service ownership and migration tests are original design choices, not vendor guarantees. Recheck beta availability and plan limits before deploying.

### One battlefield timeline — 2026-11-05

Direct user requirement: show location and day/date, with one timeline and no turns. [Implementation](18-simulation-clock-and-replay.md#one-battlefield-timeline--2026-11-05). Location/date use the existing Little Round Top provenance in [16](16-playable-poc.md). No new historical measurement claims; the start time remains authored.

### Unit counters — 2026-11-05

Direct user requirement: split/combine units and show strength, type, skill, energy and morale in icons. [Display contract](29-unit-counters-and-readiness.md). Energy is an original UI mapping of existing fatigue, not a historical calibration or new simulation rule. No additional external sources.

### Design scale assessment — 2026-11-05

[Assessment and evidence](30-design-scale-assessment.md) draws on inspected poc-8 source, one fresh local scripted SQLite run and three policy/synthetic scan probes. The report links the original source, method and scope limits. No external capacity, historical calibration or deployment claims.

### Evo target and TypeScript portability — 2026-11-05

Direct user target decision and verified framework/runtime documentation: [rationale, primary sources and deployment limits](31-evo-target-and-typescript.md).

### Historical units and their colors — 2026-11-05

[Claim-by-claim source register and artifact links](32-historical-units-and-colors.md). Morrill, Chamberlain and Oates supply action testimony. Ohio State eHistory and Liberty Rifles identify company names and recruitment. Maine’s state collection, veterans’ account, Alabama archive photograph and New York State Military Museum catalog establish different levels of evidence for the colors. The included original illustration is marked as an inference.

### OpenRouter image generation — 2026-11-05

[Provider documentation and live generation record](33-openrouter-unit-images.md). The illustration accompanies a historical profile and has no role in combat adjudication.

### Six eras — 2026-11-05

[Case-by-case source register](34-six-era-command-tests.md) includes participant accounts, institutional histories, original orders where recoverable, and limits on the proposed translations into game orders.

### Field glasses, appearance variation and Cannae

[Field glass](35-field-glasses-and-appearance.md) records the checked local observation, generated asset, model, cost and visual limitations. [Cannae](36-cannae-army-scale.md) uses Polybius III.113–117 and Livy XXII.45–50, distinguishing their historical accounts from the proposed controller instructions and synthetic route test.

### Battle gallery research — November 5, 2026

[Gallery register](battle-gallery/README.md) links the per-action manifests and scene captions. [Cannae visual research](battle-gallery/cannae.md) ties formation, kit, terrain and visibility to Polybius III.113–117, Livy XXII.43–49, the Italian Ministry of Culture's Canne site record and the University of Liverpool landscape comparison (2016, fig. 4). Archive photographs and reference pages are not bundled as source art.

## First-five selection register — 2026-11-06

Access date for every entry: **2026-11-06 (UTC)**. Used in [37 — first five selections and source register](37-first-five-selection-register.md), which states what each source supports and where its evidence stops.

### S40

**Sam K. Cowan — *Sergeant York and His People*.** Funk & Wagnalls, copyright 1922; Grosset & Dunlap printing. [Project Gutenberg eBook #19117](https://www.gutenberg.org/files/19117/19117.txt), released 2006-08-25. Read the narrative of 8 October 1918, the printed diary excerpts and the excerpts of four survivors' affidavits (Donohue, Sacina, Beardsley, Wills). Supports the diary's order and outcome statements and the affidavits' existence among Buxton's records. A 1922 popular book that frames the affidavits as confirming York; the full affidavits were not read.

### S41

**James P. Gregory Jr. — *Unraveling the Myth of Sgt. Alvin York: The Other Sixteen*.** Texas A&M University Press, 2023, ISBN 9781648430763. [Project MUSE listing](https://muse.jhu.edu/book/125322). Read the publisher's summary, contents and appendix titles only. Supports the existence of the survivors' later dispute; the book's evidence was not read.

### S42

**Middle Tennessee State University via Newswise — site-location release, 2006-12-08.** [Release](https://www.newswise.com/articles/researchers-utilize-scientific-detection-historic-evidence-to-uncover-sgt-yorks-battle-site). Read the method (GIS, historic maps, 1919 affidavits, 1929 correspondence) and reported artifacts. An institutional press release, not a peer-reviewed report.

### S43

**CBN report reposted by History News Network, 2007-03-25 — "Army officer: Sgt. York battle site located".** [HNN page](https://www.hnn.us/article/37526). Read only that Lt-Col Douglas Mastriano disputed the MTSU site. Gives no coordinates for either site.

### S44

**Wellington to Bathurst, 19 June 1815.** [Wikisource transcription](https://en.wikisource.org/wiki/Wellingon%27s_Waterloo_dispatch_to_Lord_Bathurst,_19_June_1815), citing *London Gazette Extraordinary* no. 17028, 22 June 1815, pp. 1213–1215, and Gurwood (1838) pp. 478–484. Read the Hougoumont passage: Byng's Guards detachment under Macdonell, then Home; held all day; no gate mentioned. Transcription not checked against the Gazette scan.

### S45

**Age of Revolution (Waterloo Association) — object pages.** [Battle Instructions written by the Duke of Wellington](https://ageofrevolution.waterlooassociation.org.uk/200-object/battle-instructions-written-by-duke/) (Apsley House) and [Lock of the Gate of Hougoumont](https://ageofrevolution.waterlooassociation.org.uk/200-object/lock-of-the-gate-of-hougoumont/) (Guards Museum). Read the note's instructions to Macdonell about the fire, and the names given for the gate party and the French party. Neither page cites a primary source for the gate narrative.

### S46

**Gareth Glover Collection — "Private Matthew Clay at Quatre-Bras and Waterloo".** [Page](https://garethglovercollection.com/?p=130). Read the publication details (Bedford, 1853; Ken Trotman reprint 2006, ISBN 1905074255) and Glover's argument that two break-ins were merged in later retellings. Clay's text itself was not read.

**Re-read 2026-11-06 (already cited in [34](34-six-era-command-tests.md)):** Age of Revolution *Closing the Gates*, NAM *Battle of Waterloo*, NPS *April 19, 1775*, NPS Oates report, Paradata *Pegasus Bridge*. **Not retrievable or not read 2026-11-06:** the *Army History* "Field study of Hill 223" item cited in [34](34-six-era-command-tests.md) (HTTP 403 at history.army.mil and at a ky.ng.mil mirror; no readable copy found; kept in 34 and the fixture marked dead and unverified). The second item, "The other sixteen", was replaced in 34 and the fixture by the S41 Project MUSE listing (HTTP 200, 2026-11-06 UTC); no Spring 2026 *Army History* article under that title was found; the Clements Library Gage manuscript (HTTP 403); Mastriano's 2007 report (unreadable PDF) and later book; York's official Medal of Honor citation; Beamish vol. 2 (Baring); Clay 1853; Siborne, *Waterloo Letters* (1891). [37](37-first-five-selection-register.md) relies on none of these.

## Concord North Bridge spec — 2026-11-06

Access date for every entry: **2026-11-06 (UTC)**. Used in [43 — Concord North Bridge scenario build spec](43-concord-scenario-spec.md). Read through a summarising fetch, so quoted phrases may be paraphrased.

### S47

**Minute Man National Historical Park — *The events of April 19*.** [Page](https://www.nps.gov/mima/learn/historyculture/april-19-1775.htm), updated 2025-05-17. Read the North Bridge timeline (07:30, 09:00, 09:30, 11:00), Laurie's three companies of about 96 men, about 400 militia, Barrett's and Buttrick's orders, the three first shots and the unordered British fire, and the casualties at the bridge. Does not say which bank each force held, and does not confirm the plank removal.

### S48

**National Park Service — *Captain Isaac Davis*.** [Page](https://www.nps.gov/people/captain-isaac-davis.htm), updated 2023-01-17. Read the company size (about 40), the company's place in front of the column with Buttrick and Robinson, and Davis's death at the bridge with Private Abner Hosmer. Names no successor to Davis.

### S49

**American Battlefield Trust — *Old North Bridge*.** [Page](https://www.battlefields.org/learn/articles/old-north-bridge), published 2023-03-04, updated 2024-04-19. Read the force figures (two British companies guarding the bridge, about 90 men; close to 400 militia). Differs from S47 on the number of companies. Names neither bank, nor who fired first.
