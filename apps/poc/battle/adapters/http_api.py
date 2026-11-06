"""HTTP resource mapping. The service receives use-case names, never URLs."""

from ..services.battle import BattleService

COMMANDS = {
    "/api/new": "new",
    "/api/mode": "mode",
    "/api/orders": "orders",
    "/api/standing-orders": "standing",
    "/api/recommendations": "recommendation",
    "/api/formations": "formation",
    "/api/advance": "advance",
    "/api/chat": "chat",
}


class HttpApi:
    def __init__(self, service: BattleService):
        self.service = service

    def state(self, god=False):
        return self.service.state(god)

    def read(self, path, query):
        god = query.get("view", ["commander"])[0] == "god"
        game_id = query.get("game_id", [self.service.game_id])[0]
        if path == "/api/state":
            return self.service.state(god)
        if path == "/api/map":
            return self.service.map()
        if path == "/api/history":
            return self.service.queries.history(game_id)
        if path == "/api/replay":
            return self.service.queries.replay(
                game_id, int(query.get("revision", ["0"])[0]), god=god
            )
        if path == "/api/export":
            return self.service.queries.export(self.service.game_id)
        raise ValueError("Unknown resource.")

    def mutate(self, path, body):
        if path == "/api/clock":
            return self.service.clock_control(
                body.get("game_id"), body.get("command"), body.get("speed")
            )
        command = COMMANDS.get(path)
        if command is None:
            raise ValueError("Unknown action.")
        return self.service.execute(
            command, body, game_id=body.get("game_id"), revision=body.get("revision")
        )

    # Compatibility for original callers of server.Application; new code uses service ports.
    @property
    def gid(self):
        return self.service.game_id

    @property
    def store(self):
        return self.service.repository

    @property
    def clock(self):
        return self.service.clock
