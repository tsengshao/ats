from __future__ import annotations

import argparse
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from lxml import etree
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.oxml.xmlchemy import OxmlElement
from pptx.util import Emu, Inches


SLIDE_W_IN = 13.333
SLIDE_H_IN = 7.5
INFO_FONT_SIZE = 355600
SELECTED_FONT_SIZE = 254000
MARGIN_X = Emu(91440)
MARGIN_Y = Emu(45720)
SCRIPT_DIR = Path(__file__).resolve().parent
TEMPLATE_PATH = SCRIPT_DIR / "test.pptx"
FFMPEG_PATH = Path(shutil.which("ffmpeg") or "/Users/shao/miniforge3/envs/vapor/bin/ffmpeg")
P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS = {"p": P_NS, "a": A_NS, "r": R_NS}


@dataclass(frozen=True)
class BoxLayout:
    left: int
    top: int
    width: int
    height: int


@dataclass(frozen=True)
class TemplateLayout:
    rain: BoxLayout
    ivt: BoxLayout
    skewt: BoxLayout
    info: BoxLayout
    selected: BoxLayout
    movie: BoxLayout
    movie_src_rect: dict[str, str]


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


def date_key_to_compact_text(day_key: str) -> str:
    return datetime.strptime(day_key, "%Y%m%d").strftime("%d%b%Y")


def find_image(folder: Path, pattern: str, day_key: str) -> Path:
    matches = sorted(folder.glob(pattern.format(day=day_key)))
    if not matches:
        raise FileNotFoundError(f"missing image in {folder} for {day_key}")
    return matches[0]


def find_movie(mode_dir: Path, day_key: str) -> Path | None:
    movie_path = mode_dir / "rain_hr" / f"{date_key_to_compact_text(day_key)}.mp4"
    return movie_path if movie_path.exists() else None


def extract_movie_first_frame(movie_path: Path, poster_dir: Path) -> Path:
    poster_dir.mkdir(parents=True, exist_ok=True)
    poster_path = poster_dir / f"{movie_path.stem}.png"
    if poster_path.exists():
        return poster_path
    if not FFMPEG_PATH.exists():
        raise FileNotFoundError(f"ffmpeg not found: {FFMPEG_PATH}")

    subprocess.run(
        [
            str(FFMPEG_PATH),
            "-y",
            "-i",
            str(movie_path),
            "-vf",
            "select=eq(n\\,0)",
            "-frames:v",
            "1",
            str(poster_path),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return poster_path


def parse_rain_metadata(image_path: Path) -> tuple[str, str, int]:
    _, day_key, event_type, phase_idx = image_path.stem.split("_")
    date_text = datetime.strptime(day_key, "%Y%m%d").strftime("%Y-%m-%d")
    return date_text, event_type, int(phase_idx)


def day_key_from_rain(image_path: Path) -> str:
    return image_path.stem.split("_")[1]


def shape_box(shape) -> BoxLayout:
    return BoxLayout(int(shape.left), int(shape.top), int(shape.width), int(shape.height))


def load_template_layout() -> TemplateLayout:
    template_prs = Presentation(str(TEMPLATE_PATH))
    slide = template_prs.slides[0]
    rain, ivt, skewt, info, selected, movie = slide.shapes

    movie_pic = movie.element
    src_rect = movie_pic.xpath("./p:blipFill/a:srcRect")
    movie_src_rect = {}
    if src_rect:
        for key in ("l", "t", "r", "b"):
            value = src_rect[0].get(key)
            if value is not None:
                movie_src_rect[key] = value

    return TemplateLayout(
        rain=shape_box(rain),
        ivt=shape_box(ivt),
        skewt=shape_box(skewt),
        info=shape_box(info),
        selected=shape_box(selected),
        movie=shape_box(movie),
        movie_src_rect=movie_src_rect,
    )


def add_picture_fixed(slide, image_path: Path, layout: BoxLayout) -> None:
    slide.shapes.add_picture(
        str(image_path),
        Emu(layout.left),
        Emu(layout.top),
        width=Emu(layout.width),
        height=Emu(layout.height),
    )


def add_info_box(slide, mode_name: str, date_text: str, event_type: str, phase_idx: int, layout: BoxLayout) -> None:
    box = slide.shapes.add_textbox(Emu(layout.left), Emu(layout.top), Emu(layout.width), Emu(layout.height))
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


def add_selected_box(slide, selected_idx: int, layout: BoxLayout) -> None:
    box = slide.shapes.add_textbox(Emu(layout.left), Emu(layout.top), Emu(layout.width), Emu(layout.height))
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


def build_movie_timing(shape_id: int) -> etree._Element:
    xml = f"""
    <p:timing xmlns:p="{P_NS}">
      <p:tnLst>
        <p:par>
          <p:cTn id="1" dur="indefinite" restart="never" nodeType="tmRoot">
            <p:childTnLst>
              <p:seq concurrent="1" nextAc="seek">
                <p:cTn id="2" dur="indefinite" nodeType="mainSeq">
                  <p:childTnLst>
                    <p:par>
                      <p:cTn id="3" fill="hold">
                        <p:stCondLst>
                          <p:cond delay="indefinite"/>
                          <p:cond evt="onBegin" delay="0">
                            <p:tn val="2"/>
                          </p:cond>
                        </p:stCondLst>
                        <p:childTnLst>
                          <p:par>
                            <p:cTn id="4" fill="hold">
                              <p:stCondLst>
                                <p:cond delay="0"/>
                              </p:stCondLst>
                              <p:childTnLst>
                                <p:par>
                                  <p:cTn id="5" presetID="1" presetClass="mediacall" presetSubtype="0" fill="hold" nodeType="afterEffect">
                                    <p:stCondLst>
                                      <p:cond delay="0"/>
                                    </p:stCondLst>
                                    <p:childTnLst>
                                      <p:cmd type="call" cmd="playFrom(0.0)">
                                        <p:cBhvr>
                                          <p:cTn id="6" dur="10000" fill="hold"/>
                                          <p:tgtEl>
                                            <p:spTgt spid="{shape_id}"/>
                                          </p:tgtEl>
                                        </p:cBhvr>
                                      </p:cmd>
                                    </p:childTnLst>
                                  </p:cTn>
                                </p:par>
                              </p:childTnLst>
                            </p:cTn>
                          </p:par>
                        </p:childTnLst>
                      </p:cTn>
                    </p:par>
                  </p:childTnLst>
                </p:cTn>
                <p:prevCondLst>
                  <p:cond evt="onPrev" delay="0">
                    <p:tgtEl>
                      <p:sldTgt/>
                    </p:tgtEl>
                  </p:cond>
                </p:prevCondLst>
                <p:nextCondLst>
                  <p:cond evt="onNext" delay="0">
                    <p:tgtEl>
                      <p:sldTgt/>
                    </p:tgtEl>
                  </p:cond>
                </p:nextCondLst>
              </p:seq>
              <p:video>
                <p:cMediaNode vol="80000">
                  <p:cTn id="7" repeatCount="indefinite" fill="hold" display="0">
                    <p:stCondLst>
                      <p:cond delay="indefinite"/>
                    </p:stCondLst>
                  </p:cTn>
                  <p:tgtEl>
                    <p:spTgt spid="{shape_id}"/>
                  </p:tgtEl>
                </p:cMediaNode>
              </p:video>
              <p:seq concurrent="1" nextAc="seek">
                <p:cTn id="8" restart="whenNotActive" fill="hold" evtFilter="cancelBubble" nodeType="interactiveSeq">
                  <p:stCondLst>
                    <p:cond evt="onClick" delay="0">
                      <p:tgtEl>
                        <p:spTgt spid="{shape_id}"/>
                      </p:tgtEl>
                    </p:cond>
                  </p:stCondLst>
                  <p:endSync evt="end" delay="0">
                    <p:rtn val="all"/>
                  </p:endSync>
                  <p:childTnLst>
                    <p:par>
                      <p:cTn id="9" fill="hold">
                        <p:stCondLst>
                          <p:cond delay="0"/>
                        </p:stCondLst>
                        <p:childTnLst>
                          <p:par>
                            <p:cTn id="10" fill="hold">
                              <p:stCondLst>
                                <p:cond delay="0"/>
                              </p:stCondLst>
                              <p:childTnLst>
                                <p:par>
                                  <p:cTn id="11" presetID="2" presetClass="mediacall" presetSubtype="0" fill="hold" nodeType="clickEffect">
                                    <p:stCondLst>
                                      <p:cond delay="0"/>
                                    </p:stCondLst>
                                    <p:childTnLst>
                                      <p:cmd type="call" cmd="togglePause">
                                        <p:cBhvr>
                                          <p:cTn id="12" dur="1" fill="hold"/>
                                          <p:tgtEl>
                                            <p:spTgt spid="{shape_id}"/>
                                          </p:tgtEl>
                                        </p:cBhvr>
                                      </p:cmd>
                                    </p:childTnLst>
                                  </p:cTn>
                                </p:par>
                              </p:childTnLst>
                            </p:cTn>
                          </p:par>
                        </p:childTnLst>
                      </p:cTn>
                    </p:par>
                  </p:childTnLst>
                  <p:nextCondLst>
                    <p:cond evt="onClick" delay="0">
                      <p:tgtEl>
                        <p:spTgt spid="{shape_id}"/>
                      </p:tgtEl>
                    </p:cond>
                  </p:nextCondLst>
                </p:cTn>
              </p:seq>
            </p:childTnLst>
          </p:cTn>
        </p:par>
      </p:tnLst>
    </p:timing>
    """
    return etree.fromstring(xml.encode("utf-8"))


def configure_movie_shape(slide, movie_shape, movie_name: str, src_rect: dict[str, str]) -> None:
    movie_pic = movie_shape.element
    c_nv_pr = movie_pic.xpath("./p:nvPicPr/p:cNvPr")[0]
    c_nv_pr.set("name", movie_name)

    blip_fill = movie_pic.xpath("./p:blipFill")[0]
    existing = blip_fill.xpath("./a:srcRect")
    if existing:
        src_rect_el = existing[0]
        for key, value in src_rect.items():
            src_rect_el.set(key, value)
    elif src_rect:
        src_rect_el = OxmlElement("a:srcRect")
        for key, value in src_rect.items():
            src_rect_el.set(key, value)
        stretch = blip_fill.xpath("./a:stretch")[0]
        blip_fill.insert(blip_fill.index(stretch), src_rect_el)

    slide_el = slide.element
    existing_timing = slide_el.xpath("./p:timing")
    new_timing = build_movie_timing(movie_shape.shape_id)
    if existing_timing:
        slide_el.replace(existing_timing[0], new_timing)
    else:
        slide_el.append(new_timing)


def add_movie_fixed(slide, movie_path: Path, poster_frame_image: Path, layout: BoxLayout, src_rect: dict[str, str]) -> None:
    movie_shape = slide.shapes.add_movie(
        str(movie_path),
        Emu(layout.left),
        Emu(layout.top),
        Emu(layout.width),
        Emu(layout.height),
        poster_frame_image=str(poster_frame_image),
        mime_type="video/mp4",
    )
    configure_movie_shape(slide, movie_shape, movie_path.stem, src_rect)


def is_selected(images: dict[str, Path | None]) -> bool:
    _, event_type, phase_idx = parse_rain_metadata(images["rain"])
    return event_type == "other" and phase_idx == 1


def add_day_slide(
    prs: Presentation,
    mode_name: str,
    images: dict[str, Path | None],
    selected_idx: int | None,
    template: TemplateLayout,
    poster_dir: Path,
) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_picture_fixed(slide, images["rain"], template.rain)
    add_picture_fixed(slide, images["ivt"], template.ivt)
    add_picture_fixed(slide, images["skewt"], template.skewt)
    date_text, event_type, phase_idx = parse_rain_metadata(images["rain"])
    add_info_box(slide, mode_name, date_text, event_type, phase_idx, template.info)
    if selected_idx is not None:
        add_selected_box(slide, selected_idx, template.selected)
    if images["rain_hr"] is not None:
        add_movie_fixed(
            slide,
            images["rain_hr"],
            extract_movie_first_frame(images["rain_hr"], poster_dir),
            template.movie,
            template.movie_src_rect,
        )


def collect_day_assets(mode_dir: Path, day_key: str) -> dict[str, Path | None]:
    return {
        "rain": find_image(mode_dir / "rain", "imerg_{day}_*.png", day_key),
        "ivt": find_image(mode_dir / "ivt", "ivt_{day}_*.png", day_key),
        "skewt": find_image(mode_dir / "skewt", f"skewt_{mode_dir.name}_{{day}}_*.png", day_key),
        "rain_hr": find_movie(mode_dir, day_key),
    }


def collect_days(mode_dir: Path, start_day: datetime, days: int) -> list[dict[str, Path | None]]:
    items = []
    for offset in range(days):
        day = start_day + timedelta(days=offset)
        items.append(collect_day_assets(mode_dir, date_to_key(day)))
    return items


def summarize_movies(slides: list[dict[str, Path | None]]) -> tuple[list[str], list[str]]:
    with_movies: list[str] = []
    without_movies: list[str] = []
    for images in slides:
        date_text = date_key_to_compact_text(day_key_from_rain(images["rain"]))
        if images["rain_hr"] is not None:
            with_movies.append(date_text)
        else:
            without_movies.append(date_text)
    return with_movies, without_movies


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


def collect_selected_days(mode_dir: Path, selected_dates_path: Path) -> list[tuple[dict[str, Path | None], int]]:
    items: list[tuple[dict[str, Path | None], int]] = []
    for day_key, selected_idx in parse_selected_dates(selected_dates_path):
        items.append((collect_day_assets(mode_dir, day_key), selected_idx))
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
    template = load_template_layout()

    prs = Presentation()
    prs.slide_width = Inches(SLIDE_W_IN)
    prs.slide_height = Inches(SLIDE_H_IN)

    with tempfile.TemporaryDirectory(prefix="daily_pptx_posters_") as temp_dir:
        poster_dir = Path(temp_dir)
        slide_items: list[dict[str, Path | None]] = []
        if args.selected_dates:
            selected_dates_path = resolve_path(args.selected_dates)
            selected_days = collect_selected_days(mode_dir, selected_dates_path)
            slide_items = [images for images, _ in selected_days]
            for images, selected_idx in selected_days:
                add_day_slide(prs, mode_dir.name, images, selected_idx, template, poster_dir)
        else:
            start_day = datetime.strptime(args.start, "%Y-%m-%d")
            selected_map = selected_index_map(mode_dir)
            slide_items = collect_days(mode_dir, start_day, args.days)
            for images in slide_items:
                if args.selected_only and not is_selected(images):
                    continue
                selected_idx = selected_map.get(day_key_from_rain(images["rain"]))
                add_day_slide(prs, mode_dir.name, images, selected_idx, template, poster_dir)

        output.parent.mkdir(parents=True, exist_ok=True)
        prs.save(str(output))
        with_movies, without_movies = summarize_movies(slide_items)
        print(f"movie slides: {len(with_movies)}")
        # if with_movies:
        #     print("with movie:", ", ".join(with_movies))
        # if without_movies:
        #     print("without movie:", ", ".join(without_movies))


if __name__ == "__main__":
    main()
