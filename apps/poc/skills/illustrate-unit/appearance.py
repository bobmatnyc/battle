"""Sample a dated profile's cosmetic mix without consulting simulation state."""
import hashlib
import random


def appearance_brief(choices, *, cosmetic_seed, condition_cues, dress_visible):
    """Inputs are approved display phrases. The seed stays local.

    Each choice pairs a phrase with a relative weight; equal weights represent
    an artistic assumption. Six anonymous visual samples describe the mix.
    Neither their count nor their weights represent troop strength.
    """
    if not dress_visible:
        return "Indistinct movement; clothing and condition cannot be resolved."
    if not choices:
        return "Clothing details are unresolved."
    phrases, weights = zip(*choices)
    if any(weight <= 0 for weight in weights):
        raise ValueError("Appearance weights must be positive.")
    seed = hashlib.sha256(cosmetic_seed.encode("utf-8")).digest()
    rng = random.Random(seed)
    samples = rng.choices(phrases, weights=weights, k=6)
    mixture = sorted(set(samples), key=lambda phrase: (-samples.count(phrase), phrase))
    description = "Representative dress, in order of prominence: " + ", ".join(mixture) + "."
    if condition_cues:
        description += " " + " ".join(condition_cues)
    return description
