"""Invoice PDF renderer — exports InvoiceImageData as a PDF using ReportLab.

Usage:
    renderer = InvoicePdfRenderer()
    pdf_bytes = renderer.to_bytes(data)
"""

from __future__ import annotations

import io
from datetime import date
from decimal import Decimal

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas

from app.services.invoice_image import InvoiceImageData

# ---------------------------------------------------------------------------
# Colour palette (mirrors the Pillow renderer exactly)
# ---------------------------------------------------------------------------

_C_HEADER_BG   = colors.Color(20 / 255,  35 / 255,  30 / 255)
_C_HEADER_TEXT = colors.white
_C_ACCENT      = colors.Color(37 / 255,  99 / 255,  68 / 255)
_C_BG          = colors.white
_C_SURFACE     = colors.Color(247 / 255, 249 / 255, 248 / 255)
_C_BORDER      = colors.Color(215 / 255, 222 / 255, 219 / 255)
_C_TEXT        = colors.Color(18 / 255,  24 / 255,  22 / 255)
_C_MUTED       = colors.Color(105 / 255, 118 / 255, 114 / 255)
_C_HEADER_SUB  = colors.Color(180 / 255, 200 / 255, 190 / 255)

_STATUS_FG: dict[str, colors.Color] = {
    "DRAFT":  colors.Color(140 / 255, 140 / 255, 140 / 255),
    "ISSUED": colors.Color(37 / 255,  99 / 255,  68 / 255),
    "PAID":   colors.Color(16 / 255,  130 / 255, 78 / 255),
    "VOID":   colors.Color(190 / 255, 45 / 255,  45 / 255),
}
_STATUS_BG: dict[str, colors.Color] = {
    "DRAFT":  colors.Color(235 / 255, 235 / 255, 235 / 255),
    "ISSUED": colors.Color(220 / 255, 242 / 255, 230 / 255),
    "PAID":   colors.Color(210 / 255, 245 / 255, 228 / 255),
    "VOID":   colors.Color(250 / 255, 220 / 255, 220 / 255),
}


def _fmt_date(d: date | None) -> str:
    return d.strftime("%d %b %Y") if d else "—"


class InvoicePdfRenderer:
    """Renders an InvoiceImageData to a PDF byte string using ReportLab."""

    PAGE_W, PAGE_H = A4          # 595.27 x 841.89 pt
    PAD = 14 * mm                # left/right margin
    CONTENT_W = PAGE_W - PAD * 2

    def to_bytes(self, data: InvoiceImageData) -> bytes:
        """Return the PDF as raw bytes."""
        buf = io.BytesIO()
        c = Canvas(buf, pagesize=A4)
        c.setTitle(f"Invoice {data.invoice_number}")
        c.setAuthor(data.business_name)

        y = self.PAGE_H  # ReportLab Y grows upward from bottom
        y = self._draw_header(c, data, y)
        y = self._draw_meta_row(c, data, y)
        y = self._draw_parties(c, data, y)
        y = self._draw_divider(c, y)
        y = self._draw_items(c, data, y)
        y = self._draw_totals(c, data, y)
        if data.notes:
            y = self._draw_notes(c, data, y)
        self._draw_footer(c, data)

        c.save()
        return buf.getvalue()

    # ------------------------------------------------------------------
    # Helper: draw text with a given font / size / colour
    # ------------------------------------------------------------------

    def _text(
        self,
        c: Canvas,
        x: float,
        y: float,
        text: str,
        size: int = 10,
        bold: bool = False,
        colour: colors.Color = _C_TEXT,
        align: str = "left",
    ) -> None:
        font = "Helvetica-Bold" if bold else "Helvetica"
        c.setFont(font, size)
        c.setFillColor(colour)
        if align == "right":
            c.drawRightString(x, y, text)
        elif align == "center":
            c.drawCentredString(x, y, text)
        else:
            c.drawString(x, y, text)

    # ------------------------------------------------------------------
    # Header band
    # ------------------------------------------------------------------

    def _draw_header(self, c: Canvas, data: InvoiceImageData, y: float) -> float:
        h = 28 * mm
        top = y
        bottom = y - h

        c.setFillColor(_C_HEADER_BG)
        c.rect(0, bottom, self.PAGE_W, h, fill=1, stroke=0)

        # Business name (left)
        self._text(c, self.PAD, bottom + 16 * mm, data.business_name,
                   size=16, bold=True, colour=_C_HEADER_TEXT)
        if data.business_email:
            self._text(c, self.PAD, bottom + 9 * mm, data.business_email,
                       size=8, colour=_C_HEADER_SUB)

        # INVOICE label + number (right)
        self._text(c, self.PAGE_W - self.PAD, bottom + 16 * mm, "INVOICE",
                   size=16, bold=True, colour=_C_HEADER_TEXT, align="right")
        self._text(c, self.PAGE_W - self.PAD, bottom + 9 * mm, data.invoice_number,
                   size=8, colour=_C_HEADER_SUB, align="right")

        return bottom - 6 * mm

    # ------------------------------------------------------------------
    # Meta row (issued / due / currency / status)
    # ------------------------------------------------------------------

    def _draw_meta_row(self, c: Canvas, data: InvoiceImageData, y: float) -> float:
        cols = [
            ("ISSUED",   _fmt_date(data.issued_on)),
            ("DUE",      _fmt_date(data.due_on)),
            ("CURRENCY", data.currency_code),
            ("STATUS",   data.status),
        ]
        col_w = self.CONTENT_W / len(cols)
        label_y = y - 3 * mm
        value_y = label_y - 5 * mm

        for i, (label, value) in enumerate(cols):
            x = self.PAD + i * col_w
            self._text(c, x, label_y, label, size=7, colour=_C_MUTED)
            if label == "STATUS":
                self._draw_status_badge(c, x, value_y - 1 * mm, value)
            else:
                self._text(c, x, value_y, value, size=10, bold=True)

        return value_y - 10 * mm

    def _draw_status_badge(self, c: Canvas, x: float, y: float, status: str) -> None:
        key = status.upper()
        bg = _STATUS_BG.get(key, colors.Color(0.9, 0.9, 0.9))
        fg = _STATUS_FG.get(key, _C_MUTED)
        label = status.capitalize()
        pad_x = 2.5 * mm
        pad_y = 1 * mm
        w = len(label) * 2.4 * mm + pad_x * 2
        h = 5 * mm

        c.setFillColor(bg)
        c.roundRect(x, y, w, h, radius=1.5 * mm, fill=1, stroke=0)
        c.setFont("Helvetica-Bold", 7)
        c.setFillColor(fg)
        c.drawString(x + pad_x, y + pad_y + 0.5 * mm, label)

    # ------------------------------------------------------------------
    # Parties (FROM / BILL TO)
    # ------------------------------------------------------------------

    def _draw_parties(self, c: Canvas, data: InvoiceImageData, y: float) -> float:
        mid = self.PAD + self.CONTENT_W / 2

        start_y = y - 3 * mm
        # FROM
        self._text(c, self.PAD, start_y, "FROM", size=7, colour=_C_MUTED)
        self._text(c, self.PAD, start_y - 5 * mm, data.business_name, size=11, bold=True)
        by = start_y - 10 * mm
        if data.business_email:
            self._text(c, self.PAD, by, data.business_email, size=9, colour=_C_MUTED)
            by -= 4.5 * mm

        # BILL TO
        self._text(c, mid, start_y, "BILL TO", size=7, colour=_C_MUTED)
        self._text(c, mid, start_y - 5 * mm, data.customer_name, size=11, bold=True)
        cy = start_y - 10 * mm
        if data.customer_email:
            self._text(c, mid, cy, data.customer_email, size=9, colour=_C_MUTED)
            cy -= 4.5 * mm
        if data.customer_address:
            for line in data.customer_address.splitlines()[:2]:
                self._text(c, mid, cy, line.strip(), size=9, colour=_C_MUTED)
                cy -= 4.5 * mm

        return min(by, cy) - 5 * mm

    # ------------------------------------------------------------------
    # Divider line
    # ------------------------------------------------------------------

    def _draw_divider(self, c: Canvas, y: float, full_width: bool = False) -> float:
        x0 = 0 if full_width else self.PAD
        x1 = self.PAGE_W if full_width else self.PAGE_W - self.PAD
        c.setStrokeColor(_C_BORDER)
        c.setLineWidth(0.5)
        c.line(x0, y, x1, y)
        return y - 4 * mm

    # ------------------------------------------------------------------
    # Line items table
    # ------------------------------------------------------------------

    _COL_RATIOS = [0.44, 0.12, 0.16, 0.12, 0.16]
    _COL_HEADERS = ["DESCRIPTION", "QTY", "UNIT PRICE", "TAX", "TOTAL"]

    def _col_x(self, col: int) -> float:
        return self.PAD + sum(self._COL_RATIOS[:col]) * self.CONTENT_W

    def _col_right_x(self, col: int) -> float:
        return self.PAD + sum(self._COL_RATIOS[: col + 1]) * self.CONTENT_W

    def _draw_items(self, c: Canvas, data: InvoiceImageData, y: float) -> float:
        row_h = 7 * mm

        # Header row background
        c.setFillColor(_C_SURFACE)
        c.rect(self.PAD, y - row_h, self.CONTENT_W, row_h, fill=1, stroke=0)

        for ci, hdr in enumerate(self._COL_HEADERS):
            if ci == 0:
                self._text(c, self._col_x(ci) + 1 * mm, y - row_h + 2 * mm,
                           hdr, size=7, colour=_C_MUTED)
            else:
                self._text(c, self._col_right_x(ci) - 1 * mm, y - row_h + 2 * mm,
                           hdr, size=7, colour=_C_MUTED, align="right")

        y -= row_h

        sym = data.currency_code[:1] if data.currency_code else "$"

        if not data.items:
            self._text(c, self.PAD + 2 * mm, y - row_h + 2.5 * mm,
                       "No line items", size=9, colour=_C_MUTED)
            return y - row_h - 4 * mm

        for idx, item in enumerate(data.items):
            # Alternating row background
            if idx % 2 == 1:
                c.setFillColor(_C_SURFACE)
                c.rect(self.PAD, y - row_h, self.CONTENT_W, row_h, fill=1, stroke=0)

            text_y = y - row_h + 2 * mm
            desc = item.description[:60] + ("…" if len(item.description) > 60 else "")
            self._text(c, self._col_x(0) + 1 * mm, text_y, desc, size=9)
            self._text(c, self._col_right_x(1) - 1 * mm, text_y,
                       f"{item.quantity:g}", size=9, align="right")
            self._text(c, self._col_right_x(2) - 1 * mm, text_y,
                       f"{sym}{item.unit_price:,.2f}", size=9, align="right")
            self._text(c, self._col_right_x(3) - 1 * mm, text_y,
                       f"{item.tax_rate:.0f}%", size=9, align="right")
            self._text(c, self._col_right_x(4) - 1 * mm, text_y,
                       f"{sym}{item.line_total:,.2f}", size=9, align="right")
            y -= row_h

        return y - 5 * mm

    # ------------------------------------------------------------------
    # Totals
    # ------------------------------------------------------------------

    def _draw_totals(self, c: Canvas, data: InvoiceImageData, y: float) -> float:
        sym   = data.currency_code[:1] if data.currency_code else "$"
        right = self.PAGE_W - self.PAD
        lx    = right - 55 * mm
        row_h = 6 * mm

        rows = [
            ("Subtotal", f"{sym}{data.subtotal:,.2f}"),
            ("Tax",      f"{sym}{data.tax_total:,.2f}"),
        ]
        for label, value in rows:
            self._text(c, lx, y, label, size=9, colour=_C_MUTED)
            self._text(c, right, y, value, size=9, align="right")
            y -= row_h

        # Divider
        y -= 2 * mm
        c.setStrokeColor(_C_BORDER)
        c.setLineWidth(0.5)
        c.line(lx, y, right, y)
        y -= 5 * mm

        self._text(c, lx, y, "Total", size=12, bold=True)
        self._text(c, right, y, f"{sym}{data.total:,.2f}",
                   size=12, bold=True, colour=_C_ACCENT, align="right")

        return y - 10 * mm

    # ------------------------------------------------------------------
    # Notes
    # ------------------------------------------------------------------

    def _draw_notes(self, c: Canvas, data: InvoiceImageData, y: float) -> float:
        self._text(c, self.PAD, y, "NOTES", size=7, colour=_C_MUTED)
        y -= 5 * mm
        for line in (data.notes or "").splitlines()[:4]:
            self._text(c, self.PAD, y, line[:100], size=9)
            y -= 4.5 * mm
        return y - 4 * mm

    # ------------------------------------------------------------------
    # Footer (pinned to the page bottom)
    # ------------------------------------------------------------------

    def _draw_footer(self, c: Canvas, data: InvoiceImageData) -> None:
        footer_h = 8 * mm
        c.setFillColor(_C_HEADER_BG)
        c.rect(0, 0, self.PAGE_W, footer_h, fill=1, stroke=0)
        msg = f"Thank you for your business  ·  {data.business_name}"
        c.setFont("Helvetica", 8)
        c.setFillColor(_C_MUTED)
        c.drawCentredString(self.PAGE_W / 2, footer_h / 2 - 1.5 * mm, msg)
