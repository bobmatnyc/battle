/* Presentation-only status of each drawn map mark: sourced (with the citation),
 * reconstructed, or illustrative. docs/research/72 §3.
 *
 * Why: a player must be able to tell a sourced feature from an authored one, and
 * the owner's default ruling keeps that out of engine and scenario data, so no
 * edition, replay digest or contract fixture changes.
 * What: scenario id -> mark key -> {status, source, footprint_m?}. A key is a
 * feature id; `<building>#walls` and `<building>#<opening>` for a compound's walls
 * and gates; `crossing:c,r` for a bridge crossing cell that is not a bridge feature.
 * `footprint_m` is the drawn building size in metres (width, depth), itself authored;
 * `name` labels a crossing cell, which has no feature name.
 * Citations are the S-ids of docs/research/09-sources.md and each entry's
 * `provenance`; anything without a cited source is illustrative.
 * Test: scripts/check_map_features.mjs (coverage, status in tooltip and legend). */
const BattleFeatureSources = (() => {
  const LRT = 'Authored POC content (docs/research/24): position and width illustrative, not a surveyed 1863 feature.';
  const HOUGOUMONT = "Authored: the entry's map is an illustrative layout, not surveyed (docs/research/42); no source places this lane.";
  const CONCORD = "Authored: the entry's map is an illustrative layout, not surveyed (docs/research/43); no source places this road.";
  const PEGASUS = "Authored: the entry's map is an illustrative layout, not surveyed; no map sheet was read (docs/research/52 §7).";
  const S54 = 'S54 (Wikipedia, Operation Deadstick; secondary) lists this defence; its hex and cover are authored.';
  const concord = {
    'muster-road': {status: 'illustrative', source: CONCORD},
    'town-road': {status: 'illustrative', source: CONCORD},
    'crossing:12,10': {status: 'reconstructed', name: 'North Bridge', source: 'North Bridge over the Concord River (S47, S49). '
      + 'Planks intact is a reconstruction: S47 says an officer suggested lifting them and does not confirm it '
      + "(entry map.bridge). The hex is authored; the bridge hex costs its own movement, not the road's."},
  };
  const TABLE = {
    'little-round-top': {
      'north-lane': {status: 'illustrative', source: LRT},
      'south-track': {status: 'illustrative', source: LRT},
      farmstead: {status: 'illustrative', source: LRT + ' Footprint 30 x 18 m authored.', footprint_m: [30, 18]},
      barn: {status: 'illustrative', source: LRT + ' Footprint 26 x 14 m authored.', footprint_m: [26, 14]},
      'prepared-works': {status: 'illustrative', source: LRT},
    },
    'hougoumont-north-gate': {
      'north-lane': {status: 'illustrative', source: HOUGOUMONT},
      'west-lane': {status: 'illustrative', source: HOUGOUMONT},
      'wood-ride': {status: 'illustrative', source: HOUGOUMONT},
      hougoumont: {status: 'illustrative', footprint_m: [40, 26],
        source: 'Chateau and farm buildings: footprint 40 x 26 m authored; no plan or survey was read (docs/research/42). '
          + 'S44 names Hougoumont, held by a Guards detachment, but places no building.'},
      'hougoumont#walls': {status: 'illustrative',
        source: 'Walled compound of 7 hexes (the chateau hex and its six neighbours, about 150 m across) is authored '
          + '(docs/research/42); no source read gives the wall line.'},
      'hougoumont#north-gate': {status: 'sourced',
        source: 'Open north gate for friendly traffic: Age of Revolution, Closing the Gates at Hougoumont, 1815; NAM, '
          + 'Battle of Waterloo (docs/research/37 §2); both secondary and uncited. Its hex edge is authored.'},
    },
    'concord-north-bridge': concord,
    'concord-north-bridge-v1': concord,
    'pegasus-bridge': {
      'benouville-road': {status: 'illustrative', source: PEGASUS},
      'bridges-road': {status: 'illustrative', source: PEGASUS},
      'ranville-road': {status: 'illustrative', source: PEGASUS},
      'west-mg-posts': {status: 'sourced', source: S54},
      'west-trenches': {status: 'sourced', source: S54},
      'east-mg-post': {status: 'sourced', source: S54},
      'orne-pillbox': {status: 'illustrative', source: "Unlabelled in the entry; map.defences says the pillbox 'to the north' "
        + 'is not placed, so which pillbox this is stays open (docs/research/64 §6 question 4).'},
      'canal-bridge': {status: 'reconstructed', source: 'Caen Canal bridge at Bénouville (S51 p. 1 para 2); wired with charges '
        + 'is inferred (S54, secondary; S51 p. 1 para 3: sappers "cut wires and removed charges"). The hex is authored.'},
      'crossing:19,10': {status: 'sourced', name: 'Orne bridge', source: 'Orne bridge at Ranville (S51 p. 1 para 2); not a bridge feature in this '
        + 'variant, so it has no state and stays passable. The hex is authored.'},
    },
    'hill-223-patrol': {
      'old-trench': {status: 'sourced', source: 'S40 (Cowan, Sergeant York and His People) narrative: an old trench on the '
        + 'hillside on the route (docs/research/56 §7); its hex and cover are authored.'},
    },
  };
  /** The status table of one scenario: a copy, empty for a scenario with no marks. */
  function forScenario(id) {
    return JSON.parse(JSON.stringify(TABLE[id] || {}));
  }
  return {forScenario};
})();
