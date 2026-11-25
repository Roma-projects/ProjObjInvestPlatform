from pydantic import ValidationError
import pytest

from app.schemas.business_listing import BusinessListingDraft


def test_sale_reason_accepts_long_reason() -> None:
    reason = "Переезд владельца. " * 20

    draft = BusinessListingDraft(sale_reason=reason)

    assert draft.sale_reason == reason


def test_sale_reason_rejects_more_than_1000_characters() -> None:
    with pytest.raises(ValidationError):
        BusinessListingDraft(sale_reason="x" * 1001)