# -*- coding: utf-8 -*-
# gridforge/configLoader.py
"""
Loads GridForge Command Cloud runtime configuration from environment values.

The loader keeps Phase 0 configuration small and explicit while preserving a
single boundary for later AI, auth, persistence, deployment, and notification
settings.

Author: @seanl
Version: 0001
Creation Date: 10/07/2026
Last Updated: 10/07/2026
"""

from __future__ import annotations

# 1) Standard library imports (alphabetized)
from dataclasses import dataclass
import os
from pathlib import Path
from typing import Any, Mapping

# 2) Third-party imports (alphabetized)

# 3) Application-specific imports (alphabetized)


@dataclass(frozen=True)
class AppConfig:
    """
    Stores normalized application configuration values.

    Args:
        app_env: Human-readable environment name.
        secret_key: Flask session secret key.
        persistence_backend: Repository backend name.
        sqlite_database_path: SQLite database path for later persistence.
        openai_api_key: OpenAI API key when configured.
        openai_model: Default AI model for customer-facing blueprint generation.
        developer_plan_model: Default AI model for private developer-plan generation.
        testing: Whether Flask should run in testing mode.
    """

    app_env: str
    secret_key: str
    persistence_backend: str
    sqlite_database_path: str | None
    openai_api_key: str | None
    openai_model: str
    developer_plan_model: str
    testing: bool = False

    def toFlaskConfig(self) -> dict[str, Any]:
        """
        Converts this config object into Flask config keys.

        Returns:
            A dictionary suitable for Flask app config updates.
        """
        return {
            "APP_ENV": self.app_env,
            "DEVELOPER_PLAN_MODEL": self.developer_plan_model,
            "OPENAI_API_KEY": self.openai_api_key,
            "OPENAI_MODEL": self.openai_model,
            "PERSISTENCE_BACKEND": self.persistence_backend,
            "SECRET_KEY": self.secret_key,
            "SQLITE_DATABASE_PATH": self.sqlite_database_path,
            "TESTING": self.testing,
        }


def coerceBool(value: Any) -> bool:
    """
    Converts common environment-style values into booleans.

    Args:
        value: Raw value from an environment variable or test override.

    Returns:
        True for enabled boolean-like values; otherwise False.
    """
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def readDotenvValues(dotenv_path: str | os.PathLike[str] = ".env") -> dict[str, str]:
    """
    Reads local dotenv key/value pairs without mutating process environment.

    Args:
        dotenv_path: Dotenv file path to read.

    Returns:
        Parsed dotenv values, or an empty dictionary when the file is missing.
    """
    path = Path(dotenv_path)
    if not path.is_file():
        return {}
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        parsed = parseDotenvLine(raw_line)
        if parsed is not None:
            key, value = parsed
            values[key] = value
    return values


def parseDotenvLine(raw_line: str) -> tuple[str, str] | None:
    """
    Parses one dotenv assignment line.

    Args:
        raw_line: Raw dotenv line.

    Returns:
        Parsed key and value, or None for blank/comment/invalid lines.
    """
    stripped_line = raw_line.strip()
    if not stripped_line or stripped_line.startswith("#"):
        return None
    if stripped_line.startswith("export "):
        stripped_line = stripped_line[len("export ") :].strip()
    if "=" not in stripped_line:
        return None
    key, raw_value = stripped_line.split("=", 1)
    key = key.strip()
    if not key or any(character.isspace() for character in key):
        return None
    return key, stripDotenvValue(raw_value)


def stripDotenvValue(raw_value: str) -> str:
    """
    Trims a dotenv value and removes matching surrounding quotes.

    Args:
        raw_value: Raw value text.

    Returns:
        Normalized dotenv value.
    """
    value = raw_value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def buildConfigEnvironment(
    environ: Mapping[str, str] | None,
    overrides: Mapping[str, Any] | None,
) -> Mapping[str, str]:
    """
    Builds the environment mapping used by configuration loading.

    Args:
        environ: Explicit environment mapping, primarily for tests.
        overrides: Optional Flask-style overrides.

    Returns:
        Environment values with local dotenv defaults applied when appropriate.
    """
    if environ is not None:
        return environ
    if disablesDotenvLoading(overrides):
        return os.environ
    dotenv_values = readDotenvValues()
    if not dotenv_values:
        return os.environ
    return {**dotenv_values, **os.environ}


def disablesDotenvLoading(overrides: Mapping[str, Any] | None) -> bool:
    """
    Checks whether explicit test overrides should isolate config from local dotenv.

    Args:
        overrides: Optional Flask-style overrides.

    Returns:
        True when dotenv loading should be skipped.
    """
    if not overrides:
        return False
    for key, value in overrides.items():
        if key.upper() == "TESTING" and coerceBool(value):
            return True
    return False


def optionalEnvValue(value: str | None) -> str | None:
    """
    Normalizes an optional environment string.

    Args:
        value: Raw environment value.

    Returns:
        Stripped value, or None when blank or missing.
    """
    if value is None:
        return None
    stripped_value = value.strip()
    return stripped_value or None


def loadConfig(
    environ: Mapping[str, str] | None = None,
    overrides: Mapping[str, Any] | None = None,
) -> AppConfig:
    """
    Loads normalized application configuration.

    Args:
        environ: Optional environment mapping for tests.
        overrides: Optional Flask-style config overrides.

    Returns:
        Normalized AppConfig.
    """
    env = buildConfigEnvironment(environ, overrides)
    config = AppConfig(
        app_env=str(env.get("APP_ENV", "local")).strip() or "local",
        secret_key=str(env.get("FLASK_SECRET_KEY", "gridforge-dev-secret")),
        persistence_backend=str(env.get("PERSISTENCE_BACKEND", "memory")).strip().lower()
        or "memory",
        sqlite_database_path=optionalEnvValue(env.get("SQLITE_DATABASE_PATH")),
        openai_api_key=optionalEnvValue(env.get("OPENAI_API_KEY")),
        openai_model=str(env.get("OPENAI_MODEL", "gpt-4o-mini")).strip() or "gpt-4o-mini",
        developer_plan_model=str(
            env.get("DEVELOPER_PLAN_MODEL", env.get("OPENAI_MODEL", "gpt-4o-mini"))
        ).strip()
        or "gpt-4o-mini",
        testing=coerceBool(env.get("TESTING", False)),
    )
    if overrides:
        return applyOverrides(config, overrides)
    return config


def applyOverrides(config: AppConfig, overrides: Mapping[str, Any]) -> AppConfig:
    """
    Applies Flask-style overrides to a normalized config object.

    Args:
        config: Base configuration.
        overrides: Explicit override mapping.

    Returns:
        AppConfig with supported overrides applied.
    """
    return AppConfig(
        app_env=str(overrides.get("APP_ENV", config.app_env)),
        secret_key=str(overrides.get("SECRET_KEY", config.secret_key)),
        persistence_backend=str(overrides.get("PERSISTENCE_BACKEND", config.persistence_backend)),
        sqlite_database_path=optionalEnvValue(
            str(overrides["SQLITE_DATABASE_PATH"])
            if "SQLITE_DATABASE_PATH" in overrides
            else config.sqlite_database_path
        ),
        openai_api_key=optionalEnvValue(
            str(overrides["OPENAI_API_KEY"])
            if "OPENAI_API_KEY" in overrides
            else config.openai_api_key
        ),
        openai_model=str(overrides.get("OPENAI_MODEL", config.openai_model)),
        developer_plan_model=str(
            overrides.get("DEVELOPER_PLAN_MODEL", config.developer_plan_model)
        ),
        testing=coerceBool(overrides.get("TESTING", config.testing)),
    )
