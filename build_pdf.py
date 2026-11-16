"""Pure Python Enterprise PDF Generator for SENTINEL Project Documentation.
Zero external dependencies required.
Generates a fully standard, beautiful, multi-page PDF document with:
- Title banner and metadata
- Table of contents & section headings (H1, H2, H3)
- Word-wrapped paragraphs with proper typographic hierarchy
- Formatted tables with shaded headers and alternating row fills
- Monospaced code blocks with background borders
- Running headers, footers, and page numbers
"""
import re
import zlib
from pathlib import Path
from datetime import datetime

class PDFBuilder:
    def __init__(self):
        self.objects = []  # list of bytes
        self.page_obj_ids = []
        self.width = 595.28   # A4 width (pt)
        self.height = 841.89  # A4 height (pt)
        self.margin_left = 46.0
        self.margin_right = 46.0
        self.margin_top = 54.0
        self.margin_bottom = 54.0
        self.printable_width = self.width - self.margin_left - self.margin_right

        # Font IDs
        # F1: Helvetica, F2: Helvetica-Bold, F3: Helvetica-Oblique, F4: Courier, F5: Courier-Bold
        self.fonts = {
            "regular": "F1",
            "bold": "F2",
            "italic": "F3",
            "mono": "F4",
            "mono_bold": "F5",
        }

    def _add_object(self, data: bytes) -> int:
        self.objects.append(data)
        return len(self.objects)  # 1-based index

    def build_pdf(self, pages_commands: list[list[str]]) -> bytes:
        total_pages = len(pages_commands)

        # 1. Fonts definitions
        font_f1 = self._add_object(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
        font_f2 = self._add_object(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>")
        font_f3 = self._add_object(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Oblique /Encoding /WinAnsiEncoding >>")
        font_f4 = self._add_object(b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier /Encoding /WinAnsiEncoding >>")
        font_f5 = self._add_object(b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier-Bold /Encoding /WinAnsiEncoding >>")

        # ProcSet & Resource Dict
        res_dict = f"""<<
/ProcSet [/PDF /Text /ImageB /ImageC /ImageI]
/Font <<
  /F1 {font_f1} 0 R
  /F2 {font_f2} 0 R
  /F3 {font_f3} 0 R
  /F4 {font_f4} 0 R
  /F5 {font_f5} 0 R
>>
>>""".encode("latin1")
        res_obj = self._add_object(res_dict)

        # Reserve pages object placeholder
        pages_obj_id = self._add_object(b"")
        page_indices = []

        # For each page, render commands stream
        for page_num, cmds in enumerate(pages_commands, start=1):
            stream_content = "\n".join(cmds).encode("latin1", errors="replace")
            comp_stream = zlib.compress(stream_content)
            stream_obj = self._add_object(
                f"<< /Length {len(comp_stream)} /Filter /FlateDecode >>\nstream\n".encode("latin1")
                + comp_stream
                + b"\nendstream"
            )
            page_obj = self._add_object(
                f"""<<
/Type /Page
/Parent {pages_obj_id} 0 R
/MediaBox [0 0 {self.width:.2f} {self.height:.2f}]
/Contents {stream_obj} 0 R
/Resources {res_obj} 0 R
>>""".encode("latin1")
            )
            page_indices.append(page_obj)

        # Now fill the reserved Pages Object
        kids_str = " ".join(f"{idx} 0 R" for idx in page_indices)
        self.objects[pages_obj_id - 1] = f"<< /Type /Pages /Kids [{kids_str}] /Count {total_pages} >>".encode("latin1")

        # Catalog Object
        catalog_obj = self._add_object(
            f"<< /Type /Catalog /Pages {pages_obj_id} 0 R >>".encode("latin1")
        )

        # Output generation with xref table
        out = bytearray()
        out.extend(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")

        offsets = [0]
        for idx, obj_data in enumerate(self.objects, start=1):
            offsets.append(len(out))
            out.extend(f"{idx} 0 obj\n".encode("latin1"))
            out.extend(obj_data)
            out.extend(b"\nendobj\n")

        xref_start = len(out)
        out.extend(f"xref\n0 {len(self.objects) + 1}\n".encode("latin1"))
        out.extend(b"0000000000 65535 f \n")
        for off in offsets[1:]:
            out.extend(f"{off:010d} 00000 n \n".encode("latin1"))

        out.extend(
            f"""trailer
<<
/Size {len(self.objects) + 1}
/Root {catalog_obj} 0 R
>>
startxref
{xref_start}
%%EOF\n""".encode("latin1")
        )

        return bytes(out)

def escape_pdf(text: str) -> str:
    """Escapes special characters in PDF string literals and maps unicode to clean ASCII."""
    # Map common unicode characters to ASCII
    rep = {
        "•": "*",
        "—": "---",
        "–": "--",
        "“": '"',
        "”": '"',
        "‘": "'",
        "’": "'",
        "§": "Section ",
        "€": "EUR ",
        "…": "...",
        "·": " - ",
        "×": "x",
        "≤": "<=",
        "≥": ">=",
        "→": "->",
        "\t": "    ",
    }
    for k, v in rep.items():
        text = text.replace(k, v)

    # Filter to printable latin1/ascii
    clean = []
    for ch in text:
        if 32 <= ord(ch) <= 126 or 160 <= ord(ch) <= 255:
            clean.append(ch)
        else:
            clean.append(" ")
    text = "".join(clean)

    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

def char_width(ch: str, font: str = "regular", size: float = 9.5) -> float:
    if "mono" in font:
        return size * 0.60
    is_bold = "bold" in font
    w_factor = 1.08 if is_bold else 1.0
    if ch in "ijl|!:,.'":
        return size * 0.28 * w_factor
    if ch in "frtI ":
        return size * 0.35 * w_factor
    if ch in "abcdeghknopquvxyz0123456789-":
        return size * 0.54 * w_factor
    if ch in "mwABCDEFGHJKLMNOPQRSTUVXYZ":
        return size * 0.70 * w_factor
    if ch in "W@#%&":
        return size * 0.88 * w_factor
    return size * 0.55 * w_factor

def text_width(text: str, font: str = "regular", size: float = 9.5) -> float:
    return sum(char_width(c, font, size) for c in text)

def wrap_text(text: str, max_width: float, font: str = "regular", size: float = 9.5) -> list[str]:
    words = text.split(" ")
    lines = []
    current_words = []
    current_w = 0.0
    space_w = char_width(" ", font, size)

    for w in words:
        w_w = text_width(w, font, size)
        if not current_words:
            current_words.append(w)
            current_w = w_w
        elif current_w + space_w + w_w <= max_width:
            current_words.append(w)
            current_w += space_w + w_w
        else:
            lines.append(" ".join(current_words))
            current_words = [w]
            current_w = w_w

    if current_words:
        lines.append(" ".join(current_words))
    return lines or [""]

class PDFDocumentFormatter:
    def __init__(self):
        self.builder = PDFBuilder()
        self.pages = []
        self.current_page_cmds = []
        self.cursor_y = self.builder.height - self.builder.margin_top
        self.page_number = 1

    def _start_new_page(self):
        if self.current_page_cmds:
            self._render_page_chrome()
            self.pages.append(self.current_page_cmds)
            self.current_page_cmds = []
            self.page_number += 1
        self.cursor_y = self.builder.height - self.builder.margin_top

    def _render_page_chrome(self):
        """Draws running header and footer."""
        # Top Header (Only on page 2 and later)
        if self.page_number > 1:
            self.current_page_cmds.append("0.5 0.55 0.62 rg")  # Muted slate gray
            self.current_page_cmds.append(
                f"BT /F1 8.5 Tf 1 0 0 1 {self.builder.margin_left} {self.builder.height - 35:.2f} Tm (SENTINEL  -  Read-Only Enterprise Agent  -  System Architecture) Tj ET"
            )
            # Thin divider line
            self.current_page_cmds.append(
                f"0.82 0.85 0.90 RG 0.5 w {self.builder.margin_left} {self.builder.height - 40:.2f} m {self.builder.width - self.builder.margin_right} {self.builder.height - 40:.2f} l S"
            )

        # Footer on all pages
        foot_y = 35.0
        self.current_page_cmds.append(
            f"0.82 0.85 0.90 RG 0.5 w {self.builder.margin_left} {foot_y + 10:.2f} m {self.builder.width - self.builder.margin_right} {foot_y + 10:.2f} l S"
        )
        self.current_page_cmds.append("0.5 0.55 0.62 rg")
        self.current_page_cmds.append(
            f"BT /F1 8 Tf 1 0 0 1 {self.builder.margin_left} {foot_y:.2f} Tm (Enterprise Security & Architecture  -  Safe by Construction) Tj ET"
        )
        page_str = f"Page {self.page_number}"
        self.current_page_cmds.append(
            f"BT /F2 8 Tf 1 0 0 1 {self.builder.width - self.builder.margin_right - 40:.2f} {foot_y:.2f} Tm ({escape_pdf(page_str)}) Tj ET"
        )

    def check_space(self, height_needed: float):
        if self.cursor_y - height_needed < self.builder.margin_bottom:
            self._start_new_page()

    def draw_banner(self, title: str, subtitle: str, metadata: str):
        banner_h = 92.0
        self.check_space(banner_h + 20)
        y = self.cursor_y - banner_h

        # Navy Background box
        self.current_page_cmds.append(f"0.06 0.09 0.16 rg {self.builder.margin_left:.2f} {y:.2f} {self.builder.printable_width:.2f} {banner_h:.2f} re f")
        # Cyan accent line at left
        self.current_page_cmds.append(f"0.02 0.64 0.93 RG 4 w {self.builder.margin_left + 2:.2f} {y:.2f} m {self.builder.margin_left + 2:.2f} {y + banner_h:.2f} l S")

        # Title
        self.current_page_cmds.append("1.0 1.0 1.0 rg")
        self.current_page_cmds.append(
            f"BT /F2 18 Tf 1 0 0 1 {self.builder.margin_left + 16:.2f} {y + 60:.2f} Tm ({escape_pdf(title)}) Tj ET"
        )

        # Subtitle
        self.current_page_cmds.append("0.22 0.74 0.97 rg")
        self.current_page_cmds.append(
            f"BT /F2 11 Tf 1 0 0 1 {self.builder.margin_left + 16:.2f} {y + 38:.2f} Tm ({escape_pdf(subtitle)}) Tj ET"
        )

        # Metadata
        self.current_page_cmds.append("0.58 0.64 0.72 rg")
        self.current_page_cmds.append(
            f"BT /F1 8.5 Tf 1 0 0 1 {self.builder.margin_left + 16:.2f} {y + 18:.2f} Tm ({escape_pdf(metadata)}) Tj ET"
        )

        self.cursor_y = y - 18.0

    def draw_heading_1(self, text: str):
        self.check_space(38)
        self.cursor_y -= 12.0
        y = self.cursor_y

        # Primary H1 heading text
        self.current_page_cmds.append("0.08 0.22 0.42 rg")
        self.current_page_cmds.append(
            f"BT /F2 14 Tf 1 0 0 1 {self.builder.margin_left:.2f} {y:.2f} Tm ({escape_pdf(text)}) Tj ET"
        )

        # Blue underline rule
        self.current_page_cmds.append(
            f"0.15 0.45 0.75 RG 1.5 w {self.builder.margin_left:.2f} {y - 4:.2f} m {self.builder.margin_left + 240:.2f} {y - 4:.2f} l S"
        )
        self.current_page_cmds.append(
            f"0.82 0.85 0.90 RG 0.5 w {self.builder.margin_left + 240:.2f} {y - 4:.2f} m {self.builder.width - self.builder.margin_right:.2f} {y - 4:.2f} l S"
        )
        self.cursor_y = y - 16.0

    def draw_heading_2(self, text: str):
        self.check_space(30)
        self.cursor_y -= 8.0
        y = self.cursor_y

        self.current_page_cmds.append("0.12 0.24 0.36 rg")
        self.current_page_cmds.append(
            f"BT /F2 11.5 Tf 1 0 0 1 {self.builder.margin_left:.2f} {y:.2f} Tm ({escape_pdf(text)}) Tj ET"
        )
        self.cursor_y = y - 12.0

    def draw_heading_3(self, text: str):
        self.check_space(24)
        self.cursor_y -= 5.0
        y = self.cursor_y

        self.current_page_cmds.append("0.18 0.32 0.46 rg")
        self.current_page_cmds.append(
            f"BT /F2 10.5 Tf 1 0 0 1 {self.builder.margin_left:.2f} {y:.2f} Tm ({escape_pdf(text)}) Tj ET"
        )
        self.cursor_y = y - 10.0

    def draw_paragraph(self, text: str, font="regular", size=9.5, leading=13.0, text_color="0.15 0.18 0.22"):
        lines = wrap_text(text, self.builder.printable_width, font=font, size=size)
        total_h = len(lines) * leading
        self.check_space(total_h + 4)

        font_tag = self.builder.fonts.get(font, "F1")
        self.current_page_cmds.append(f"{text_color} rg")

        for line in lines:
            self.current_page_cmds.append(
                f"BT /{font_tag} {size:.1f} Tf 1 0 0 1 {self.builder.margin_left:.2f} {self.cursor_y:.2f} Tm ({escape_pdf(line)}) Tj ET"
            )
            self.cursor_y -= leading
        self.cursor_y -= 4.0

    def draw_bullet(self, title: str, body: str = ""):
        bullet_indent = 16.0
        text_width_avail = self.builder.printable_width - bullet_indent

        full_text = f"{title}: {body}" if (title and body) else (title or body)
        lines = wrap_text(full_text, text_width_avail, font="regular", size=9.0)
        total_h = len(lines) * 12.5
        self.check_space(total_h + 3)

        # Draw bullet symbol
        self.current_page_cmds.append("0.15 0.45 0.75 rg")
        self.current_page_cmds.append(
            f"{self.builder.margin_left + 4:.2f} {self.cursor_y + 3:.2f} 3.0 3.0 re f"
        )

        # Draw lines
        self.current_page_cmds.append("0.15 0.18 0.22 rg")
        for idx, line in enumerate(lines):
            f_tag = "F2" if (idx == 0 and title and not body) else "F1"
            self.current_page_cmds.append(
                f"BT /{f_tag} 9.0 Tf 1 0 0 1 {self.builder.margin_left + bullet_indent:.2f} {self.cursor_y:.2f} Tm ({escape_pdf(line)}) Tj ET"
            )
            self.cursor_y -= 12.5
        self.cursor_y -= 2.0

    def draw_code_block(self, lines: list[str]):
        font_size = 7.5
        leading = 10.2
        padding = 7.0
        block_h = len(lines) * leading + padding * 2
        self.check_space(block_h + 8)

        y = self.cursor_y - block_h

        # Light gray-slate background
        self.current_page_cmds.append(
            f"0.96 0.97 0.98 rg {self.builder.margin_left:.2f} {y:.2f} {self.builder.printable_width:.2f} {block_h:.2f} re f"
        )
        # Border
        self.current_page_cmds.append(
            f"0.84 0.88 0.92 RG 0.7 w {self.builder.margin_left:.2f} {y:.2f} {self.builder.printable_width:.2f} {block_h:.2f} re S"
        )

        # Text lines
        self.current_page_cmds.append("0.15 0.20 0.28 rg")
        text_y = y + block_h - padding - font_size
        for l in lines:
            trunc = l[:95]  # fit width
            self.current_page_cmds.append(
                f"BT /F4 {font_size:.1f} Tf 1 0 0 1 {self.builder.margin_left + padding:.2f} {text_y:.2f} Tm ({escape_pdf(trunc)}) Tj ET"
            )
            text_y -= leading

        self.cursor_y = y - 8.0

    def draw_table(self, headers: list[str], rows: list[list[str]], col_ratios: list[float] | None = None):
        cols_count = len(headers)
        if not col_ratios:
            col_ratios = [1.0 / cols_count] * cols_count
        widths = [r * self.builder.printable_width for r in col_ratios]

        # Calculate heights for rows
        def row_height(cell_texts, font="regular", size=8.0):
            max_lines = 1
            for t, w in zip(cell_texts, widths):
                lines = wrap_text(t, w - 8, font=font, size=size)
                max_lines = max(max_lines, len(lines))
            return max(18.0, max_lines * 10.5 + 7.0)

        hdr_h = row_height(headers, font="bold", size=8.5)
        total_table_h = hdr_h + sum(row_height(r) for r in rows)

        # If table doesn't fit on this page, start new page
        if self.cursor_y - hdr_h - 20 < self.builder.margin_bottom:
            self._start_new_page()

        # Render Header
        self.check_space(hdr_h)
        y = self.cursor_y - hdr_h
        # Header background (deep navy)
        self.current_page_cmds.append(
            f"0.12 0.18 0.28 rg {self.builder.margin_left:.2f} {y:.2f} {self.builder.printable_width:.2f} {hdr_h:.2f} re f"
        )

        cur_x = self.builder.margin_left
        self.current_page_cmds.append("1.0 1.0 1.0 rg")
        for h_text, w in zip(headers, widths):
            wrapped = wrap_text(h_text, w - 8, font="bold", size=8.5)
            ty = y + hdr_h - 11.0
            for wl in wrapped:
                self.current_page_cmds.append(
                    f"BT /F2 8.5 Tf 1 0 0 1 {cur_x + 4:.2f} {ty:.2f} Tm ({escape_pdf(wl)}) Tj ET"
                )
                ty -= 10.0
            cur_x += w

        self.cursor_y = y

        # Render Data Rows
        for r_idx, r_data in enumerate(rows):
            rh = row_height(r_data, font="regular", size=8.0)
            self.check_space(rh)
            y = self.cursor_y - rh

            # Alternating row background
            bg_color = "0.97 0.98 1.0 rg" if r_idx % 2 == 1 else "1.0 1.0 1.0 rg"
            self.current_page_cmds.append(
                f"{bg_color} {self.builder.margin_left:.2f} {y:.2f} {self.builder.printable_width:.2f} {rh:.2f} re f"
            )
            # Bottom border line
            self.current_page_cmds.append(
                f"0.88 0.90 0.94 RG 0.5 w {self.builder.margin_left:.2f} {y:.2f} m {self.builder.width - self.builder.margin_right:.2f} {y:.2f} l S"
            )

            cur_x = self.builder.margin_left
            self.current_page_cmds.append("0.18 0.22 0.28 rg")
            for c_text, w in zip(r_data, widths):
                wrapped = wrap_text(c_text, w - 8, font="regular", size=8.0)
                ty = y + rh - 10.0
                for wl in wrapped:
                    self.current_page_cmds.append(
                        f"BT /F1 8.0 Tf 1 0 0 1 {cur_x + 4:.2f} {ty:.2f} Tm ({escape_pdf(wl)}) Tj ET"
                    )
                    ty -= 9.5
                cur_x += w

            self.cursor_y = y

        # Outer border around table
        self.cursor_y -= 8.0

    def finish(self) -> bytes:
        if self.current_page_cmds:
            self._render_page_chrome()
            self.pages.append(self.current_page_cmds)
        return self.builder.build_pdf(self.pages)


def parse_and_render_markdown(md_text: str) -> bytes:
    doc = PDFDocumentFormatter()

    # Document Title Banner
    doc.draw_banner(
        title="SENTINEL  -  Read-Only Enterprise Agent",
        subtitle="Complete Architecture, Security Invariants & System Reference Guide",
        metadata=f"Generated: {datetime.now().strftime('%B %d, %Y')}  -  Specification: Autonomy Ladder Days 1-6"
    )

    lines = md_text.splitlines()
    i = 0
    total_lines = len(lines)

    in_code_block = False
    code_lines = []

    in_table = False
    table_headers = []
    table_rows = []

    while i < total_lines:
        line = lines[i]
        stripped = line.strip()

        # Handle Code Block Fences
        if stripped.startswith("```"):
            if not in_code_block:
                in_code_block = True
                code_lines = []
            else:
                in_code_block = False
                doc.draw_code_block(code_lines)
                code_lines = []
            i += 1
            continue

        if in_code_block:
            code_lines.append(line)
            i += 1
            continue

        # Handle Tables
        if "|" in stripped and stripped.startswith("|") and stripped.endswith("|"):
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            # Check if separator row
            if all(set(c).issubset({"-", ":", " "}) for c in cells):
                i += 1
                continue
            if not in_table:
                in_table = True
                table_headers = cells
                table_rows = []
            else:
                table_rows.append(cells)
            i += 1
            continue
        elif in_table:
            # End of table
            in_table = False
            # Determine ratios
            cols_c = len(table_headers)
            if cols_c == 4:
                ratios = [0.22, 0.26, 0.24, 0.28]
            elif cols_c == 3:
                ratios = [0.28, 0.32, 0.40]
            elif cols_c == 2:
                ratios = [0.35, 0.65]
            else:
                ratios = [1.0 / cols_c] * cols_c
            doc.draw_table(table_headers, table_rows, ratios)
            table_headers = []
            table_rows = []
            # continue processing current line

        # Empty lines
        if not stripped:
            i += 1
            continue

        # Headings
        if stripped.startswith("# "):
            # Skip primary title since banner handles it
            if "Complete Architecture" not in stripped:
                doc.draw_heading_1(stripped[2:].strip())
            i += 1
            continue
        if stripped.startswith("## "):
            doc.draw_heading_1(stripped[3:].strip())
            i += 1
            continue
        if stripped.startswith("### "):
            doc.draw_heading_2(stripped[4:].strip())
            i += 1
            continue
        if stripped.startswith("#### "):
            doc.draw_heading_3(stripped[5:].strip())
            i += 1
            continue

        # Bullet lists
        if stripped.startswith("- ") or stripped.startswith("* "):
            bullet_text = stripped[2:].strip()
            # Split title and body if bold
            if bullet_text.startswith("**") and "**" in bullet_text[2:]:
                parts = bullet_text.split("**", 2)
                b_title = parts[1].strip()
                b_body = parts[2].lstrip(": ").strip()
                doc.draw_bullet(b_title, b_body)
            else:
                doc.draw_bullet(bullet_text)
            i += 1
            continue

        # Numbered lists
        m_num = re.match(r"^([0-9]+)\.\s+(.*)", stripped)
        if m_num:
            num_str = m_num.group(1)
            num_text = m_num.group(2).strip()
            if num_text.startswith("**") and "**" in num_text[2:]:
                parts = num_text.split("**", 2)
                n_title = f"{num_str}. {parts[1].strip()}"
                n_body = parts[2].lstrip(": ").strip()
                doc.draw_bullet(n_title, n_body)
            else:
                doc.draw_bullet(f"{num_str}. {num_text}")
            i += 1
            continue

        # Horizontal rules
        if stripped in ("---", "***", "___"):
            doc.cursor_y -= 8.0
            i += 1
            continue

        # Normal paragraph
        doc.draw_paragraph(stripped)
        i += 1

    if in_table and table_headers:
        cols_c = len(table_headers)
        ratios = [1.0 / cols_c] * cols_c
        doc.draw_table(table_headers, table_rows, ratios)

    return doc.finish()

def main():
    root_dir = Path(__file__).resolve().parent
    md_path = root_dir / "PROJECT_DOCUMENTATION.md"
    pdf_path = root_dir / "SENTINEL_PROJECT_DOCUMENTATION.pdf"

    if not md_path.exists():
        print(f"Error: {md_path} not found.")
        return

    print(f"Reading markdown content from {md_path.name}...")
    md_text = md_path.read_text(encoding="utf-8")

    print("Formatting and building PDF document...")
    pdf_bytes = parse_and_render_markdown(md_text)

    pdf_path.write_bytes(pdf_bytes)
    print(f"SUCCESS: Generated {pdf_path.name} ({len(pdf_bytes):,} bytes)")

if __name__ == "__main__":
    main()
