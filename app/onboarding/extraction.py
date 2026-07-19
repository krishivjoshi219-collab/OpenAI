"""Swappable file-extraction providers used during onboarding imports."""

from __future__ import annotations

import csv
import io
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
        parser_map = {
            ImportKind.CUSTOMERS: self._parse_customers,
            ImportKind.PRODUCTS:  self._parse_products,
            ImportKind.STOCK:     self._parse_stock,
            ImportKind.INVOICES:  self._parse_invoices,
        }
        records = parser_map[kind](rows)
        return ExtractionPreview(kind=kind, file_name=file_name, records=records)

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
                name=self._required(
                    row, "name", "customer_name", "full_name", "contact_name",
                    "contact", "client_name", "client",
                ),
                email=self._optional(
                    row, "email", "email_address", "contact_email", "e_mail",
                ),
                phone=self._optional(
                    row, "phone", "phone_number", "telephone", "mobile",
                    "mobile_number", "tel", "contact_number",
                ),
                billing_address=self._optional(
                    row, "billing_address", "address", "street_address",
                    "location", "bill_to_address",
                ),
            )
            for row in rows
        ]

    def _parse_products(self, rows: list[dict[str, str]]) -> list[ExtractedRecord]:
        return [
            ProductRecord(
                name=self._required(
                    row, "name", "product_name", "item_name", "item",
                    "product", "title",
                ),
                sku=self._required(
                    row, "sku", "product_code", "item_code", "code", "ref",
                    "reference", "part_number", "product_id",
                ),
                unit_price=self._decimal(
                    row, "unit_price", "price", "selling_price", "sale_price",
                    "rate", "list_price", "retail_price",
                ),
                cost_price=self._optional_decimal(
                    row, "cost_price", "cost", "purchase_price", "buy_price", "cogs",
                ),
                description=self._optional(
                    row, "description", "details", "notes", "product_description", "summary",
                ),
            )
            for row in rows
        ]

    def _parse_stock(self, rows: list[dict[str, str]]) -> list[ExtractedRecord]:
        return [
            StockRecord(
                sku=self._required(
                    row, "sku", "product_code", "item_code", "code",
                    "ref", "reference", "product_id",
                ),
                quantity_on_hand=self._decimal(
                    row, "quantity_on_hand", "quantity", "stock", "qty",
                    "stock_level", "on_hand", "available", "inventory",
                    "balance", "current_stock",
                ),
                reorder_level=self._optional_decimal(
                    row, "reorder_level", "reorder_point", "min_stock",
                    "minimum", "min_qty", "reorder",
                ) or Decimal("0"),
            )
            for row in rows
        ]

    def _parse_invoices(self, rows: list[dict[str, str]]) -> list[ExtractedRecord]:
        records: list[ExtractedRecord] = []
        for row in rows:
            status_value = self._optional(
                row, "status", "invoice_status", "state", "payment_status",
            ) or InvoiceStatus.DRAFT.value
            try:
                status = InvoiceStatus(status_value.lower())
            except ValueError as error:
                raise ValueError(f"Unsupported invoice status: {status_value}") from error
            records.append(
                InvoiceRecord(
                    invoice_number=self._required(
                        row, "invoice_number", "number", "invoice_no", "inv_no",
                        "invoice_num", "invoice_id", "ref", "reference", "no",
                    ),
                    customer_name=self._required_with_default(
                        row, "Unknown Customer", "customer_name", "customer", "client", "client_name",
                        "bill_to", "billed_to", "name", "buyer", "sold_to", "account",
                    ),
                    customer_email=self._optional(
                        row, "customer_email", "email", "client_email", "bill_to_email",
                    ),
                    currency_code=(
                        self._optional(row, "currency_code", "currency", "curr", "ccy") or "USD"
                    ).upper(),
                    total=self._decimal(
                        row, "total", "amount", "total_amount", "grand_total",
                        "invoice_total", "balance_due", "amount_due", "net_total",
                    ),
                    status=status,
                    issued_on=self._optional_date(
                        row, "issued_on", "issue_date", "invoice_date", "date",
                        "created_date", "created_on",
                    ),
                    due_on=self._optional_date(
                        row, "due_on", "due_date", "payment_due", "due", "payment_date",
                    ),
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
    def _required_with_default(row: dict[str, str], default: str, *names: str) -> str:
        value = CsvExtractionProvider._optional(row, *names)
        if value is not None:
            return value
        normalized_names = {CsvExtractionProvider._normalize(name) for name in names}
        for key, val in row.items():
            if CsvExtractionProvider._normalize(key) in normalized_names and val and val.strip():
                return val.strip()
        for val in row.values():
            if val and val.strip():
                return val.strip()
        return default

    @staticmethod
    def _optional(row: dict[str, str], *names: str) -> str | None:
        normalized_names = {CsvExtractionProvider._normalize(name) for name in names}
        for key, value in row.items():
            if CsvExtractionProvider._normalize(key) in normalized_names and value and value.strip():
                return value.strip()
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


class PdfExtractionProvider(CsvExtractionProvider):
    """Extract onboarding records from PDF files that contain data tables.

    Uses pdfplumber to locate the first readable table whose column headers
    match the requested import kind.  Falls back to an explicit warning if
    the PDF is corrupt, password-protected, or contains no parseable tables.
    """

    def supports(self, file_name: str) -> bool:
        return file_name.lower().endswith(".pdf")

    def extract(self, kind: ImportKind, file_name: str, content: bytes) -> ExtractionPreview:
        try:
            import pdfplumber  # type: ignore[import-untyped]
        except ImportError:
            return ExtractionPreview(
                kind=kind,
                file_name=file_name,
                is_supported=False,
                warnings=["pdfplumber is not installed. Run: pip install pdfplumber"],
            )

        try:
            rows = self._extract_rows_from_pdf(pdfplumber, content)
        except Exception as exc:  # noqa: BLE001
            return ExtractionPreview(
                kind=kind,
                file_name=file_name,
                is_supported=False,
                warnings=[
                    f"Could not read PDF: {exc}. "
                    "Ensure the file is not password-protected or corrupted."
                ],
            )

        if not rows:
            return ExtractionPreview(
                kind=kind,
                file_name=file_name,
                is_supported=False,
                warnings=[
                    "No data table found in the PDF. "
                    "Export a table (not a scanned image) so the columns can be read."
                ],
            )

        try:
            parser_map = {
                ImportKind.CUSTOMERS: self._parse_customers,
                ImportKind.PRODUCTS:  self._parse_products,
                ImportKind.STOCK:     self._parse_stock,
                ImportKind.INVOICES:  self._parse_invoices,
            }
            records = parser_map[kind](rows)
        except (ValueError, KeyError) as exc:
            return ExtractionPreview(
                kind=kind,
                file_name=file_name,
                is_supported=False,
                warnings=[
                    f"Table found but column mapping failed: {exc}. "
                    "Check that the PDF table has the expected column headers."
                ],
            )

        return ExtractionPreview(kind=kind, file_name=file_name, records=records)

    # ------------------------------------------------------------------
    # PDF-specific helpers
    # ------------------------------------------------------------------

    def _extract_rows_from_pdf(self, pdfplumber: object, content: bytes) -> list[dict[str, str]]:
        """Open PDF bytes and return normalised dict rows from the best table found."""
        with pdfplumber.open(io.BytesIO(content)) as pdf:  # type: ignore[attr-defined]
            # Collect all tables from all pages
            all_tables: list[list[list[str | None]]] = []
            for page in pdf.pages:
                for table in page.extract_tables():
                    if table and len(table) >= 2:  # header + at least one data row
                        all_tables.append(table)

        if not all_tables:
            return []

        # Use the largest table (most data rows) as the primary source
        table = max(all_tables, key=len)
        raw_headers = table[0]
        headers = [self._normalize(str(h) if h is not None else "") for h in raw_headers]

        rows: list[dict[str, str]] = []
        for raw_row in table[1:]:
            # Pad short rows to avoid index errors
            padded = list(raw_row) + [None] * (len(headers) - len(raw_row))
            row = {h: (str(v) if v is not None else "").strip() for h, v in zip(headers, padded)}
            # Skip entirely blank rows
            if any(row.values()):
                rows.append(row)

        return rows


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

    return ExtractionProviderRegistry(
        [CsvExtractionProvider(), PdfExtractionProvider(), UnsupportedFileProvider()]
    )
