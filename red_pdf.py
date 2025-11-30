from dataclasses import asdict, dataclass, fields
import csv
from cv2.typing import MatLike
import os
from pathlib import Path
from typing import TypeAlias

from pdf2image import convert_from_path
import pytesseract  # type: ignore
import re
import cv2
import numpy as np
from PIL import Image
from collections import namedtuple
import logging

logger = logging.getLogger(__name__)
Reason: TypeAlias = str
CellCoord = namedtuple("CellCoord", ["x", "y", "w", "h"])


WHITE = (255, 255, 255)
BLUE = (0, 0, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)

INC_THRESHOLD_MIN = 500
INC_THRESHOLD_MID = 1000
INC_THRESHOLD_MAX = 1500

CELL_ROW_Y_THRESHOLD = 25
CELL_ROW_X_THRESHOLD = 25
CELL_PADDING = 5

N_COLUMNS = 16

COLUMN_RECORD_NUM = 0
COLUMN_NAME = 1
COLUMN_ADDRESS = 2
COLUMN_EGN = 3
COLUMN_N_PACK_1 = 4
COLUMN_N_PACK_2 = 5
COLUMN_N_PACK_3 = 6
COLUMN_DATE = 13
COLUMN_SIGNATURE = 14
COLUMN_NOTE = 15

SIGNATURE_COLUMNS = {COLUMN_DATE, COLUMN_SIGNATURE, COLUMN_NOTE}
TXT_COLUMNS = {COLUMN_RECORD_NUM, COLUMN_NAME, COLUMN_ADDRESS, COLUMN_EGN}

COL_AVG_WIDTHS = [
    145,
    412,
    660,
    251,
    131,
    133,
    97,
    94,
    171,
    68,
    133,
    92,
    212,
    227,
    228,
    252,
]

COL_AVG_XS = [
    76,
    223,
    636,
    1298,
    1552,
    1686,
    1820,
    1919,
    2015,
    2188,
    2258,
    2394,
    2487,
    2701,
    2929,
    3158,
]


def pdf_to_images(pdf_path, dpi=300) -> list[Image.Image]:
    return convert_from_path(pdf_path, dpi=dpi)


def crop_image_bottom(image: Image.Image, perc=50) -> Image.Image:
    w, h = image.size
    top = h - int(h * (perc / 100))
    bottom = h
    crop = image.crop(box=(0, top, w, bottom))
    return crop


def crop_image_center(image: Image.Image, perc=50) -> Image.Image:
    w, h = image.size
    center_length = int(h * (perc / 100))
    top = int((h - center_length) / 2)
    bottom = top + center_length
    crop = image.crop(box=(0, top, w, bottom))
    return crop


def crop_image_top(image: Image.Image, perc=50) -> Image.Image:
    w, h = image.size
    top = 0
    bottom = int(h * (perc / 100))
    crop = image.crop(box=(0, top, w, bottom))
    return crop


def preprocess(img: Image.Image) -> MatLike:
    gray = cv2.cvtColor(np.array(img), cv2.COLOR_BGR2GRAY)

    # Binary inverse (table lines become white)
    _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    return bw


def get_vertical_lines(bw, sensitivity=50):
    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, sensitivity))
    vertical_lines = cv2.morphologyEx(bw, cv2.MORPH_OPEN, vertical_kernel, iterations=3)
    return vertical_lines


def get_horizontal_lines(bw, sensitivity=50):
    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (sensitivity, 1))
    horizontal_lines = cv2.morphologyEx(
        bw, cv2.MORPH_OPEN, horizontal_kernel, iterations=3
    )
    return horizontal_lines


def combine_lines(vertical, horizontal):
    table = cv2.addWeighted(vertical, 0.5, horizontal, 0.5, 0)
    return table


def find_cells(table_img) -> list[CellCoord]:
    contours, _ = cv2.findContours(table_img, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    boxes = []
    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        if w > 30 and h > 20:  # filter noise
            boxes.append(CellCoord(x, y, w, h))

    return boxes


def group_cells_by_row(cells: list[CellCoord], y_threshold):
    # Ensure we have CellCoord objects and group by Y proximity.

    rows: list[list[CellCoord]] = [[]]
    cells.sort(key=lambda c: c.y)
    row_y = cells[0].y
    row = rows[0]

    for cell in cells:
        placed = False

        if abs(cell.y - row_y) < y_threshold:
            row.append(cell)
            placed = True
            row_y = (cell.y + row_y) // 2

        if not placed:
            row = [cell]
            rows.append(row)
            row_y = cell.y

    for row in rows:
        row.sort(key=lambda c: c.x)
    return rows


def draw_cell_img(cell: CellCoord, img: Image.Image, clr=RED) -> Image.Image:
    x, y, w, h = cell
    arr = cv2.rectangle(np.array(img), (x, y), (x + w, y + h), clr, 2)
    return Image.fromarray(arr)


def draw_cell_arr(cell: CellCoord, arr: np.ndarray, clr=RED) -> np.ndarray:
    x, y, w, h = cell
    return cv2.rectangle(arr, (x, y), (x + w, y + h), clr, 2)


@dataclass
class Page:
    pdf_name: str
    pagenum: int
    image: Image.Image
    table_border: CellCoord
    rows: list[list[CellCoord]]
    reconstructed: dict[tuple[int, int], CellCoord] | None = None


def reconstruct_missing_cells(page: Page):
    reconstructed = {}
    for row_ndx, row in enumerate(page.rows):
        if len(row) == N_COLUMNS:
            continue
        logger.error(
            f"Page {page.pdf_name}, page {page.pagenum}, row {row_ndx}, N columns {len(row)}, expected {N_COLUMNS}"
        )
        created = []

        for col_ndx in range(N_COLUMNS):
            avg_w = COL_AVG_WIDTHS[col_ndx]
            avg_x = COL_AVG_XS[col_ndx]
            cell = row[col_ndx] if col_ndx < len(row) else row[-1]

            if abs(cell.x - avg_x) > CELL_ROW_X_THRESHOLD:
                new = CellCoord(x=avg_x, y=cell.y, w=avg_w, h=cell.h)
                created.append(new)
                reconstructed[(row_ndx, col_ndx)] = new
                logger.error(f"  Reconstructed cell at ({row_ndx}, {col_ndx})")
        for cell in created:
            row.append(cell)
            row.sort(key=lambda c: c.x)
    page.reconstructed = reconstructed or None


def process_pdf(pdf: Path):
    logging.info(f"Processing File: {pdf.name} - started")
    images = pdf_to_images(pdf)
    logger.debug(f"Extracted {len(images)} pages")

    pages = []
    for pagenum, image in enumerate(images):
        image = image.transpose(Image.Transpose.ROTATE_90)
        if pagenum == 0:
            image = crop_image_bottom(image, perc=25)

        bw = preprocess(image)
        vertical = get_vertical_lines(bw, sensitivity=30)
        horizontal = get_horizontal_lines(bw, sensitivity=30)

        table_lines = combine_lines(vertical, horizontal)
        cells = find_cells(table_lines)
        if not cells:
            ValueError(f"Failed to find table in page {pagenum}, file: {pdf.name}")
        table_border = cells.pop(0)
        rows = group_cells_by_row(cells, y_threshold=CELL_ROW_Y_THRESHOLD)
        page = Page(
            pdf_name=pdf.name,
            pagenum=pagenum,
            image=image,
            table_border=table_border,
            rows=rows,
        )

        reconstruct_missing_cells(page=page)
        pages.append(page)

    logging.info(f"Processing File: {pdf.name} - completed")
    return pages


@dataclass
class ResultRecord:
    number: int | None = None
    name: str | None = None
    address: str | None = None
    egn: int | None = None
    has_date: bool | None = None
    has_signature: bool | None = None
    has_note: bool | None = None
    confidence: float = 0
    pdf: str = ""
    page: int = -1


def process_ocr(page: Page) -> list[ResultRecord]:
    img_arr: np.ndarray = np.array(page.image)
    records = []

    for _, row in enumerate(page.rows):
        record = ResultRecord(pdf=page.pdf_name, page=page.pagenum)
        for col_ndx, cell in enumerate(row):
            if col_ndx in TXT_COLUMNS:
                x, y, w, h = cell
                cell_arr = img_arr[y : y + h, x : x + w]
                cell_img = Image.fromarray(cell_arr)

                text = pytesseract.image_to_string(cell_img, lang="bul").strip()

                if col_ndx in {COLUMN_RECORD_NUM, COLUMN_EGN}:
                    m = re.search(r"\b\d+\b", text)
                    number = int(m.group(0)) if m else None
                    if col_ndx == COLUMN_RECORD_NUM:
                        record.number = number
                    if col_ndx == COLUMN_EGN:
                        record.egn = number
                elif col_ndx == COLUMN_NAME:
                    record.name = text
                elif col_ndx == COLUMN_ADDRESS:
                    record.address = text

            elif col_ndx in SIGNATURE_COLUMNS:
                x, y, w, h = (
                    cell.x + CELL_PADDING,
                    cell.y + CELL_PADDING,
                    cell.w - 2 * CELL_PADDING,
                    cell.h - 2 * CELL_PADDING,
                )
                cell_arr = img_arr[y : y + h, x : x + w]
                # TODO: remove bellow
                cell_img = Image.fromarray(cell_arr)

                gray = cv2.cvtColor(cell_arr, cv2.COLOR_BGR2GRAY)
                _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
                ink_pixels = cv2.countNonZero(thresh)
                confidence: float = 0
                if INC_THRESHOLD_MAX < ink_pixels:
                    confidence = 1
                elif INC_THRESHOLD_MID < ink_pixels:
                    confidence = 0.6
                elif INC_THRESHOLD_MIN < ink_pixels:
                    confidence = 0.3
                has_ink = confidence > 0
                record.confidence = confidence
                if col_ndx == COLUMN_DATE:
                    record.has_date = has_ink
                elif col_ndx == COLUMN_SIGNATURE:
                    record.has_signature = has_ink
                elif col_ndx == COLUMN_NOTE:
                    record.has_note = has_ink

        records.append(record)
    return records


def write_records_csv(records: list[ResultRecord], out_path):
    """Write a list of ResultRecord dataclass instances to a CSV file.

    - `records` may be empty; a CSV with only headers will be created.
    - `out_path` can be a `str` or `pathlib.Path`.
    """
    out_path = Path(out_path)
    field_names = [f.name for f in fields(ResultRecord)]

    with out_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=field_names)
        writer.writeheader()
        for r in records:
            row = asdict(r)
            writer.writerow(row)


def main(src_folder):
    curr_folder = os.getcwd()
    pdfs = Path(src_folder).glob("*.pdf")
    if not pdfs:
        raise FileNotFoundError(f"No PDF files found in {src_folder} folder")

    records = []
    for pdf in pdfs:
        pages = process_pdf(pdf=pdf)
        for page in pages:
            ocr_results = process_ocr(page=page)
            records.extend(ocr_results)
    write_records_csv(records=records, out_path=curr_folder)


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.DEBUG)
    if not len(sys.argv) == 2:
        ValueError("Please provide source folder path as argument")
    main(src_folder=sys.argv[1])
