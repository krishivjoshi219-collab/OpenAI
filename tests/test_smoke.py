from config.settings import Settings


def test_settings_support_sqlite() -> None:
    settings = Settings(database_url="sqlite:///./test.db")

    assert settings.database_url.startswith("sqlite")

