import importlib.util
import unittest
from pathlib import Path

HELPER = Path(__file__).resolve().parents[1] / "agents/skills/create-mr/mr_workflow.py"
spec = importlib.util.spec_from_file_location("mr_workflow", HELPER)
workflow = importlib.util.module_from_spec(spec)
spec.loader.exec_module(workflow)


class FixtureTransport:
    def request(self, method, path, **kwargs):
        assert method == "GET"
        responses = {
            "projects/3": {"default_branch": "trunk"},
            "projects/3/merge_requests": [],
            "projects/3/repository/branches/topic": {"commit": {"id": "abc"}},
        }
        return responses[path], {}


class WorkflowTests(unittest.TestCase):
    def test_create_draft_targets_project_branch(self):
        client = workflow.GitLab(FixtureTransport(), 3, allowed=("create",))
        draft = client.create_mr("topic", "abc", "title", "description")
        self.assertTrue(draft["dry_run"])
        self.assertEqual(draft["payload"]["target_branch"], "trunk")
        with self.assertRaises(workflow.Refused):
            client.create_mr("trunk", "abc", "title", "description")

    def test_release_requires_project_acceptance_at_release_head(self):
        check = {
            "passed": True,
            "commit": "abc",
            "scope": "suite",
            "checks": [{"command": "test", "result": "passed"}],
        }
        record = {
            "head": "abc",
            "acceptance": {
                "offline": check,
                "build": check,
                "external": dict(check, required=True, reason="integration"),
            },
        }
        workflow.release_acceptance(record)
        record["acceptance"]["external"]["commit"] = "older"
        with self.assertRaises(workflow.Refused):
            workflow.release_acceptance(record)
