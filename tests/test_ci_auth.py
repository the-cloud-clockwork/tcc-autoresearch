import re
from pathlib import Path

import yaml


def test_workflows_do_not_read_personal_tokens():
    workflows = Path(__file__).resolve().parents[1] / ".github" / "workflows"
    personal_tokens = (
        "ORG_GITHUB_TOKEN",
        "GHCR_PAT",
        "UPSTREAM_SYNC_PAT",
        "RELEASE_TOKEN",
        "QITP_ANTON_DISPATCH_TOKEN",
        "GH_TOKEN",
    )
    for workflow in sorted(workflows.glob("*.y*ml")):
        for expression in re.findall(
            r"\$\{\{(.*?)\}\}", workflow.read_text(), re.DOTALL
        ):
            for token in personal_tokens:
                assert not re.search(
                    rf"\bsecrets\s*(?:\.\s*{token}\b|\[\s*['\"]{token}['\"]\s*\])",
                    expression,
                ), f"{workflow.name} reads personal token {token}"


def test_release_passes_org_ci_app_credentials():
    workflow = (
        Path(__file__).resolve().parents[1] / ".github" / "workflows" / "release.yml"
    )
    release = yaml.safe_load(workflow.read_text())["jobs"]["release"]
    assert (
        release["uses"]
        == "The-Cloud-Clockwork/.github/.github/workflows/release-reusable.yml@main"
    )
    assert release["secrets"] == {
        "TCC_CI_CLIENT_ID": "${{ secrets.TCC_CI_CLIENT_ID }}",
        "TCC_CI_APP_PRIVATE_KEY": "${{ secrets.TCC_CI_APP_PRIVATE_KEY }}",
    }
    assert release["with"] == {
        "bump": "${{ inputs.bump }}",
        "downstream_workflows": "workflow.yaml",
    }
