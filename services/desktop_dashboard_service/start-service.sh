python3 -m venv .venv
. .venv/bin/activate
pip install -e .[dev]
epaper-dashboard-service --config examples/dashboard_config.toml

