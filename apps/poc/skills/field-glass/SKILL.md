---
name: field-glass
description: Render an inferred eye-level view from a player's command position, using a brief description of what that observer could see.
---

# Look across the battlefield

**Map interaction.** Place the [binocular icon](binoculars.svg) beside the map controls. Its button has a localized accessible name, “Look across the battlefield”, a visible focus indicator and a pressed state while aiming. Let the player select a bearing by clicking a map hex or using keyboard direction controls. Identify the observer, direction and local observation time. “Take a look” generates once. Loading, cancel, retry and close leave the clock alone.

**Viewpoint and period.** Start at the player's command formation. An aim point sets direction, even if the crest in front obscures it. Apply the ordinary sight range and equipment profile. The icon is an interface convention across eras. In a Roman scenario use unaided eyesight unless scenario evidence establishes another capability. A distant scout's image can be reviewed only as a separately dated, delivered dispatch. Do not transfer the player to the scout.

**Local scene projection.** From a single committed revision, project a viewing cone against the scenario’s hex elevations, cover, woods, structures, sight limits and seasonal/weather visibility. Describe foreground, middle distance and skyline relative to the observer. Use only features the observer can see. A road continues behind a crest only in the map briefing. Show that road in the image only up to the visible crest. Use battlefield time for light. Do not imply precise atmospheric or illumination measurements the scenario does not contain.

**Enemy evidence.** Use fresh local sightings by this observer inside the cone. A confirmed but partly concealed formation can appear behind cover; a weak sighting permits indistinct movement. Smoothed strength bands do not license individually countable men, insignia or exact weapons. Omit stale reports, rumors, contacts seen solely by other units, and God Mode truth. Empty sighting evidence permits a landscape view. The generated pixels never create contacts, orders or evidence. Keep the deterministic contact summary beside the reconstruction.

**Provider boundary.** The [sample observation packet](example-observation.json) is local test evidence. Only a short prose scene description approved for this player's view may go to OpenRouter. Use allowlisted phrases for terrain relationships, season, weather, period equipment and contact clarity. Exclude raw data, coordinates, IDs, saves, dispatch text, event logs and screenshots. Use the server-only image adapter and model setting from the [unit illustration skill](../illustrate-unit/SKILL.md). Put the caption “Field-glass reconstruction” in the interface. Provide equivalent localized text for players who cannot see the image.

**Time, reuse and failure.** Key the authorized local snapshot by battle, observer, observation time, bearing, view settings and renderer edition. Deduplicate paid work for identical authorized briefs and settings. Recheck access before revealing any stored image. When a request returns, attach it to its original observation time. Replay can reopen a saved image without generating. Offline or failed generation still displays the local sightline description. Keep profile art, battlefield imagery and command-map rendering separate.

**Acceptance.** Verify a crest hides a unit, changing hidden enemy state leaves the exported brief identical, a stale remote sighting contributes no live figures, a seasonal change affects the visible scene, and map panning, double clicks, replay and opening God Mode do not generate extra calls. Check both pointer and keyboard paths, caller authorization and the serialized outbound body.

**Visual check.** Treat extra tracks, missing obstacles, crisp soldiers from a weak sighting and invented structures as material discrepancies. The first provider trial made a road-like gap where no road was visible. Preserve the text summary as the authoritative reading. In the POC, review example assets before using them as demonstrations; if a scene cannot be shown faithfully, use the local terrain/observation summary instead. Never derive targeting or pathfinding from generated pixels.

If uniforms are actually visible, use the [profile’s seeded dress and condition variation](../illustrate-unit/SKILL.md#variation-in-dress-and-accoutrements). At low confidence or beyond identification distance, render indistinct movement and omit all unit-specific dress cues. Use only the approved short outbound description, never lineage, seed, IDs or exact personnel/equipment counts.
