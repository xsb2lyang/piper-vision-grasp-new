def test_project_imports() -> None:
    import piper_app  # noqa: F401
    import pyAgxArm  # noqa: F401


def test_cli_imports() -> None:
    import piper_app.cli.drag_monitor_gui  # noqa: F401
    import piper_app.cli.teleop_tcp_gui  # noqa: F401
    import piper_app.cli.teleop_tcp_keyboard  # noqa: F401
    import piper_app.camera.d405  # noqa: F401


def test_project_defaults() -> None:
    from piper_app.config import load_project_defaults

    defaults = load_project_defaults()
    assert defaults["robot"]["robot"] == "piper"
    assert "speed_percent" in defaults["teleop"]
    assert defaults["camera"]["enabled"] is True
    assert defaults["camera"]["serial"] == "auto"
    assert "depth_min_m" in defaults["camera"]
