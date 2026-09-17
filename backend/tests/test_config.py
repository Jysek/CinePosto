"""Test delle Settings: i segreti non devono mai finire nei log di produzione.

Il token admin protegge gli endpoint di riimportazione. In sviluppo è comodo generarlo
al volo (e stamparlo, per poterlo usare); in produzione no: o c'è, o il processo non parte.
"""

from pydantic import ValidationError
import pytest

from app.config import Settings

VALID_TOKEN = "token-di-prova-lungo-abbastanza-1234567890"


def _settings(**overrides) -> Settings:
    """Costruisce Settings senza leggere il file .env (i test devono essere ermetici)."""
    return Settings(_env_file=None, **overrides)


def test_uses_the_token_from_configuration_when_present():
    settings = _settings(env="production", admin_token=VALID_TOKEN)

    assert settings.admin_token == VALID_TOKEN


def test_generates_a_random_token_in_development_when_missing(capsys):
    settings = _settings(env="development", admin_token="")

    assert len(settings.admin_token) >= 32
    assert settings.admin_token in capsys.readouterr().out


def test_replaces_the_placeholder_token_in_development():
    settings = _settings(env="development", admin_token="change-me-before-deploy")

    assert settings.admin_token != "change-me-before-deploy"
    assert len(settings.admin_token) >= 32


def test_refuses_to_start_in_production_without_a_token():
    with pytest.raises(ValidationError, match="ADMIN_TOKEN è obbligatorio"):
        _settings(env="production", admin_token="")


def test_never_prints_the_token_in_production(capsys):
    placeholder = "change-me-before-deploy"

    with pytest.raises(ValidationError):
        _settings(env="production", admin_token=placeholder)

    captured = capsys.readouterr()
    assert placeholder not in captured.out
    assert placeholder not in captured.err
