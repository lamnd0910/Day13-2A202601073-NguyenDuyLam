from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
ALERT_RULES_PATH = REPO_ROOT / "config" / "alert_rules.yaml"
SLO_PATH = REPO_ROOT / "config" / "slo.yaml"
RUNBOOK_PATH = REPO_ROOT / "docs" / "alerts.md"

REQUIRED_FIELDS = ("name", "severity", "condition", "duration", "type", "owner", "runbook")
ALLOWED_SEVERITIES = {"info", "warning", "critical"}
DURATION_PATTERN = re.compile(r"^\d+[ms]$")
CONDITION_PATTERN = re.compile(r"^(?P<sli>\w+)\s*(?P<operator>[<>]=?)\s*(?P<value>[\d.]+)$")


def load_alerts() -> list[dict]:
    return yaml.safe_load(ALERT_RULES_PATH.read_text(encoding="utf-8"))["alerts"]


def load_slis() -> dict:
    return yaml.safe_load(SLO_PATH.read_text(encoding="utf-8"))["slis"]


def slugify(heading: str) -> str:
    """Match the anchor GitHub generates for a markdown heading."""
    slug = heading.strip().lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    return re.sub(r"\s+", "-", slug)


def runbook_anchors() -> set[str]:
    text = RUNBOOK_PATH.read_text(encoding="utf-8")
    return {slugify(m) for m in re.findall(r"^#{1,6}\s+(.+)$", text, flags=re.MULTILINE)}


def test_alert_rules_define_exactly_three_alerts() -> None:
    alerts = load_alerts()

    assert len(alerts) == 3
    assert [alert["name"] for alert in alerts] == [
        "HighLatencyP95",
        "HighErrorRate",
        "LowQualityScore",
    ]


@pytest.mark.parametrize("config_path", [ALERT_RULES_PATH, SLO_PATH])
def test_no_placeholder_left_in_config(config_path: Path) -> None:
    text = config_path.read_text(encoding="utf-8")

    assert "TODO" not in text
    assert "Replace with your group" not in text


def test_every_alert_has_all_required_fields_filled() -> None:
    for alert in load_alerts():
        for field in REQUIRED_FIELDS:
            assert field in alert, f"{alert.get('name')} thiếu field {field}"
            assert str(alert[field]).strip(), f"{alert['name']}.{field} bị bỏ trống"


def test_severity_and_duration_use_supported_values() -> None:
    for alert in load_alerts():
        assert alert["severity"] in ALLOWED_SEVERITIES, alert["name"]
        assert DURATION_PATTERN.fullmatch(alert["duration"]), alert["name"]


def test_runbook_links_point_at_existing_sections() -> None:
    anchors = runbook_anchors()

    for alert in load_alerts():
        path, _, anchor = alert["runbook"].partition("#")
        assert path == "docs/alerts.md", alert["name"]
        assert anchor, f"{alert['name']} thiếu anchor runbook"
        assert anchor in anchors, f"{alert['name']} trỏ tới section không tồn tại: #{anchor}"


def test_alert_thresholds_match_the_slo_objectives() -> None:
    slis = load_slis()

    for alert in load_alerts():
        match = CONDITION_PATTERN.fullmatch(alert["condition"])
        assert match, f"{alert['name']} có condition không parse được: {alert['condition']}"

        sli = match.group("sli")
        assert sli in slis, f"{alert['name']} tham chiếu SLI không có trong slo.yaml: {sli}"
        assert float(match.group("value")) == pytest.approx(slis[sli]["objective"]), (
            f"{alert['name']} lệch ngưỡng so với slo.yaml"
        )
