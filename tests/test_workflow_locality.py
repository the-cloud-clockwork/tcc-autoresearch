import re
from pathlib import Path


def test_workflows_do_not_call_private_org_repository():
    workflows = Path(__file__).resolve().parents[1] / ".github" / "workflows"
    files = sorted([*workflows.glob("*.yml"), *workflows.glob("*.yaml")])
    assert files
    for workflow in files:
        assert not re.search(r"uses:\s*the-cloud-clockwork/\.github/", workflow.read_text(), re.IGNORECASE), workflow
