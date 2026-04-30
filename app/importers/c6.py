import io
import re
from dataclasses import dataclass

import pdfplumber

# DD/MM at start of string (possibly with surrounding whitespace)
_DATE_RE = re.compile(r'^\s*(\d{2})/(\d{2})\s+')
# Brazilian amount at end: 1.234,56 or 234,56
_AMOUNT_RE = re.compile(r'([\d]+(?:\.\d{3})*,\d{2})\s*$')
# Year in statement header
_YEAR_RE = re.compile(r'\b(20\d{2})\b')


@dataclass
class C6Transaction:
    day: int
    month: int
    year: int
    description: str
    amount: float  # positive = expense


def _to_float(s: str) -> float | None:
    """'1.234,56' → 1234.56"""
    try:
        return float(s.replace('.', '').replace(',', '.'))
    except ValueError:
        return None


def _from_text_line(line: str, year: int) -> C6Transaction | None:
    dm = _DATE_RE.match(line)
    if not dm:
        return None
    remainder = line[dm.end():]
    am = _AMOUNT_RE.search(remainder)
    if not am:
        return None
    amount = _to_float(am.group(1))
    if not amount or amount <= 0:
        return None
    desc = remainder[: am.start()].strip()
    if not desc:
        return None
    return C6Transaction(
        day=int(dm.group(1)),
        month=int(dm.group(2)),
        year=year,
        description=desc,
        amount=amount,
    )


def _from_table_row(row: list, year: int) -> C6Transaction | None:
    if not row:
        return None
    cells = [str(c or '').strip() for c in row]
    # Find the date cell
    date_cell = None
    for c in cells:
        if _DATE_RE.match(c + ' '):
            date_cell = c
            break
    if date_cell is None:
        return None
    dm = re.match(r'(\d{2})/(\d{2})', date_cell)
    # Last cell that looks like an amount
    amount_str = None
    desc_parts = []
    for c in cells:
        if c == date_cell:
            continue
        if _AMOUNT_RE.match(c):
            amount_str = c
        elif c:
            desc_parts.append(c)
    if not amount_str:
        return None
    amount = _to_float(amount_str)
    if not amount or amount <= 0:
        return None
    desc = ' '.join(desc_parts).strip()
    if not desc:
        return None
    return C6Transaction(
        day=int(dm.group(1)),
        month=int(dm.group(2)),
        year=year,
        description=desc,
        amount=amount,
    )


def parse_c6_pdf(file_bytes: bytes, ref_year: int | None = None) -> list[C6Transaction]:
    from datetime import datetime
    if ref_year is None:
        ref_year = datetime.now().year

    transactions: list[C6Transaction] = []

    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        # Try to detect the statement year from the first page
        first_text = pdf.pages[0].extract_text() or '' if pdf.pages else ''
        ym = _YEAR_RE.search(first_text)
        if ym:
            ref_year = int(ym.group(1))

        for page in pdf.pages:
            # Strategy 1: table rows
            for table in (page.extract_tables() or []):
                for row in table:
                    t = _from_table_row(row, ref_year)
                    if t:
                        transactions.append(t)

            # Strategy 2: plain text lines
            text = page.extract_text() or ''
            for line in text.splitlines():
                t = _from_text_line(line, ref_year)
                if t:
                    transactions.append(t)

    # Deduplicate (table + text may overlap)
    seen: set[tuple] = set()
    unique: list[C6Transaction] = []
    for t in transactions:
        key = (t.day, t.month, t.year, t.description, t.amount)
        if key not in seen:
            seen.add(key)
            unique.append(t)

    # Sort by month then day
    unique.sort(key=lambda t: (t.month, t.day))
    return unique
