"""Deterministic replay algorithm; storage and transitions are supplied by callers."""


def verify(repository, game_id, apply):
    history = repository.history(game_id)
    state = repository.load(game_id, 0)
    for item in history[1:]:
        expected = repository.load(game_id, item["revision"])
        state = apply(state, expected["last_action"])
        if state != expected:
            raise ValueError(f"Replay diverged at revision {item['revision']}")
    return {"revisions": len(history), "turns": state["turn"], "status": "identical"}


def verify_recorded(repository, game_id, apply, inputs):
    """Why: a batch game (``batch_store.BatchStore``) keeps full snapshots only
    at keyframes, so replay cannot compare every stored snapshot.
    What: re-runs ``inputs`` (``repository.inputs``) from revision 0, checks
    each replayed state's digest (``repository.digest``) against the recorded
    sha256, each keyframe against its stored snapshot, and the end state
    against the game's latest state. Same result shape as ``verify``.
    Test: `test_tampered_action_or_final_state_fails_verification`,
    `test_keyframes_are_kept_and_checked`."""
    state = repository.load(game_id, 0)
    for item in inputs:
        if item["revision"] > 0:
            state = apply(state, item["action"])
        if repository.digest(state) != item["sha256"]:
            raise ValueError(f"Replay diverged at revision {item['revision']}")
        if item["keyframe"] and state != repository.load(game_id, item["revision"]):
            raise ValueError(f"Replay diverged at revision {item['revision']}")
    if state != repository.load(game_id):
        raise ValueError("Replay diverged from the saved final state")
    return {"revisions": len(inputs), "turns": state["turn"], "status": "identical"}
