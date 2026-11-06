# Temporary units, aggregate training and remixing

## Confirmed direction

The user clarified that units are not long-lived, commanders can choose to train or remix them, and this is not an individual combat game. The lifecycle and accounting rules below are proposals within that direction, not historical claims or implementation authorization.

A unit is a temporary organization of combat capability for an assignment. It has an operational ID, aggregate personnel/equipment state, orders and a controller while active. It does not need a permanent personality, biography or experience track. No individual soldier records, inventories, skill trees or autonomous minds are required.

Short-lived does not mean silently discarding a unit at every battle boundary. It means the campaign must support replacing, dissolving and reconstituting formations without depending on their permanent identity. The exact lifecycle boundary is a scenario/command rule, not an arbitrary expiration timer.

## What carries forward

| Concept | Proposed treatment |
| --- | --- |
| Historical archetype | Reusable versioned capability/organization reference |
| Force resources | Aggregate personnel counts, proficiency categories, equipment, ammunition and condition |
| Active formation | Temporary allocation of those resources to a role, mission and commander |
| Unit controller | Context bound to the active assignment; retire or rebind at a lifecycle transition |
| Audit history | Archived formation IDs and quantity-bearing transitions for replay |

Campaign continuity resides in force resources, operational conditions and decisions. It does not require tracking the same soldier or platoon from beginning to end. Command identities establish authority; this does not imply a commander-character RPG either.

## Cohorts and training

Represent personnel in aggregate buckets where distinctions affect capability: role, relevant proficiency, equipment qualification, and condition. Avoid inventing a unique cohort for each person. A count reaching one still denotes an accounting quantity, not a named character.

Training is a commander-selected activity with a target capability, eligible cohorts, prerequisite equipment/instructors if modeled, duration, availability cost and bounded deterministic progress. Distinguish individual-skill **statistics at cohort level** from collective formation proficiency such as coordination. Training can change those aggregate statistics without simulating individual lessons or assigning personal XP.

Inference chooses among legal training plans within delegated authority. Rules compute progress and costs. A model cannot declare a unit trained merely because its explanation sounds plausible. Interrupted training retains only the progress allowed by the rule; it cannot complete again after retry/replay. Do not assume a quick exercise creates mastery or that all weapon skills transfer equally.

Training rates, prerequisites, ceilings and retention are not calibrated here. Keep skill dimensions narrow and measurable; avoid an all-purpose veterancy multiplier. Training and combat exposure are different possible inputs, not interchangeable XP rewards.

## Remixing formations

The proposed command vocabulary includes form, split, merge, redistribute and disband. A remix plan specifies source quantities, destination formations, equipment/ammunition allocation, roles, commander/controller assignment and effective time. Rules validate availability, location, compatibility, capacity and any reorganization delay before an atomic transition.

Proposed default: perform substantial reorganization between engagements or in a declared regrouping state. Any in-contact split/transfer needs separate rules for travel time, exposure, command and lost coordination; it cannot teleport troops or evade an incoming effect. This timing policy remains a design choice.

Illustrative: combine 20 trained rifle troops and 10 less-trained rifle troops into a 30-person formation. Preserve both aggregate proficiency groups initially. The second group does not inherit the first group's training instantly. Any displayed average is only a summary; specialist operation still requires the appropriate qualified count and equipment. No soldier names or IDs are necessary.

Proficiency, fatigue and wounds follow the transferred quantities. Formation cohesion is recomputed from documented continuity and integration rules, not copied at its best predecessor value. Command trust/refusal needs a similarly explicit mapping. A rename or split/merge cannot erase mutiny, replenish ammunition, reset equipment faults or convert wounded personnel into fit troops.

## Identity, orders and accounting

Each transition creates successor allocations and retires or reduces the predecessor. Archived predecessors remain available for audit but cannot receive new actionable orders. An order addressed to a retired formation is rejected or replaced through a recorded command action; it does not silently fan out to all successors.

Transfer only authorized mission and observation context to a new controller. Reorganization cannot spread hidden knowledge to every new formation or restart independent fault draws to obtain a favorable result. Preserve causal episodes and numerical residuals under declared allocation rules.

For each relevant resource/category, source-before plus explicit arrivals equals source-after plus destination allocations plus explicit expenditure/loss. Personnel cannot be simultaneously available in a force pool and assigned to a formation. Equipment and ammunition have the same single-accounting requirement. Mixed training/condition categories may remain distinct rather than being flattened into one scalar.

Ships remain physical platforms with persistent damage and inventory when supported; temporary crew assignments or flotillas do not make their hull condition disappear. This physical continuity is compatible with aggregate crew simulation and temporary military organization.

## Scope and checks

The first headless duel still uses two fixed aggregate formations. Training and remixing are later command capabilities; acknowledging them now does not initiate provisioning, recruitment, purchasing or a force-builder UI.

When built, verify conservation, stale-order rejection, controller retirement, no free readiness improvement from repeated split/merge, qualified-crew requirements, training interruption/resumption, and exact transition replay. Test that the entire system runs without a soldier-identity table or individual-agent loop.
