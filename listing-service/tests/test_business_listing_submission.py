"""Regression tests for submitting business listings with monetary values."""

import json
import unittest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

# Import the database module first so its DeclarativeBase is available while
# the ORM package registers all models (the same order used by the service).
from app.database import Base  # noqa: F401
from app.models.business_listing import BusinessListing
from app.models.outbox import OutboxEvent
from app.services.business_listing_service import BusinessListingService


class BusinessListingSubmissionTests(unittest.IsolatedAsyncioTestCase):
    async def test_submit_encodes_decimal_values_for_jsonb_outbox(self) -> None:
        user_id = uuid4()
        listing_id = uuid4()
        row = BusinessListing(
            id=listing_id,
            user_id=user_id,
            status="draft",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            business_type="food",
            property_type="free_purpose",
            transfer_method="full_transfer_training",
            deal_composition="owner",
            business_name="Кофейня",
            short_description="Готовый бизнес",
            full_description="Небольшая кофейня с собственной посадочной зоной.",
            sale_price=Decimal("1250000.50"),
            country="Россия",
            city="Москва",
            seller_status="self_employed",
            seller_name="Продавец",
            stock_value=Decimal("12500.75"),
            debts_receivable=Decimal("1500.25"),
            debts_payable=Decimal("725.10"),
            monthly_loan_payments=Decimal("999.99"),
            average_check=Decimal("450.50"),
            files={"main_photo": "/public/main.png", "photos": [f"/public/{i}.png" for i in range(5)]},
            documents={},
            equipment_list=[{
                "equipment_name": "Кофемашина",
                "equipment_brand": "Test Brand",
                "equipment_condition": "хорошее",
                "equipment_purchase_year": 2023,
                "equipment_value": Decimal("240000.00"),
            }],
            staff_details=[{"position": "Бариста", "count": 2, "salary": Decimal("65000.00")}],
            monthly_financials=[{
                "month": "2026-01",
                "revenue": Decimal("1000000.00"),
                "total_expenses": Decimal("500000.00"),
                "net_profit": Decimal("500000.00"),
            }],
            cost_structure=[],
            seasonality_months=[],
            peak_hours=[],
            analytics_results={},
        )
        session = Mock()
        session.get = AsyncMock(return_value=None)
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        session.add = Mock()
        service = BusinessListingService(session)
        service.get = AsyncMock(return_value=row)

        await service.submit(user_id, listing_id)

        events = [call.args[0] for call in session.add.call_args_list]
        listing_event = next(event for event in events if isinstance(event, OutboxEvent))
        encoded = json.dumps(listing_event.payload, allow_nan=False)
        payload = json.loads(encoded)
        analytics = payload["data_for_analytics"]

        self.assertEqual(row.status, "processing")
        self.assertEqual(analytics["sale_price"], 1250000.5)
        self.assertEqual(analytics["stock_value"], 12500.75)
        self.assertEqual(analytics["debts_receivable"], 1500.25)
        self.assertEqual(analytics["debts_payable"], 725.1)
        self.assertEqual(analytics["monthly_loan_payments"], 999.99)
        self.assertEqual(analytics["average_check"], 450.5)
        self.assertEqual(analytics["short_description"], "Готовый бизнес")
        self.assertEqual(analytics["full_description"], "Небольшая кофейня с собственной посадочной зоной.")
        self.assertEqual(analytics["equipment_list"][0]["equipment_name"], "Кофемашина")
        self.assertEqual(analytics["equipment_list"][0]["equipment_value"], 240000.0)
        self.assertEqual(analytics["staff_details"][0]["position"], "Бариста")
        self.assertEqual(analytics["monthly_financials"][0]["month"], "2026-01")
        self.assertEqual(analytics["monthly_financials"][0]["revenue"], 1000000.0)
        self.assertEqual(session.flush.await_count, 2)
        session.refresh.assert_awaited_once_with(
            row,
            attribute_names=["id", "status", "verification_status", "created_at", "updated_at"],
        )


if __name__ == "__main__":
    unittest.main()
