"""Registry operations of the response: promote a challenger (A7) and roll back (A8, GR-6).

Promotion keeps the replaced version under ``previous_alias``; rollback swaps the two aliases,
so a rollback can itself be undone with one more ``make rollback``.
"""

from typing import Any

import mlflow
from mlflow import MlflowClient

CHAMPION = "champion"


def register(model: Any, name: str, trusted: list[str]) -> str:
    """Log ``model`` in the active run and register it as a new version of ``name``."""
    info = mlflow.sklearn.log_model(model, name="model", skops_trusted_types=trusted)
    return str(mlflow.register_model(info.model_uri, name).version)


def alias_version(name: str, alias: str) -> str | None:
    """Version currently behind ``alias`` (None if the alias does not exist)."""
    try:
        return str(MlflowClient().get_model_version_by_alias(name, alias).version)
    except mlflow.exceptions.MlflowException:
        return None


def promote(name: str, version: str, previous_alias: str) -> dict[str, str | None]:
    """Point ``champion`` at ``version``; the replaced version goes to ``previous_alias``."""
    client, current = MlflowClient(), alias_version(name, CHAMPION)
    if current is not None:
        client.set_registered_model_alias(name, previous_alias, current)
    client.set_registered_model_alias(name, CHAMPION, version)
    return {"champion": version, previous_alias: current}


def rollback(name: str, previous_alias: str) -> dict[str, str | None]:
    """Swap ``champion`` and ``previous_alias`` (GR-6); fails if there is nothing to go back to."""
    client = MlflowClient()
    current, previous = alias_version(name, CHAMPION), alias_version(name, previous_alias)
    if previous is None:
        raise RuntimeError(f"{name}: no '{previous_alias}' version to roll back to")
    client.set_registered_model_alias(name, CHAMPION, previous)
    if current is not None:
        client.set_registered_model_alias(name, previous_alias, current)
    return {"champion": previous, previous_alias: current}
