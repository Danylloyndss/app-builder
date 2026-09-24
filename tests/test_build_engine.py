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

    def test_generic_feature_artifacts_are_generated(self) -> None:
        mission = "Create a mobile expense tracker with form, dashboard, calculator and history"
        with tempfile.TemporaryDirectory() as temp_dir:
            engine = BuildEngine(Path(temp_dir))
            engine.implement(mission)
            root = Path(temp_dir)
            for name in ("capabilities.json", "form-schema.json", "dashboard.json", "mobile.json", "calculator.json", "list.json"):
                self.assertTrue((root / ".app-builder" / name).exists() if name == "capabilities.json" else (root / name).exists())
            caps = json.loads((root / ".app-builder" / "capabilities.json").read_text())
            self.assertEqual(caps["generated_by"], "App Builder V1")
            self.assertIn("dashboard", caps["features"])

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

            self.assertIn("Client", schema["entities"])
            self.assertIn("name", schema["entity_fields"]["Client"])
            self.assertEqual(manifest["schema"], ".app-builder/backend_schema.json")
            self.assertEqual(contract["resources"]["records"]["fields"], schema["fields"])
            self.assertEqual(contract["primary_entity"], schema["entity"])
            self.assertIn("business_rules", contract)
            self.assertIn(schema["entity"], [item["entity"] for item in contract["resources"].values()])
            py_compile.compile(str(Path(temp_dir) / "backend.py"), doraise=True)
            py_compile.compile(str(Path(temp_dir) / "tests" / "test_backend_integration.py"), doraise=True)
            integration = subprocess.run(
                [sys.executable, str(Path(temp_dir) / "tests" / "test_backend_integration.py")],
                cwd=temp_dir, capture_output=True, text=True, timeout=10,
            )
            self.assertEqual(integration.returncode, 0, integration.stderr or integration.stdout)
            backend = (Path(temp_dir) / "backend.py").read_text(encoding="utf-8")
            self.assertIn("SCHEMA", backend)
            self.assertIn("Client", backend)
            self.assertIn("/api/", backend)
            self.assertIn("idx_entity_records_entity", backend)
            self.assertEqual(contract["version"], 3)
            self.assertEqual(contract["primary_resource"], "client")
            self.assertEqual(contract["resources"]["client"]["GET"], "/api/client")
            self.assertEqual(contract["resources"]["client"]["POST"], "/api/client")
            self.assertEqual(contract["compatibility"]["records"], "/api/records")
            self.assertEqual(contract["resources"]["client"]["field_definitions"][0]["name"], "id")
            self.assertEqual(contract["resources"]["client"]["field_definitions"][1]["type"], "text")
            self.assertTrue(any(item["name"] == "name" and item["required"] for item in contract["resources"]["client"]["field_definitions"]))


if __name__ == "__main__":
    unittest.main()
