from routeguard.config import Settings


def test_default_settings(monkeypatch) -> None:
    env_vars = [
        "APP_ENV",
        "LOG_LEVEL",
        "GROQ_API_KEY",
        "GROQ_MODEL",
        "GROQ_JUDGE_MODEL",
        "LANGSMITH_TRACING",
        "LANGSMITH_API_KEY",
        "LANGSMITH_PROJECT",
    ]

    for variable in env_vars:
        monkeypatch.delenv(variable, raising=False)

    settings = Settings(_env_file=None)

    assert settings.app_env == "development"
    assert settings.log_level == "INFO"
    assert settings.groq_api_key is None
    assert settings.groq_model == "qwen/qwen3-32b"
    assert settings.groq_judge_model == "openai/gpt-oss-20b"
    assert settings.langsmith_tracing is False
    assert settings.langsmith_api_key is None
    assert settings.langsmith_project == "routeguard"


def test_environment_overrides_settings(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "testing")
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    monkeypatch.setenv(
        "GROQ_JUDGE_MODEL",
        "test-judge-model",
    )

    settings = Settings(_env_file=None)

    assert settings.app_env == "testing"
    assert settings.langsmith_tracing is True
    assert settings.groq_judge_model == "test-judge-model"


def test_api_key_is_secret(monkeypatch) -> None:
    monkeypatch.setenv(
        "GROQ_API_KEY",
        "super-secret-key",
    )

    settings = Settings(_env_file=None)

    assert settings.groq_api_key is not None
    assert str(settings.groq_api_key) == "**********"
    assert settings.groq_api_key.get_secret_value() == "super-secret-key"
