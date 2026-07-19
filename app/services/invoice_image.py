"""Invoice image renderer — exports invoice data as JPG or AVIF using Pillow.

Usage:
    renderer = InvoiceImageRenderer()
    jpeg_bytes = renderer.to_bytes(data, fmt="jpeg")
    avif_bytes = renderer.to_bytes(data, fmt="avif")
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Literal

from PIL import Image, ImageDraw, ImageFont

Format = Literal["jpeg", "avif"]

# ---------------------------------------------------------------------------
# Data transfer objects
# ---------------------------------------------------------------------------


@dataclass
class LineItemData:
    """A single line item on an invoice."""

    description: str
    quantity: Decimal
    unit_price: Decimal
    tax_rate: Decimal
    line_total: Decimal


@dataclass
class InvoiceImageData:
    """All data needed to render an invoice image."""

    invoice_number: str
    status: str
    currency_code: str
    subtotal: Decimal
    tax_total: Decimal
    total: Decimal
    business_name: str
    customer_name: str
    items: list[LineItemData] = field(default_factory=list)
    issued_on: date | None = None
    due_on: date | None = None
    notes: str | None = None
    business_email: str | None = None
    customer_email: str | None = None
    customer_address: str | None = None


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------

_STATUS_COLORS: dict[str, tuple[int, int, int]] = {
    "DRAFT":  (140, 140, 140),
    "ISSUED": ( 37,  99,  68),
    "PAID":   ( 16, 130,  78),
    "VOID":   (190,  45,  45),
}

_STATUS_BG: dict[str, tuple[int, int, int]] = {
    "DRAFT":  (235, 235, 235),
    "ISSUED": (220, 242, 230),
    "PAID":   (210, 245, 228),
    "VOID":   (250, 220, 220),
}


def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Try system fonts in order, fall back to Pillow default."""
    candidates = (
        [
            "/run/current-system/sw/share/X11/fonts/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
        ]
        if bold
        else [
            "/run/current-system/sw/share/X11/fonts/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        ]
    )
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


class InvoiceImageRenderer:
    """Renders an InvoiceImageData as a professional-looking PIL image."""

    W = 900
    PAD = 56
    HEADER_H = 120

    # Palette (dark-green theme matching the app)
    C_HEADER_BG   = ( 20,  35,  30)
    C_HEADER_TEXT = (255, 255, 255)
    C_ACCENT      = ( 37,  99,  68)
    C_BG          = (255, 255, 255)
    C_SURFACE     = (247, 249, 248)
    C_BORDER      = (215, 222, 219)
    C_TEXT        = ( 18,  24,  22)
    C_MUTED       = (105, 118, 114)

    def to_bytes(self, data: InvoiceImageData, fmt: Format = "jpeg") -> bytes:
        """Render *data* and return the encoded image bytes."""
        img = self._render(data)
        buf = io.BytesIO()
        if fmt == "jpeg":
            img.save(buf, format="JPEG", quality=92, optimize=True)
        else:
            img.save(buf, format="AVIF", quality=75)
        return buf.getvalue()

    # ------------------------------------------------------------------
    # Internal rendering pipeline
    # ------------------------------------------------------------------

    def _render(self, data: InvoiceImageData) -> Image.Image:
        height = self._estimate_height(data)
        img = Image.new("RGB", (self.W, height), self.C_BG)
        draw = ImageDraw.Draw(img)
        y = self._draw_header(draw, img, data)
        y = self._draw_meta_row(draw, data, y)
        y = self._draw_parties(draw, data, y)
        y = self._draw_divider(draw, y)
        y = self._draw_items(draw, img, data, y)
        y = self._draw_totals(draw, data, y)
        if data.notes:
            y = self._draw_notes(draw, data, y)
        self._draw_footer(draw, img, data, y)
        return img

    def _estimate_height(self, data: InvoiceImageData) -> int:
        return (
            self.HEADER_H
            + 70      # meta row
            + 130     # parties
            + 20      # divider
            + 40      # table header
            + max(len(data.items), 1) * 38
            + 130     # totals
            + (80 if data.notes else 0)
            + 80      # footer
            + 40      # bottom padding
        )

    # -- Header -----------------------------------------------------------

    def _draw_header(self, draw: ImageDraw.ImageDraw, img: Image.Image, data: InvoiceImageData) -> int:
        h = self.HEADER_H
        draw.rectangle([(0, 0), (self.W, h)], fill=self.C_HEADER_BG)

        f_big   = _load_font(26, bold=True)
        f_small = _load_font(13)
        f_inv   = _load_font(13)

        # Business name (left)
        draw.text((self.PAD, 36), data.business_name, font=f_big, fill=self.C_HEADER_TEXT)
        if data.business_email:
            draw.text((self.PAD, 70), data.business_email, font=f_small, fill=(180, 200, 190))

        # "INVOICE" label (right)
        label = "INVOICE"
        label_w = draw.textlength(label, font=f_big)
        draw.text((self.W - self.PAD - label_w, 36), label, font=f_big, fill=self.C_HEADER_TEXT)

        # Invoice number below label
        num_w = draw.textlength(data.invoice_number, font=f_inv)
        draw.text(
            (self.W - self.PAD - num_w, 70),
            data.invoice_number,
            font=f_inv,
            fill=(180, 200, 190),
        )
        return h + 24

    # -- Meta row (dates + status badge) ----------------------------------

    def _draw_meta_row(self, draw: ImageDraw.ImageDraw, data: InvoiceImageData, y: int) -> int:
        f_label = _load_font(11)
        f_value = _load_font(13, bold=True)

        def fmt_date(d: date | None) -> str:
            return d.strftime("%d %b %Y") if d else "—"

        cols = [
            ("ISSUED",   fmt_date(data.issued_on)),
            ("DUE",      fmt_date(data.due_on)),
            ("CURRENCY", data.currency_code),
            ("STATUS",   data.status),
        ]
        col_w = (self.W - self.PAD * 2) // len(cols)
        for i, (label, value) in enumerate(cols):
            x = self.PAD + i * col_w
            draw.text((x, y), label, font=f_label, fill=self.C_MUTED)
            if label == "STATUS":
                self._draw_badge(draw, x, y + 18, value)
            else:
                draw.text((x, y + 18), value, font=f_value, fill=self.C_TEXT)

        return y + 60

    def _draw_badge(self, draw: ImageDraw.ImageDraw, x: int, y: int, status: str) -> None:
        key = status.upper()
        bg  = _STATUS_BG.get(key, (230, 230, 230))
        fg  = _STATUS_COLORS.get(key, (80, 80, 80))
        f   = _load_font(11, bold=True)
        text = status.capitalize()
        tw   = int(draw.textlength(text, font=f))
        pad  = 8
        draw.rounded_rectangle(
            [(x, y), (x + tw + pad * 2, y + 20)],
            radius=4,
            fill=bg,
        )
        draw.text((x + pad, y + 4), text, font=f, fill=fg)

    # -- Parties (bill from / bill to) ------------------------------------

    def _draw_parties(self, draw: ImageDraw.ImageDraw, data: InvoiceImageData, y: int) -> int:
        f_label = _load_font(11)
        f_name  = _load_font(14, bold=True)
        f_detail = _load_font(12)

        mid = self.W // 2

        # FROM
        draw.text((self.PAD, y), "FROM", font=f_label, fill=self.C_MUTED)
        draw.text((self.PAD, y + 16), data.business_name, font=f_name, fill=self.C_TEXT)
        by = y + 38
        if data.business_email:
            draw.text((self.PAD, by), data.business_email, font=f_detail, fill=self.C_MUTED)
            by += 18

        # TO
        draw.text((mid, y), "BILL TO", font=f_label, fill=self.C_MUTED)
        draw.text((mid, y + 16), data.customer_name, font=f_name, fill=self.C_TEXT)
        cy = y + 38
        if data.customer_email:
            draw.text((mid, cy), data.customer_email, font=f_detail, fill=self.C_MUTED)
            cy += 18
        if data.customer_address:
            for line in data.customer_address.splitlines()[:2]:
                draw.text((mid, cy), line.strip(), font=f_detail, fill=self.C_MUTED)
                cy += 18

        return max(by, cy) + 20

    # -- Divider ----------------------------------------------------------

    def _draw_divider(self, draw: ImageDraw.ImageDraw, y: int) -> int:
        draw.line([(self.PAD, y), (self.W - self.PAD, y)], fill=self.C_BORDER, width=1)
        return y + 20

    # -- Line items table -------------------------------------------------

    COL_WIDTHS = [0.44, 0.12, 0.16, 0.12, 0.16]  # fractions of usable width
    COL_HEADERS = ["DESCRIPTION", "QTY", "UNIT PRICE", "TAX", "TOTAL"]

    def _col_x(self, col: int) -> int:
        usable = self.W - self.PAD * 2
        return self.PAD + int(sum(self.COL_WIDTHS[:col]) * usable)

    def _draw_items(
        self,
        draw: ImageDraw.ImageDraw,
        img: Image.Image,
        data: InvoiceImageData,
        y: int,
    ) -> int:
        f_head = _load_font(10, bold=True)
        f_body = _load_font(12)
        row_h  = 36

        # Table header bg
        draw.rectangle([(self.PAD, y), (self.W - self.PAD, y + row_h)], fill=self.C_SURFACE)
        for ci, header in enumerate(self.COL_HEADERS):
            align_right = ci > 0
            x = self._col_x(ci)
            if align_right:
                col_end = self._col_x(ci + 1) if ci < len(self.COL_WIDTHS) - 1 else self.W - self.PAD
                tw = int(draw.textlength(header, font=f_head))
                x = col_end - tw
            draw.text((x, y + 11), header, font=f_head, fill=self.C_MUTED)
        y += row_h

        sym = data.currency_code[:1] if data.currency_code else "$"

        if not data.items:
            draw.text((self.PAD, y + 10), "No line items", font=f_body, fill=self.C_MUTED)
            return y + row_h

        for idx, item in enumerate(data.items):
            bg = self.C_SURFACE if idx % 2 == 1 else self.C_BG
            draw.rectangle([(self.PAD, y), (self.W - self.PAD, y + row_h)], fill=bg)

            cells = [
                item.description[:54] + ("…" if len(item.description) > 54 else ""),
                f"{item.quantity:g}",
                f"{sym}{item.unit_price:,.2f}",
                f"{item.tax_rate:.0f}%",
                f"{sym}{item.line_total:,.2f}",
            ]
            for ci, cell in enumerate(cells):
                align_right = ci > 0
                x = self._col_x(ci)
                if align_right:
                    col_end = self._col_x(ci + 1) if ci < len(self.COL_WIDTHS) - 1 else self.W - self.PAD
                    tw = int(draw.textlength(cell, font=f_body))
                    x = col_end - tw
                draw.text((x, y + 11), cell, font=f_body, fill=self.C_TEXT)
            y += row_h

        return y + 16

    # -- Totals block -----------------------------------------------------

    def _draw_totals(self, draw: ImageDraw.ImageDraw, data: InvoiceImageData, y: int) -> int:
        f_label  = _load_font(12)
        f_value  = _load_font(12)
        f_total_label = _load_font(14, bold=True)
        f_total_value = _load_font(16, bold=True)

        sym   = data.currency_code[:1] if data.currency_code else "$"
        right = self.W - self.PAD
        lx    = self.W - self.PAD - 240
        row_h = 26

        rows = [
            ("Subtotal", f"{sym}{data.subtotal:,.2f}", False),
            ("Tax",      f"{sym}{data.tax_total:,.2f}",  False),
        ]
        for label, value, _ in rows:
            tw = int(draw.textlength(value, font=f_value))
            draw.text((lx, y), label, font=f_label, fill=self.C_MUTED)
            draw.text((right - tw, y), value, font=f_value, fill=self.C_TEXT)
            y += row_h

        # Divider before total
        y += 4
        draw.line([(lx, y), (right, y)], fill=self.C_BORDER, width=1)
        y += 10

        total_str = f"{sym}{data.total:,.2f}"
        tw = int(draw.textlength(total_str, font=f_total_value))
        draw.text((lx, y), "Total", font=f_total_label, fill=self.C_TEXT)
        draw.text((right - tw, y), total_str, font=f_total_value, fill=self.C_ACCENT)
        return y + 44

    # -- Notes ------------------------------------------------------------

    def _draw_notes(self, draw: ImageDraw.ImageDraw, data: InvoiceImageData, y: int) -> int:
        f_label = _load_font(11)
        f_body  = _load_font(12)
        draw.text((self.PAD, y), "NOTES", font=f_label, fill=self.C_MUTED)
        y += 16
        for line in (data.notes or "").splitlines()[:3]:
            draw.text((self.PAD, y), line[:90], font=f_body, fill=self.C_TEXT)
            y += 18
        return y + 12

    # -- Footer -----------------------------------------------------------

    def _draw_footer(
        self,
        draw: ImageDraw.ImageDraw,
        img: Image.Image,
        data: InvoiceImageData,
        y: int,
    ) -> None:
        draw.line([(0, y), (self.W, y)], fill=self.C_HEADER_BG, width=3)
        f = _load_font(11)
        msg = f"Thank you for your business  ·  {data.business_name}"
        tw = int(draw.textlength(msg, font=f))
        draw.text(((self.W - tw) // 2, y + 14), msg, font=f, fill=self.C_MUTED)
