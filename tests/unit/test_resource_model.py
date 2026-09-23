import pytest
from pydantic import ValidationError

from one_credit.models import Resource


def test_resource_model_accepts_identifier_and_metadata():
    resource = Resource(
        id="resource-001",
        name="Market Brief",
        kind="document",
        url="https://example.com/brief",
        metadata={"topic": "strategy"},
    )

    assert resource.id == "resource-001"
    assert resource.name == "Market Brief"
    assert resource.kind == "document"
    assert resource.url == "https://example.com/brief"
    assert resource.metadata["topic"] == "strategy"


def test_resource_model_rejects_blank_name():
    with pytest.raises(ValidationError):
        Resource(id="resource-002", name="   ", kind="document")
