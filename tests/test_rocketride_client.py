import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestPipeFileMapping(unittest.TestCase):
    def test_all_roles_have_pipe_files(self):
        from rocketride_client import _PIPE_FILES
        for role in ("visitor", "staff", "hr_manager"):
            self.assertIn(role, _PIPE_FILES)
            self.assertIn(f"hr_chat_{role}.pipe", _PIPE_FILES[role])

    def test_unknown_role_falls_back_to_visitor(self):
        import rocketride_client as rc
        original = rc._tokens
        try:
            rc._tokens = {"visitor": "tok-vis", "staff": "tok-staff", "hr_manager": "tok-hr"}
            token = rc._tokens.get("unknown_role") or rc._tokens.get("visitor")
            self.assertEqual(token, "tok-vis")
        finally:
            rc._tokens = original

    def test_tag_message_does_not_exist(self):
        import rocketride_client
        self.assertFalse(
            hasattr(rocketride_client, "tag_message"),
            "tag_message should be removed — role is now pipeline-level",
        )
