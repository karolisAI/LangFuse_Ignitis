import pytest
from pydantic import ValidationError

from app.settings import Settings


def test_environment_overrides_dotenv_and_secrets_are_hidden(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "LANGFUSE_PUBLIC_KEY=example-public\n"
        "LANGFUSE_SECRET_KEY=example-secret\n"
        "SPECIALIST_URL=http://from-file:8001\n"
        "LANGFUSE_TRACING_ENABLED=false\n"
        "SPECIALIST_TIMEOUT_SECONDS=2.5\n"
        "GOOGLE_API_KEY=example-google-secret\n"
        "UNRELATED_SETTING=ignored\n",
        encoding="utf-8",
    )
    # conftest provides fake Langfuse credentials; let this test read its own file.
    for name in ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_BASE_URL"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("SPECIALIST_URL", "http://from-environment:9001")
    settings = Settings(_env_file=env_file)

    assert str(settings.specialist_url) == "http://from-environment:9001/"
    assert settings.langfuse_tracing_enabled is False
    assert settings.specialist_timeout_seconds == 2.5
    assert settings.langfuse_secret_key.get_secret_value() == "example-secret"
    assert "example-secret" not in repr(settings)
    assert "example-google-secret" not in repr(settings)


@pytest.mark.parametrize("field,value", [
    ("specialist_url", "not-a-url"),
    ("langfuse_base_url", "ftp://localhost"),
    ("specialist_timeout_seconds", 0),
    ("langfuse_tracing_enabled", "not-a-boolean"),
])
def test_invalid_settings_are_rejected(field, value):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **{field: value})


def test_missing_credentials_fail_at_startup(monkeypatch):
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY")
    monkeypatch.delenv("LANGFUSE_SECRET_KEY")
    with pytest.raises(ValidationError) as exc:
        Settings(_env_file=None)
    assert {error["loc"][0] for error in exc.value.errors()} == {
        "langfuse_public_key", "langfuse_secret_key",
    }


def test_empty_optional_settings_keep_defaults(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("GOOGLE_API_KEY=\nADK_MODEL=\nOTEL_SERVICE_NAME=\n", encoding="utf-8")
    settings = Settings(_env_file=env_file)
    assert settings.google_api_key.get_secret_value() == ""
    assert settings.adk_model == "gemini-2.5-flash"
    assert settings.otel_service_name is None
