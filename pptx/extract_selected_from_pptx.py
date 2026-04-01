from __future__ import annotations

import argparse
import io
from datetime import datetime
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE_TYPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Emu


SELECTED_FILL = RGBColor(0xFF, 0xE6, 0x50)
SELECTED_LINE = RGBColor(0xC8, 0x1E, 0x1E)
SELECTED_TEXT = RGBColor(0xB4, 0x14, 0x14)
SELECTED_FONT_SIZE = Emu(254000)
MARGIN_X = Emu(91440)
MARGIN_Y = Emu(45720)
SCRIPT_DIR = Path(__file__).resolve().parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="source pptx path, e.g. pptx/nicam_first10.pptx")
    parser.add_argument("--output", required=True, help="output selected pptx path")
    parser.add_argument("--dates-output", required=True, help="output txt path for selected dates")
    return parser.parse_args()


def resolve_path(path_str: str) -> Path:
    path = Path(path_str)
    return path if path.is_absolute() else (SCRIPT_DIR / path).resolve()


def is_selected_shape(shape) -> bool:
    return hasattr(shape, "text") and shape.text.strip().lower().startswith("selected")


def find_selected_shape(slide):
    for shape in slide.shapes:
        if is_selected_shape(shape):
            return shape
    return None


def find_date_text(slide) -> str:
    for shape in slide.shapes:
        if not hasattr(shape, "text_frame") or shape.text_frame is None:
            continue
        lines = [p.text.strip() for p in shape.text_frame.paragraphs if p.text.strip()]
        if len(lines) >= 2 and lines[1][:4].isdigit():
            return lines[1]
    raise ValueError("date text box not found")


def format_date_text(date_text: str) -> str:
    return datetime.strptime(date_text, "%Y-%m-%d").strftime("%d%b%Y")


def copy_picture(dst_slide, shape) -> None:
    blob = io.BytesIO(shape.image.blob)
    dst_slide.shapes.add_picture(blob, shape.left, shape.top, width=shape.width, height=shape.height)


def copy_textbox(dst_slide, shape) -> None:
    box = dst_slide.shapes.add_textbox(shape.left, shape.top, shape.width, shape.height)
    box.fill.solid() if shape.fill.type == 1 else box.fill.background()
    if shape.fill.type == 1:
        box.fill.fore_color.rgb = shape.fill.fore_color.rgb
    if shape.line.width:
        box.line.width = shape.line.width
        if shape.line.color and shape.line.color.rgb:
            box.line.color.rgb = shape.line.color.rgb
    else:
        box.line.fill.background()

    src_tf = shape.text_frame
    dst_tf = box.text_frame
    dst_tf.clear()
    dst_tf.margin_left = src_tf.margin_left
    dst_tf.margin_right = src_tf.margin_right
    dst_tf.margin_top = src_tf.margin_top
    dst_tf.margin_bottom = src_tf.margin_bottom
    dst_tf.word_wrap = src_tf.word_wrap

    for idx, src_p in enumerate(src_tf.paragraphs):
        dst_p = dst_tf.paragraphs[0] if idx == 0 else dst_tf.add_paragraph()
        dst_p.alignment = src_p.alignment
        for src_r in src_p.runs:
            dst_r = dst_p.add_run()
            dst_r.text = src_r.text
            if src_r.font.size:
                dst_r.font.size = src_r.font.size
            dst_r.font.bold = src_r.font.bold
            dst_r.font.italic = src_r.font.italic
            dst_r.font.name = src_r.font.name
            try:
                if src_r.font.color.rgb:
                    dst_r.font.color.rgb = src_r.font.color.rgb
            except Exception:
                pass


def restyle_selected_box(shape, idx: int) -> None:
    existing_colors: list[RGBColor | None] = []
    for paragraph in shape.text_frame.paragraphs:
        color = None
        for run in paragraph.runs:
            try:
                if run.font.color.rgb:
                    color = run.font.color.rgb
                    break
            except Exception:
                pass
        existing_colors.append(color)

    shape.fill.solid()
    shape.fill.fore_color.rgb = SELECTED_FILL
    shape.line.color.rgb = SELECTED_LINE
    shape.line.width = Emu(38100)

    tf = shape.text_frame
    tf.clear()
    tf.margin_left = MARGIN_X
    tf.margin_right = MARGIN_X
    tf.margin_top = MARGIN_Y
    tf.margin_bottom = MARGIN_Y
    tf.word_wrap = True

    p1 = tf.paragraphs[0]
    p1.alignment = PP_ALIGN.CENTER
    r1 = p1.add_run()
    r1.text = "Selected"
    r1.font.size = SELECTED_FONT_SIZE
    r1.font.bold = True
    r1.font.color.rgb = existing_colors[0] or SELECTED_TEXT

    p2 = tf.add_paragraph()
    p2.alignment = PP_ALIGN.CENTER
    r2 = p2.add_run()
    r2.text = str(idx)
    r2.font.size = SELECTED_FONT_SIZE
    r2.font.bold = True
    r2.font.color.rgb = (existing_colors[1] if len(existing_colors) > 1 else None) or SELECTED_TEXT


def main() -> None:
    args = parse_args()
    src = Presentation(str(resolve_path(args.input)))
    dst = Presentation()
    dst.slide_width = src.slide_width
    dst.slide_height = src.slide_height

    dates: list[str] = []
    selected_idx = 0

    for slide in src.slides:
        if find_selected_shape(slide) is None:
            continue

        selected_idx += 1
        dates.append(f"{selected_idx} {format_date_text(find_date_text(slide))}")
        new_slide = dst.slides.add_slide(dst.slide_layouts[6])

        for shape in slide.shapes:
            if shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
                copy_picture(new_slide, shape)
            elif hasattr(shape, "text_frame") and shape.text_frame is not None:
                copy_textbox(new_slide, shape)

        new_selected = find_selected_shape(new_slide)
        if new_selected is not None:
            restyle_selected_box(new_selected, selected_idx)

    output = resolve_path(args.output)
    dates_output = resolve_path(args.dates_output)
    output.parent.mkdir(parents=True, exist_ok=True)
    dates_output.parent.mkdir(parents=True, exist_ok=True)
    dst.save(str(output))
    dates_output.write_text("\n".join(dates) + ("\n" if dates else ""), encoding="utf-8")


if __name__ == "__main__":
    main()
