---
name: illustrate-unit
description: Generate a photorealistic historical reconstruction of an identified unit using OpenRouter.
---

# Illustrate a unit

Use this game skill when a player requests an illustration from a historical unit profile. Caption the image **AI reconstruction**. Preserve the stylized command map.

1. Resolve the selected profile through the player's normal view. Use only the identified historical formation, era, terrain description, role and supported equipment. Omit undated colors, hidden contacts, current strengths and live battlefield positions. The skill depicts an aggregate unit. The number of figures does not represent its strength.
2. Request one image of the documented scene. Match the [tested request](example-request.json). Use the dedicated OpenRouter image endpoint and the existing server-side credential. Configure the requested model with OPENROUTER_IMAGE_MODEL, default google/gemini-2.5-flash-image, independently of the commander model. Verify output capability before substituting a model.
3. Decode data[0].b64_json. Limit response size and validate the actual raster and dimensions. Persist an asset ID, checksum, profile and source revisions, caption, skill version, requested model, and returned model and cost when available. Show the localized label with the image.
4. Reuse an accepted asset on repeat requests, offline and during replay. Deduplicate identical in-flight requests by profile edition, style and model. Check the player's permission again when serving cached art. On timeout or invalid output retain the prior image and offer an explicit retry. Run generation outside the simulation clock and store no art decisions in combat state.
5. Verify the integration by generating once from a unit panel, reopening the same asset offline, and checking that unidentified contacts cannot request or retrieve it. Test simultaneous clicks, failed responses and key isolation with a fake provider before a separate live smoke.

[Live provider example, evidence and historical sources](../../../../docs/research/33-openrouter-unit-images.md)

## Variation in dress and accoutrements

Before generating the scene, select visual variants from the dated unit profile. Draw independently only between interchangeable details supported by that profile. Use documented issue proportions when known. Otherwise allow an equal draw among plausible variants for artistic variety, label the mix inferred, and avoid implying a measured historical distribution. Keep a consistent baseline within a unit and within a clothing issue. For example, the 15th Alabama impression allows muted brown or gray jackets. Do not impose the same palette on the 20th Maine or on a different century.

Apply visible condition as a separate layer: known dry marching can add dust to hems, rain can darken wool, and reported fatigue can affect posture. Do not turn morale into literal damage, infer losses from torn clothes, or add missing equipment to make a unit look more varied. A split inherits the parent's appearance mix; a combine carries the component mixes forward. Keep this aggregate and use no persistent individual identities.

Draw with a dedicated cosmetic seed keyed to scenario/profile edition and formation lineage, retaining the selected mix with the asset. Weather, wear and posture can change when reported conditions change. Reopening the unit or replaying the same moment must not redraw the mix. Save the accepted image. A seed alone cannot reproduce an external model's pixels. Apply the same visibility cap to these details as to unit identification.

[appearance.py](appearance.py) is a callable reference sampler for the adapter. Supply a list of allowed phrases with relative weights, a local cosmetic seed, authorized condition phrases and the visibility decision. Include its returned prose in the prepared image brief. The function uses a private random generator and sends no requests.
