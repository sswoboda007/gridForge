# -*- coding: utf-8 -*-
# tests/test_configLoader.py
"""
Tests GridForge runtime configuration loading.

The tests verify deterministic environment parsing, dotenv handling, and testing
overrides used by the Flask app factory.

Author: @seanl
Version: 0001
Creation Date: 10/07/2026
Last Updated: 10/07/2026
"""

from __future__ import annotations

# 1) Standard library imports (alphabetized)
from pathlib import Path

# 2) Third-party imports (alphabetized)

# 3) Application-specific imports (alphabetized)
from gridforge.configLoader import (
    buildConfigEnvironment,
    coerceBool,
    disablesDotenvLoading,
    loadConfig,
    optionalEnvValue,
    parseDotenvLine,
    readDotenvValues,
    stripDotenvValue,
)


def test_parseDotenvLineHandlesQuotesAndComments() -> None:
    """
    Verifies dotenv line parsing handles common local configuration shapes.

    Returns:
        None.
    """
    assert parseDotenvLine("# comment") is None
    assert parseDotenvLine("") is None
    assert parseDotenvLine("APP_ENV=local") == ("APP_ENV", "local")
    assert parseDotenvLine("export OPENAI_MODEL='gpt-4o-mini'") == (
        "OPENAI_MODEL",
        "gpt-4o-mini",
    )


def test_readDotenvValuesReadsExistingFile(tmp_path: Path) -> None:
    """
    Verifies dotenv values are read without mutating process environment.

    Args:
        tmp_path: Temporary directory fixture.

    Returns:
        None.
    """
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text("APP_ENV=test-file\nOPENAI_MODEL=demo-model\n", encoding="utf-8")

    values = readDotenvValues(dotenv_path)

    assert values == {"APP_ENV": "test-file", "OPENAI_MODEL": "demo-model"}


def test_loadConfigUsesOverridesAndTestingFlag() -> None:
    """
    Verifies explicit overrides control test configuration.

    Returns:
        None.
    """
    config = loadConfig(
        environ={"APP_ENV": "local", "OPENAI_MODEL": "base-model"},
        overrides={"APP_ENV": "test", "SECRET_KEY": "secret", "TESTING": True},
    )

    assert config.app_env == "test"
    assert config.openai_model == "base-model"
    assert config.secret_key == "secret"
    assert config.testing is True
    assert config.toFlaskConfig()["TESTING"] is True


def test_configHelpersHandleFalseAndMissingValues(tmp_path: Path) -> None:
    """
    Verifies helper functions handle false, missing, and blank values.

    Args:
        tmp_path: Temporary directory fixture.

    Returns:
        None.
    """
    assert coerceBool("false") is False
    assert coerceBool("yes") is True
    assert readDotenvValues(tmp_path / "missing.env") == {}
    assert parseDotenvLine("not-an-assignment") is None
    assert parseDotenvLine("BAD KEY=value") is None
    assert stripDotenvValue(" unquoted ") == "unquoted"
    assert optionalEnvValue(None) is None
    assert optionalEnvValue("   ") is None
    assert optionalEnvValue(" value ") == "value"


def test_buildConfigEnvironmentRespectsExplicitAndTestingInputs() -> None:
    """
    Verifies environment building isolates tests from local dotenv loading.

    Returns:
        None.
    """
    explicit_environment = {"APP_ENV": "explicit"}

    assert buildConfigEnvironment(explicit_environment, None) is explicit_environment
    assert disablesDotenvLoading(None) is False
    assert disablesDotenvLoading({"APP_ENV": "test"}) is False
    assert disablesDotenvLoading({"TESTING": True}) is True


def test_loadConfigUsesDefaultsWithoutOverrides() -> None:
    """
    Verifies default environment loading without overrides.

    Returns:
        None.
    """
    config = loadConfig(environ={})

    assert config.app_env == "local"
    assert config.secret_key == "gridforge-dev-secret"
    assert config.persistence_backend == "memory"
    assert config.sqlite_database_path is None
    assert config.openai_api_key is None
    assert config.openai_model == "gpt-4o-mini"
    assert config.developer_plan_model == "gpt-4o-mini"
    assert config.testing is False


def test_loadConfigAppliesAllSupportedOverrides() -> None:
    """
    Verifies every supported Flask-style override is applied.

    Returns:
        None.
    """
    config = loadConfig(
        environ={
            "APP_ENV": "local",
            "DEVELOPER_PLAN_MODEL": "base-developer-model",
            "FLASK_SECRET_KEY": "base-secret",
            "OPENAI_API_KEY": "base-key",
            "OPENAI_MODEL": "base-model",
            "PERSISTENCE_BACKEND": "memory",
            "SQLITE_DATABASE_PATH": "base.sqlite3",
            "TESTING": "false",
        },
        overrides={
            "APP_ENV": "override-env",
            "DEVELOPER_PLAN_MODEL": "override-developer-model",
            "OPENAI_API_KEY": "override-key",
            "OPENAI_MODEL": "override-model",
            "PERSISTENCE_BACKEND": "sqlite",
            "SECRET_KEY": "override-secret",
            "SQLITE_DATABASE_PATH": "override.sqlite3",
            "TESTING": "true",
        },
    )

    assert config.app_env == "override-env"
    assert config.developer_plan_model == "override-developer-model"
    assert config.openai_api_key == "override-key"
    assert config.openai_model == "override-model"
    assert config.persistence_backend == "sqlite"
    assert config.secret_key == "override-secret"
    assert config.sqlite_database_path == "override.sqlite3"
    assert config.testing is True
