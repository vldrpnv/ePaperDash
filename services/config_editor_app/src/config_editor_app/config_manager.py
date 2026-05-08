import tomlkit
from pathlib import Path
import typing


class ConfigManager:
    def __init__(self, filepath: Path | str):
        self.filepath = Path(filepath)
        self.doc = tomlkit.parse(self.filepath.read_text())

    def get(self, section: str, key: str) -> typing.Any:
        return self.doc.get(section, {}).get(key)

    def update(self, section: str, key: str, value: typing.Any):
        if section not in self.doc:
            self.doc[section] = tomlkit.table()
        target_section = self.doc.get(section)
        if isinstance(target_section, typing.Dict):
            target_section[key] = value

    def get_list(self, list_name: str) -> list[dict]:
        result = self.doc.get(list_name, [])
        if isinstance(result, list):
            return result
        return []

    def append_list(self, list_name: str, item: dict):
        if list_name not in self.doc:
            self.doc[list_name] = tomlkit.aot()

        table = tomlkit.table()
        for k, v in item.items():
            table[k] = v
        target_list = self.doc.get(list_name)
        if hasattr(target_list, "append"):
            target_list.append(table)  # type: ignore

    def save(self):
        self.filepath.write_text(tomlkit.dumps(self.doc))
