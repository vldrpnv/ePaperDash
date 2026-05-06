from pathlib import Path
from config_editor_app.preview_generator import generate_preview


def test_generate_preview_calls_renderer(tmp_path: Path):

    config_file = tmp_path / "test_config.toml"
    svg_file = tmp_path / "test.svg"
    svg_file.write_text(
        '<svg width="100" height="100" xmlns="http://www.w3.org/2000/svg"><text id="mock_slot" x="10" y="10"></text></svg>'
    )

    config_file.write_text(f"""
[layout]
template = "{svg_file}"
width = 100
height = 100

[mqtt]
host = "127.0.0.1"
port = 1883
topic = "test"

[[panels]]
source = "mock_source"
renderer = "mock_renderer"
slot = "mock_slot"
""")

    png_bytes = generate_preview(config_file)
    assert isinstance(png_bytes, bytes)
    assert png_bytes.startswith(b"\x89PNG")
