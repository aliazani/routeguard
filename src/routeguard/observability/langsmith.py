import os

from routeguard.config import Settings


def configure_langsmith(settings: Settings) -> None:
    os.environ["LANGSMITH_TRACING"] = str(settings.langsmith_tracing).lower()

    os.environ["LANGSMITH_PROJECT"] = settings.langsmith_project

    if settings.langsmith_api_key is not None:
        os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key.get_secret_value()
