from __future__ import annotations

import argparse
import posixpath
import re
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

from lxml import etree


SCRIPT_DIR = Path(__file__).resolve().parent
P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PR_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
NS = {"p": P_NS, "a": A_NS, "r": R_NS, "pr": PR_NS}
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="source pptx path, e.g. pptx/nicam_all.pptx")
    parser.add_argument("--output", required=True, help="output selected pptx path")
    parser.add_argument("--dates-output", required=True, help="output txt path for selected dates")
    return parser.parse_args()


def resolve_path(path_str: str) -> Path:
    path = Path(path_str)
    return path if path.is_absolute() else (SCRIPT_DIR / path).resolve()


def format_date_text(date_text: str) -> str:
    return datetime.strptime(date_text, "%Y-%m-%d").strftime("%d%b%Y")


def parse_xml(xml_bytes: bytes) -> etree._Element:
    return etree.fromstring(xml_bytes)


def ppt_rel_target_to_partname(target: str) -> str:
    target_path = Path(target)
    if target_path.is_absolute():
        return target_path.as_posix().lstrip("/")
    return (Path("ppt") / target_path).as_posix()


def rels_part_for(partname: str) -> str:
    path = Path(partname)
    return (path.parent / "_rels" / f"{path.name}.rels").as_posix()


def resolve_relationship_target(base_partname: str | None, target: str) -> str:
    if target.startswith("/"):
        return target.lstrip("/")
    if base_partname is None:
        return posixpath.normpath(target)
    base_dir = posixpath.dirname(base_partname)
    return posixpath.normpath(posixpath.join(base_dir, target))


def find_selected_shape(slide_root: etree._Element) -> etree._Element | None:
    for shape in slide_root.xpath(".//p:sp", namespaces=NS):
        texts = [t.text.strip() for t in shape.xpath(".//a:t", namespaces=NS) if t.text and t.text.strip()]
        if texts and texts[0].lower() == "selected":
            return shape
    return None


def find_date_text(slide_root: etree._Element) -> str:
    for shape in slide_root.xpath(".//p:sp", namespaces=NS):
        lines = [t.text.strip() for t in shape.xpath(".//a:t", namespaces=NS) if t.text and t.text.strip()]
        if len(lines) >= 2 and DATE_RE.match(lines[1]):
            return lines[1]
    raise ValueError("date text box not found")


def update_selected_index(slide_root: etree._Element, idx: int) -> None:
    shape = find_selected_shape(slide_root)
    if shape is None:
        return

    paragraphs = shape.xpath("./p:txBody/a:p", namespaces=NS)
    if not paragraphs:
        raise ValueError("selected text box paragraphs not found")

    if len(paragraphs) == 1:
        new_paragraph = etree.SubElement(paragraphs[0].getparent(), f"{{{A_NS}}}p")
        run = etree.SubElement(new_paragraph, f"{{{A_NS}}}r")
        etree.SubElement(run, f"{{{A_NS}}}t")
        paragraphs.append(new_paragraph)

    number_paragraph = paragraphs[1]
    runs = number_paragraph.xpath("./a:r", namespaces=NS)
    if not runs:
        run = etree.SubElement(number_paragraph, f"{{{A_NS}}}r")
        etree.SubElement(run, f"{{{A_NS}}}t")
        runs = [run]

    text_node = runs[0].find(f"{{{A_NS}}}t")
    if text_node is None:
        text_node = etree.SubElement(runs[0], f"{{{A_NS}}}t")
    text_node.text = str(idx)

    for extra_run in runs[1:]:
        number_paragraph.remove(extra_run)


def build_selected_slides(
    zin: zipfile.ZipFile,
    presentation_root: etree._Element,
    presentation_rels_root: etree._Element,
) -> tuple[dict[str, etree._Element], set[str], list[str]]:
    rels_by_id = {
        rel.get("Id"): rel
        for rel in presentation_rels_root.xpath("./pr:Relationship", namespaces=NS)
        if rel.get("Type", "").endswith("/slide")
    }

    selected_slide_parts: dict[str, etree._Element] = {}
    selected_rel_ids: set[str] = set()
    dates: list[str] = []

    for sld_id in presentation_root.xpath("./p:sldIdLst/p:sldId", namespaces=NS):
        rel_id = sld_id.get(f"{{{R_NS}}}id")
        rel = rels_by_id[rel_id]
        slide_partname = ppt_rel_target_to_partname(rel.get("Target"))
        slide_root = parse_xml(zin.read(slide_partname))

        if find_selected_shape(slide_root) is None:
            continue

        selected_idx = len(selected_slide_parts) + 1
        update_selected_index(slide_root, selected_idx)
        dates.append(f"{selected_idx} {format_date_text(find_date_text(slide_root))}")
        selected_slide_parts[slide_partname] = slide_root
        selected_rel_ids.add(rel_id)

    return selected_slide_parts, selected_rel_ids, dates


def filter_presentation(
    presentation_root: etree._Element,
    presentation_rels_root: etree._Element,
    selected_rel_ids: set[str],
) -> None:
    sld_id_lst = presentation_root.xpath("./p:sldIdLst", namespaces=NS)[0]
    for sld_id in list(sld_id_lst):
        rel_id = sld_id.get(f"{{{R_NS}}}id")
        if rel_id not in selected_rel_ids:
            sld_id_lst.remove(sld_id)

    for rel in list(presentation_rels_root):
        rel_id = rel.get("Id")
        rel_type = rel.get("Type", "")
        if rel_type.endswith("/slide") and rel_id not in selected_rel_ids:
            presentation_rels_root.remove(rel)


def update_app_slides_count(app_root: etree._Element, count: int) -> None:
    slides = app_root.find(".//{http://schemas.openxmlformats.org/officeDocument/2006/extended-properties}Slides")
    if slides is not None:
        slides.text = str(count)


def compute_reachable_parts(zin: zipfile.ZipFile) -> set[str]:
    reachable = {"[Content_Types].xml", "_rels/.rels"}
    pending: list[str | None] = [None]

    while pending:
        owner = pending.pop()
        rels_name = "_rels/.rels" if owner is None else rels_part_for(owner)
        if rels_name not in zin.namelist():
            continue

        if rels_name not in reachable:
            reachable.add(rels_name)

        rels_root = parse_xml(zin.read(rels_name))
        for rel in rels_root.xpath("./pr:Relationship", namespaces=NS):
            target_mode = rel.get("TargetMode")
            if target_mode == "External":
                continue
            target_part = resolve_relationship_target(owner, rel.get("Target"))
            if target_part in reachable:
                continue
            reachable.add(target_part)
            pending.append(target_part)

    return reachable


def prune_content_types(content_types_root: etree._Element, kept_parts: set[str]) -> None:
    for override in list(
        content_types_root.findall("{http://schemas.openxmlformats.org/package/2006/content-types}Override")
    ):
        part_name = override.get("PartName", "").lstrip("/")
        if part_name and part_name not in kept_parts:
            content_types_root.remove(override)


def main() -> None:
    args = parse_args()
    input_path = resolve_path(args.input)
    output = resolve_path(args.output)
    dates_output = resolve_path(args.dates_output)

    with zipfile.ZipFile(input_path) as zin:
        presentation_root = parse_xml(zin.read("ppt/presentation.xml"))
        presentation_rels_root = parse_xml(zin.read("ppt/_rels/presentation.xml.rels"))
        selected_slide_parts, selected_rel_ids, dates = build_selected_slides(zin, presentation_root, presentation_rels_root)
        filter_presentation(presentation_root, presentation_rels_root, selected_rel_ids)

        app_root = parse_xml(zin.read("docProps/app.xml"))
        update_app_slides_count(app_root, len(selected_slide_parts))
        content_types_root = parse_xml(zin.read("[Content_Types].xml"))

        rewritten_parts = {
            "ppt/presentation.xml": etree.tostring(
                presentation_root,
                xml_declaration=True,
                encoding="UTF-8",
                standalone="yes",
            ),
            "ppt/_rels/presentation.xml.rels": etree.tostring(
                presentation_rels_root,
                xml_declaration=True,
                encoding="UTF-8",
                standalone="yes",
            ),
            "docProps/app.xml": etree.tostring(app_root, xml_declaration=True, encoding="UTF-8", standalone="yes"),
        }
        rewritten_parts.update(
            {
                slide_partname: etree.tostring(slide_root, xml_declaration=True, encoding="UTF-8", standalone="yes")
                for slide_partname, slide_root in selected_slide_parts.items()
            }
        )

        output.parent.mkdir(parents=True, exist_ok=True)
        dates_output.parent.mkdir(parents=True, exist_ok=True)

        temp_package = {info.filename: zin.read(info.filename) for info in zin.infolist()}
        temp_package.update(rewritten_parts)
        temp_package["[Content_Types].xml"] = zin.read("[Content_Types].xml")

        with tempfile.NamedTemporaryFile(suffix=".pptx", delete=False, dir=output.parent) as tmp_file:
            temp_zip_path = Path(tmp_file.name)

        with zipfile.ZipFile(temp_zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zout:
            for name, data in temp_package.items():
                zout.writestr(name, data)

        with zipfile.ZipFile(temp_zip_path) as ztmp:
            reachable_parts = compute_reachable_parts(ztmp)

        prune_content_types(content_types_root, reachable_parts)
        reachable_parts.add("[Content_Types].xml")
        rewritten_parts["[Content_Types].xml"] = etree.tostring(
            content_types_root,
            xml_declaration=True,
            encoding="UTF-8",
            standalone="yes",
        )
        temp_package.update(rewritten_parts)

        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as zout:
            for name, data in temp_package.items():
                if name not in reachable_parts:
                    continue
                zout.writestr(name, data)

        temp_zip_path.unlink(missing_ok=True)

    dates_output.write_text("\n".join(dates) + ("\n" if dates else ""), encoding="utf-8")


if __name__ == "__main__":
    main()
