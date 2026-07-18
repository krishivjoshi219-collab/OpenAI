"""Swappable file-extraction providers used during onboarding imports."""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from io import StringIO
from typing import Protocol

from app.models.enums import InvoiceStatus


class ImportKind(StrEnum):
    """Business records available for onboarding import."""

    INVOICES = "invoices"
    CUSTOMERS = "customers"
    PRODUCTS = "products"
    STOCK = "stock"


@dataclass(frozen=True)
class CustomerRecord:
    """Normalized customer data extracted from an uploaded file."""

    name: str
    email: str | None = None
    phone: str | None = None
    billing_address: str | None = None


@dataclass(frozen=True)
class ProductRecord:
    """Normalized product data extracted from an uploaded file."""

    name: str
    sku: str
    unit_price: Decimal
    cost_price: Decimal | None = None
    description: str | None = None


@dataclass(frozen=True)
class StockRecord:
    """Normalized stock balance extracted from an uploaded file."""

    sku: str
    quantity_on_hand: Decimal
    reorder_level: Decimal = Decimal("0")


@dataclass(frozen=True)
class InvoiceRecord:
    """Normalized invoice header extracted from an uploaded file."""

    invoice_number: str
    customer_name: str
    customer_email: str | None
    currency_code: str
    total: Decimal
    status: InvoiceStatus = InvoiceStatus.DRAFT
    issued_on: date | None = None
    due_on: date | None = None


ExtractedRecord = CustomerRecord | ProductRecord | StockRecord | InvoiceRecord


@dataclass(frozen=True)
class ExtractionPreview:
    """Reviewable extraction result returned before any database write."""

    kind: ImportKind
    file_name: str
    records: list[ExtractedRecord] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    is_supported: bool = True


class ExtractionProvider(Protocol):
    """Contract implemented by local, OCR, and AI extraction providers."""

    def supports(self, file_name: str) -> bool:
        """Return whether this provider can inspect the uploaded file."""

    def extract(self, kind: ImportKind, file_name: str, content: bytes) -> ExtractionPreview:
        """Extract normalized records without writing to the database."""


class CsvExtractionProvider:
    """Deterministically extract supported onboarding records from UTF-8 CSV files."""

    def supports(self, file_name: str) -> bool:
        """Accept CSV files regardless of letter casing."""

        return file_name.lower().endswith(".csv")

    def extract(self, kind: ImportKind, file_name: str, content: bytes) -> ExtractionPreview:
        """Parse a CSV upload into reviewable, validated records."""

        rows = self._read_rows(content)
        parsers: dict[ImportKind, list[ExtractedRecord]] = {
            ImportKind.CUSTOMERS: self._parse_customers(rows),
            ImportKind.PRODUCTS: self._parse_products(rows),
            ImportKind.STOCK: self._parse_stock(rows),
            ImportKind.INVOICES: self._parse_invoices(rows),
        }
        return ExtractionPreview(kind=kind, file_name=file_name, records=parsers[kind])

    def _read_rows(self, content: bytes) -> list[dict[str, str]]:
        text = content.decode("utf-8-sig")
        reader = csv.DictReader(StringIO(text))
        if reader.fieldnames is None:
            raise ValueError("The CSV must include a header row.")
        return [
            {self._normalize(key): (value or "").strip() for key, value in row.items()}
            for row in reader
        ]

    def _parse_customers(self, rows: list[dict[str, str]]) -> list[ExtractedRecord]:
        return [
            CustomerRecord(
                name=self._required(row, "name"),
                email=self._optional(row, "email"),
                phone=self._optional(row, "phone"),
                billing_address=self._optional(row, "billing_address", "address"),
            )
            for row in rows
        ]

    def _parse_products(self, rows: list[dict[str, str]]) -> list[ExtractedRecord]:
        return [
            ProductRecord(
                name=self._required(row, "name"),
                sku=self._required(row, "sku"),
                unit_price=self._decimal(row, "unit_price", "price"),
                cost_price=self._optional_decimal(row, "cost_price", "cost"),
                description=self._optional(row, "description"),
            )
            for row in rows
        ]

    def _parse_stock(self, rows: list[dict[str, str]]) -> list[ExtractedRecord]:
        return [
            StockRecord(
                sku=self._required(row, "sku"),
                quantity_on_hand=self._decimal(row, "quantity_on_hand", "quantity", "stock"),
                reorder_level=self._optional_decimal(row, "reorder_level") or Decimal("0"),
            )
            for row in rows
        ]

    def _parse_invoices(self, rows: list[dict[str, str]]) -> list[ExtractedRecord]:
        records: list[ExtractedRecord] = []
        for row in rows:
            status_value = self._optional(row, "status") or InvoiceStatus.DRAFT.value
            try:
                status = InvoiceStatus(status_value.lower())
            except ValueError as error:
                raise ValueError(f"Unsupported invoice status: {status_value}") from error
            records.append(
                InvoiceRecord(
                    invoice_number=self._required(row, "invoice_number", "number"),
                    customer_name=self._required(row, "customer_name", "customer"),
                    customer_email=self._optional(row, "customer_email", "email"),
                    currency_code=(
                        self._optional(row, "currency_code", "currency") or "USD"
                    ).upper(),
                    total=self._decimal(row, "total", "amount"),
                    status=status,
                    issued_on=self._optional_date(row, "issued_on", "issue_date"),
                    due_on=self._optional_date(row, "due_on", "due_date"),
                )
            )
        return records

    @staticmethod
    def _normalize(value: str | None) -> str:
        return (value or "").strip().lower().replace(" ", "_").replace("-", "_")

    @staticmethod
    def _required(row: dict[str, str], *names: str) -> str:
        value = CsvExtractionProvider._optional(row, *names)
        if value is None:
            raise ValueError(f"A required column value is missing: {names[0]}")
        return value

    @staticmethod
    def _optional(row: dict[str, str], *names: str) -> str | None:
        for name in names:
            if value := row.get(name):
                return value
        return None

    @staticmethod
    def _decimal(row: dict[str, str], *names: str) -> Decimal:
        value = CsvExtractionProvider._required(row, *names)
        try:
            return Decimal(value.replace(",", ""))
        except InvalidOperation as error:
            raise ValueError(f"Invalid decimal value for {names[0]}: {value}") from error

    @staticmethod
    def _optional_decimal(row: dict[str, str], *names: str) -> Decimal | None:
        value = CsvExtractionProvider._optional(row, *names)
        if value is None:
            return None
        try:
            return Decimal(value.replace(",", ""))
        except InvalidOperation as error:
            raise ValueError(f"Invalid decimal value for {names[0]}: {value}") from error

    @staticmethod
    def _optional_date(row: dict[str, str], *names: str) -> date | None:
        value = CsvExtractionProvider._optional(row, *names)
        if value is None:
            return None
        try:
            return date.fromisoformat(value)
        except ValueError as error:
            raise ValueError(f"Invalid ISO date for {names[0]}: {value}") from error


class UnsupportedFileProvider:
    """Return an explicit review result when no installed provider supports a file."""

    def supports(self, file_name: str) -> bool:
        """Act as the registry fallback."""

        return True

    def extract(self, kind: ImportKind, file_name: str, content: bytes) -> ExtractionPreview:
        """Describe the missing provider without attempting OCR or AI processing."""

        extension = file_name.rsplit(".", maxsplit=1)[-1].upper() if "." in file_name else "file"
        return ExtractionPreview(
            kind=kind,
            file_name=file_name,
            is_supported=False,
            warnings=[
                f"{extension} extraction is not installed yet. Upload a CSV export or add a "
                "provider for this format."
            ],
        )


class ExtractionProviderRegistry:
    """Resolve an extraction provider without coupling onboarding to a vendor."""

    def __init__(self, providers: list[ExtractionProvider]) -> None:
        self._providers = providers

    def extract(self, kind: ImportKind, file_name: str, content: bytes) -> ExtractionPreview:
        """Delegate extraction to the first provider supporting the file."""

        provider = next(provider for provider in self._providers if provider.supports(file_name))
        return provider.extract(kind, file_name, content)


def create_extraction_registry() -> ExtractionProviderRegistry:
    """Create the local onboarding extraction registry."""

    return ExtractionProviderRegistry([CsvExtractionProvider(), UnsupportedFileProvider()])
