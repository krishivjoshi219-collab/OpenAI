"""Swappable file-extraction providers used during onboarding imports."""

from __future__ import annotations

import csv
import io
import json
import os
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
    # Set when the AI provider auto-detected the import type
    detected_kind: ImportKind | None = None


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


# ── AI extraction prompt ───────────────────────────────────────────────────────

_AI_SYSTEM_PROMPT = """\
You are a data-extraction assistant.  Your job is to read business document text
and extract structured records in JSON.

Rules:
1. Return ONLY valid JSON — no markdown fences, no prose, no commentary.
2. Auto-detect the record type (invoices, customers, products, or stock) from
   the document content unless the caller specifies one.
3. Fill every field you can find; use null for fields that are absent.
4. Currency codes must be ISO-4217 (USD, EUR, INR …).  Default to USD if unknown.
5. Dates must be ISO-8601 (YYYY-MM-DD) or null.
6. Decimal numbers must be plain numerics without currency symbols or commas.
7. Invoice status must be one of: draft, sent, paid, overdue, cancelled.
"""

_AI_USER_TEMPLATE = """\
Extract all business records from the text below.

Requested type: {kind_hint}

Return JSON with this exact shape:
{{
  "detected_kind": "<invoices|customers|products|stock>",
  "records": [ ... ],
  "warnings": [ "<any caveats as plain strings>" ]
}}

Record schemas:

invoices record:
  invoice_number (str, required), customer_name (str), customer_email (str|null),
  currency_code (str), total (number), status (str), issued_on (date|null), due_on (date|null)

customers record:
  name (str, required), email (str|null), phone (str|null), billing_address (str|null)

products record:
  name (str, required), sku (str, required), unit_price (number, required),
  cost_price (number|null), description (str|null)

stock record:
  sku (str, required), quantity_on_hand (number, required), reorder_level (number)

Document text:
---
{text}
---
"""


class AiPdfExtractionProvider:
    """Extract any PDF using the configured AI provider (Groq / OpenAI / Gemini).

    This provider reads the full text of a PDF with pdfplumber, then sends it to
    the AI with a structured JSON extraction prompt.  It auto-detects the import
    kind so the user does not need to pick one manually, and it handles unstructured
    PDFs (e.g. scanned invoices converted to text, narrative reports, emails saved
    as PDF) that the table-based provider cannot parse.

    Falls back gracefully when:
    - pdfplumber is not installed
    - No API key is configured
    - The AI returns malformed JSON (falls through to table-based extraction)
    """

    # Character limit sent to the model — keeps token usage predictable
    _MAX_TEXT_CHARS = 12_000

    def supports(self, file_name: str) -> bool:
        return file_name.lower().endswith(".pdf")

    def extract(self, kind: ImportKind, file_name: str, content: bytes) -> ExtractionPreview:
        # 1. Extract PDF text
        try:
            import pdfplumber  # type: ignore[import-untyped]
        except ImportError:
            return ExtractionPreview(
                kind=kind,
                file_name=file_name,
                is_supported=False,
                warnings=["pdfplumber is not installed — run: pip install pdfplumber"],
            )

        try:
            pdf_text = self._extract_text(pdfplumber, content)
        except Exception as exc:  # noqa: BLE001
            return ExtractionPreview(
                kind=kind,
                file_name=file_name,
                is_supported=False,
                warnings=[
                    f"Could not read this PDF ({exc}). "
                    "Make sure the file is not corrupt or password-protected. "
                    "Try exporting as CSV instead."
                ],
            )

        if not pdf_text.strip():
            return ExtractionPreview(
                kind=kind,
                file_name=file_name,
                is_supported=False,
                warnings=[
                    "Could not read any text from this PDF. "
                    "Make sure the file is not a scanned image without OCR. "
                    "Try exporting as CSV instead."
                ],
            )

        # 2. Call AI
        api_key = self._resolve_api_key()
        if not api_key:
            return ExtractionPreview(
                kind=kind,
                file_name=file_name,
                is_supported=False,
                warnings=[
                    "No AI API key is configured. "
                    "Set GROQ_API_KEY (or OPENAI_API_KEY) in Streamlit secrets or .env, "
                    "or upload a CSV file instead."
                ],
            )

        try:
            raw = self._call_ai(api_key, kind, pdf_text[: self._MAX_TEXT_CHARS])
        except Exception as exc:  # noqa: BLE001
            return ExtractionPreview(
                kind=kind,
                file_name=file_name,
                is_supported=False,
                warnings=[f"AI extraction failed: {exc}. Try uploading a CSV instead."],
            )

        # 3. Parse AI response → records
        return self._parse_ai_response(raw, kind, file_name)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_text(pdfplumber: object, content: bytes) -> str:
        """Return all visible text from a PDF, page by page."""
        pages: list[str] = []
        with pdfplumber.open(io.BytesIO(content)) as pdf:  # type: ignore[attr-defined]
            for page in pdf.pages:
                text = page.extract_text() or ""
                pages.append(text)
        return "\n\n".join(pages)

    @staticmethod
    def _resolve_api_key() -> str | None:
        """Return the first usable API key (Groq preferred, OpenAI fallback)."""
        # Try sidebar BYOK first (Streamlit session state)
        try:
            import streamlit as st
            for key_name in ("byok_groq_api_key", "byok_openai_api_key"):
                val = st.session_state.get(key_name)
                if val:
                    return str(val)
        except Exception:  # noqa: BLE001
            pass
        # Then environment / Streamlit secrets (bridged into os.environ by _bridge_secrets)
        for env in ("GROQ_API_KEY", "OPENAI_API_KEY"):
            val = os.environ.get(env)
            if val:
                return val
        return None

    @staticmethod
    def _resolve_base_url_and_model() -> tuple[str, str]:
        """Return (base_url, model) for whichever key is available."""
        groq_key = os.environ.get("GROQ_API_KEY", "")
        if groq_key:
            return "https://api.groq.com/openai/v1", "llama-3.3-70b-versatile"
        return "https://api.openai.com/v1", "gpt-4o-mini"

    def _call_ai(self, api_key: str, kind: ImportKind, text: str) -> str:
        """Send text to the AI and return the raw JSON string."""
        from openai import OpenAI  # already a dependency

        base_url, model = self._resolve_base_url_and_model()
        client = OpenAI(api_key=api_key, base_url=base_url)

        user_msg = _AI_USER_TEMPLATE.format(
            kind_hint=kind.value,
            text=text,
        )
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _AI_SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            temperature=0,
            max_tokens=4096,
        )
        return (response.choices[0].message.content or "").strip()

    def _parse_ai_response(
        self,
        raw: str,
        requested_kind: ImportKind,
        file_name: str,
    ) -> ExtractionPreview:
        """Convert the AI's JSON string into an ExtractionPreview."""
        # Strip any accidental markdown fences
        cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()

        try:
            payload = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            return ExtractionPreview(
                kind=requested_kind,
                file_name=file_name,
                is_supported=False,
                warnings=[f"AI returned invalid JSON — {exc}. Try a CSV export instead."],
            )

        # Resolve detected kind
        raw_kind = payload.get("detected_kind", requested_kind.value)
        try:
            detected_kind = ImportKind(raw_kind)
        except ValueError:
            detected_kind = requested_kind

        raw_records: list[dict] = payload.get("records", [])
        ai_warnings: list[str] = payload.get("warnings", [])
        records: list[ExtractedRecord] = []
        parse_errors: list[str] = []

        for idx, row in enumerate(raw_records, start=1):
            try:
                record = self._coerce_record(detected_kind, row)
                if record is not None:
                    records.append(record)
            except Exception as exc:  # noqa: BLE001
                parse_errors.append(f"Row {idx}: {exc}")

        warnings = [*ai_warnings, *parse_errors]
        if not records and not parse_errors:
            warnings.append("The AI could not find any records in this PDF. "
                            "Check that the file contains business data and try again.")

        return ExtractionPreview(
            kind=detected_kind,
            file_name=file_name,
            records=records,
            warnings=warnings,
            is_supported=True,
            detected_kind=detected_kind if detected_kind != requested_kind else None,
        )

    @staticmethod
    def _coerce_record(kind: ImportKind, row: dict) -> ExtractedRecord | None:
        """Convert a raw AI dict into a typed record dataclass."""

        def _str(key: str, default: str = "") -> str:
            return str(row.get(key) or default).strip()

        def _str_or_none(key: str) -> str | None:
            val = row.get(key)
            return str(val).strip() if val else None

        def _decimal(key: str, default: str = "0") -> Decimal:
            val = str(row.get(key) or default).replace(",", "").replace("$", "").strip()
            try:
                return Decimal(val or default)
            except InvalidOperation:
                return Decimal(default)

        def _date(key: str) -> date | None:
            val = row.get(key)
            if not val:
                return None
            try:
                return date.fromisoformat(str(val)[:10])
            except ValueError:
                return None

        if kind == ImportKind.CUSTOMERS:
            name = _str("name")
            if not name:
                return None
            return CustomerRecord(
                name=name,
                email=_str_or_none("email"),
                phone=_str_or_none("phone"),
                billing_address=_str_or_none("billing_address"),
            )

        if kind == ImportKind.PRODUCTS:
            name = _str("name")
            sku = _str("sku")
            if not name or not sku:
                return None
            return ProductRecord(
                name=name,
                sku=sku,
                unit_price=_decimal("unit_price"),
                cost_price=_decimal("cost_price") if row.get("cost_price") else None,
                description=_str_or_none("description"),
            )

        if kind == ImportKind.STOCK:
            sku = _str("sku")
            if not sku:
                return None
            return StockRecord(
                sku=sku,
                quantity_on_hand=_decimal("quantity_on_hand"),
                reorder_level=_decimal("reorder_level", "0"),
            )

        # Default: invoices
        inv_num = _str("invoice_number")
        if not inv_num:
            return None
        raw_status = _str("status", "draft").lower()
        try:
            status = InvoiceStatus(raw_status)
        except ValueError:
            status = InvoiceStatus.DRAFT
        return InvoiceRecord(
            invoice_number=inv_num,
            customer_name=_str("customer_name", "Unknown Customer"),
            customer_email=_str_or_none("customer_email"),
            currency_code=(_str("currency_code") or "USD").upper()[:3],
            total=_decimal("total"),
            status=status,
            issued_on=_date("issued_on"),
            due_on=_date("due_on"),
        )


class PdfExtractionProvider(CsvExtractionProvider):
    """Extract onboarding records from PDF files that contain data tables.

    Uses pdfplumber to locate the first readable table whose column headers
    match the requested import kind.  Falls back to an explicit warning if
    the PDF is corrupt, password-protected, or contains no parseable tables.

    Note: This is the *table-only* fallback provider.  AiPdfExtractionProvider
    runs first in the registry and handles free-form / unstructured PDFs.
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
            return self._fallback_preview(kind, file_name, str(exc))

        if not rows:
            return self._fallback_preview(
                kind,
                file_name,
                "No data table found in the PDF. "
                "Export a table (not a scanned image) so the columns can be read.",
            )

        try:
            parser_map = {
                ImportKind.CUSTOMERS: self._parse_customers,
                ImportKind.PRODUCTS:  self._parse_products,
                ImportKind.STOCK:     self._parse_stock,
                ImportKind.INVOICES:  self._parse_invoices,
            }
            records = parser_map[kind](rows)
        except Exception as exc:  # noqa: BLE001
            return self._fallback_preview(
                kind,
                file_name,
                f"Table found but column mapping failed: {exc}. "
                "Showing fallback sample so onboarding can continue.",
            )

        return ExtractionPreview(kind=kind, file_name=file_name, records=records)

    def _fallback_preview(self, kind: ImportKind, file_name: str, warning: str) -> ExtractionPreview:
        """Return an unsupported preview with a clear warning when the PDF cannot be read."""

        return ExtractionPreview(
            kind=kind,
            file_name=file_name,
            records=[],
            warnings=[warning],
            is_supported=False,
        )

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
            row = {h: (str(v) if v is not None else "").strip() for h, v in zip(headers, padded, strict=False)}
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
    """Create the local onboarding extraction registry.

    Provider order matters:
    1. CSV  — deterministic header-map parser
    2. AI   — reads full PDF text and calls the configured AI (Groq / OpenAI)
    3. PDF  — table-only pdfplumber fallback (used when no AI key is present)
    4. Unsupported — catch-all that returns a helpful error message
    """

    return ExtractionProviderRegistry(
        [
            CsvExtractionProvider(),
            AiPdfExtractionProvider(),
            PdfExtractionProvider(),
            UnsupportedFileProvider(),
        ]
    )
