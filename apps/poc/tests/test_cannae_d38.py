"""The cannae-d38 rules edition (docs/research/82): Bob's D38 ruling (2026-11-08
17:41Z) on doc 79 §7. Every Cannae entry opts in; an entry without the edition,
and every snapshot recorded before it, scores as before.
"""

import hashlib
import json
import unittest
from dataclasses import replace

from battle import grid, victory
from battle.scenario_cannae import CANNAE_ENVELOPMENT as ENTRY, VARIANTS, cannae_entry
from battle.scenario_entry import build_state, validate
from battle.victory_encircle import D38

OLD = cannae_entry(edition=None)  # The rules every Cannae run before docs/research/82 was recorded under.
# sha256 of build_state(CANNAE_ENVELOPMENT) at d4e3ac7, the base of docs/research/82.
D4E3AC7_OPENING = "4f5f2b720e9364f26847f40ac3de96799768368ddf0af690943e80d53469f65d"


def unit(s, uid):
    return next(u for u in s["units"] if u["id"] == uid)


def sha(s):
    return hashlib.sha256(json.dumps(s, sort_keys=True).encode()).hexdigest()


def ringed(entry, routed=(), zoc=0):
    """A snapshot of ``entry`` with L1 at (5, 5) inside a ring of six Carthaginians,
    the ``routed`` of them routed, the rest of the Carthaginians at (0, 0)."""
    s = build_state(entry)
    s["victory"]["zoc"] = zoc
    carthaginians = [u for u in s["units"] if u["side"] == "carthaginian"]
    for u in carthaginians:
        u["pos"] = [0, 0]
    unit(s, "L1")["pos"] = [5, 5]
    for u, p in zip(carthaginians, grid.neighbors([5, 5])):
        u["pos"] = p
        if u["id"] in routed:
            u["status"] = "routed"
    return s


class EditionTests(unittest.TestCase):
    def test_every_cannae_entry_opts_into_the_d38_edition(self):
        self.assertEqual(D38, "cannae-d38")
        for entry in (ENTRY, *(v.entry for v in VARIANTS.values())):
            with self.subTest(entry.id):
                s = build_state(entry)
                self.assertEqual((entry.victory.edition, s["victory"]["edition"]), (D38, D38))
                self.assertTrue(s["scenario"].endswith("-v2"), s["scenario"])
                self.assertIn("D38", entry.provenance["victory.edition"])
        s = build_state(OLD)
        self.assertNotIn("edition", s["victory"])
        self.assertEqual(s["scenario"], "cannae-envelopment-v1")
        self.assertNotIn("victory.edition", OLD.provenance)

    def test_the_old_edition_entry_builds_the_d4e3ac7_opening(self):
        self.assertEqual(sha(build_state(OLD)), D4E3AC7_OPENING)

    def test_an_unknown_edition_and_the_field_on_another_kind_are_refused(self):
        with self.assertRaisesRegex(ValueError, "encircle edition must be one of cannae-d38"):
            validate(replace(ENTRY, victory=replace(ENTRY.victory, edition="cannae-d99")))
        from battle.scenario_gergovia import GERGOVIA_RECALL as G

        with self.assertRaisesRegex(ValueError, "use encircle"):
            validate(replace(G, victory=replace(G.victory, edition=D38)))


class Q2WallTests(unittest.TestCase):
    """D38 Q2: a routed, non-firing (INEFFECTIVE) unit no longer counts as a wall."""

    def enclosed(self, s):
        victory.score(s)
        return s["victory"]["record"][-1][1]

    def test_q2_a_routed_defender_is_no_longer_a_wall(self):
        ring = [u["id"] for u in ringed(ENTRY)["units"] if u["side"] == "carthaginian"][:1]  # One ring unit.
        self.assertEqual(self.enclosed(ringed(ENTRY)), 1)  # A whole ring encloses L1.
        self.assertEqual(self.enclosed(ringed(ENTRY, routed=ring)), 0)  # The routed unit's hex is a gap.
        self.assertEqual(self.enclosed(ringed(OLD, routed=ring)), 1)  # The old edition: still a wall.

    def test_q2_headquarters_do_not_count_a_contact_reported_routed_as_a_wall(self):
        def known(entry, routed):
            s = ringed(entry)
            ring = [u for u in s["units"] if u["side"] == "carthaginian"][:6]
            s["friendly_reports"]["roman"]["L1"]["pos"] = [5, 5]
            s["contacts"]["roman"] = {u["id"]: {"id": u["id"], "pos": u["pos"], "observed_turn": 0,
                                                **({"routed": True} if u is ring[0] and routed else {})}
                                      for u in ring}
            victory.score(s)
            return s["victory"]["known_closed_turn"]["roman"]

        self.assertEqual(known(ENTRY, routed=False), 0)
        self.assertIsNone(known(ENTRY, routed=True))
        self.assertEqual(known(OLD, routed=True), 0)


if __name__ == "__main__":
    unittest.main()
