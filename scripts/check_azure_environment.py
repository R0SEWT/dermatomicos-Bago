"""Validate Azure resource metadata expected by the Lumi development environment."""

from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import subprocess
import sys
from typing import Any


DEFAULT_CONFIG_PATH = pathlib.Path("config.json")


def load_config(path: pathlib.Path) -> dict[str, str]:
    if not path.exists():
        raise RuntimeError(
            f"{path} does not exist. Copy config.example.json to config.json first."
        )
    data = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "subscription_id",
        "resource_group",
        "ai_services_account",
        "ai_deployment",
        "ai_project",
        "storage_account",
        "key_vault",
    }
    missing = sorted(required - data.keys())
    if missing:
        raise RuntimeError(f"Missing config fields: {', '.join(missing)}")
    return {key: str(data[key]) for key in required}


def az_json(*args: str) -> Any:
    command = ["az", *args, "--output", "json", "--only-show-errors"]
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown Azure CLI error"
        raise RuntimeError(f"{' '.join(command)} failed: {detail}")
    return json.loads(result.stdout)


def check_environment(config: dict[str, str]) -> list[str]:
    if shutil.which("az") is None:
        raise RuntimeError("Azure CLI is not installed or is not on PATH.")

    messages: list[str] = []
    account = az_json("account", "show")
    active_subscription = account.get("id")
    if active_subscription != config["subscription_id"]:
        raise RuntimeError(
            "Active Azure subscription does not match config.json. Run: "
            f"az account set --subscription {config['subscription_id']}"
        )
    messages.append(f"subscription: {account.get('name')} ({active_subscription})")

    group = az_json("group", "show", "--name", config["resource_group"])
    messages.append(
        f"resource group: {group['name']} ({group['location']}, "
        f"{group['properties']['provisioningState']})"
    )

    ai_account = az_json(
        "cognitiveservices", "account", "show",
        "--name", config["ai_services_account"],
        "--resource-group", config["resource_group"],
    )
    messages.append(
        f"AI Services: {ai_account['name']} ({ai_account['kind']}, "
        f"{ai_account['properties']['provisioningState']})"
    )

    deployment = az_json(
        "cognitiveservices", "account", "deployment", "show",
        "--name", config["ai_services_account"],
        "--resource-group", config["resource_group"],
        "--deployment-name", config["ai_deployment"],
    )
    model = deployment["properties"]["model"]
    messages.append(
        f"model deployment: {deployment['name']} "
        f"({model['name']} {model.get('version', 'unknown')})"
    )

    project_id = (
        f"/subscriptions/{config['subscription_id']}"
        f"/resourceGroups/{config['resource_group']}"
        "/providers/Microsoft.MachineLearningServices/workspaces/"
        f"{config['ai_project']}"
    )
    project = az_json("resource", "show", "--ids", project_id)
    messages.append(
        f"Foundry project: {project['name']} ({project['kind']}, {project['location']})"
    )

    storage = az_json(
        "storage", "account", "show",
        "--name", config["storage_account"],
        "--resource-group", config["resource_group"],
    )
    if storage.get("allowBlobPublicAccess") is not False:
        raise RuntimeError("Storage account must disallow public blob access.")
    if storage.get("enableHttpsTrafficOnly") is not True:
        raise RuntimeError("Storage account must require HTTPS.")
    messages.append(f"storage: {storage['name']} (HTTPS required, public blobs disabled)")

    vault = az_json(
        "keyvault", "show",
        "--name", config["key_vault"],
        "--resource-group", config["resource_group"],
    )
    if vault["properties"].get("enableRbacAuthorization") is not True:
        raise RuntimeError("Key Vault must use Azure RBAC authorization.")
    messages.append(f"Key Vault: {vault['name']} (Azure RBAC enabled)")
    return messages


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=pathlib.Path, default=DEFAULT_CONFIG_PATH)
    args = parser.parse_args()

    try:
        messages = check_environment(load_config(args.config))
    except (OSError, ValueError, RuntimeError, KeyError) as exc:
        print(f"[error] {exc}", file=sys.stderr)
        return 1

    for message in messages:
        print(f"[ok] {message}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
