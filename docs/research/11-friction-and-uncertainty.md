# Minimal dice, credible vagaries of war

## Direction and evidence

**User requirement:** minimize dice rolling while accounting for well-understood vagaries of war. Deterministic graph-backed resolution remains the foundation; inference remains limited to delegated decisions and declared tie-breakers.

**Design proposal:** produce uncertainty primarily through incomplete information and explicit causal conditions. Reserve stochastic mechanisms for variation that matters at the modeled scale and cannot reasonably be represented through those conditions. A small number of draws is not enough by itself: a single arbitrary draw deciding the battle would still violate the intent.

Marine Corps doctrine distinguishes friction, uncertain information and chance as related aspects of war. It describes information as potentially incomplete or contradictory and friction as arising from physical and human conditions. This supports distinguishing mechanisms; it does not provide empirical event probabilities or validate this game model. [S25](09-sources.md#s25)

“Well understood” should mean a supported causal mechanism at a stated scale. It does not mean that an exact probability or coefficient is known. Game rules provide precedents; historical and technical evidence must still justify parameters for the chosen era.

## Four sources of uncertainty

| Source | Proposed treatment | Example |
| --- | --- | --- |
| Hidden state | Explicit state with limited observation | Enemy ammunition or a blocked route is unknown to the commander |
| Causal friction | Deterministic consequence of conditions and history | Congestion delays a messenger; fatigue reduces movement capacity |
| Human choice | Delegated decision using authorized observations | A subordinate decides to preserve the unit rather than press an attack |
| Residual variation | Narrow, evidence-backed stochastic event if needed | Unrepresented component variation affects equipment failure timing |

Parameter uncertainty is separate: lack of evidence about a coefficient calls for sensitivity analysis, not an arbitrary new roll during every attack. Hidden state can be fixed by a fixture or varied across an experimental scenario set without being resampled during play. Sampling it once at setup still counts as stochastic modeling and requires the same provenance.

## Candidate mechanisms

These are proposed representations, not calibrated historical findings.

| Mechanism | Deterministic core | Possible residual uncertainty / limit |
| --- | --- | --- |
| Delayed orders | Transmission availability, travel time, terrain, congestion, interruption and queue state | Communication error only where a supported model is needed; never generic order-failure odds |
| Stale/conflicting reports | Observation time, delivery delay, source provenance and confidence | Misidentification needs evidence; do not inject random false reports for drama |
| Surprise | Occlusion, attention, observation time and unobserved movement | A separate surprise bonus should not duplicate those effects |
| Suppression and morale | Incoming threat, casualties, isolation, condition, leadership and recovery history | Avoid a morale save every turn; human-condition coefficients remain uncertain |
| Weapon/equipment problems | Ammunition, reload state, wear, operating conditions and crew availability | A fault threshold/lifetime model may be justified by reliability evidence |
| Weather, smoke and visibility | Coherent environmental state, persistence and spatial propagation | Variation must be correlated over space/time, not independently rolled per unit |
| Terrain and traffic | Passability, slope, surface condition, footprint, route capacity and congestion | Unmapped obstacles may be fixed hidden facts; no arbitrary movement penalty roll |
| Naval disruption | Wind/current, heading, sea state, damaged systems and damage-control capacity | Shared environmental causes affect multiple vessels consistently |
| Local population | Shelter availability, route blockage, exposure and movement capacity | Avoid random civilian events without a behavioral basis |

Mechanisms should have exploitable mitigations: redundant communication, rest, observation, maintenance, reserves, route choice, or restrained orders. The player should be able to reduce exposure to a risk even when its exact occurrence remains uncertain.

## Residual-event contract

Before enabling a stochastic mechanism, record:

1. The cause and evidence, applicable era/unit, confidence and parameter range.
2. Why the deterministic model omits meaningful variation and why adding the mechanism improves credibility.
3. The relevant exposure: elapsed operating time, rounds fired, sustained stress, or a distinct episode—not merely “one more tick.”
4. Its rate/threshold distribution and supporting assumptions, duration, recovery conditions and maximum plausible scope.
5. Shared causes and correlations, so weather or a failed communications link does not become unrelated rolls for every affected unit.
6. Seed/draw identity, realized value, parent causes and state transition in the authoritative event record.
7. What each commander can observe, how the event can be mitigated, and a deterministic fallback/test mode.

A candidate reliability approach samples a latent threshold once for a component or episode, accumulates relevant exposure deterministically, then transitions into a persistent fault state when the threshold is crossed. Repair or replacement creates a new episode. This is only suitable where the exposure and lifetime assumptions are defensible; some failures require other models. Reducing the number of RNG calls does not make a poor model more realistic.

Never use independent repeated rolls to approximate the same persistent fault. Avoid double counting: fog that already reduces visibility must not also cause an unexplained global combat penalty. Shared causes should link to their consequences in the graph, enabling audit and sensitivity analysis.

## Combat without routine hit rolls

For the aggregate duel, prefer deterministic fire/exposure calculations and accumulated effects. Preserve fractional numerical residuals across steps, enforce conservation, and resolve simultaneous effects together. Separate suppression from casualties. The [simulation-methods document](03-simulation-methods.md) describes the candidate accumulator and its limits.

This abstraction can become too smooth or create predictable casualty thresholds. Test those defects rather than asserting that fewer dice inherently increases realism. Detailed geometry, persistent cohort variation or narrowly supported residual dispersion may eventually be needed. Do not secretly add generic damage noise to make results look less regular.

An inference tie-breaker selects a legal decision; it is not a disguised hit roll, morale roll or winner selection. Missing rules and uncertain historical data go into the research backlog, not a model-referee prompt.

## First-duel scope

Start with fixed scenario conditions, limited observations, explicit reload/ammunition, exposure, fatigue, suppression, persistent orders and timed communication. Exercise controlled friction variants one at a time: reduced visibility, a blocked route, delayed message delivery, or a declared equipment fault. Scripted fault fixtures test consequences without claiming a historical frequency.

Only introduce live stochastic triggers after evidence and experiments show what the deterministic baseline misses. The default must remain runnable with zero random draws. Do not implement an all-era incident generator or random event-card deck.

## Validation and explanation

- Same state and recorded decisions reproduce the same effects; changing tick size must not change the number of chances for a fault.
- Disabling residual chance retains uncertainty for commanders through hidden state and delayed information.
- Compare baseline, each causal mechanism and any stochastic extension separately; measure distributions and extreme outcomes, not just average losses.
- Measure how outcomes vary with player decisions, hidden starting conditions and residual events separately. Do not prescribe an unsupported percentage of victory attributable to luck.
- Verify duration, correlation, recovery, conservation and graph causation for persistent events.
- Check mitigation behavior under controlled conditions and look for threshold exploits.
- Reports identify recorded causes while respecting fog of war. “The order arrived late because the crossing was blocked” is appropriate when evidenced; “bad luck” is not an explanation.

No numerical probabilities, failure rates or historical validation are established by this document. All proposed mechanisms remain subject to calibration and the research-only boundary.
