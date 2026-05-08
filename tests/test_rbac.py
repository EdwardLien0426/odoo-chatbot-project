import importlib.util
import sys
import unittest


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_BASE = "/home/pohsu/odoo18/my_addons/website_llm_chat"
rbac = _load(f"{_BASE}/rbac.py", "rbac")
rc = _load(f"{_BASE}/rocketride_client.py", "rocketride_client")


class TestGetAllowedFields(unittest.TestCase):
    def test_visitor_excludes_work_email(self):
        fields = rbac.get_allowed_fields("visitor")
        self.assertIn("name", fields)
        self.assertIn("department", fields)
        self.assertIn("job_title", fields)
        self.assertNotIn("work_email", fields)

    def test_staff_includes_work_email(self):
        self.assertIn("work_email", rbac.get_allowed_fields("staff"))

    def test_hr_manager_includes_work_email(self):
        self.assertIn("work_email", rbac.get_allowed_fields("hr_manager"))

    def test_unknown_role_behaves_as_visitor(self):
        self.assertNotIn("work_email", rbac.get_allowed_fields("unknown_role"))


class TestTagMessage(unittest.TestCase):
    def test_appends_system_role_tag(self):
        result = rc.tag_message("who is John?", "visitor")
        self.assertEqual(result, "who is John?\n[SYSTEM_ROLE:visitor]")

    def test_hr_manager_tag(self):
        result = rc.tag_message("find Alice", "hr_manager")
        self.assertEqual(result, "find Alice\n[SYSTEM_ROLE:hr_manager]")

    def test_staff_tag(self):
        result = rc.tag_message("list engineers", "staff")
        self.assertEqual(result, "list engineers\n[SYSTEM_ROLE:staff]")


if __name__ == "__main__":
    unittest.main()
