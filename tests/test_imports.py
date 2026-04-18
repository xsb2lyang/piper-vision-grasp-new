def test_project_imports() -> None:
    import piper_app  # noqa: F401
    import pyAgxArm  # noqa: F401


def test_project_defaults() -> None:
    from piper_app.config import load_project_defaults

    defaults = load_project_defaults()
    assert defaults["robot"]["robot"] == "piper"
    assert "speed_percent" in defaults["teleop"]
