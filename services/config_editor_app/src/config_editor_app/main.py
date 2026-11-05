from nicegui import ui
import os
from pathlib import Path
from config_editor_app.config_manager import ConfigManager
from config_editor_app.preview_generator import generate_preview
import base64

# Use DASHBOARD_CONFIG_PATH or default to desktop_dashboard_service/examples/dashboard_config.toml
DEFAULT_CONFIG = (
    Path(__file__).parent.parent.parent.parent
    / "desktop_dashboard_service"
    / "examples"
    / "dashboard_config.toml"
)
config_path = os.environ.get("DASHBOARD_CONFIG_PATH", DEFAULT_CONFIG)

try:
    manager: ConfigManager | None = ConfigManager(config_path)
except Exception:
    manager = None


def render_ui():
    if not manager:
        ui.label(f"Failed to load configuration from {config_path}").classes("text-red")
        return

    ui.page_title("Dashboard Config Editor")

    with ui.row().classes(
        "w-full justify-between items-center bg-primary text-white p-4"
    ):
        ui.label("ePaper Dashboard Editor").classes("text-2xl font-bold")
        ui.button("Save Configuration", on_click=lambda: save_and_refresh()).classes(
            "bg-secondary"
        )

    with ui.row().classes("w-full p-4 h-full"):
        # Left Panel - Forms
        with ui.column().classes("w-1/2 p-4 h-full overflow-auto"):
            with ui.tabs() as tabs:
                ui.tab("Layout & MQTT", icon="settings")
                ui.tab("Sources", icon="cloud_download")
                ui.tab("Panels/Profiles", icon="dashboard")

            with ui.tab_panels(tabs, value="Layout & MQTT").classes("w-full"):
                with ui.tab_panel("Layout & MQTT"):
                    ui.label("Layout Settings").classes("text-xl font-bold")
                    ui.input(
                        "Template SVG Path", value=manager.get("layout", "template")
                    ).on(
                        "blur",
                        lambda e: update_config("layout", "template", e.sender.value),
                    )
                    ui.number("Width", value=manager.get("layout", "width")).on(
                        "blur",
                        lambda e: update_config("layout", "width", int(e.sender.value)),
                    )
                    ui.number("Height", value=manager.get("layout", "height")).on(
                        "blur",
                        lambda e: update_config(
                            "layout", "height", int(e.sender.value)
                        ),
                    )

                    ui.label("MQTT Settings").classes("text-xl font-bold mt-4")
                    ui.input("Host", value=manager.get("mqtt", "host")).on(
                        "blur", lambda e: update_config("mqtt", "host", e.sender.value)
                    )
                    ui.number("Port", value=manager.get("mqtt", "port")).on(
                        "blur",
                        lambda e: update_config("mqtt", "port", int(e.sender.value)),
                    )
                    ui.input("Topic", value=manager.get("mqtt", "topic")).on(
                        "blur", lambda e: update_config("mqtt", "topic", e.sender.value)
                    )

                with ui.tab_panel("Sources"):
                    ui.label("Shared Data Sources").classes("text-xl font-bold")
                    ui.label("Edit directly in TOML for now if complex.")
                    for source in manager.get_list("sources"):
                        with ui.card().classes("w-full mb-2"):
                            ui.label(f"ID: {source.get('id')}")
                            ui.label(f"Plugin: {source.get('source')}")

                with ui.tab_panel("Panels/Profiles"):
                    ui.label("Legacy Panels").classes("text-xl font-bold")
                    for panel in manager.get_list("panels"):
                        with ui.card().classes("w-full mb-2"):
                            ui.label(
                                f"Slot: {panel.get('slot')} | Source: {panel.get('source')} | Renderer: {panel.get('renderer')}"
                            )

                    ui.label("Time-of-day Profiles").classes("text-xl font-bold mt-4")
                    for profile in manager.get_list("profiles"):
                        with ui.card().classes("w-full mb-2"):
                            ui.label(
                                f"Profile: {profile.get('id')} ({profile.get('start_time')})"
                            )
                            ui.label(f"Template: {profile.get('template')}")

        # Right Panel - Live Preview
        with ui.column().classes("w-1/2 p-4 flex-center"):
            ui.label("Live Preview").classes("text-xl font-bold")
            preview_img = ui.image().classes("border shadow-lg max-w-full")

            with ui.row().classes("mt-4 w-full justify-center"):
                ui.label("Upload Custom Icon").classes("font-bold self-center mr-4")
                ui.upload(on_upload=lambda e: handle_upload(e)).props(
                    "accept=image/*"
                ).classes("max-w-xs")

            def refresh_preview():
                try:
                    manager.save()
                    png_bytes = generate_preview(config_path)
                    b64 = base64.b64encode(png_bytes).decode()
                    preview_img.source = f"data:image/png;base64,{b64}"
                except Exception as e:
                    ui.notify(f"Preview error: {e}", type="negative")

            def handle_upload(e):
                upload_dir = Path(config_path).parent / "icons"
                upload_dir.mkdir(exist_ok=True)
                dest = upload_dir / e.name
                dest.write_bytes(e.content.read())
                ui.notify(f"Uploaded icon to {dest}", type="positive")

            refresh_preview()

    def update_config(section, key, value):
        manager.update(section, key, value)
        refresh_preview()

    def save_and_refresh():
        manager.save()
        refresh_preview()
        ui.notify("Configuration saved successfully", type="positive")


@ui.page("/")
def index_page():
    render_ui()


def main():
    ui.run(title="Dashboard Editor")


if __name__ in {"__main__", "__mp_main__"}:
    main()
