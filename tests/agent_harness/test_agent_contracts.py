from pathlib import Path
import re
import tomllib
import unittest

from tests.agent_harness.routing import CORE_AGENTS


ROOT = Path(__file__).resolve().parents[2]
AGENT_DIR = ROOT / ".codex" / "agents"
ROLE_DIR = ROOT / ".agents" / "roles"
ROUTING_CONTRACT = ROOT / ".agents" / "routing" / "governance-agent-routing.yaml"
SKILL_DIR = ROOT / ".agents" / "skills"
ROLE_DOC = ROOT / "docs" / "governance" / "governance-roles-and-agent-profiles.md"


def parse_skill_front_matter(content: str) -> dict[str, str]:
    if not content.startswith("---\n"):
        return {}
    _, front_matter, _ = content.split("---", 2)
    values: dict[str, str] = {}
    for line in front_matter.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        values[key.strip()] = value.strip().strip('"')
    return values


class AgentContractTests(unittest.TestCase):
    def test_role_profile_document_names_core_governance_roles(self):
        content = ROLE_DOC.read_text(encoding="utf-8")
        for agent in CORE_AGENTS:
            expected_phrases = {agent, agent.replace("-", " ")}
            with self.subTest(agent=agent):
                self.assertTrue(
                    any(phrase in content.lower() for phrase in expected_phrases),
                    msg=f"{agent} is not named in {ROLE_DOC}",
                )

    def test_custom_agent_definitions_are_complete_when_present(self):
        if not AGENT_DIR.exists():
            self.skipTest(".codex/agents is introduced in the agent-system phase")

        agents = {}
        for path in sorted(AGENT_DIR.glob("*.toml")):
            with self.subTest(path=path):
                data = tomllib.loads(path.read_text(encoding="utf-8"))
                for field in ("name", "description", "developer_instructions"):
                    self.assertIn(field, data)
                    self.assertTrue(str(data[field]).strip())
                agents[data["name"]] = path

        self.assertEqual(set(agents), CORE_AGENTS)

    def test_model_neutral_role_contracts_exist_for_core_agents(self):
        self.assertTrue(ROLE_DIR.exists(), msg=".agents/roles must contain model-neutral role contracts")

        role_files = {path.stem: path for path in ROLE_DIR.glob("*.yaml")}
        self.assertEqual(set(role_files), CORE_AGENTS)

        for agent, path in sorted(role_files.items()):
            content = path.read_text(encoding="utf-8")
            with self.subTest(agent=agent):
                self.assertIn(f"id: {agent}", content)
                self.assertIn("name:", content)
                self.assertIn("description:", content)
                self.assertIn("source_of_truth:", content)
                self.assertIn("primary_files:", content)
                self.assertIn("responsibilities:", content)
                self.assertIn("validations:", content)
                self.assertIn("output_contract:", content)

    def test_model_neutral_routing_contract_covers_core_agents(self):
        self.assertTrue(ROUTING_CONTRACT.exists(), msg=".agents/routing/governance-agent-routing.yaml is required")
        content = ROUTING_CONTRACT.read_text(encoding="utf-8")

        self.assertIn("always_select:", content)
        self.assertIn("repo-steward", content)
        for agent in CORE_AGENTS:
            with self.subTest(agent=agent):
                self.assertIn(agent, content)

    def test_skill_definitions_are_complete_when_present(self):
        if not SKILL_DIR.exists():
            self.skipTest(".agents/skills is introduced in the agent-system phase")

        skill_names = set()
        for path in sorted(SKILL_DIR.glob("*/SKILL.md")):
            with self.subTest(path=path):
                content = path.read_text(encoding="utf-8")
                front_matter = parse_skill_front_matter(content)
                self.assertIn("name", front_matter)
                self.assertIn("description", front_matter)
                self.assertRegex(content.lower(), re.compile(r"workflow|steps|procedure"))
                self.assertRegex(content.lower(), re.compile(r"output|report|validation"))
                skill_names.add(front_matter["name"])

        self.assertGreaterEqual(len(skill_names), len(CORE_AGENTS))
