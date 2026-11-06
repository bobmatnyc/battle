# Cannae • double envelopment at army scale

**Second Punic War, Apulia, Italy, 216 BCE.** Add this experiment alongside the six small-action cases, including Gergovia. At Cannae the player delegates to a center, wings and cavalry commands. Each controls aggregate formations. The test asks whether local decisions can produce an encirclement, whether the Roman player can prevent it, and what each headquarters actually knows.

## What the accounts support

Polybius describes an advanced center of Iberian and Celtic infantry giving ground under Roman pressure. African infantry on either side turned against the Roman flanks. Victorious cavalry subsequently attacked the rear. Livy also narrates the Roman advance and the flank attacks. The Roman army suffered a decisive defeat. These literary accounts establish an ordering for comparison; neither supplies a synchronized staff log. Map orientation, exact strength, timings, losses and the degree of deliberate control over the center’s recoil remain uncertain. [Polybius, Histories III.113–117](https://penelope.uchicago.edu/thayer/e/roman/texts/polybius/3%2A.html#113) · [Livy, XXII.45–50](https://facultystaff.richmond.edu/~wstevens/romanhistory/history222texts/livycannae.pdf)

## Two-sided orders to test

- **Carthaginian command.** Advance the center, maintain cohesion while yielding under pressure, and retain the African infantry on its shoulders. Let the wing commanders turn inward when the Romans have passed them. Cavalry contests the enemy horse, then seeks the rear if the situation permits. Encode intent and local triggers separately; a script must never declare a pocket closed.
- **Roman command.** Concentrate infantry against the projecting center and protect the flanks with cavalry. React to threats observed by each local command. The historical baseline can continue pressing the center. In a second run reserve a formation and a retreat lane. Keep the Carthaginian plan out of the Roman controller’s briefing.

## Evaluation and falsification

Use a larger frontage and an explicit army-to-sector-to-formation hierarchy. Durations and distances need scale-appropriate calibration. At every checkpoint record sector frontage, facing, cohesion, capacity for passage, local signal or messenger receipt, cavalry disengagement, escape-lane throughput and the forces actually enclosed. Separate the moment a route closes on the ground from the moment it becomes known at headquarters. Treat groups outside the pocket as separate. Record escape, surrender and losses independently.

A successful reproduction shows a center giving ground without breaking, pressure on both Roman flanks, and mounted pressure in the rear reducing or closing withdrawal for the engaged mass. The verdict depends on movement and route capacity, not simply on which army wins. Compare time ordering and source-supported outcomes before matching disputed casualty totals. Rerun with delayed cavalry, one wing unable to turn, or a Roman reserve preserving a corridor. The model must allow a failed pincer.

## What ran

The [four executable route tests](../../apps/poc/experiments/cannae/test_escape_routes.py) use the existing hex pathfinder on synthetic flat ground. Front pressure alone leaves an escape route. Two wings plus front pressure still leave the rear open. Completing a ring blocks all three modeled exits. Removing any sector reopens a path. Run from apps/poc with `python3 -m unittest discover -s experiments/cannae -v`. All four passed. These tests validate the geometry diagnostic only. The army engagement, capacity-constrained movement, command delays and historical replay are open project milestones.

## Game-pack images

[Two illustrated moments and their sources](battle-gallery/cannae.md) accompany this case. The [local pack manifest](../../apps/poc/experiments/cannae/art/manifest.json) includes the two asset paths and a portable copy of the research.
