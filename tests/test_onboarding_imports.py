"""Tests for deterministic onboarding extraction and confirmation persistence."""

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.database.base import Base
from app.models import Business, Customer
from app.onboarding.extraction import CustomerRecord, ImportKind, create_extraction_registry
from app.onboarding.service import OnboardingImportService


def test_csv_customer_preview_is_reviewable_before_persistence() -> None:
    """CSV providers return normalized records without opening a database transaction."""

    preview = create_extraction_registry().extract(
        ImportKind.CUSTOMERS,
        "customers.csv",
        b"name,email,phone\nAda Lovelace,ada@example.com,555-0100\n",
    )

    assert preview.is_supported is True
    assert len(preview.records) == 1
    assert isinstance(preview.records[0], CustomerRecord)
    assert preview.records[0].name == "Ada Lovelace"


def test_confirmation_persists_reviewed_customer_records() -> None:
    """Confirmed records are written to their business-scoped database models."""

    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    preview = create_extraction_registry().extract(
        ImportKind.CUSTOMERS,
        "customers.csv",
        b"name,email\nAda Lovelace,ada@example.com\n",
    )

    with Session(engine) as session:
        business = Business(name="Analytical Engines", slug="analytical-engines")
        session.add(business)
        session.flush()
        confirmation = OnboardingImportService(session).confirm(business.id, preview)
        session.commit()

        customer = session.scalar(select(Customer))
        assert customer is not None
        assert customer.business_id == business.id
        assert customer.email == "ada@example.com"
        assert confirmation.created == 1


def test_unsupported_file_is_never_silently_extracted() -> None:
    """Unsupported formats (e.g. xlsx) are rejected without silent data loss."""

    preview = create_extraction_registry().extract(ImportKind.INVOICES, "invoices.xlsx", b"PK\x03\x04")

    assert preview.is_supported is False
    assert preview.records == []


def test_corrupt_pdf_returns_explicit_warning() -> None:
    """A truncated or corrupt PDF produces a clear warning rather than a crash."""

    preview = create_extraction_registry().extract(ImportKind.INVOICES, "invoice.pdf", b"%PDF")

    assert preview.is_supported is False
    assert preview.records == []
    assert any("PDF" in w or "pdf" in w or "read" in w.lower() for w in preview.warnings)
