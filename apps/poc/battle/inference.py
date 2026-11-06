"""Compatibility facade for early POC callers.

New application code receives CommanderService and DecisionProvider explicitly.
This facade retains the old function API and request_json patch point for fixtures.
"""

from .command_policy import SYSTEM, fallback_orders, observation_for, validated


def settings():
    from .config import Settings

    config = Settings.load()
    return {"OPENROUTER_API_KEY": config.api_key, "OPENROUTER_MODEL": config.model}


def configured():
    return bool(settings()["OPENROUTER_API_KEY"])


def request_json(system, payload):
    from .adapters.openrouter import OpenRouterProvider
    from .config import Settings

    return OpenRouterProvider(Settings.load()).request(system, payload)


def _commander():
    from .adapters.rules import RulesSimulation
    from .services.commander import CommanderService

    class LegacyRequestProvider:
        # Constructing this shim performs no environment, filesystem or network IO.
        available = True
        model = ""

        def request(self, instruction, payload):
            return request_json(instruction, payload)

    return CommanderService(RulesSimulation(), LegacyRequestProvider())


def decide(s, side="confederate", mode="openrouter"):
    return _commander().decide(s, side, mode)


def chat(s, text, mode="openrouter"):
    return _commander().chat(s, text, mode)
