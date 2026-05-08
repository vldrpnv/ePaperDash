from pathlib import Path
from config_editor_app.config_manager import ConfigManager


def test_config_manager_loads_file(tmp_path: Path):
    config_file = tmp_path / "dashboard_config.toml"
    config_file.write_text("""
[layout]
template = "my_layout.svg"
width = 800
height = 480
""")

    manager = ConfigManager(config_file)
    assert manager.get("layout", "template") == "my_layout.svg"


def test_config_manager_updates_and_saves(tmp_path: Path):
    config_file = tmp_path / "dashboard_config.toml"
    config_file.write_text("""
[layout]
template = "my_layout.svg"
width = 800
height = 480
""")

    manager = ConfigManager(config_file)
    manager.update("layout", "template", "new_layout.svg")
    manager.save()

    new_content = config_file.read_text()
    assert 'template = "new_layout.svg"' in new_content


def test_config_manager_handles_sources_and_profiles(tmp_path: Path):
    config_file = tmp_path / "dashboard_config.toml"
    config_file.write_text("""
[[sources]]
id = "weather1"
source = "weather_plugin"

[[profiles]]
id = "morning"
start_time = "06:00"
""")

    manager = ConfigManager(config_file)
    sources = manager.get_list("sources")
    assert len(sources) == 1
    assert sources[0]["id"] == "weather1"

    manager.append_list("sources", {"id": "cal1", "source": "calendar_plugin"})
    manager.save()

    new_content = config_file.read_text()
    assert 'id = "cal1"' in new_content
