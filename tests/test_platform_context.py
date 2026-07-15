from pathlib import Path
import importlib.util
import os
import sys
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "generate_platform_context.py"

spec = importlib.util.spec_from_file_location("generate_platform_context", SCRIPT)
platform_context = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules["generate_platform_context"] = platform_context
spec.loader.exec_module(platform_context)


class PlatformContextTests(unittest.TestCase):
    def test_bitbucket_pipelines_context_uses_repository_full_name(self):
        env = {
            "BITBUCKET_REPO_FULL_NAME": "workspace/example-service",
            "BITBUCKET_BRANCH": "main",
            "BITBUCKET_COMMIT": "abc123",
            "BITBUCKET_PIPELINE_UUID": "{pipeline-uuid}",
            "BITBUCKET_BUILD_NUMBER": "42",
            "BITBUCKET_PIPELINE_URL": "https://bitbucket.example/pipelines/42",
        }

        with patch.dict(os.environ, env, clear=True):
            context = platform_context.context_for("bitbucket-pipelines")

        self.assertEqual(context["source"], "bitbucket-pipelines")
        self.assertEqual(context["repository_id"], "workspace/example-service")
        self.assertEqual(context["branch"], "main")
        self.assertEqual(context["commit_id"], "abc123")
        self.assertEqual(context["pipeline_run_id"], "42")
        self.assertEqual(context["event"], "branch_build")

    def test_bitbucket_pipelines_context_marks_pull_requests(self):
        env = {
            "BITBUCKET_WORKSPACE": "workspace",
            "BITBUCKET_REPO_SLUG": "example-service",
            "BITBUCKET_PR_ID": "17",
            "BITBUCKET_PR_DESTINATION_BRANCH": "main",
            "BITBUCKET_COMMIT": "def456",
            "BITBUCKET_BUILD_NUMBER": "43",
        }

        with patch.dict(os.environ, env, clear=True):
            context = platform_context.context_for("bitbucket-pipelines")

        self.assertEqual(context["repository_id"], "workspace/example-service")
        self.assertEqual(context["branch"], "main")
        self.assertEqual(context["event"], "pull_request")
        self.assertEqual(context["pull_request_id"], "17")
        self.assertEqual(context["pull_request_target"], "main")

    def test_bamboo_context_uses_bamboo_plan_repository_variables(self):
        env = {
            "bamboo_planRepository_repositoryUrl": "ssh://git@bitbucket.example/scm/PROJ/example-service.git",
            "bamboo_planRepository_branchName": "main",
            "bamboo_planRepository_revision": "abc123",
            "bamboo_planName": "PROJ-DSO",
            "bamboo_buildResultKey": "PROJ-DSO-42",
            "bamboo_resultsUrl": "https://bamboo.example/browse/PROJ-DSO-42",
            "bamboo_buildTriggerReason": "repository trigger",
        }

        with patch.dict(os.environ, env, clear=True):
            context = platform_context.context_for("bamboo")

        self.assertEqual(context["source"], "bamboo")
        self.assertEqual(context["repository_id"], "ssh://git@bitbucket.example/scm/PROJ/example-service.git")
        self.assertEqual(context["branch"], "main")
        self.assertEqual(context["commit_id"], "abc123")
        self.assertEqual(context["pipeline_id"], "PROJ-DSO")
        self.assertEqual(context["pipeline_run_id"], "PROJ-DSO-42")
        self.assertEqual(context["pipeline_url"], "https://bamboo.example/browse/PROJ-DSO-42")
        self.assertEqual(context["event"], "repository trigger")
