from __future__ import annotations

import argparse
from datetime import datetime, timedelta
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Emu, Inches


SLIDE_W_IN = 13.333
SLIDE_H_IN = 7.5
PICTURE_LAYOUT = {
    "rain": (2152712, 7619, 4924475, 3628621),
    "ivt": (6477000, 7619, 4922701, 3628621),
    "skewt": (1681299, 3681960, 9355001, 3137940),
}
INFO_BOX = (157298, 45719, 1995413, 2246769)
INFO_FONT_SIZE = 355600
SELECTED_BOX = (247887, 2974074, 1433412, 707886)
SELECTED_FONT_SIZE = 254000
MARGIN_X = Emu(91440)
MARGIN_Y = Emu(45720)
SCRIPT_DIR = Path(__file__).resolve().parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True, help="mode folder, e.g. fig/nicam")
    parser.add_argument("--start", help="start date, YYYY-MM-DD")
    parser.add_argument("--days", type=int, help="number of days")
    parser.add_argument(
        "--selected-dates",
        help="txt path like *_selected_date.txt; each line may be '1 03Jun2020' or '03Jun2020'",
    )
    parser.add_argument("--output", required=True, help="output pptx path, e.g. pptx/nicam_first10.pptx")
    parser.add_argument(
        "--selected-only",
        action="store_true",
        help="only output selected slides, identified by other_1 filenames",
    )
    args = parser.parse_args()

    has_range = args.start is not None or args.days is not None
    has_selected_dates = args.selected_dates is not None
    if has_range and has_selected_dates:
        parser.error("use either --start/--days or --selected-dates")
    if not has_range and not has_selected_dates:
        parser.error("either --start/--days or --selected-dates is required")
    if has_range and (args.start is None or args.days is None):
        parser.error("--start and --days must be provided together")

    return args


def resolve_path(path_str: str) -> Path:
    path = Path(path_str)
    return path if path.is_absolute() else (SCRIPT_DIR / path).resolve()


def date_to_key(day: datetime) -> str:
    return day.strftime("%Y%m%d")


def selected_date_to_key(date_text: str) -> str:
    return datetime.strptime(date_text, "%d%b%Y").strftime("%Y%m%d")


def find_image(folder: Path, pattern: str, day_key: str) -> Path:
    matches = sorted(folder.glob(pattern.format(day=day_key)))
    if not matches:
        raise FileNotFoundError(f"missing image in {folder} for {day_key}")
    return matches[0]


def parse_rain_metadata(image_path: Path) -> tuple[str, str, int]:
    _, day_key, event_type, phase_idx = image_path.stem.split("_")
    date_text = datetime.strptime(day_key, "%Y%m%d").strftime("%Y-%m-%d")
    return date_text, event_type, int(phase_idx)


def day_key_from_rain(image_path: Path) -> str:
    return image_path.stem.split("_")[1]


def add_picture_fixed(slide, image_path: Path, left: int, top: int, width: int, height: int) -> None:
    slide.shapes.add_picture(
        str(image_path),
        Emu(left),
        Emu(top),
        width=Emu(width),
        height=Emu(height),
    )


def add_info_box(slide, mode_name: str, date_text: str, event_type: str, phase_idx: int) -> None:
    left, top, width, height = INFO_BOX
    box = slide.shapes.add_textbox(Emu(left), Emu(top), Emu(width), Emu(height))
    box.fill.background()
    box.line.fill.background()

    tf = box.text_frame
    tf.clear()
    tf.margin_left = MARGIN_X
    tf.margin_right = MARGIN_X
    tf.margin_top = MARGIN_Y
    tf.margin_bottom = MARGIN_Y
    tf.word_wrap = True

    p1 = tf.paragraphs[0]
    r1 = p1.add_run()
    r1.text = mode_name.upper()
    r1.font.size = Emu(INFO_FONT_SIZE)
    r1.font.bold = True

    p2 = tf.add_paragraph()
    r2 = p2.add_run()
    r2.text = date_text
    r2.font.size = Emu(INFO_FONT_SIZE)

    tf.add_paragraph()

    p4 = tf.add_paragraph()
    r4 = p4.add_run()
    r4.text = "diurnal" if phase_idx == 1 else "non-diurnal"
    r4.font.size = Emu(INFO_FONT_SIZE)

    p5 = tf.add_paragraph()
    r5 = p5.add_run()
    r5.text = event_type
    r5.font.size = Emu(INFO_FONT_SIZE)


def add_selected_box(slide, selected_idx: int) -> None:
    left, top, width, height = SELECTED_BOX
    box = slide.shapes.add_textbox(Emu(left), Emu(top), Emu(width), Emu(height))
    box.fill.solid()
    box.fill.fore_color.rgb = RGBColor(0xFF, 0xE6, 0x50)
    box.line.color.rgb = RGBColor(0xC8, 0x1E, 0x1E)
    box.line.width = Emu(38100)

    tf = box.text_frame
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
    r1.font.size = Emu(SELECTED_FONT_SIZE)
    r1.font.bold = True
    r1.font.color.rgb = RGBColor(0xB4, 0x14, 0x14)

    p2 = tf.add_paragraph()
    p2.alignment = PP_ALIGN.CENTER
    r2 = p2.add_run()
    r2.text = str(selected_idx)
    r2.font.size = Emu(SELECTED_FONT_SIZE)
    r2.font.bold = True
    r2.font.color.rgb = RGBColor(0xB4, 0x14, 0x14)


def is_selected(images: dict[str, Path]) -> bool:
    _, event_type, phase_idx = parse_rain_metadata(images["rain"])
    return event_type == "other" and phase_idx == 1


def add_day_slide(prs: Presentation, mode_name: str, images: dict[str, Path], selected_idx: int | None) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    for label, (left, top, width, height) in PICTURE_LAYOUT.items():
        add_picture_fixed(slide, images[label], left, top, width, height)
    date_text, event_type, phase_idx = parse_rain_metadata(images["rain"])
    add_info_box(slide, mode_name, date_text, event_type, phase_idx)
    if selected_idx is not None:
        add_selected_box(slide, selected_idx)


def collect_days(mode_dir: Path, start_day: datetime, days: int) -> list[dict[str, Path]]:
    items = []
    for offset in range(days):
        day = start_day + timedelta(days=offset)
        day_key = date_to_key(day)
        items.append(
            {
                "rain": find_image(mode_dir / "rain", "imerg_{day}_*.png", day_key),
                "ivt": find_image(mode_dir / "ivt", "ivt_{day}_*.png", day_key),
                "skewt": find_image(mode_dir / "skewt", f"skewt_{mode_dir.name}_{{day}}_*.png", day_key),
            }
        )
    return items


def parse_selected_dates(selected_dates_path: Path) -> list[tuple[str, int]]:
    items: list[tuple[str, int]] = []
    for line_no, raw_line in enumerate(selected_dates_path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue

        parts = line.split()
        if len(parts) == 1:
            selected_idx = len(items) + 1
            date_text = parts[0]
        elif len(parts) == 2 and parts[0].isdigit():
            selected_idx = int(parts[0])
            date_text = parts[1]
        else:
            raise ValueError(f"invalid selected date line {line_no}: {raw_line!r}")

        items.append((selected_date_to_key(date_text), selected_idx))
    return items


def collect_selected_days(mode_dir: Path, selected_dates_path: Path) -> list[tuple[dict[str, Path], int]]:
    items: list[tuple[dict[str, Path], int]] = []
    for day_key, selected_idx in parse_selected_dates(selected_dates_path):
        items.append(
            (
                {
                    "rain": find_image(mode_dir / "rain", "imerg_{day}_*.png", day_key),
                    "ivt": find_image(mode_dir / "ivt", "ivt_{day}_*.png", day_key),
                    "skewt": find_image(mode_dir / "skewt", f"skewt_{mode_dir.name}_{{day}}_*.png", day_key),
                },
                selected_idx,
            )
        )
    return items


def selected_index_map(mode_dir: Path) -> dict[str, int]:
    mapping: dict[str, int] = {}
    selected_counter = 0
    for rain_path in sorted((mode_dir / "rain").glob("imerg_*.png")):
        date_text, event_type, phase_idx = parse_rain_metadata(rain_path)
        if event_type == "other" and phase_idx == 1:
            selected_counter += 1
            mapping[datetime.strptime(date_text, "%Y-%m-%d").strftime("%Y%m%d")] = selected_counter
    return mapping


def main() -> None:
    args = parse_args()
    mode_dir = resolve_path(args.mode)
    output = resolve_path(args.output)

    prs = Presentation()
    prs.slide_width = Inches(SLIDE_W_IN)
    prs.slide_height = Inches(SLIDE_H_IN)

    if args.selected_dates:
        selected_dates_path = resolve_path(args.selected_dates)
        for images, selected_idx in collect_selected_days(mode_dir, selected_dates_path):
            add_day_slide(prs, mode_dir.name, images, selected_idx)
    else:
        start_day = datetime.strptime(args.start, "%Y-%m-%d")
        selected_map = selected_index_map(mode_dir)
        for images in collect_days(mode_dir, start_day, args.days):
            if args.selected_only and not is_selected(images):
                continue
            selected_idx = selected_map.get(day_key_from_rain(images["rain"]))
            add_day_slide(prs, mode_dir.name, images, selected_idx)

    output.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(output))


if __name__ == "__main__":
    main()
