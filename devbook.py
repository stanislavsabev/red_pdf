# %%
import os
from pathlib import Path

from pdf2image import convert_from_path
import os
import pytesseract
import re
import cv2
import numpy as np
from PIL import Image
# %%


def pdf_to_images(pdf_path, dpi=300):
    return convert_from_path(pdf_path, dpi=dpi)


def crop_image_bottom(image: Image, perc=50):
    w, h = image.size
    top = h - int(h * (perc / 100))
    bottom = h
    crop = image.crop(box=(0, top, w, bottom))
    return crop


def crop_image_center(image: Image, perc=50):
    w, h = image.size
    center_length = int(h * (perc / 100))
    top = int((h - center_length) / 2)
    bottom = top + center_length
    crop = image.crop(box=(0, top, w, bottom))
    return crop


def crop_image_top(image: Image, perc=50):
    w, h = image.size
    top = 0
    bottom = int(h * (perc / 100))
    crop = image.crop(box=(0, top, w, bottom))
    return crop


# %%


def extract_number(image: Image):
    # Convert PIL → OpenCV
    img = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

    h, w = img.shape[:2]
    top_crop = img[0 : int(h * 0.15), :]  # top 15% of page

    text = pytesseract.image_to_string(top_crop, lang="bul")

    # Example: ID is numeric, 6–12 digits
    match = re.search(r"\b\d{6,12}\b", text)

    return match.group(0) if match else None


# %%
names = list(Path(".data").glob("*.pdf"))
names
# %%


images = pdf_to_images(names[0])
images
# %%
image = images[1]
image = image.transpose(Image.Transpose.ROTATE_90)
image
# %%
img_bottom_crop = crop_image_bottom(image, perc=25)
img_bottom_crop
# %%
top_crop = crop_image_top(img_bottom_crop, perc=20)
top_crop
# %%
w, h = top_crop.size
h, w
# %%
img = cv2.cvtColor(np.array(img_bottom_crop), cv2.COLOR_RGB2BGR)
h, w = img.shape[:2]
h, w
# %%
right_third = img[:, int(w * 0.7) : w]
right_third.shape
# %%
text = pytesseract.image_to_string(center_half, lang="bul")
text
# %%
img_right_third = Image.fromarray(right_third)
img_right_third
# %%
# ========== TABLE CELLS
import cv2
import numpy as np


# %%
# region FUNCTIONS
def preprocess(img: Image):
    gray = cv2.cvtColor(np.array(img), cv2.COLOR_BGR2GRAY)

    # Binary inverse (table lines become white)
    _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    return img, bw


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


def find_cells(table_img):
    contours, _ = cv2.findContours(table_img, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    boxes = []
    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        if w > 30 and h > 20:  # filter noise
            boxes.append((x, y, w, h))

    return boxes


def group_cells_by_row(cells, y_tolerance=10):
    # Sort cells by y1 first
    cells_sorted = sorted(cells, key=lambda b: b[1])

    rows = []
    current_row = [cells_sorted[0]]

    for cell in cells_sorted[1:]:
        _, y1, _, _ = cell
        _, last_y1, _, _ = current_row[-1]

        # Compare Y positions
        if abs(y1 - last_y1) <= y_tolerance:
            current_row.append(cell)
        else:
            rows.append(current_row)
            current_row = [cell]

    rows.append(current_row)

    # Now sort each row by x coordinate
    for i, row in enumerate(rows):
        rows[i] = sorted(row, key=lambda b: b[0])

    return rows


# endregion FUNCTIONS

# %%
pagenum = 1
image = images[pagenum]
image = image.transpose(Image.Transpose.ROTATE_90)
if pagenum == 0:
    image = crop_image_bottom(image, perc=25)
image
# %%
img, bw = preprocess(image)

# img
## %%

vertical = get_vertical_lines(bw, sensitivity=30)
horizontal = get_horizontal_lines(bw, sensitivity=30)

table_lines = combine_lines(vertical, horizontal)

cells = find_cells(table_lines)
len(cells)

# %%
# %%
WHITE = (255, 255, 255)
BLUE = (0, 0, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
# %%
# Draw detected boxes
for i, (x, y, w, h) in enumerate(cells):
    if i == 0:
        continue
    img = cv2.rectangle(np.array(img), (x, y), (x + w, y + h), BLUE, 2)
table = Image.fromarray(img)
table
# %%
# for i in range(10, 20):
cellnum = -1
x, y, w, h = cells[cellnum]
padding = 5
top_left = (x + padding, y + padding)
bottom_right = (x + w - padding, y + h - padding)
img_cell = cv2.rectangle(np.array(img), top_left, bottom_right, RED, 2)
Image.fromarray(img_cell)
# %%
# img_cell = np.array(img)
# for ndx in [1, 2, -1, -2, -3, -16, -17]:
#     x,  y, w, h = cells[ndx]
#     padding = 0
#     top_left = (x+padding, y+padding)
#     bottom_right = (x+w-padding, y+h-padding)
#     print(top_left, bottom_right)
#     img_cell = cv2.rectangle(img_cell, top_left, bottom_right, RED, 2)
# Image.fromarray(img_cell)
# # %%
# x,  y, w, h = cells[-1]
# _,  _, w1, _ = cells[-16]
# x = x + w1
# padding = 0
# top_left = (x+padding, y+padding)
# bottom_right = (x+w-padding, y+h-padding)
# print(top_left, bottom_right)
# img_cell = cv2.rectangle(img_cell, top_left, bottom_right, GREEN, 2)
# Image.fromarray(img_cell)
# %%
top_left, bottom_right
# %%
signature_area = table.crop((*top_left, *bottom_right))
gray = cv2.cvtColor(np.array(signature_area), cv2.COLOR_BGR2GRAY)
_, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
ink_pixels = cv2.countNonZero(thresh)
has_signature = ink_pixels > 500  # tune threshold
has_signature
# %%
signature_area

# %%
import pytesseract
from PIL import Image


def auto_rotate(image):
    osd = pytesseract.image_to_osd(image)

    rotation = int([x for x in osd.split() if x.isdigit()][0])  # 0, 90, 180, 270

    return image.rotate(-rotation, expand=True)


imager = auto_rotate(image)
imager
# %%
image == imager
# %%
COLUMNS = [
    "N",
    "NAMES",
    "ADDRESS",
    "EGN",
    "N_PACK_1",
    "N_PACK_2",
    "N_PACK_3",
    "IS_FORIGNER",
    "FORGIGNER",
    "ROM",
    "OTHER",
    "HOMELESS_1",
    "HOMELESS_2",
    "DATE",
    "SIGNATURE",
    "NOTE",
]
len(COLUMNS)
# %%
cells
# %%
cells = cells[-16:]
len(cells)
# %%
for i, (x, y, w, h) in enumerate(cells):
    # if i == 0:
    #     continue
    img = cv2.rectangle(np.array(img), (x, y), (x + w, y + h), BLUE, 2)
table = Image.fromarray(img)
table
# %%
# %%
cells.sort(key=lambda c: c[0])
cells
# %%

# %%
x, y, w, h = cells[-1]
imgr = cv2.rectangle(np.array(img), (x, y), (x + w, y + h), RED, 2)
table = Image.fromarray(imgr)
# %%
abs(cells[0][1] - cells[-1][1])
# %%
cells.pop(0)
# %%
abs(cells[0][1] - cells[-1][1])
# %%
avg_w = [0] * 16
avg_x = [0] * 16

for row in range(0, 15):
    print(f"ROW {row}")
    row = [cells[i] for i in range(row * 16, 16 + row * 16)]
    row = list(sorted(row, key=lambda c: c[0]))
    for col, cell in enumerate(row):
        if avg_w[col] == 0:
            avg_w[col] = cell[2]
        if avg_x[col] == 0:
            avg_x[col] = cell[0]
        print(cell)
        avg_w[col] = (avg_w[col] + cell[2]) / 2
        avg_x[col] = (avg_x[col] + cell[0]) / 2

print("w", [round(x) for x in avg_w])
print("x", [round(x) for x in avg_x])
# %%
for i, name in enumerate(
    [
        "N",
        "NAMES",
        "ADDRESS",
        "EGN",
        "N_PACK_1",
        "N_PACK_2",
        "N_PACK_3",
        "IS_FORIGNER",
        "FORGIGNER",
        "ROM",
        "OTHER",
        "HOMELESS_1",
        "HOMELESS_2",
        "DATE",
        "SIGNATURE",
        "NOTE",
    ]
):
    print(name, "=", i)
# %%
from dataclasses import dataclass, asdict, astuple


@dataclass
class ResultRow:
    number: int
    name: str
    address: str
    egn: str
    has_date: bool
    has_signature: bool
    has_note: bool
    pdf: str
    page: int


result_row = ResultRow(
    number=1,
    name="John Doe",
    address="123 Main St",
    egn="1234567890",
    has_date=True,
    has_signature=False,
    has_note=True,
    pdf="sample.pdf",
    page=0,
)
result_row
# %%

asdict(result_row)
astuple(result_row)
# %%
