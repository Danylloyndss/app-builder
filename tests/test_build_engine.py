import json
import tempfile
import unittest
import py_compile
import subprocess
import sys
from pathlib import Path

from app.build_engine import BuildEngine
from app.specification import SpecificationBuilder
from app.manager import Manager


class BuildEngineTests(unittest.TestCase):
    def test_generates_real_web_project(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            memory = Manager(temp_dir).run("Create a simple expense tracker")
            self.assertEqual(memory.status, "completed")
            self.assertFalse(memory.errors)
            self.assertTrue((Path(temp_dir) / "index.html").exists())
            self.assertTrue((Path(temp_dir) / "app.js").exists())
            self.assertTrue((Path(temp_dir) / "README.md").exists())

    def test_timesheet_features_generate_real_ui(self) -> None:
        mission = "Create a mobile timesheet with forms, data storage and manager dashboard"
        with tempfile.TemporaryDirectory() as temp_dir:
            engine = BuildEngine(Path(temp_dir))
            engine.create_structure(mission)
            engine.implement_feature("forms", mission)
            engine.implement_feature("storage", mission)
            engine.implement_feature("dashboard", mission)
            engine.implement_feature("mobile", mission)
            engine.implement_feature("calculator", mission)

            html = (Path(temp_dir) / "index.html").read_text(encoding="utf-8")
            js = (Path(temp_dir) / "app.js").read_text(encoding="utf-8")
            features = json.loads((Path(temp_dir) / ".app-builder" / "features.json").read_text(encoding="utf-8"))

            self.assertIn('name="location"', html)
            self.assertIn('id="total"', html)
            self.assertIn("localStorage", js)
            self.assertIn("dashboard", features)
            self.assertIn("mobile", features)

    def test_html_escapes_mission(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            engine = BuildEngine(Path(temp_dir))
            engine.implement("<script>alert('x')</script>")
            html = (Path(temp_dir) / "index.html").read_text(encoding="utf-8")
            self.assertNotIn("<script>alert('x')</script>", html)

    def test_generic_spec_infers_domain_entities(self) -> None:
        spec = SpecificationBuilder().build("Create an expense tracker for clients with data storage")
        self.assertIn("Expense", spec.data_entities)
        self.assertIn("Client", spec.data_entities)

    def test_spec_infers_entity_fields_and_rules(self) -> None:
        spec = SpecificationBuilder().build("Create an expense tracker for clients with data storage and amounts")
        self.assertIn("Expense", spec.entity_fields)
        self.assertIn("amount", spec.entity_fields["Expense"])
        self.assertTrue(any("Expense amount" in rule for rule in spec.business_rules))
    def test_generic_storage_generates_schema_and_contract(self) -> None:
        mission = "Create a mobile client records app with a form, data storage and history"
        with tempfile.TemporaryDirectory() as temp_dir:
            engine = BuildEngine(Path(temp_dir))
            engine.implement(mission)
            engine.implement_backend(mission)

            schema = json.loads((Path(temp_dir) / ".app-builder" / "backend_schema.json").read_text(encoding="utf-8"))
            manifest = json.loads((Path(temp_dir) / ".app-builder" / "backend.json").read_text(encoding="utf-8"))
            contract = json.loads((Path(temp_dir) / "api_contract.json").read_text(encoding="utf-8"))

            self.assertIn("ApplicationRecord", schema["entities"])
            self.assertIn("date", schema["fields"])
            self.assertEqual(manifest["schema"], ".app-builder/backend_schema.json")
            self.assertEqual(contract["resources"]["records"]["fields"], schema["fields"])
            py_compile.compile(str(Path(temp_dir) / "backend.py"), doraise=True)
            py_compile.compile(str(Path(temp_dir) / "tests" / "test_backend_integration.py"), doraise=True)
            integration = subprocess.run(
                [sys.executable, str(Path(temp_dir) / "tests" / "test_backend_integration.py")],
                cwd=temp_dir, capture_output=True, text=True, timeout=10,
            )
            self.assertEqual(integration.returncode, 0, integration.stderr or integration.stdout)
            backend = (Path(temp_dir) / "backend.py").read_text(encoding="utf-8")
            self.assertIn("SCHEMA", backend)
            self.assertIn("ApplicationRecord", backend)
            self.assertIn("entity_records", backend)
            self.assertIn("idx_entity_records_entity", backend)


if __name__ == "__main__":
    unittest.main()
