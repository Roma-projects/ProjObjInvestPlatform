import unittest

from app.model_client import VisionAnalyzer


class VerificationLevelTests(unittest.TestCase):
    def test_only_passport_copy_requires_deep_verification(self) -> None:
        analyzer = VisionAnalyzer.__new__(VisionAnalyzer)
        report = {
            "content_moderation": [{
                "image_path": "/public/review.jpg",
                "status": "review",
                "category": "uncertain",
                "reason": "Требуется ручная проверка",
                "confidence": 0.5,
            }],
            "moderation_status": "requires_moderation",
            "moderation_reasons": ["manual_review_required"],
            "moderator_report": {},
        }

        other_documents = analyzer._apply_deterministic_verdict(
            dict(report),
            {"has_documents": {"tax_certificate_doc": True}},
            None,
        )
        passport = analyzer._apply_deterministic_verdict(
            dict(report),
            {"has_documents": {"passport_copy_doc": True}},
            None,
        )

        self.assertEqual(other_documents["verification_level"], "basic")
        self.assertEqual(other_documents["moderation_status"], "requires_moderation")
        self.assertEqual(passport["verification_level"], "deep")


if __name__ == "__main__":
    unittest.main()