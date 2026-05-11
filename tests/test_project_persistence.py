"""Tests for project JSON persistence: schema version, migration, atomic save."""

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from app.domain.project import SCHEMA_VERSION
from app.services.project_service import ProjectService


def _minimal_project_payload(*, schema_version: int | None = None) -> dict:
    """Smallest payload that passes ``Project.from_dict`` and ``validate_project``."""
    data = {
        "project_id": "p1",
        "title": "Test",
        "author_source_note": "",
        "genre": "",
        "language": "vi",
        "default_narration_style": "mysterious",
        "default_art_style": "dark fantasy webtoon",
        "retelling_density": "full",
        "source_chapters": [],
        "review_episodes": [],
        "characters": [],
        "locations": [],
        "style_presets": [],
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00",
    }
    if schema_version is not None:
        data["schema_version"] = schema_version
    return data


class ProjectSchemaVersionTests(unittest.TestCase):
    def test_save_writes_current_schema_version(self) -> None:
        service = ProjectService()
        project = service.create_project("T", project_id="p1")

        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "project.json"
            service.save_project(project, path)
            data = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(data["schema_version"], SCHEMA_VERSION)
        self.assertEqual(list(data.keys())[0], "schema_version")

    def test_load_legacy_v1_payload_without_schema_version(self) -> None:
        """A file written before P2.1 has no schema_version. Loader must migrate."""
        service = ProjectService()
        payload = _minimal_project_payload()
        self.assertNotIn("schema_version", payload)

        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "legacy.json"
            path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            project = service.load_project(path)

        self.assertEqual(project.schema_version, SCHEMA_VERSION)

    def test_load_legacy_then_save_stamps_current_version(self) -> None:
        service = ProjectService()
        payload = _minimal_project_payload()

        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "legacy.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            project = service.load_project(path)
            service.save_project(project, path)
            roundtripped = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(roundtripped["schema_version"], SCHEMA_VERSION)

    def test_load_rejects_future_schema_version(self) -> None:
        service = ProjectService()
        payload = _minimal_project_payload(schema_version=SCHEMA_VERSION + 1)

        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "future.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(ValueError) as ctx:
                service.load_project(path)

        self.assertIn("schema_version", str(ctx.exception))
        self.assertIn(str(SCHEMA_VERSION + 1), str(ctx.exception))


class ProjectAtomicSaveTests(unittest.TestCase):
    def test_save_uses_tmp_file_then_replace(self) -> None:
        """save_project must write via a sibling .tmp file and os.replace, not direct write_text."""
        service = ProjectService()
        project = service.create_project("Atomic", project_id="p1")

        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "project.json"
            with patch("app.services.project_service.os.replace") as mock_replace:
                service.save_project(project, path)
                self.assertEqual(mock_replace.call_count, 1)
                args, _ = mock_replace.call_args
                tmp_arg, dest_arg = args
                self.assertEqual(Path(tmp_arg), path.with_suffix(".json.tmp"))
                self.assertEqual(Path(dest_arg), path)
                # tmp file must have been written before replace
                self.assertTrue(Path(tmp_arg).exists())

    def test_save_does_not_corrupt_existing_file_on_serialize_failure(self) -> None:
        """If serialization explodes mid-save, the original file must still be readable."""
        service = ProjectService()
        project = service.create_project("Original", project_id="p1")

        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "project.json"
            service.save_project(project, path)
            before = path.read_text(encoding="utf-8")

            # Simulate a failure DURING the atomic write (tmp written, replace
            # fails) — the destination file must remain intact.
            with patch(
                "app.services.project_service.os.replace",
                side_effect=OSError("simulated rename failure"),
            ):
                with self.assertRaises(OSError):
                    service.save_project(project, path)

            after = path.read_text(encoding="utf-8")
            self.assertEqual(before, after)
            # Clean up stray tmp file (real failure scenarios may leak one).
            tmp = path.with_suffix(".json.tmp")
            if tmp.exists():
                tmp.unlink()

    def test_save_creates_parent_dirs(self) -> None:
        service = ProjectService()
        project = service.create_project("T", project_id="p1")

        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "nested" / "deeper" / "project.json"
            service.save_project(project, path)
            self.assertTrue(path.exists())

    def test_save_then_load_roundtrip_via_atomic_write(self) -> None:
        service = ProjectService()
        project = service.create_project("Roundtrip", project_id="p1", genre="dark")

        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "project.json"
            service.save_project(project, path)
            loaded = service.load_project(path)

        self.assertEqual(loaded.project_id, "p1")
        self.assertEqual(loaded.title, "Roundtrip")
        self.assertEqual(loaded.genre, "dark")
        self.assertEqual(loaded.schema_version, SCHEMA_VERSION)


if __name__ == "__main__":
    unittest.main()
