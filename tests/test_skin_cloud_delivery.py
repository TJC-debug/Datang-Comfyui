from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SkinCloudDeliveryTests(unittest.TestCase):
    def test_core_source_manifest_matches_actual_files(self):
        core = ROOT / "skin_retouch_core"
        manifest = json.loads((core / "source-manifest.json").read_text(encoding="utf-8"))
        for row in manifest["files"]:
            with self.subTest(path=row["path"]):
                self.assertEqual(hashlib.sha256((core / row["path"]).read_bytes()).hexdigest(), row["sha256"])

    def test_package_entries_load_after_transfer_that_skips_empty_files(self):
        with tempfile.TemporaryDirectory(prefix="datang-cloud-upload-") as directory:
            transferred = Path(directory)
            shutil.copy2(ROOT / "skin_retouch_engine.py", transferred / "skin_retouch_engine.py")
            for original in (ROOT / "skin_retouch_core").rglob("*"):
                if not original.is_file() or "__pycache__" in original.parts or original.suffix == ".pyc":
                    continue
                if original.stat().st_size == 0:
                    continue
                copied = transferred / original.relative_to(ROOT)
                copied.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(original, copied)
            # Reproduce the reported package-entry load before importing heavy
            # Torch dependencies or requiring model weights and a GPU.
            program = "\n".join([
                "import importlib, importlib.util, pathlib, sys",
                "core = pathlib.Path('skin_retouch_core')",
                "spec = importlib.util.spec_from_file_location('_cloud_skin_core', core / '__init__.py', submodule_search_locations=[str(core)])",
                "module = importlib.util.module_from_spec(spec)",
                "sys.modules[spec.name] = module",
                "spec.loader.exec_module(module)",
                "for name in ('detection_model', 'inpainting_model', 'retinaface', 'retinaface.models'):",
                "    importlib.import_module('_cloud_skin_core.' + name)",
            ])
            env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
            result = subprocess.run([sys.executable, "-B", "-c", program], cwd=transferred, env=env, capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
