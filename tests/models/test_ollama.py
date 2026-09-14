import pytest

from pca.models.gateway import PlanRequest
from pca.models.ollama import OllamaProvider, parse_proposals


def test_parses_a_well_formed_response() -> None:
    raw = """{"proposals": [
        {"intent": "look", "tool": "filesystem.list", "arguments": {"path": "."},
         "expected": {}}
    ]}"""
    proposals = parse_proposals(raw)
    assert len(proposals) == 1
    assert proposals[0].tool == "filesystem.list"


def test_strips_markdown_fences_models_like_to_add() -> None:
    raw = '```json\n{"proposals": [{"intent": "i", "tool": "t", "arguments": {}}]}\n```'
    assert parse_proposals(raw)[0].tool == "t"


def test_a_model_supplied_risk_field_is_rejected() -> None:
    raw = '{"proposals": [{"intent": "i", "tool": "t", "arguments": {}, "risk": "low"}]}'
    with pytest.raises(ValueError, match="rejected"):
        parse_proposals(raw)


def test_unparseable_output_raises_rather_than_guessing() -> None:
    with pytest.raises(ValueError, match="could not parse"):
        parse_proposals("I think you should delete everything!")


def test_empty_proposal_list_is_valid() -> None:
    assert parse_proposals('{"proposals": []}') == []


def test_model_id_reports_the_configured_model() -> None:
    assert OllamaProvider(model="qwen3:27b").model_id == "ollama/qwen3:27b"


@pytest.mark.ollama
def test_live_ollama_returns_structured_proposals() -> None:
    provider = OllamaProvider()
    request = PlanRequest(
        goal="list the files in the current directory",
        observations=[],
        tool_names=["filesystem.list"],
    )
    proposals = provider.propose(request)
    assert all(p.tool for p in proposals)
