import tempfile
import unittest
import sys
from pathlib import Path


ROOT = Path(__file__).parents[2]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.local_storage import migrate_legacy_files, resolve_data_dir


class V23PersistentStorageTests(unittest.TestCase):
    def test_windows_uses_local_app_data(self):
        result = resolve_data_dir(
            "nt",
            {"LOCALAPPDATA": r"C:\\Users\\demo\\AppData\\Local"},
            Path(r"C:\\Users\\demo"),
        )
        self.assertEqual(result.name, "data")
        self.assertEqual(result.parent.name, "ProTreBotEliteX")
        self.assertIn("AppData", str(result))

    def test_explicit_data_override_always_wins(self):
        result = resolve_data_dir(
            "nt",
            {"LOCALAPPDATA": r"C:\\ignored", "PROTREBOT_DATA_DIR": r"D:\\BotData"},
            Path(r"C:\\Users\\demo"),
        )
        self.assertEqual(result, Path(r"D:\\BotData"))

    def test_non_windows_development_keeps_project_data(self):
        expected = Path("/tmp/project-data")
        result = resolve_data_dir("posix", {}, Path("/tmp/home"), expected)
        self.assertEqual(result, expected)

    def test_migration_copies_missing_files_and_never_overwrites(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            legacy = root / "legacy"
            stable = root / "stable"
            legacy.mkdir()
            stable.mkdir()
            (legacy / "owner.json").write_text("legacy-owner", encoding="utf-8")
            (legacy / "secret.dat").write_text("legacy-secret", encoding="utf-8")
            (stable / "owner.json").write_text("new-owner", encoding="utf-8")

            migrated = migrate_legacy_files(
                ("owner.json", "secret.dat"), source_dir=legacy, destination_dir=stable,
            )

            self.assertEqual(migrated, ("secret.dat",))
            self.assertEqual((stable / "owner.json").read_text(encoding="utf-8"), "new-owner")
            self.assertEqual((stable / "secret.dat").read_text(encoding="utf-8"), "legacy-secret")


if __name__ == "__main__":
    unittest.main(verbosity=2)
