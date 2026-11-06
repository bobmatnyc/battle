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
