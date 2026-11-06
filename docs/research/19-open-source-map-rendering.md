# Open-source map rendering and tiles

Date and source access: 2026-11-05. **User requirement:** prefer an OSS map tiler/renderer for the stylized command map.

## Decision and implemented POC

Use **MapLibre GL JS** as the browser renderer. It supports custom vector styling and internally tiles GeoJSON sources. The small current battlefield therefore needs no separate tile server. Its existing terrain polygons and interpolated contours become GeoJSON; MapLibre handles tiling, WebGL rendering, pan and zoom. The observer-filtered SVG command overlay remains above the terrain and follows the same projection. This retains accessible unit selection, hex targeting, fog of war and replay without introducing world-state authority in the map.

The demo vendors MapLibre GL JS **5.12.0**, a pinned release rather than an automatically changing CDN dependency. The npm package archive was checked against its registry SHA-512 integrity value. Assets, the BSD-3-Clause license with bundled dependency notices, and download provenance live in `static/vendor/maplibre/`. This is the first browser library dependency; Python still uses the standard library and there is no frontend build. The downloaded release is not claimed to be the newest release.

The CSP build uses an explicitly configured same-origin worker. No remote basemap, glyph server, tile account, Google API, CDN or runtime map-service request is required. The local source contains only scenario terrain, never hidden units, reports or agent decisions. Model calls and battle timing are unchanged. If the library, worker or WebGL cannot initialize, the map returns to the existing SVG renderer and displays a fallback notice; commands remain available.

Controls: drag to pan, wheel/pinch or plus/minus to zoom, **Fit** to return to the full field. Elevation and hex visibility remain independent controls. Map zoom does not alter metres per cell, movement costs or simulation time. Camera state is presentation-only and is not stored in battle replay.

### Coordinate limits

The authored POC is not georeferenced. For this renderer adapter only, local scene coordinates are encoded into a small Mercator plane centered at zero longitude/latitude. These coordinates are neither actual Gettysburg locations nor exported geographic evidence. One adjacent-center spacing remains exactly 50 metres in the adapter's local metric plane. The static shapes, contours and command overlay use the same conversion, with north opposite the SVG y-axis. A real-map scenario must supply a validated projection, origin, alignment and provenance before substituting actual geographic features or matching tile archives. Do not mix a modern Gettysburg basemap into this unregistered battlefield.

## Larger-map proposal: PMTiles

For larger battlefield/campaign regions, prebuild versioned vector archives and read them with the **PMTiles** MapLibre protocol adapter. PMTiles supports retrieving tiles from a single archive on static storage, avoiding a dedicated tile application server when HTTP byte ranges are available. A local serving implementation would need correct Range/206 handling; the current Python static handler has not been extended for PMTiles. The PMTiles adapter and archives are **not installed or integrated** in this POC.

Suggested content pipeline: curated historical vectors and elevation data → validated coordinate system and terrain interpretation → tile generation → versioned PMTiles archive → MapLibre style. **Tippecanoe** is a candidate for producing vector tiles from large GeoJSON; **Planetiler** is a candidate for regional basemap generation. Evaluate these tools against actual source datasets when importing a larger map. They are not needed for 504 terrain cells, and no global or regional tileset was downloaded here.

Modern OpenStreetMap-derived land, roads and buildings can help author geographic reference layers, but are not automatically valid for 1863 or any other scenario date. Provider/data licenses and attribution are separate from the renderer's OSS license. No modern roads or POIs should silently become historical traversability or cover.

## Alternatives and tradeoffs

| Option | Fit for battle | Decision |
|---|---|---|
| MapLibre GL JS | Styled vector tiles, built-in GeoJSON tiling, pan/zoom; WebGL dependency | Implemented with SVG fallback |
| Leaflet | Lightweight 2D maps, custom grid layers and simple coordinate systems; good match for raster tiles/SVG | Viable alternative; MapLibre better matches future styled vector archives |
| PMTiles | Archive/delivery format and browser adapter, not a renderer or generator | Proposed for larger maps |
| Dedicated tile server | Useful for dynamic geospatial queries or server-generated tiles | No current POC need; deployment remains deferred |

## Sources

Primary sources checked 2026-11-05:

- [MapLibre GL JS repository and license](https://github.com/maplibre/maplibre-gl-js): open-source vector rendering and BSD-3-Clause license.
- [GeoJSONSource documentation](https://maplibre.org/maplibre-gl-js/docs/API/classes/GeoJSONSource/): internal tiling of GeoJSON and source data behavior.
- [MapLibre style sources](https://maplibre.org/maplibre-style-spec/sources/): GeoJSON/vector source contracts.
- [MapLibre introduction and CSP guidance](https://maplibre.org/maplibre-gl-js/docs/): worker and asset loading guidance. Current docs can differ from the pinned 5.12.0 distribution; the shipped CSP bundle was verified in the browser.
- [PMTiles MapLibre integration](https://docs.protomaps.com/pmtiles/maplibre) and [PMTiles project](https://github.com/protomaps/PMTiles): archive/protocol capabilities.
- [MapLibre data guide](https://makewithmaplibre.com/data/): format support and conversion paths including Tippecanoe and Planetiler. These larger-data paths were reviewed, not executed.
- [Leaflet reference](https://leafletjs.com/reference): custom GridLayer, SVG overlay and CRS alternatives.

## Verification

`node scripts/check_map_geometry.mjs` checks 504 closed terrain rings, contour features, 50 m horizontal spacing, and non-mutation of scenario inputs. The existing UI harness checks command wiring and clock/reset behavior; it stubs the renderer, so it is not evidence of WebGL rendering. Actual browser verification is recorded below. Python rules and stored battle schemas have not changed.

### Local verification record — 2026-11-05

MapLibre loaded its bundled worker and rendered the actual terrain in the browser with no console warnings/errors. Zoom changed the view from 1× to 2×; keyboard pan moved the projected SVG overlay with the terrain. Elevation styling remained aligned. The geometry check also verified a missing-library fallback restoring the SVG and a visible notice. All 39 Python tests, the map geometry/fallback check, UI smoke and offline HTTP integration passed. No battle rules changed, no remote jobs ran and no deployment occurred.

Final browser check confirmed hex 12,13 targeting after selecting U2, the 100 m scale, and the MapLibre renderer after restarting the local server with the explicit worker policy. No orders were submitted. The existing completed battle replayed identically across 15 revisions / 14 intervals. Screenshot: `artifacts/battle-maplibre.jpg`. Pan/zoom changes only the command-map view; the pre-existing running battle was allowed to complete, and its history was retained.
