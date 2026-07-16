from __future__ import annotations

import json
import math
import re
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import yaml
from docx import Document
from docx.enum.section import WD_ORIENT, WD_SECTION
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import (
    WD_ALIGN_PARAGRAPH,
    WD_BREAK,
    WD_LINE_SPACING,
    WD_TAB_ALIGNMENT,
)
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor


ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / "materials-private" / "02_templates" / "课设模板.docx"
REPORT_DIR = ROOT / "report"
LOAD_JSON = ROOT / "calculations" / "results" / "load_and_transformer_results.json"
SC_JSON = ROOT / "calculations" / "results" / "short_circuit" / "short_circuit_results.json"
EQUIP_JSON = (
    ROOT
    / "calculations"
    / "results"
    / "equipment_selection"
    / "equipment_selection_results.json"
)
BASELINE_YAML = ROOT / "data" / "design_baseline.yaml"
INPUTS_YAML = ROOT / "data" / "design_inputs.yaml"

TITLE = "220kV新能源汇集变电所电气一次部分初步设计"
SHORT_TITLE = "220kV新能源汇集变电所课程设计"
DATE_RANGE = "2026年7月6日—2026年7月17日"
PUBLIC_NOTE = "公开版：姓名、学号、班级及签字字段留空，提交时由学生手工填写。"
ENGINEERING_NOTE = "课程设计底稿，非施工图；工程实施前须按现行标准及厂家资料复核。"


def load_data() -> dict:
    return {
        "load": json.loads(LOAD_JSON.read_text(encoding="utf-8")),
        "sc": json.loads(SC_JSON.read_text(encoding="utf-8")),
        "equipment": json.loads(EQUIP_JSON.read_text(encoding="utf-8")),
        "baseline": yaml.safe_load(BASELINE_YAML.read_text(encoding="utf-8")),
        "inputs": yaml.safe_load(INPUTS_YAML.read_text(encoding="utf-8")),
    }


def fmt(value: float | int | None, digits: int = 3) -> str:
    if value is None:
        return "待定"
    if isinstance(value, int):
        return str(value)
    return f"{value:.{digits}f}"


def remove_all_body_content(doc: Document) -> None:
    body = doc._element.body
    for child in list(body):
        if child.tag != qn("w:sectPr"):
            body.remove(child)


def set_cell_shading(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def set_cell_margins(cell, top=90, start=110, bottom=90, end=110) -> None:
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for key, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = tc_mar.find(qn(f"w:{key}"))
        if node is None:
            node = OxmlElement(f"w:{key}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def set_cell_no_wrap(cell) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    no_wrap = tc_pr.find(qn("w:noWrap"))
    if no_wrap is None:
        no_wrap = OxmlElement("w:noWrap")
        tc_pr.append(no_wrap)
    no_wrap.set(qn("w:val"), "true")


def set_inline_shape_alt_text(inline_shape, alt_text: str) -> None:
    doc_pr = inline_shape._inline.docPr
    doc_pr.set("descr", alt_text)
    doc_pr.set("title", alt_text)


def set_repeat_table_header(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    tbl_header = OxmlElement("w:tblHeader")
    tbl_header.set(qn("w:val"), "true")
    tr_pr.append(tbl_header)


def set_row_cant_split(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    tr_pr.append(OxmlElement("w:cantSplit"))


def set_cell_width(cell, width_cm: float) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_w = tc_pr.find(qn("w:tcW"))
    if tc_w is None:
        tc_w = OxmlElement("w:tcW")
        tc_pr.append(tc_w)
    tc_w.set(qn("w:w"), str(int(Cm(width_cm).emu / 635)))
    tc_w.set(qn("w:type"), "dxa")
    cell.width = Cm(width_cm)


def set_table_width(table, widths_cm: list[float]) -> None:
    total_dxa = sum(int(Cm(w).emu / 635) for w in widths_cm)
    tbl_pr = table._tbl.tblPr
    tbl_w = tbl_pr.find(qn("w:tblW"))
    if tbl_w is None:
        tbl_w = OxmlElement("w:tblW")
        tbl_pr.append(tbl_w)
    tbl_w.set(qn("w:w"), str(total_dxa))
    tbl_w.set(qn("w:type"), "dxa")
    tbl_layout = tbl_pr.find(qn("w:tblLayout"))
    if tbl_layout is None:
        tbl_layout = OxmlElement("w:tblLayout")
        tbl_pr.append(tbl_layout)
    tbl_layout.set(qn("w:type"), "fixed")
    grid = table._tbl.tblGrid
    for child in list(grid):
        grid.remove(child)
    for width in widths_cm:
        col = OxmlElement("w:gridCol")
        col.set(qn("w:w"), str(int(Cm(width).emu / 635)))
        grid.append(col)
    for row in table.rows:
        for index, cell in enumerate(row.cells):
            set_cell_width(cell, widths_cm[index])


def add_bottom_border(paragraph, color="000000", size="8") -> None:
    p_pr = paragraph._p.get_or_add_pPr()
    p_bdr = p_pr.find(qn("w:pBdr"))
    if p_bdr is None:
        p_bdr = OxmlElement("w:pBdr")
        p_pr.append(p_bdr)
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), size)
    bottom.set(qn("w:space"), "1")
    bottom.set(qn("w:color"), color)
    p_bdr.append(bottom)


def set_east_asia_font(run, name="宋体", latin="Times New Roman", size=12, bold=None):
    run.font.name = latin
    run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    run.font.color.rgb = RGBColor(0, 0, 0)
    r_pr = run._element.get_or_add_rPr()
    r_fonts = r_pr.rFonts
    if r_fonts is None:
        r_fonts = OxmlElement("w:rFonts")
        r_pr.insert(0, r_fonts)
    r_fonts.set(qn("w:ascii"), latin)
    r_fonts.set(qn("w:hAnsi"), latin)
    r_fonts.set(qn("w:eastAsia"), name)
    r_fonts.set(qn("w:cs"), latin)
    return run


def style_document(doc: Document) -> None:
    settings = doc.settings._element
    mirror_margins = settings.find(qn("w:mirrorMargins"))
    if mirror_margins is not None:
        settings.remove(mirror_margins)

    styles = doc.styles
    normal = styles["Normal"]
    normal.font.name = "Times New Roman"
    normal.font.size = Pt(12)
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")
    pf = normal.paragraph_format
    pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    pf.first_line_indent = Cm(0.74)
    pf.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
    pf.space_before = Pt(0)
    pf.space_after = Pt(0)

    for name, size, align, before, after in (
        ("Heading 1", 16, WD_ALIGN_PARAGRAPH.CENTER, 12, 8),
        ("Heading 2", 14, WD_ALIGN_PARAGRAPH.LEFT, 10, 6),
        ("Heading 3", 12, WD_ALIGN_PARAGRAPH.LEFT, 8, 4),
    ):
        st = styles[name]
        st.font.name = "Times New Roman"
        st.font.size = Pt(size)
        st.font.bold = True
        st.font.color.rgb = RGBColor(0, 0, 0)
        st._element.rPr.rFonts.set(qn("w:eastAsia"), "黑体")
        st.paragraph_format.alignment = align
        st.paragraph_format.first_line_indent = Cm(0)
        st.paragraph_format.left_indent = Cm(0)
        st.paragraph_format.right_indent = Cm(0)
        st.paragraph_format.space_before = Pt(before)
        st.paragraph_format.space_after = Pt(after)
        st.paragraph_format.keep_with_next = True
        st.paragraph_format.keep_together = True
    styles["Heading 1"].paragraph_format.page_break_before = None

    caption = styles["Caption"]
    caption.font.name = "Times New Roman"
    caption.font.size = Pt(10.5)
    caption.font.color.rgb = RGBColor(0, 0, 0)
    caption._element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")
    caption.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    caption.paragraph_format.first_line_indent = Cm(0)
    caption.paragraph_format.space_before = Pt(4)
    caption.paragraph_format.space_after = Pt(6)
    caption.paragraph_format.keep_with_next = True

    for name, size, left in (("toc 1", 10.5, 0.0), ("toc 2", 10.0, 0.65), ("toc 3", 9.5, 1.3)):
        try:
            toc_style = styles[name]
        except KeyError:
            continue
        toc_style.font.name = "Times New Roman"
        toc_style.font.size = Pt(size)
        toc_style.font.color.rgb = RGBColor(0, 0, 0)
        toc_style._element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")
        toc_style.paragraph_format.left_indent = Cm(left)
        toc_style.paragraph_format.first_line_indent = Cm(0)
        toc_style.paragraph_format.space_before = Pt(0)
        toc_style.paragraph_format.space_after = Pt(0)
        toc_style.paragraph_format.line_spacing = 1.0

    for section in doc.sections:
        set_section_geometry(section)


def set_section_geometry(section) -> None:
    section.orientation = WD_ORIENT.PORTRAIT
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(3.0)
    section.bottom_margin = Cm(2.5)
    section.left_margin = Cm(3.0)
    section.right_margin = Cm(2.5)
    section.header_distance = Cm(1.5)
    section.footer_distance = Cm(1.5)


def add_page_field(paragraph) -> None:
    run = paragraph.add_run()
    fld_char1 = OxmlElement("w:fldChar")
    fld_char1.set(qn("w:fldCharType"), "begin")
    instr_text = OxmlElement("w:instrText")
    instr_text.set(qn("xml:space"), "preserve")
    instr_text.text = " PAGE "
    fld_char2 = OxmlElement("w:fldChar")
    fld_char2.set(qn("w:fldCharType"), "end")
    run._r.extend([fld_char1, instr_text, fld_char2])


def set_page_number_start(section, value: int = 1) -> None:
    sect_pr = section._sectPr
    pg_num_type = sect_pr.find(qn("w:pgNumType"))
    if pg_num_type is None:
        pg_num_type = OxmlElement("w:pgNumType")
        sect_pr.append(pg_num_type)
    pg_num_type.set(qn("w:start"), str(value))


def add_update_fields_setting(doc: Document) -> None:
    settings = doc.settings._element
    update = settings.find(qn("w:updateFields"))
    if update is None:
        update = OxmlElement("w:updateFields")
        settings.append(update)
    update.set(qn("w:val"), "true")


def configure_front_section(section) -> None:
    set_section_geometry(section)
    section.header.is_linked_to_previous = False
    section.footer.is_linked_to_previous = False
    for p in section.header.paragraphs:
        p.clear()
    for p in section.footer.paragraphs:
        p.clear()


def configure_main_section(section, running_title: str) -> None:
    set_section_geometry(section)
    section.header.is_linked_to_previous = False
    section.footer.is_linked_to_previous = False
    header = section.header
    hp = header.paragraphs[0]
    hp.clear()
    hp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_east_asia_font(hp.add_run(running_title), name="宋体", size=9)
    add_bottom_border(hp, size="6")
    footer = section.footer
    fp = footer.paragraphs[0]
    fp.clear()
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_page_field(fp)
    for run in fp.runs:
        set_east_asia_font(run, name="宋体", size=9)
    set_page_number_start(section, 1)


def compact_break_paragraph(paragraph) -> None:
    paragraph.paragraph_format.first_line_indent = Cm(0)
    paragraph.paragraph_format.space_before = Pt(0)
    paragraph.paragraph_format.space_after = Pt(0)
    paragraph.paragraph_format.line_spacing = Pt(1)
    paragraph.paragraph_format.line_spacing_rule = WD_LINE_SPACING.EXACTLY
    p_pr = paragraph._p.get_or_add_pPr()
    snap_to_grid = p_pr.find(qn("w:snapToGrid"))
    if snap_to_grid is None:
        snap_to_grid = OxmlElement("w:snapToGrid")
        p_pr.append(snap_to_grid)
    snap_to_grid.set(qn("w:val"), "0")
    widow_control = p_pr.find(qn("w:widowControl"))
    if widow_control is None:
        widow_control = OxmlElement("w:widowControl")
        p_pr.append(widow_control)
    widow_control.set(qn("w:val"), "0")


def start_main_section(doc: Document, running_title: str):
    section = doc.add_section(WD_SECTION.NEW_PAGE)
    compact_break_paragraph(doc.paragraphs[-1])
    configure_main_section(section, running_title)
    return section


def add_toc(doc: Document, levels="1-3") -> None:
    heading = doc.add_paragraph()
    heading.alignment = WD_ALIGN_PARAGRAPH.CENTER
    heading.paragraph_format.first_line_indent = Cm(0)
    heading.paragraph_format.space_after = Pt(12)
    set_east_asia_font(heading.add_run("目 录"), name="黑体", size=16, bold=True)
    p = doc.add_paragraph()
    compact_break_paragraph(p)
    run = p.add_run()
    fld_char = OxmlElement("w:fldChar")
    fld_char.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = f' TOC \\o "{levels}" \\h \\z \\u '
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    placeholder = OxmlElement("w:t")
    placeholder.text = "目录将在 Microsoft Word 中自动更新。"
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.extend([fld_char, instr, separate, placeholder, end])


def logo_bytes() -> tuple[bytes, bytes]:
    with ZipFile(TEMPLATE) as archive:
        return archive.read("word/media/image1.png"), archive.read("word/media/image2.png")


def add_cover(doc: Document, document_type: str) -> None:
    logo, calligraphy = logo_bytes()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(2)
    logo_shape = p.add_run().add_picture(BytesIO(logo), width=Cm(2.6))
    set_inline_shape_alt_text(logo_shape, "学校校徽")
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(16)
    calligraphy_shape = p.add_run().add_picture(BytesIO(calligraphy), width=Cm(8.5))
    set_inline_shape_alt_text(calligraphy_shape, "学校名称书法标识")
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(8)
    set_east_asia_font(p.add_run("《发电厂电气部分》课程设计"), name="黑体", size=22, bold=True)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(7)
    set_east_asia_font(p.add_run(TITLE), name="黑体", size=18, bold=True)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(18)
    set_east_asia_font(p.add_run(document_type), name="黑体", size=20, bold=True)

    labels = [
        ("学    院", "电气与信息工程学院"),
        ("专    业", "电气工程及其自动化"),
        ("班    级", ""),
        ("姓    名", ""),
        ("学    号", ""),
        ("同组设计者", ""),
        ("指导教师", ""),
        ("任务起止日期", DATE_RANGE),
    ]
    table = doc.add_table(rows=len(labels), cols=2)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    set_table_width(table, [4.0, 9.2])
    for row, (label, value) in zip(table.rows, labels):
        row.cells[0].vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        row.cells[1].vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        p0 = row.cells[0].paragraphs[0]
        p0.alignment = WD_ALIGN_PARAGRAPH.DISTRIBUTE
        p0.paragraph_format.first_line_indent = Cm(0)
        p0.paragraph_format.line_spacing = 1.0
        p0.paragraph_format.space_before = Pt(0)
        p0.paragraph_format.space_after = Pt(0)
        set_east_asia_font(p0.add_run(label), name="宋体", size=12)
        p1 = row.cells[1].paragraphs[0]
        p1.paragraph_format.first_line_indent = Cm(0)
        p1.paragraph_format.line_spacing = 1.0
        p1.paragraph_format.space_before = Pt(0)
        p1.paragraph_format.space_after = Pt(0)
        set_east_asia_font(p1.add_run(value if value else "____________________________"), name="宋体", size=12)
        for cell in row.cells:
            set_cell_margins(cell, top=70, bottom=70)
            tc_pr = cell._tc.get_or_add_tcPr()
            borders = tc_pr.find(qn("w:tcBorders"))
            if borders is None:
                borders = OxmlElement("w:tcBorders")
                tc_pr.append(borders)
            for edge in ("top", "left", "right", "insideH", "insideV"):
                el = OxmlElement(f"w:{edge}")
                el.set(qn("w:val"), "nil")
                borders.append(el)
            bottom = OxmlElement("w:bottom")
            bottom.set(qn("w:val"), "single" if cell is row.cells[1] else "nil")
            bottom.set(qn("w:sz"), "4")
            bottom.set(qn("w:color"), "000000")
            borders.append(bottom)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(10)
    set_east_asia_font(p.add_run(PUBLIC_NOTE), name="宋体", size=9)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_east_asia_font(p.add_run(ENGINEERING_NOTE), name="宋体", size=9)


def set_page_break_before(paragraph, enabled: bool) -> None:
    """Write an explicit OOXML value so Word cannot inherit the style setting."""
    p_pr = paragraph._p.get_or_add_pPr()
    page_break = p_pr.find(qn("w:pageBreakBefore"))
    if page_break is None:
        page_break = OxmlElement("w:pageBreakBefore")
        p_pr.append(page_break)
    page_break.set(qn("w:val"), "1" if enabled else "0")


def add_heading(
    doc: Document,
    text: str,
    level: int = 1,
    *,
    page_break_before: bool | None = None,
):
    paragraph = doc.add_paragraph(text, style=f"Heading {level}")
    if page_break_before is not None:
        set_page_break_before(paragraph, page_break_before)
    elif level == 1:
        set_page_break_before(paragraph, True)
    return paragraph


def add_body(doc: Document, text: str, *, bold_lead: str | None = None):
    p = doc.add_paragraph()
    if bold_lead and text.startswith(bold_lead):
        set_east_asia_font(p.add_run(bold_lead), name="宋体", size=12, bold=True)
        text = text[len(bold_lead) :]
    set_east_asia_font(p.add_run(text), name="宋体", size=12)
    return p


def get_list_num_id(doc: Document, ordered: bool) -> int:
    cache_name = "_course_ordered_num_id" if ordered else "_course_bullet_num_id"
    cached = getattr(doc, cache_name, None)
    if cached is not None:
        return cached
    numbering = doc.part.numbering_part.element
    abstract_ids = [
        int(node.get(qn("w:abstractNumId")))
        for node in numbering.findall(qn("w:abstractNum"))
        if node.get(qn("w:abstractNumId")) is not None
    ]
    num_ids = [
        int(node.get(qn("w:numId")))
        for node in numbering.findall(qn("w:num"))
        if node.get(qn("w:numId")) is not None
    ]
    abstract_id = max(abstract_ids, default=0) + 1
    num_id = max(num_ids, default=0) + 1
    abstract = OxmlElement("w:abstractNum")
    abstract.set(qn("w:abstractNumId"), str(abstract_id))
    multi = OxmlElement("w:multiLevelType")
    multi.set(qn("w:val"), "singleLevel")
    abstract.append(multi)
    lvl = OxmlElement("w:lvl")
    lvl.set(qn("w:ilvl"), "0")
    start = OxmlElement("w:start")
    start.set(qn("w:val"), "1")
    lvl.append(start)
    num_fmt = OxmlElement("w:numFmt")
    num_fmt.set(qn("w:val"), "decimal" if ordered else "bullet")
    lvl.append(num_fmt)
    lvl_text = OxmlElement("w:lvlText")
    lvl_text.set(qn("w:val"), "%1." if ordered else "•")
    lvl.append(lvl_text)
    lvl_jc = OxmlElement("w:lvlJc")
    lvl_jc.set(qn("w:val"), "left")
    lvl.append(lvl_jc)
    p_pr = OxmlElement("w:pPr")
    tabs = OxmlElement("w:tabs")
    tab = OxmlElement("w:tab")
    tab.set(qn("w:val"), "num")
    tab.set(qn("w:pos"), "420")
    tabs.append(tab)
    p_pr.append(tabs)
    ind = OxmlElement("w:ind")
    ind.set(qn("w:left"), "720")
    ind.set(qn("w:hanging"), "300")
    p_pr.append(ind)
    lvl.append(p_pr)
    abstract.append(lvl)
    numbering.append(abstract)
    num = OxmlElement("w:num")
    num.set(qn("w:numId"), str(num_id))
    abs_ref = OxmlElement("w:abstractNumId")
    abs_ref.set(qn("w:val"), str(abstract_id))
    num.append(abs_ref)
    numbering.append(num)
    setattr(doc, cache_name, num_id)
    return num_id


def add_bullets(
    doc: Document,
    items: list[str],
    ordered: bool = False,
    *,
    keep_together: bool = False,
) -> None:
    num_id = get_list_num_id(doc, ordered)
    for item in items:
        p = doc.add_paragraph(style="List Paragraph")
        p.paragraph_format.first_line_indent = Cm(0)
        p.paragraph_format.left_indent = Cm(0.74)
        p.paragraph_format.keep_together = keep_together
        p_pr = p._p.get_or_add_pPr()
        num_pr = OxmlElement("w:numPr")
        ilvl = OxmlElement("w:ilvl")
        ilvl.set(qn("w:val"), "0")
        num = OxmlElement("w:numId")
        num.set(qn("w:val"), str(num_id))
        num_pr.extend([ilvl, num])
        p_pr.append(num_pr)
        set_east_asia_font(p.add_run(item), name="宋体", size=11.5)


def add_equation(
    doc: Document,
    expression: str,
    number: str | None = None,
    *,
    compact: bool = False,
) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.first_line_indent = Cm(0)
    p.paragraph_format.space_before = Pt(1 if compact else 4)
    p.paragraph_format.space_after = Pt(1 if compact else 4)
    if number:
        p.paragraph_format.tab_stops.add_tab_stop(Cm(15.5), WD_TAB_ALIGNMENT.RIGHT)
    run = p.add_run(expression)
    set_east_asia_font(run, name="Cambria Math", latin="Cambria Math", size=11.0 if compact else 11.5)
    if number:
        p.add_run("\t")
        set_east_asia_font(p.add_run(f"({number})"), name="宋体", size=10.5)


def add_table(
    doc: Document,
    caption: str,
    headers: list[str],
    rows: list[list[object]],
    widths_cm: list[float] | None = None,
    font_size: float = 9.5,
    note: str | None = None,
    nowrap_header_columns: set[int] | None = None,
    nowrap_body_columns: set[int] | None = None,
    margin_x: int = 110,
    margin_y: int = 90,
    keep_note_with_table: bool = False,
) -> None:
    nowrap_header_columns = nowrap_header_columns or set()
    nowrap_body_columns = nowrap_body_columns or set()
    cap = doc.add_paragraph(caption, style="Caption")
    cap.paragraph_format.keep_with_next = True
    table = doc.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    table.style = "Table Grid"
    if widths_cm is None:
        widths_cm = [15.5 / len(headers)] * len(headers)
    if abs(sum(widths_cm) - 15.5) > 0.2:
        scale = 15.5 / sum(widths_cm)
        widths_cm = [w * scale for w in widths_cm]
    set_table_width(table, widths_cm)
    header = table.rows[0]
    set_repeat_table_header(header)
    set_row_cant_split(header)
    for index, value in enumerate(headers):
        cell = header.cells[index]
        if index in nowrap_header_columns:
            set_cell_no_wrap(cell)
        set_cell_shading(cell, "D9E2F3")
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.first_line_indent = Cm(0)
        p.paragraph_format.line_spacing = 1.0
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(0)
        set_east_asia_font(p.add_run(str(value)), name="黑体", size=font_size, bold=True)
        set_cell_margins(cell, top=margin_y, bottom=margin_y, start=margin_x, end=margin_x)
    for row_values in rows:
        row = table.add_row()
        set_row_cant_split(row)
        for index, value in enumerate(row_values):
            cell = row.cells[index]
            if index in nowrap_body_columns:
                set_cell_no_wrap(cell)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            p = cell.paragraphs[0]
            p.paragraph_format.first_line_indent = Cm(0)
            p.paragraph_format.line_spacing = 1.0
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(0)
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER if index > 0 else WD_ALIGN_PARAGRAPH.LEFT
            set_east_asia_font(p.add_run(str(value)), name="宋体", size=font_size)
            set_cell_margins(cell, top=margin_y, bottom=margin_y, start=margin_x, end=margin_x)
    if note:
        if keep_note_with_table:
            for cell in table.rows[-1].cells:
                for paragraph in cell.paragraphs:
                    paragraph.paragraph_format.keep_with_next = True
        p = doc.add_paragraph()
        p.paragraph_format.first_line_indent = Cm(0)
        p.paragraph_format.space_before = Pt(3)
        p.paragraph_format.keep_together = True
        set_east_asia_font(p.add_run(f"注：{note}"), name="宋体", size=9)


def add_figure(doc: Document, path: Path, caption: str, width_cm: float = 15.5) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.first_line_indent = Cm(0)
    p.paragraph_format.keep_with_next = True
    figure_shape = p.add_run().add_picture(str(path), width=Cm(width_cm))
    set_inline_shape_alt_text(figure_shape, caption)
    cap = doc.add_paragraph(caption, style="Caption")
    cap.paragraph_format.keep_with_next = False
    cap.paragraph_format.keep_together = True


def add_optional_figure(
    doc: Document,
    path: Path,
    caption: str,
    *,
    missing_message: str,
    width_cm: float = 15.5,
) -> None:
    if path.exists():
        add_figure(doc, path, caption, width_cm=width_cm)
        return
    add_note_box(doc, "图纸待集成", missing_message)


def add_note_box(doc: Document, title: str, text: str) -> None:
    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    set_table_width(table, [15.5])
    set_row_cant_split(table.rows[0])
    cell = table.cell(0, 0)
    set_cell_shading(cell, "F2F2F2")
    set_cell_margins(cell, top=140, bottom=140, start=160, end=160)
    p = cell.paragraphs[0]
    p.paragraph_format.first_line_indent = Cm(0)
    p.paragraph_format.line_spacing = 1.15
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(0)
    set_east_asia_font(p.add_run(f"{title}："), name="黑体", size=10.5, bold=True)
    set_east_asia_font(p.add_run(text), name="宋体", size=10.5)


def add_references(doc: Document, references: list[str]) -> None:
    add_heading(doc, "参考文献", 1)
    for index, item in enumerate(references, 1):
        p = doc.add_paragraph()
        p.paragraph_format.first_line_indent = Cm(-0.74)
        p.paragraph_format.left_indent = Cm(0.74)
        p.paragraph_format.line_spacing = 1.25
        p.paragraph_format.keep_together = True
        set_east_asia_font(p.add_run(f"[{index}] {item}"), name="宋体", size=10.0)


REFERENCES = [
    "苗世洪等. 发电厂电气部分（第五版）[M]. 北京: 中国电力出版社, 2015.",
    "西北电力设计院. 电力工程电气设计手册: 电气一次部分[M]. 北京: 中国电力出版社.",
    "GB/T 15544.1-2023 三相交流系统短路电流计算 第1部分: 电流计算.",
    "DL/T 5222-2021 导体和电器选择设计规程.",
    "DL/T 5352-2018 高压配电装置设计规范.",
    "GB 50060-2008 3~110kV高压配电装置设计规范.",
    "GB/T 3906-2020 3.6kV~40.5kV交流金属封闭开关设备和控制设备.",
    "GB/T 1984-2024 高压交流断路器.",
    "GB/T 1985-2023 高压交流隔离开关和接地开关.",
    "GB/T 20840.1-2010 互感器 第1部分: 通用技术要求.",
    "GB/T 50064-2014 交流电气装置的过电压保护和绝缘配合设计规范.",
    "GB/T 50065-2011 交流电气装置的接地设计规范.",
]


def new_document(document_type: str) -> Document:
    doc = Document(TEMPLATE)
    remove_all_body_content(doc)
    style_document(doc)
    section = doc.sections[0]
    configure_front_section(section)
    add_cover(doc, document_type)
    return doc


def build_design_description(data: dict) -> Path:
    load = data["load"]
    sc = data["sc"]
    baseline = data["baseline"]
    doc = new_document("技术设计说明书")

    front = doc.add_section(WD_SECTION.NEW_PAGE)
    configure_front_section(front)
    add_heading(doc, "摘  要", 1, page_break_before=False)
    add_body(
        doc,
        "本课程设计面向一座220kV新能源汇集变电所，完成220/35/10/0.4kV电气一次部分初步设计。"
        "在任务书给定的系统容量、线路、负荷和自然条件基础上，采用单母线分段的220kV主接线，"
        "35kV和10kV均采用单母线两分段，0.4kV采用单母线分段暗备用。配置2×180MVA、220/35kV、"
        "YNd11、uk=14%的主变，2×31.5MVA、35/10.5kV、YNd11、uk=8%的T10，2×±12Mvar SVG，"
        "以及2×200kVA、SCB14、Dyn11、uk=4%的所用变。"
        "计算得到35kV汇集计算容量280.286MVA，主变正常负载率77.857%；主变N-1时需限发35.780%。"
        "课程短路模型下10kV条件性最大综合短路电流为15.638kA，禁止并列敏感性为28.472kA。"
        "设备按额定电压、持续电流、开断、峰值和1.10s热稳定进行等级预筛，并补齐CT/PT、零序CT、母线、"
        "绝缘子/套管、MOA、接地变+低电阻和接地开关的课程配置。35/10kV母联转供时仅保留健康侧1套接地源。"
        "CAD按三张必交图加一张L1线路间隔增强详图组织。",
    )
    p = doc.add_paragraph()
    p.paragraph_format.first_line_indent = Cm(0)
    set_east_asia_font(p.add_run("关键词："), name="黑体", size=12, bold=True)
    set_east_asia_font(
        p.add_run("新能源汇集变电所；电气主接线；主变压器；短路电流；设备选择；配电装置"),
        name="宋体",
        size=11.5,
    )
    doc.add_page_break()
    add_toc(doc)

    main_sec = start_main_section(doc, SHORT_TITLE + "—技术设计说明书")

    add_heading(doc, "第一章 电气主接线设计", 1, page_break_before=False)
    add_heading(doc, "1.1 原始资料与设计范围", 2)
    add_body(
        doc,
        "设计对象为第5组220kV新能源汇集变电所。本站通过12回35kV集电线路汇集风电、光伏和储能电能，"
        "经两台220/35kV主变升压后由两回220kV线路送出，并预留第三回线路。10kV系统承担站用备用电源、"
        "无功补偿、冷却和集控通信等辅助负荷，0.4kV系统向站内低压负荷供电。",
    )
    add_table(
        doc,
        "表1-1 主要原始资料",
        ["项目", "任务书或冻结值", "设计处理"],
        [
            ["电压等级", "220/35/10/0.4kV", "覆盖一次主接线、辅助系统和所用电"],
            ["主变压器", "2×180MVA、YNd11、uk=14%", "220/35kV双绕组、油浸、户外、有载调压"],
            ["220kV线路", "2回在运、1回预留；LGJ-400/50", "向西北出线；N-1校核温度修正载流量"],
            ["35kV集电线路", "12回在运、2回预留", "WA/WB共7回架空并设入口MOA；PVA/PVB/ES共5回电缆并设ZCT"],
            ["10kV电源变", "2×31.5MVA、YNd11、uk=8%", "35/10.5kV，分别供10kV-I/II段"],
            ["所用变", "2×200kVA、SCB14、Dyn11、uk=4%", "10/0.4kV，轮换暗备用"],
            ["系统等值", "S1=2400MVA，xc1=0.40；S2=2000MVA，xc2=0.45", "换算至100MVA基准"],
            ["220kV线路长度", "L1=70km，L2=85km，L3=60km", "L3不参加本期基准计算"],
            ["自然条件", "最高41℃，最低-12℃，平均15℃", "设备和导体环境校核"],
            ["场址补充假设", "海拔≤1000m，污秽d级", "课程假设；真实工程须替换"],
        ],
        [3.2, 6.4, 5.9],
        9.3,
    )
    add_note_box(
        doc,
        "设计边界",
        "计算、设备等级和CAD几何用于课程设计闭环。精确设备型号、厂家41℃服务条件、完整标准短路模型、"
        "CT/PT/ZCT完整负荷与暂态参数、35/10kV母线机械、MOA能量/TOV、接地源厂家联锁、避雷针保护范围和"
        "接地网接触/跨步电压不在本次课程底稿中冒充已完成。",
    )

    add_heading(doc, "1.2 主接线设计原则", 2)
    principles_paragraph = add_body(
        doc,
        "主接线应满足安全可靠、运行灵活、检修方便、经济合理和便于扩建等要求。本站以新能源集中送出为主，"
        "正常运行时尽量保持各电源分列，事故转供前先隔离故障源，避免通过母联形成未经许可的系统并列。",
    )
    principles_paragraph.paragraph_format.keep_together = True
    add_bullets(
        doc,
        [
            "220kV侧应适应两回本期线路、两台主变和一回远期预留线路。",
            "35kV侧应把同一场站回路分散到两段母线，并为两台T10和预留回路留出间隔。",
            "10kV侧应保证两套SVG和重要辅助负荷分段供电，禁止两台健康T10长期并列。",
            "0.4kV所用电采用两台所用变暗备用，任一台应能承担全部经常负荷。",
        ],
    )

    add_heading(doc, "1.3 220kV主接线方案比较", 2)
    add_table(
        doc,
        "表1-2 220kV候选方案技术比较",
        ["方案", "主要优点", "主要不足", "结论"],
        [
            ["内桥接线", "断路器数量少，初投资低", "远期第三回线路扩建困难；运行灵活性较差", "仅作比较"],
            ["单母线分段", "接线清晰、经济；母线故障限制在一段；预留扩建方便", "一段检修时该段线路和主变退出", "采用"],
            ["双母线不带旁路", "检修灵活、供电可靠、扩建方便", "隔离开关多、占地及投资高、倒闸复杂", "可靠性要求提高时升级"],
        ],
        [3.0, 4.8, 4.8, 2.9],
        9.2,
    )
    scheme_conclusion = add_body(
        doc,
        "综合本期回路数、课程图纸表达和经济性，220kV采用单母线分段。L1、T1接I段，L2、T2接II段，"
        "L3按远期预留间隔设置。分段断路器正常断开；只有调度许可且同期检查通过后才允许条件闭合。",
    )
    scheme_conclusion.paragraph_format.keep_together = True

    add_heading(doc, "1.4 35kV、10kV与0.4kV接线", 2)
    add_table(
        doc,
        "表1-3 各电压等级接线与正常状态",
        ["电压等级", "接线方式", "正常分段/母联状态", "运行要点"],
        [
            ["220kV", "单母线分段", "断开", "系统1、系统2分列；条件闭合须调度许可和同期"],
            ["35kV", "单母线两分段", "断开", "两台主变各带一段；事故转供前隔离故障主变"],
            ["10kV", "单母线两分段", "断开", "两台T10各带一段；健康T10禁止并列"],
            ["0.4kV", "单母线分段", "闭合", "正常仅一台所用变运行，另一台暗备用"],
        ],
        [2.4, 4.0, 3.1, 6.0],
        9.3,
    )
    add_table(
        doc,
        "表1-4 35kV馈线分配",
        ["母线段", "本期馈线", "有功容量/MW", "附加间隔"],
        [
            ["35kV-I", "WA-1、WA-2、WB-1、WB-2（架空）；PVA-1、PVB-1（电缆）", "130", "T10-1-HV；预留1回"],
            ["35kV-II", "WA-3、WA-4、WB-3（架空）；PVA-2、PVB-2、ES-1（电缆）", "140", "T10-2-HV；预留1回"],
        ],
        [2.6, 7.2, 2.4, 3.3],
        9.2,
    )
    add_figure(
        doc,
        ROOT / "drawings" / "exports" / "single_line_a1.png",
        "图1-1 SLD-01 220kV新能源汇集变电所电气主接线简图（A1，NTS，课程设计底图）",
    )

    add_heading(doc, "1.5 正常、条件与禁止运行方式", 2, page_break_before=True)
    add_table(
        doc,
        "表1-5 运行方式门控",
        ["类别", "运行方式", "处理原则"],
        [
            ["允许", "220/35/10kV分段分列；0.4kV单台所用变带两段", "正常运行基准"],
            ["条件允许", "220kV分段闭合", "调度许可并同期检查后方可闭合"],
            ["事故转供", "一台主变或一台T10退出后闭合下一级母联", "先隔离故障源；退出受电段接地源，仅保留健康侧1套"],
            ["禁止", "两台健康主变经35kV母联并列", "仅保留短路敏感性，不作为运行方式"],
            ["禁止", "两台健康T10经10kV母联并列", "联锁闭锁；避免短路电流显著上升"],
            ["禁止", "35/10kV母联闭合且两套接地源同时投入", "低电阻并联会改变接地故障电流与保护配合"],
            ["禁止", "两台所用变经0.4kV并列", "两进线与母联设置电气、机械联锁"],
        ],
        [2.2, 6.1, 7.2],
        9.2,
    )

    add_heading(doc, "第二章 负荷计算及变压器选择", 1)
    add_heading(doc, "2.1 35kV与10kV综合负荷", 2)
    add_body(
        doc,
        "35kV新能源负荷按各项视在功率求和，再计0.95最大同时出力系数和5%线损；单回馈线电流按各类"
        "最大负荷在回路间平均分配，不重复乘同时系数。10kV辅助负荷按0.80同时系数和5%线损计算。",
    )
    add_equation(doc, "Sᵢ = Pᵢ / cosφᵢ", "2-1")
    add_equation(doc, "I = S / (√3 U)", "2-2")
    add_table(
        doc,
        "表2-1 综合负荷计算结果",
        ["项目", "结果", "说明"],
        [
            ["35kV原始视在功率", "280.988MVA", "270MW按逐项功率因数折算"],
            ["计0.95同时出力", "266.939MVA", "主变容量计算用"],
            ["再计5%线损", "280.286MVA", "本期主变校核容量"],
            ["10kV辅助负荷", "1.757MVA", "计0.80同时系数和5%线损"],
            ["保守叠加10kV敏感性", "282.043MVA", "不替代主校核口径"],
        ],
        [5.0, 3.6, 6.9],
        9.5,
    )

    add_heading(doc, "2.2 主变压器选择", 2)
    add_body(
        doc,
        "选用2×180MVA、220/35kV双绕组油浸式有载调压主变，联结组YNd11，短路电压uk=14%。"
        "220kV星形中性点经专用中性点CT直接接地，35kV侧为三角形绕组。两台正常运行时"
        "每台承担140.143MVA，负载率77.857%。一台退出时，另一台额定容量只能覆盖64.220%的最大计算负荷，"
        "缺口100.286MVA，因此按任务书允许的新能源限发策略，基准限发比例为35.780%。",
    )
    add_table(
        doc,
        "表2-2 主变容量与N-1校验",
        ["指标", "计算值", "结论"],
        [
            ["装机容量", "360.000MVA", "2×180MVA"],
            ["正常每台负荷", "140.143MVA", "均衡分配"],
            ["正常负载率", "77.857%", "满足课程设计经济运行要求"],
            ["N-1覆盖比例", "64.220%", "低于全部最大负荷"],
            ["N-1容量缺口", "100.286MVA", "通过新能源限发处理"],
            ["N-1限发比例", "35.780%", "当前总N-1控制因素"],
        ],
        [5.0, 4.0, 6.5],
        9.5,
    )

    add_heading(doc, "2.3 10kV电源变与无功补偿", 2)
    add_body(
        doc,
        "10kV由2×31.5MVA、35/10.5kV、YNd11、uk=8%的T10供电，每段配置±12Mvar SVG。"
        "按目标功率因数0.98，需补偿21.8875Mvar；选24Mvar后裕度9.65%，pf≈0.98147。"
        "T10正常负载率39.58%，N-1最严吸收工况79.17%。",
    )
    add_table(
        doc,
        "表2-3 T10与SVG配置",
        ["设备", "配置", "正常状态", "校验结论"],
        [
            ["T10-1、T10-2", "2×31.5MVA，35/10.5kV，YNd11，uk=8%", "各带一段10kV母线", "N-1最严79.17%"],
            ["SVG-1、SVG-2", "2×±12Mvar", "每段一套，电压/无功/功率因数控制", "补偿后pf≈0.98147"],
        ],
        [3.1, 5.2, 4.0, 3.2],
        9.2,
        "容量属于任务书缺项下的课程冻结值，最终由无功电压与谐波专题覆盖。",
    )

    add_heading(doc, "2.4 所用变压器选择", 2)
    station_service_paragraph = add_body(
        doc,
        "扣除110kV不适用项后，连续负荷96.3kW，最严场景需192.913kVA。"
        "选用2×200kVA、10/0.4kV、SCB14干式、Dyn11、uk=4%的所用变，每台可带全部经常负荷并留约10%裕度。"
        "正常一台供电且0.4kV母联闭合，另一台及进线暗备用。",
    )
    station_service_paragraph.paragraph_format.keep_together = True

    add_heading(doc, "第三章 最大持续工作电流及短路计算", 1)
    add_heading(doc, "3.1 各回路最大持续工作电流", 2)
    feeder_rows = []
    for item in load["load_35kv"]["items"]:
        feeder_rows.append(
            [
                item["label_zh"],
                item["circuits"],
                f'{item["per_circuit_current_a"]:.3f}',
                "计5%线损，不乘0.95",
            ]
        )
    add_table(
        doc,
        "表3-1 35kV单回馈线设计电流",
        ["负荷类别", "回路数", "单回电流/A", "计算口径"],
        feeder_rows,
        [4.2, 2.2, 3.4, 5.7],
        9.5,
    )
    add_table(
        doc,
        "表3-2 主要回路持续电流职责",
        ["回路", "最大持续电流/A", "设计说明"],
        [
            ["220kV线路间隔", "735.559", "一回退出时另一回承担全部本期送出"],
            ["220kV分段", "735.559", "一段事故转供全部本期送出功率的课程保守职责"],
            ["主变220kV侧", "495.996", "180MVA额定电流×1.05"],
            ["主变35kV侧/35kV母联", "3117.691", "180MVA额定电流×1.05"],
            ["35kV-I段", "2230.732", "按I段实际6回馈线累加"],
            ["35kV-II段", "2404.371", "按II段实际6回馈线累加"],
            ["T10 35kV侧", "545.596", "31.5MVA额定电流×1.05"],
            ["T10 10kV设备口径", "1909.586", "按10kV开关设备电压基准×1.05"],
            ["单套SVG馈线", "692.820", "12Mvar、10.5kV额定电流×1.05"],
        ],
        [5.0, 3.7, 6.8],
        9.2,
    )

    add_heading(doc, "3.2 220kV线路导线校核与N-1", 2)
    conductor_paragraph = add_body(
        doc,
        "LGJ-400/50课程参考载流量为592A（25℃环境、70℃导体）。41℃修正系数0.802773，课程允许值"
        "475.242A；正常每回367.780A通过。单回全送735.559A时需限发35.390%；主变N-1限发后线路电流"
        "472.377A，余量2.864A，因此当前仍由主变容量控制。",
    )
    conductor_paragraph.paragraph_format.keep_together = True
    add_note_box(
        doc,
        "证据边界",
        "592A来自旧版二手课程参数表，仅作保守校核；厂家热额定值须结合风速、日照、环境及导体温度复核。",
    )

    add_heading(doc, "3.3 短路计算方法与计算点", 2)
    add_body(
        doc,
        "短路初算采用任务书规定的100MVA基准容量和230/37/10.5kV平均额定电压。网络按标幺电抗法处理，"
        "初步忽略电阻；主变电抗按uk=14%，T10按uk=8%。新能源和SVG贡献在敏感性中按额定电流1.1~1.2倍"
        "算术叠加，峰值采用课程系数k=1.8。该方法用于课程设备等级预筛，不替代GB/T 15544.1-2023完整计算。",
    )
    add_equation(doc, "X*sys = xc × SB / Ssys", "3-1", compact=True)
    add_equation(doc, "X*line = xL × SB / UB²", "3-2", compact=True)
    add_equation(doc, "X*T = (uk% / 100) × SB / SN", "3-3", compact=True)
    add_equation(doc, "Ik = SB / (√3 UB XΣ*)", "3-4", compact=True)
    add_equation(doc, "ip = √2 k Ik", "3-5", compact=True)
    add_table(
        doc,
        "表3-3 短路职责分级（禁止并列值仅作联锁与误操作风险提示）",
        ["电压级", "正常必选/kA", "条件预校核/kA", "禁并敏感/kA", "课程峰值/kA"],
        [
            ["220kV", "4.033", "7.385", "—", "18.798"],
            ["35kV", "13.265", "16.291", "25.694", "41.470"],
            ["10kV", "14.492", "15.638", "28.472", "39.808"],
        ],
        [2.2, 3.3, 3.5, 3.4, 3.1],
        8.4,
        margin_x=75,
        margin_y=50,
    )

    add_heading(doc, "第四章 主要电气设备选择", 1)
    add_heading(doc, "4.1 选择与校验原则", 2)
    add_body(
        doc,
        "一次设备按额定电压、最大持续工作电流、短路开断、关合/峰值耐受和热稳定逐项校验。热稳定等值时间"
        "按后备保护1.00s与断路器总开断0.08s向上取1.10s。环境最高温度41℃、海拔≤1000m和污秽d级作为"
        "课程设计条件。室外主变、T10、可能的户外SVG及导体按41℃复核，35/10kV室内开关柜统一按受控≤40℃；"
        "厂家精确服务条件未取得时，设备状态只能写为额定值等级预筛通过。",
    )
    add_equation(doc, "Ue ≥ Un；Ie ≥ Imax", "4-1")
    add_equation(doc, "Ibr ≥ Ik；ipeak,rated ≥ ip", "4-2")
    add_equation(doc, "Ith² tr ≥ Ik² t", "4-3")

    add_heading(doc, "4.2 断路器、隔离开关和开关柜", 2)
    add_table(
        doc,
        "表4-1 主要开关设备课程目标等级",
        ["安装位置", "目标等级", "额定电流/A", "开断/kA", "峰值/kA", "热稳定"],
        [
            ["220kV线路/主变/分段断路器", "252kV户外SF6", "3150", "50", "125", "50kA/3s"],
            ["220kV隔离开关", "252kV户外", "3150", "—", "125", "50kA/3s"],
            ["35kV主变进线/母联柜", "40.5kV金属铠装", "3150", "31.5", "80", "31.5kA/4s"],
            ["35kV馈线/T10柜", "40.5kV金属铠装", "1250", "31.5", "80", "31.5kA/4s"],
            ["35kV接地变馈线柜", "40.5kV金属铠装", "1250", "31.5", "80", "31.5kA/4s"],
            ["10kV进线/母联柜", "12kV金属铠装", "2500", "31.5", "80", "31.5kA/4s"],
            ["10kV SVG/辅助馈线柜", "12kV金属铠装", "1250", "31.5", "80", "31.5kA/4s"],
            ["10kV接地变馈线柜", "12kV金属铠装", "1250", "31.5", "80", "31.5kA/4s"],
        ],
        [4.4, 3.2, 2.2, 2.0, 1.9, 1.8],
        8.8,
        "35kV 3150A相对3117.691A仅余32.309A（约1.04%）；10kV已升级为2500A，相对1909.586A"
        "余590.414A。接地变馈线分别覆盖400A/200A课程职责。35/10kV柜统一按室内受控≤40℃，仍须由厂家温升和精确柜型确认。",
    )

    add_table(
        doc,
        "表4-2 已审查设备的适用性结论",
        ["设备", "课程结论", "依据与复核条件"],
        [
            ["限流电抗器", "35/10kV均不设置", "16.291/15.638kA低于31.5kA设备能力；最终短路职责超过31.5kA时重审"],
            ["高压熔断器", "不作为主回路设备", "仅在35/10kV PT柜按厂家方案设置一次熔断器及二次保护"],
            ["阻波器", "当前不配置", "仅在通信专业确定电力线载波通信及耦合方案时配置"],
        ],
        [3.0, 4.0, 8.5],
        9.0,
    )

    add_heading(doc, "4.3 CT与PT/CVT课程配置", 2)
    add_body(
        doc,
        "各电压等级每段主母线配置电压互感器；凡装有断路器的回路原则上配置三相CT，电缆单相接地保护另设"
        "零序CT。下表冻结一次变比、课程芯级组合和职责，但负担、饱和、拐点电压、暂态性能、窗口尺寸、"
        "电缆压降和精确型号仍等待保护计量清册。",
    )
    add_table(
        doc,
        "表4-3 CT课程目标配置",
        ["位置", "变比", "芯级目标", "短时/峰值"],
        [
            ["220kV线路", "1000/1A", "0.2S、0.5、5P30，按需PX", "50kA/3s；125kA"],
            ["220kV主变", "600/1A", "0.2S、0.5、5P30、PX", "50kA/3s；125kA"],
            ["主变220kV中性点", "600/1A", "PX限制接地故障、5P30中性点过流", "单相接地/零序专题待定"],
            ["220kV分段", "1000/1A", "0.5、5P30母线保护、PX母差", "50kA/3s；125kA"],
            ["35kV进线/母联", "4000/1A", "0.2S、0.5、5P30、PX", "31.5kA/4s；80kA"],
            ["35kV馈线/T10", "800/1A", "0.2S、0.5、5P30", "31.5kA/4s；80kA"],
            ["10kV进线/母联", "2500/1A", "0.2S、0.5、5P30、PX", "31.5kA/4s；80kA"],
            ["10kV馈线/SVG", "1000/1A", "0.2S、0.5、5P30", "31.5kA/4s；80kA"],
            ["35kV电缆馈线ZCT", "100/1A", "5P20或厂家等效零序保护级", "5回；一次剩余电流目标400A"],
            ["10kV电缆/SVG ZCT", "50/1A", "5P20或厂家等效零序保护级", "2回SVG+3类辅助；目标200A"],
        ],
        [3.5, 2.6, 5.7, 3.7],
        8.2,
        "短时栏峰值单位为kA；ZCT职责与三相CT分开，三相电缆芯线同穿窗口而屏蔽接地回流线不得穿入。课程芯级组合不作为订货清册。",
    )
    add_table(
        doc,
        "表4-4 PT/CVT课程目标配置",
        ["电压级", "型式与一次电压", "二次绕组", "准确级"],
        [
            ["220kV", "每段单相CVT组；220/√3kV", "100/√3V测量、100/√3V保护、100/3V开口三角", "0.2、3P"],
            ["35kV", "每段三台单相电磁式VT；35/√3kV", "100/√3V测量、100/√3V保护、100/3V开口三角", "0.5、3P"],
            ["10kV", "每段三台单相电磁式VT；10/√3kV", "100/√3V测量、100/√3V保护、100/3V开口三角", "0.5、3P"],
        ],
        [2.2, 4.2, 6.7, 2.4],
        8.5,
        "容量、铁磁谐振、同期抽取和厂家精确型号仍待二次专业复核。",
    )

    add_heading(doc, "4.4 MOA、中性点接地与接地开关", 2)
    add_table(
        doc,
        "表4-5 MOA参数与绝缘裕度课程预筛",
        ["电压级/型号", "Ur/Uc/In/残压", "绝缘裕度", "配置位置"],
        [
            ["220kV YH10W-204/532", "204kV/159kV/10kA/≤532kV", "Uc余13.508kV；950/532=1.786＞1.15", "线路入口、主变高压端"],
            ["35kV YH5WZ-51/134", "51kV/40.8kV/5kA/≤134kV", "Uc仅余0.300kV（约0.74%）；185/134=1.381＞1.15", "母线PT柜、主变端、7回架空入口"],
            ["10kV YH5WZ-17/45", "17kV/13.6kV/5kA/≤45kV", "Uc余1.600kV；75/45=1.667＞1.15", "母线PT柜、T10/SVG端"],
        ],
        [3.5, 4.4, 4.6, 3.0],
        8.2,
        "仅为课程预筛；35kV的TOV、能量、引线压降、线路放电等级和精确型号待专题复核。",
        keep_note_with_table=True,
    )
    doc.add_page_break()
    add_table(
        doc,
        "表4-6 接地参数与接地开关课程配置",
        ["位置", "课程配置", "等级/参数", "工程边界"],
        [
            ["主变220kV中性点", "经600/1A中性点CT直接接地", "PX+5P30课程目标", "持续/短时/峰值按单相接地与零序专题，不沿用三相回路职责"],
            ["35kV-I/II段", "每段1000kVA ZN接地变+低电阻", "400A/10s；R≈50.5Ω", "2套；1250A馈线柜；600/1A相CT+400/1A中性点CT"],
            ["10kV-I/II段", "每段200kVA ZN接地变+低电阻", "200A/10s；R≈28.9Ω", "2套；1250A馈线柜；300/1A相CT+200/1A中性点CT"],
            ["35/10kV母联转供", "合母联前退出受电/故障段接地源", "仅保留健康侧1套", "联锁禁止母联合闸且两套接地源并联；分列后恢复每段1套"],
            ["220kV线路侧ES", "线路侧QS配常开ES", "252kV、50kA/3s、125kA峰值", "感应电流开合等级待厂家专题"],
            ["35/10kV柜内ES", "柜内常开并设机械/电气联锁", "31.5kA/4s、80kA峰值", "精确柜型和联锁图待核"],
        ],
        [3.1, 4.5, 4.2, 3.7],
        8.1,
    )
    add_note_box(
        doc,
        "防雷与接地边界",
        "MOA绝缘配合不等于直击雷保护完成。缺少雷暴日、建筑高度、土壤电阻率和接地网几何时，不虚构"
        "避雷针保护范围、接地网电阻、接触电压或跨步电压。",
    )

    add_heading(doc, "4.5 母线、绝缘子与套管", 2, page_break_before=True)
    add_body(
        doc,
        "母线型式已从原则选择推进到课程级截面和性能预筛。220kV管母完成载流、热稳、简化弯曲和电晕；"
        "35/10kV矩形母线只完成载流与热稳，电动力、支撑机械、连接金具和厂家温升仍待复核。",
    )
    add_table(
        doc,
        "表4-7 母线课程级选择",
        ["电压级", "课程选择", "持续/热稳定", "补充校验"],
        [
            ["220kV", "铝合金管母Φ100/90mm", "1605.546A＞735.559A；123.785kA＞7.385kA", "弯曲应力10.048＜70MPa；电晕330.444＞145.492kV"],
            ["35kV", "每相3×125×10mm矩形铝母线", "4194A＞3117.691A；311.067kA＞16.291kA", "机械/电动力和厂家温升待核"],
            ["10kV", "每相2×125×10mm矩形铝母线", "3282A＞1909.586A；207.378kA＞15.638kA", "机械/电动力和厂家温升待核"],
        ],
        [2.2, 4.0, 5.5, 3.8],
        8.1,
    )
    add_table(
        doc,
        "表4-8 绝缘子与套管课程目标",
        ["电压级", "最高电压/LIWV", "持续/短时/峰值课程目标", "尚需厂家数据"],
        [
            ["220kV", "252/950kV", "630A；50kA/3s；125kA", "d级；爬距、机械破坏负荷、精确型号"],
            ["35kV", "40.5/185kV", "4000A；31.5kA/4s；80kA", "户外接口d级；爬距、机械与安装图"],
            ["10kV", "12/75kV", "2500A；31.5kA/4s；80kA", "户外接口d级；爬距、机械与安装图"],
        ],
        [2.2, 3.3, 5.2, 4.8],
        8.3,
        "当前35/10kV方案无裸母线直接穿墙，独立裸母线穿墙套管不单列；方案改变时重新选择。",
    )

    add_heading(doc, "第五章 配电装置设计与运行", 1)
    add_heading(doc, "5.1 配电装置型式", 2)
    add_table(
        doc,
        "表5-1 配电装置型式选择",
        ["电压等级", "采用型式", "选择理由"],
        [
            ["220kV", "户外AIS、分相中型", "回路不多、课程断面表达清晰、扩建方便、投资低于GIS"],
            ["35kV", "室内金属铠装移开式开关柜", "回路多、分段明确、运行维护方便"],
            ["10kV", "室内金属铠装移开式开关柜", "适合T10进线、SVG和辅助负荷分柜组织"],
            ["0.4kV", "室内低压开关柜", "单母线分段、暗备用和联锁切换"],
        ],
        [2.5, 5.2, 7.8],
        9.4,
    )

    add_heading(doc, "5.2 220kV户外AIS课程几何", 2)
    add_table(
        doc,
        "表5-2 平面与断面主要参数",
        ["参数", "课程采用值", "说明"],
        [
            ["站区范围", "145m×90m", "课程总体边界"],
            ["道路宽度", "4m", "设备运输与检修通道"],
            ["相间距", "4m", "典型三相设备中心距"],
            ["典型功能中心距", "14m", "课程间隔节距"],
            ["母线标高", "9.0m", "断面课程值"],
            ["出线构架标高", "14.5m", "向西北出线"],
            ["主变构架标高", "11.5m", "主变进线构架"],
            ["母线至出线构架", "29m", "平断面一致"],
            ["母线至主变构架/中心", "20m/27m", "平断面一致"],
        ],
        [5.0, 3.5, 7.0],
        9.4,
    )
    add_table(
        doc,
        "表5-3 220kV屋外配电装置课程最小净距",
        ["类别", "采用值/mm", "含义"],
        [
            ["A1", "1800", "带电部分至接地部分"],
            ["A2", "2000", "不同相带电部分之间"],
            ["B1", "2550", "带电部分至栅栏/运输轮廓等课程控制距离"],
            ["B2", "1900", "带电部分至网状遮栏"],
            ["C", "4300", "无遮栏裸导体至地面"],
            ["D", "3800", "检修或不同时间带电部分的课程控制距离"],
        ],
        [2.6, 3.0, 9.9],
        9.4,
        "取自课程讲义表7-2的220J列；施工设计仍须按DL/T 5352-2018全文复核。",
    )
    add_heading(doc, "5.3 事故运行与联锁", 2)
    operation_paragraph = add_body(
        doc,
        "主变N-1时先切除并隔离故障主变，故障清除后闭合35kV母联，并把存活主变负荷限制在180MVA以内，"
        "按当前计算限发35.780%。一回220kV线路退出时，剩余线路也必须受LGJ-400/50温度修正载流量约束。"
        "T10或所用变切换均先隔离故障进线，再投入备用电源，严禁两个健康电源通过低压母联并列。"
        "35/10kV母联合闸前还须退出受电侧接地源，仅保留健康电源侧1套；禁止母联闭合且两套低电阻接地源并联。",
    )
    operation_paragraph.paragraph_format.keep_together = True
    add_figure(
        doc,
        ROOT / "drawings" / "exports" / "switchyard_plan_a1.png",
        "图5-1 LAY-220-01 220kV户外AIS配电装置平面布置图（A1，1:200，课程设计底图）",
    )
    add_figure(
        doc,
        ROOT / "drawings" / "exports" / "switchyard_section_a1.png",
        "图5-2 SEC-220-01 220kV户外AIS典型间隔断面图（A1，1:100，课程设计底图）",
    )
    add_optional_figure(
        doc,
        ROOT / "drawings" / "exports" / "switchyard_line_bay_detail_a1.png",
        "图5-3 SEC-220-L1-01 220kV I段L1线路间隔断面详图（A1，1:50，课程设计增强详图）",
        missing_message=(
            "预期文件drawings/exports/switchyard_line_bay_detail_a1.png尚不存在。正式再生成前必须完成第四图"
            "导出与目检，不得把本提示版作为最终提交版。"
        ),
    )

    add_heading(doc, "第六章 结论与设计边界", 1)
    add_heading(doc, "6.1 主要设计结论", 2)
    add_bullets(
        doc,
        [
            "主接线采用220kV、35kV和10kV单母线分段；220kV分段断路器、35/10kV母联正常断开，0.4kV母联正常闭合。",
            "主变采用2×180MVA、220/35kV、YNd11、uk=14%，正常负载率77.857%；N-1需限发35.780%。",
            "采用2×31.5MVA、35/10.5kV、YNd11、uk=8%的T10和2×±12Mvar SVG，补偿后功率因数约0.98147。",
            "所用变采用2×200kVA、SCB14、Dyn11、uk=4%，暗备用，正常一台运行。",
            "10kV条件性最大课程短路电流15.638kA，设备按31.5kA开断等级预筛。",
            "220kV配电装置采用户外AIS分相中型，35/10kV采用室内金属铠装移开式开关柜。",
            "35kV采用2×1000kVA、10kV采用2×200kVA ZN接地变+低电阻；正常每段1套，母联转供时仅保留健康侧1套。",
            "CAD按三张必交图加SEC-220-L1-01增强详图组织，共四张A1图。",
        ],
    )
    add_heading(doc, "6.2 课程假设与待复核项目", 2)
    add_table(
        doc,
        "表6-1 课程冻结值与最终工程边界",
        ["项目", "课程设计采用", "最终工程复核"],
        [
            ["短路方法", "100MVA标幺X-only；k=1.8；变流器1.1~1.2倍", "按GB/T 15544.1-2023完整R/X、电压系数、κ和开断时刻"],
            ["设备", "额定值等级预筛", "精确厂家型号、41℃修正、外绝缘与型式试验"],
            ["无功", "目标pf=0.98；2×±12Mvar", "无功电压、谐波与SVG动态专题"],
            ["CT/PT/ZCT", "三相CT/PT目标及35/10kV电缆回路零序CT", "负担、饱和、暂态性能、窗口尺寸、二次容量和电缆压降"],
            ["导体与母线", "220kV载流/热稳/简化弯曲/电晕；35/10kV载流/热稳", "35/10kV电动力与支撑机械、厂家温升、共振和连接金具"],
            ["MOA", "Ur/Uc/In/残压与LIWV裕度课程预筛", "接地方式、10s TOV、能量、引线压降和厂家型号"],
            ["场址与布置", "海拔≤1000m、污秽d级、课程几何", "真实场址、DL/T 5352全文和厂家外形基础图"],
            ["接地与直击雷", "接地设备包、母联切换顺序和设备接地接口", "单相接地/零序、厂家联锁、土壤电阻率、接触/跨步电压和避雷针范围"],
        ],
        [3.2, 5.2, 7.1],
        8.7,
    )

    add_heading(doc, "6.3 图纸和计算成果清单", 2)
    add_table(
        doc,
        "表6-2 本阶段成果",
        ["编号", "成果", "文件"],
        [
            ["SLD-01", "电气主接线简图", "drawings/exports/\nsingle_line_a1.pdf"],
            ["LAY-220-01", "220kV户外AIS平面布置图", "drawings/exports/\nswitchyard_plan_a1.pdf"],
            ["SEC-220-01", "220kV户外AIS典型间隔断面图", "drawings/exports/\nswitchyard_section_a1.pdf"],
            ["SEC-220-L1-01", "220kV I段L1线路间隔断面详图", "drawings/exports/\nswitchyard_line_bay_detail_a1.pdf"],
            ["CALC-LT", "负荷、变压器与持续电流结果", "calculations/results/\nload_and_transformer_summary.md"],
            ["CALC-SC", "短路计算结果", "calculations/results/short_circuit/\nshort_circuit_summary.md"],
            ["CALC-EQ", "设备额定值预筛", "calculations/results/equipment_selection/\nequipment_selection_summary.md"],
        ],
        [2.7, 5.1, 7.7],
        8.5,
        margin_y=55,
    )
    add_references(doc, REFERENCES)

    path = REPORT_DIR / "01_220kV新能源汇集变电所_技术设计说明书.docx"
    finalize_document(doc, path)
    return path


def build_calculation_book(data: dict) -> Path:
    load = data["load"]
    sc = data["sc"]
    equipment = data["equipment"]
    doc = new_document("技术设计计算书")

    front = doc.add_section(WD_SECTION.NEW_PAGE)
    configure_front_section(front)
    add_toc(doc)

    main_sec = start_main_section(doc, SHORT_TITLE + "—技术设计计算书")

    add_heading(doc, "计算说明与统一基准", 1, page_break_before=False)
    add_body(
        doc,
        "本计算书保留负荷、容量、持续电流、标幺电抗、短路电流和设备校验的公式、代入和中间结果。"
        "除特别说明外，功率单位采用MW/Mvar/MVA，电压采用kV，电流采用A或kA。短路计算为任务书"
        "X-only课程初算，最终工程值仍须按现行标准和厂家模型复核。",
    )
    add_table(
        doc,
        "表0-1 统一计算条件",
        ["项目", "采用值", "说明"],
        [
            ["短路基准容量SB", "100MVA", "全网统一"],
            ["平均额定电压UB", "230/37/10.5kV", "220/35/10kV级"],
            ["35kV同时出力系数", "0.95", "仅用于主变综合容量"],
            ["10kV同时系数", "0.80", "辅助负荷综合计算"],
            ["线损率", "5%", "主结果按乘1.05"],
            ["最高环境温度", "41℃", "导体和设备环境校核"],
            ["峰值系数k", "1.8", "课程假设"],
            ["热稳定等值时间", "1.10s", "后备保护1.00s+总开断0.08s向上取整"],
            ["变流器短路贡献", "1.1~1.2倍额定电流", "算术相加课程上界"],
        ],
        [5.0, 4.0, 6.5],
        9.3,
    )
    add_heading(doc, "主要符号", 2)
    symbol_paragraph = add_body(
        doc,
        "P、Q、S分别表示有功、无功和视在功率；cosφ为功率因数；Imax为最大持续工作电流；"
        "X*为标幺电抗；Ik为三相短路初始对称电流；ip为课程峰值电流；Ith和tr分别为设备短时耐受电流及持续时间。",
    )
    symbol_paragraph.paragraph_format.keep_together = True

    add_heading(doc, "前置计算 负荷及变压器容量", 1)
    add_heading(doc, "A.1 35kV新能源负荷", 2)
    add_equation(doc, "Sᵢ = Pᵢ / cosφᵢ", "A-1")
    add_equation(doc, "Qᵢ = Pᵢ tan(arccos(cosφᵢ))", "A-2")
    rows = []
    for item in load["load_35kv"]["items"]:
        rows.append(
            [
                item["label_zh"],
                fmt(item["active_power_mw"], 1),
                fmt(item["power_factor"], 2),
                item["circuits"],
                fmt(item["base_apparent_mva"], 3),
                fmt(item["base_reactive_mvar"], 3),
                fmt(item["per_circuit_current_a"], 3),
            ]
        )
    add_table(
        doc,
        "表A-1 35kV负荷逐项计算",
        ["负荷", "P/MW", "cosφ", "回路", "S/MVA", "Q/Mvar", "单回设计电流/A"],
        rows,
        [2.6, 1.9, 1.8, 1.7, 2.0, 2.1, 3.4],
        8.0,
        "单回设计电流已计5%线损，不乘0.95同时出力系数。",
        nowrap_header_columns={1, 2, 3, 4, 5},
        nowrap_body_columns={1, 2, 3, 4, 5, 6},
        margin_x=75,
    )
    add_equation(doc, "ΣS = 280.988185 MVA", "A-3")
    add_equation(doc, "S35 = 280.988185 × 0.95 × 1.05 = 280.285714 MVA", "A-4")
    add_body(
        doc,
        "向量法按P、Q分别计同时系数和线损得到279.840482MVA；任务书课程主口径采用逐项视在功率和的"
        "标量处理，得到280.285714MVA。两者接近，正式容量校验取后者。",
    )

    add_heading(doc, "A.2 10kV辅助负荷", 2)
    rows = []
    for item in load["load_10kv"]["items"]:
        rows.append(
            [
                item["label_zh"],
                fmt(item["active_power_mw"], 1),
                fmt(item["power_factor"], 2),
                fmt(item["base_apparent_mva"], 3),
                fmt(item["per_circuit_current_a"], 3),
            ]
        )
    add_table(
        doc,
        "表A-2 10kV辅助负荷逐项计算",
        ["负荷", "P/MW", "cosφ", "S/MVA", "单回设计电流/A"],
        rows,
        [5.0, 2.0, 2.0, 2.7, 3.8],
        9.2,
    )
    add_equation(doc, "S10 = 2.091503 × 0.80 × 1.05 = 1.756863 MVA", "A-5")

    add_heading(doc, "A.3 主变压器容量与N-1", 2)
    add_equation(doc, "Snormal,each = 280.285714 / 2 = 140.142857 MVA", "A-6")
    add_equation(doc, "βnormal = 140.142857 / 180 × 100% = 77.857%", "A-7")
    add_equation(doc, "KN-1 = 180 / 280.285714 × 100% = 64.220%", "A-8")
    add_equation(doc, "ΔS = 280.285714 − 180 = 100.285714 MVA", "A-9")
    add_equation(doc, "Kcurtail = (1 − 180 / 280.285714) × 100% = 35.7798%", "A-10")
    add_body(
        doc,
        "主变课程型式冻结为2×180MVA、220/35kV双绕组、YNd11、uk=14%；220kV星形中性点经专用CT"
        "直接接地，35kV侧为三角形绕组。",
    )
    add_body(
        doc,
        "若保守叠加10kV辅助负荷，所需容量为282.042577MVA，正常负载率78.345%，N-1缺口"
        "102.042577MVA。该值作为敏感性，不改变主校核口径。",
    )

    add_heading(doc, "A.4 所用变压器", 2)
    add_table(
        doc,
        "表A-3 所用电负荷统计结果",
        ["统计口径", "功率/kW"],
        [
            ["连续适用负荷", "96.3"],
            ["短时适用负荷", "89.0"],
            ["明确经常负荷", "81.2"],
            ["明确不经常负荷", "68.1"],
            ["未标频度连续负荷", "36.0"],
            ["经常短时负荷", "44.0"],
            ["短时同时投入值", "22.0"],
        ],
        [9.5, 6.0],
        9.5,
    )
    add_equation(doc, "Sbase = 118.3 × 1.10 / 0.80 = 162.6625 kVA", "A-11")
    add_equation(doc, "Sworst = 140.3 × 1.10 / 0.80 = 192.9125 kVA", "A-12")
    add_body(doc, "选用2×200kVA、10/0.4kV、SCB14干式、Dyn11、uk=4%的所用变，暗备用；正常一台运行。")

    add_heading(doc, "A.5 SVG与T10", 2)
    add_equation(doc, "Qc = P [tanφ1 − tanφ2]", "A-13")
    add_body(
        doc,
        "T10冻结为2×31.5MVA、35/10.5kV、YNd11、uk=8%，两段各设±12Mvar SVG。计入10kV辅助无功后"
        "需21.8875Mvar，选24Mvar，裕度9.65%，补偿后功率因数0.98147。式(A-17)按10.5kV绕组电压计算，"
        "式(A-18)按10kV开关设备校核电压计算，二者校核对象不同。",
    )
    add_equation(doc, "IT10,35 = 31.5 / (√3 × 35) = 519.615 A", "A-14")
    add_equation(doc, "1.05 IT10,35 = 545.596 A", "A-15")
    add_equation(doc, "IT10,10.5 = 31.5 / (√3 × 10.5) = 1732.051 A", "A-16")
    add_equation(doc, "1.05 IT10,10.5 = 1818.653 A", "A-17")
    add_equation(doc, "1.05 IT10,10kV设备口径 = 31.5/(√3×10)×1.05 = 1909.586 A", "A-18")
    add_heading(doc, "第五章 各回路最大持续工作电流计算书", 1)
    add_heading(doc, "5.1 通用公式与主变回路", 2)
    add_equation(doc, "Imax = Smax / (√3 Un)", "5-1")
    add_equation(doc, "IT,220 = 180 / (√3 × 220) × 1.05 = 495.996 A", "5-2")
    add_equation(doc, "IT,35 = 180 / (√3 × 35) × 1.05 = 3117.691 A", "5-3")
    add_equation(doc, "IL,normal = 280.285714 / (2√3 × 220) = 367.780 A", "5-4")
    add_equation(doc, "IL,N-1 = 280.285714 / (√3 × 220) = 735.559 A", "5-5")

    add_heading(doc, "5.2 35kV馈线与母线段", 2)
    feeder_rows = []
    for item in load["load_35kv"]["items"]:
        feeder_rows.append(
            [
                item["label_zh"],
                item["circuits"],
                fmt(item["base_per_circuit_mva"], 3),
                fmt(item["per_circuit_design_mva"], 3),
                fmt(item["per_circuit_current_a"], 3),
            ]
        )
    add_table(
        doc,
        "表5-1 35kV馈线持续电流",
        ["负荷", "回路数", "单回基础S/MVA", "计损耗S/MVA", "Imax/A"],
        feeder_rows,
        [3.5, 2.0, 3.0, 3.0, 4.0],
        9.0,
    )
    add_equation(doc, "I35-I = 2230.732 A；I35-II = 2404.371 A", "5-6")
    add_body(
        doc,
        "母线段电流按实际馈线分配累加，不把全站4623.515A简单平均。35kV母联按一台主变额定电流"
        "1.05倍，即3117.691A承担事故转供职责。",
    )

    add_heading(doc, "5.3 10kV及SVG回路", 2)
    add_table(
        doc,
        "表5-2 10kV主要回路持续电流",
        ["回路", "Imax/A", "计算依据"],
        [
            ["T10进线/10kV母联", "1909.586", "31.5MVA按10kV设备口径×1.05"],
            ["单套SVG", "692.820", "12Mvar按10.5kV额定电流×1.05"],
            ["站用电备用电源", "57.056", "0.8MW、pf=0.85、计5%线损"],
            ["无功补偿及冷却", "42.792", "0.6MW、pf=0.85、计5%线损"],
            ["集控通信及监控", "26.943", "0.4MW、pf=0.90、计5%线损"],
        ],
        [5.0, 3.5, 7.0],
        9.4,
    )

    add_heading(doc, "5.4 LGJ-400/50温度修正", 2)
    add_equation(doc, "KT = √[(70−41)/(70−25)] = 0.802773", "5-7")
    add_equation(doc, "Iallow,41 = 592 × 0.802773 = 475.242 A", "5-8")
    add_equation(doc, "Kline-curtail = (1−475.242/735.559)×100% = 35.390%", "5-9")
    add_equation(doc, "Imain-T-N-1 = 180/(√3×220) = 472.377 A", "5-10")
    add_body(
        doc,
        "主变N-1后的线路电流472.377A，小于课程允许值475.242A，余量2.864A。因此主变限发35.780%"
        "略严于线路限发35.390%，但厂家热额定资料到位后必须覆盖复核。",
    )

    add_heading(doc, "第六章 短路电流计算书", 1)
    add_heading(doc, "6.1 标幺值与等值网络", 2)
    add_equation(doc, "ZB,220 = UB²/SB = 230²/100 = 529 Ω", "6-1")
    add_equation(doc, "X*sys1 = 0.40×100/2400 = 0.016667", "6-2")
    add_equation(doc, "X*sys2 = 0.45×100/2000 = 0.022500", "6-3")
    add_equation(doc, "X*L1 = 0.40×70×100/230² = 0.052930", "6-4")
    add_equation(doc, "X*L2 = 0.40×85×100/230² = 0.064272", "6-5")
    add_equation(doc, "X*path1 = 0.069597；X*path2 = 0.086772", "6-6")
    add_equation(doc, "X*parallel = X1X2/(X1+X2) = 0.038621", "6-7")
    add_equation(doc, "X*T = 0.14×100/180 = 0.077778", "6-8")
    add_equation(doc, "X*T10 = 0.08×100/31.5 = 0.253968", "6-9")
    add_table(
        doc,
        "表6-1 元件标幺电抗",
        ["元件", "X*/pu", "说明"],
        [
            ["系统1", "0.016667", "以2400MVA为原基准"],
            ["L1", "0.052930", "70km，0.40Ω/km"],
            ["系统1+L1", "0.069597", "220kV-I段分列电源路径"],
            ["系统2", "0.022500", "以2000MVA为原基准"],
            ["L2", "0.064272", "85km，0.40Ω/km"],
            ["系统2+L2", "0.086772", "220kV-II段分列电源路径"],
            ["两电源并联", "0.038621", "220kV分段条件闭合"],
            ["每台主变", "0.077778", "180MVA，uk=14%"],
            ["每台T10", "0.253968", "31.5MVA，uk=8%"],
        ],
        [5.0, 3.0, 7.5],
        9.4,
    )

    add_heading(doc, "6.2 220kV短路点", 2)
    add_equation(doc, "Ik,220-I = 100/(√3×230×0.069597) = 3.607 kA", "6-10")
    add_body(doc, "计I段新能源贡献上界0.426kA，课程控制职责为4.033kA，课程峰值10.266kA；3.607kA仅为电网分量。")
    add_equation(doc, "Ik,220-II = 100/(√3×230×0.086772) = 2.893 kA", "6-11")
    add_body(doc, "计II段新能源贡献上界0.459kA，课程综合上限为3.352kA。")
    add_equation(doc, "Ik,220-closed = 100/(√3×230×0.038621) = 6.500 kA", "6-12")
    add_body(
        doc,
        "6.500kA和电网峰值16.546kA仅为电网分量。计全部新能源贡献上界0.885kA后，条件性控制职责"
        "为7.385kA，课程峰值18.798kA；该场景必须以系统允许并列为前提。",
    )

    add_heading(doc, "6.3 35kV短路点", 2)
    add_equation(doc, "XΣ,35-I = 0.069597 + 0.077778 = 0.147375", "6-13")
    add_equation(doc, "Ik,35-I,grid = 100/(√3×37×0.147375) = 10.588 kA", "6-14")
    add_body(doc, "加I段新能源贡献上界2.677kA，综合上限13.265kA。")
    add_equation(doc, "XΣ,35-II = 0.086772 + 0.077778 = 0.164550", "6-15")
    add_equation(doc, "Ik,35-II,grid = 9.483 kA；综合上限12.368 kA", "6-16")
    add_body(
        doc,
        "220kV分段条件闭合时，两段上游等值相同，35kV-II段因新能源额定电流较大形成最大综合上限"
        "16.291kA，课程峰值41.470kA。两台健康主变低压侧并列时综合敏感性25.694kA，属于禁止方式。",
    )

    add_heading(doc, "6.4 10kV短路点", 2)
    add_equation(doc, "XΣ,10-I = 0.069597+0.077778+0.253968 = 0.401343", "6-17")
    add_equation(doc, "Ik,10-I,grid = 13.700 kA；计SVG后14.492 kA", "6-18")
    add_equation(doc, "XΣ,10-II = 0.086772+0.077778+0.253968 = 0.418518", "6-19")
    add_equation(doc, "Ik,10-II,grid = 13.138 kA；计SVG后13.930 kA", "6-20")
    add_body(
        doc,
        "220kV分段条件闭合时，单台T10供本段的综合上限为15.638kA，课程峰值39.808kA。两台健康T10"
        "经10kV母联并列时综合敏感性为28.472kA，仅用于联锁风险提示。",
    )

    add_heading(doc, "6.5 全部计算点汇总", 2)
    status_map = {
        "permitted_separate_operation": "允许分列",
        "conditional_pending_system_parallel_permission": "条件并列",
        "conditional_dispatch_permission_only": "条件并列",
        "not_permitted_non_normal_sensitivity": "禁止敏感性",
    }
    point_label_map = {
        "SC-220-BUS-CLOSED": "220kV分段闭合",
        "SC-220-I-SEPARATE": "220kV-I分列",
        "SC-220-II-SEPARATE": "220kV-II分列",
        "SC-35-I-220-CLOSED": "35kV-I上游闭合",
        "SC-35-II-220-CLOSED": "35kV-II上游闭合",
        "SC-35-I-220-SEPARATE": "35kV-I分列",
        "SC-35-II-220-SEPARATE": "35kV-II分列",
        "SC-35-BOTH-TRANSFORMERS-SENSITIVITY": "35kV主变并列敏感",
        "SC-10-I-220-SEPARATE": "10kV-I分列",
        "SC-10-I-220-CLOSED": "10kV-I上游闭合",
        "SC-10-II-220-SEPARATE": "10kV-II分列",
        "SC-10-II-220-CLOSED": "10kV-II上游闭合",
        "SC-10-BOTH-T10-SENSITIVITY": "10kV T10并列敏感",
    }
    sc_rows = []
    for point in sc["points"].values():
        max_total = point.get("conservative_total_symmetrical_current_range_ka", {}).get("maximum")
        sc_rows.append(
            [
                point_label_map.get(point["point_id"], point["point_id"]),
                str(point["voltage_level"]).removesuffix("kV"),
                fmt(point["equivalent_reactance_pu"], 6),
                fmt(point["grid_symmetrical_current_ka"], 3),
                fmt(max_total, 3),
                fmt(point.get("course_total_peak_sensitivity_ka"), 3),
                status_map.get(point["normal_operation_status"], point["normal_operation_status"]),
            ]
        )
    add_table(
        doc,
        "表6-2 短路计算点汇总",
        ["计算点", "电压/kV", "XΣ/pu", "电网Ik/kA", "综合上限/kA", "课程峰值/kA", "方式"],
        sc_rows,
        [3.0, 1.8, 1.9, 1.9, 1.9, 1.9, 3.1],
        6.7,
        nowrap_body_columns={0, 1, 2, 3, 4, 5},
        margin_x=45,
        margin_y=30,
    )

    add_heading(doc, "第七章 主要电气设备选择计算书", 1)
    add_heading(doc, "7.1 校验条件", 2)
    add_equation(doc, "Ue ≥ Un；Ie ≥ Imax", "7-1")
    add_equation(doc, "Ibr ≥ Ik；Imaking ≥ ip；Ipeak withstand ≥ ip", "7-2")
    add_equation(doc, "Ith² tr ≥ Ik² t；t = 1.10 s", "7-3")
    add_body(
        doc,
        "开断和峰值预筛采用条件性最大职责：220kV 7.385/18.798kA，35kV 16.291/41.470kA，"
        "10kV 15.638/39.808kA。禁止并列敏感性不抬高正常设备必选职责，但必须落实联锁。",
    )

    add_heading(doc, "7.2 额定电压与持续电流", 2)
    add_table(
        doc,
        "表7-1 代表性设备持续电流校验",
        ["设备/回路", "所需电流/A", "候选额定/A", "裕度/A", "结论"],
        [
            ["220kV线路断路器/\n隔离开关", "735.559", "3150", "2414.441", "预筛通过"],
            ["220kV主变回路", "495.996", "3150", "2654.004", "预筛通过"],
            ["35kV主变进线/母联", "3117.691", "3150", "32.309", "预筛通过；室内≤40℃与厂家温升待核"],
            ["35kV馈线/T10", "最大546.963", "1250", "703.037", "预筛通过"],
            ["10kV T10进线/母联", "1909.586", "2500", "590.414", "预筛通过；室内≤40℃与厂家温升待核"],
            ["10kV SVG馈线", "692.820", "1250", "557.180", "预筛通过"],
        ],
        [4.5, 2.8, 2.7, 2.7, 2.8],
        8.8,
    )

    add_heading(doc, "7.3 开断、关合与动稳定", 2)
    add_table(
        doc,
        "表7-2 开断和峰值校验",
        ["电压级", "所需开断/kA", "候选开断/kA", "所需峰值/kA", "候选峰值/kA", "结论"],
        [
            ["220kV", "7.385", "50", "18.798", "125", "预筛通过"],
            ["35kV", "16.291", "31.5", "41.470", "80", "预筛通过"],
            ["10kV", "15.638", "31.5", "39.808", "80", "预筛通过"],
        ],
        [2.1, 2.5, 2.5, 2.5, 2.6, 3.3],
        9.0,
    )

    add_heading(doc, "7.4 热稳定", 2)
    thermal_rows = []
    for level, ik, ith, tr in (
        ("220kV", 7.384571960617697, 50.0, 3.0),
        ("35kV", 16.290983445518524, 31.5, 4.0),
        ("10kV", 15.638094419605405, 31.5, 4.0),
    ):
        required = ik * ik * 1.10
        available = ith * ith * tr
        thermal_rows.append(
            [level, fmt(ik, 3), fmt(required, 3), f"{fmt(ith,1)}kA/{fmt(tr,0)}s", fmt(available, 1), "预筛通过"]
        )
    add_table(
        doc,
        "表7-3 热稳定I²t校验",
        ["电压级", "Ik / kA", "Ik²t / kA²·s", "候选耐受", "Ith²tr / kA²·s", "结论"],
        thermal_rows,
        [2.3, 2.1, 2.4, 2.7, 2.8, 3.2],
        8.4,
        nowrap_body_columns={0, 1, 2, 3, 4},
        margin_x=75,
        margin_y=65,
    )

    add_heading(doc, "7.5 CT/PT、母线、MOA和接地开关课程预筛", 2)
    add_table(
        doc,
        "表7-4 母线课程预筛",
        ["电压级", "课程选择", "持续电流校验", "补充校验"],
        [
            ["220kV", "铝合金管母Φ100/90mm", "1605.546＞735.559A", "热稳123.785＞7.385kA；应力10.048＜70MPa；电晕330.444＞145.492kV"],
            ["35kV", "每相3×125×10mm矩形铝母线", "4194＞3117.691A", "热稳311.067＞16.291kA；机械/电动力待核"],
            ["10kV", "每相2×125×10mm矩形铝母线", "3282＞1909.586A", "热稳207.378＞15.638kA；机械/电动力待核"],
        ],
        [2.2, 4.2, 3.8, 5.3],
        8.2,
        "220kV管母已做简化弯曲和电晕；35/10kV仅完成载流与热稳。支撑共振、连接金具、厂家温升及两级矩形母线机械校验仍待精确资料。",
        keep_note_with_table=True,
    )
    add_table(
        doc,
        "表7-5 MOA参数与绝缘裕度",
        ["型号", "Ur/Uc/In/残压", "课程校验", "边界"],
        [
            ["YH10W-204/532", "204/159kV；10kA；≤532kV", "Uc余13.508kV；950/532=1.786", "TOV/能量/厂家型号待核"],
            ["YH5WZ-51/134", "51/40.8kV；5kA；≤134kV", "Uc仅余0.300kV（约0.74%）；185/134=1.381", "接地方式、10s TOV、能量、引线压降必核"],
            ["YH5WZ-17/45", "17/13.6kV；5kA；≤45kV", "Uc余1.600kV；75/45=1.667", "TOV/能量/厂家型号待核"],
        ],
        [3.8, 3.8, 4.4, 3.5],
        7.9,
        "LIWV/残压比课程下限取1.15。",
        nowrap_body_columns={0},
        margin_x=75,
        margin_y=65,
    )
    add_table(
        doc,
        "表7-6 CT/PT课程目标",
        ["对象", "一次变比/电压", "课程目标", "工程待核"],
        [
            ["220kV线路/分段CT", "1000/1A", "0.2S/0.5/5P30，按需PX；50kA/3s、125kA", "负担、饱和、拐点、暂态级"],
            ["220kV主变CT", "600/1A", "0.2S/0.5/5P30/PX；50kA/3s、125kA", "负担、差动配合和精确型号"],
            ["主变中性点CT", "600/1A", "PX限制接地故障+5P30中性点过流", "单相接地/零序职责；不沿用三相短路"],
            ["35kV进线/母联CT", "4000/1A", "0.2S/0.5/5P30/PX；31.5kA/4s、80kA", "负担、饱和和精确型号"],
            ["35kV馈线/T10 CT", "800/1A", "0.2S/0.5/5P30；31.5kA/4s、80kA", "零序与保护配合"],
            ["10kV进线/母联CT", "2500/1A", "0.2S/0.5/5P30/PX；31.5kA/4s、80kA", "负担、饱和和精确型号"],
            ["10kV馈线/SVG CT", "1000/1A", "0.2S/0.5/5P30；31.5kA/4s、80kA", "零序与保护配合"],
            ["35kV电缆馈线ZCT", "100/1A", "5回；一次剩余电流目标400A；5P20或厂家等效", "窗口、屏蔽接地回路、负担和拐点"],
            ["10kV电缆/SVG ZCT", "50/1A", "2回SVG+3类辅助馈线；一次剩余电流目标200A", "窗口、屏蔽接地回路、负担和拐点"],
            ["220/35/10kV PT", "220/√3、35/√3、10/√3kV", "100/√3V测量/保护+100/3V开口三角；0.2或0.5、3P", "容量、铁磁谐振、同期抽取"],
        ],
        [3.2, 3.3, 5.1, 3.9],
        7.7,
    )
    add_table(
        doc,
        "表7-7 绝缘、接地和适用性结论",
        ["项目", "课程采用", "结论或边界"],
        [
            ["绝缘子/设备套管", "252/950、40.5/185、12/75kV；套管630/4000/2500A及本级短时/峰值", "电压、电流、短时和峰值课程检查通过；爬距、机械负荷和精确型号待厂家"],
            ["35kV中性点", "2×1000kVA ZN接地变+低电阻；400A/10s、R≈50.5Ω", "1250A柜；600/1A相CT+400/1A中性点CT；厂家成套待核"],
            ["10kV中性点", "2×200kVA ZN接地变+低电阻；200A/10s、R≈28.9Ω", "1250A柜；300/1A相CT+200/1A中性点CT；厂家成套待核"],
            ["接地源联锁", "母联合闸前退出受电/故障段接地源，仅保留健康侧1套", "禁止母联闭合且两套并联；分列后恢复每段1套"],
            ["接地开关", "220kV线路侧常开ES；35/10kV柜内常开ES", "短时等级随本级设备；感应电流开合和联锁图待核"],
            ["限流电抗器", "不设置", "35/10kV职责低于31.5kA；最终短路超过设备能力时重审"],
            ["高压熔断器", "非主回路设备", "仅PT柜按厂家方案配置一次熔断/二次保护"],
            ["阻波器", "当前不配置", "仅确定电力线载波通信时配置"],
        ],
        [3.4, 5.0, 7.1],
        8.1,
    )

    add_heading(doc, "7.6 最终工程复核边界", 2)
    add_table(
        doc,
        "表7-8 尚未具备最终校验输入的项目",
        ["项目", "本课程已完成", "最终仍需输入"],
        [
            ["CT", "一次变比、芯级与短路等级目标", "负担、饱和、拐点、暂态级、二次负荷与电缆"],
            ["PT/CVT", "一次/二次电压、准确级和开口三角", "容量、铁磁谐振、同期抽取和精确型号"],
            ["母线/导体", "220kV载流/热稳/简化弯曲/电晕；35/10kV载流/热稳", "35/10kV电动力与支撑机械、厂家温升、共振、无线电干扰和金具"],
            ["绝缘子/套管", "最高电压、LIWV、套管持续/短时/峰值课程检查", "机械破坏负荷、爬距、端子荷载、厂家图"],
            ["MOA", "Ur、Uc、In、残压和LIWV裕度", "接地方式、10s TOV、能量、引线压降和精确型号"],
            ["接地", "接地变+低电阻设备包、馈线CT目标、母联切换逻辑及接地接口", "单相接地/零序、厂家联锁、土壤电阻率、接地网、接触/跨步电压"],
            ["设备环境", "室外41℃；35/10kV室内柜受控≤40℃；≤1000m、d级", "精确型号服务条件和修正系数"],
        ],
        [3.0, 5.0, 7.5],
        8.8,
    )
    add_note_box(
        doc,
        "最终状态",
        "上述额定值校验为课程等级预筛，不代表已取得精确订货型号。报告中应使用“预筛通过、最终型号待厂家资料”"
        "的表述，避免把缺少的数据按0处理或自动判为通过。",
    )

    add_heading(doc, "7.7 可追溯计算文件", 2)
    add_table(
        doc,
        "表7-9 计算结果与脚本路径",
        ["内容", "结果文件", "计算脚本"],
        [
            ["负荷、变压器、持续电流", "results/load_and_transformer_\nresults.json", "load_and_transformers/\ncalculate.py"],
            ["回路电流", "results/circuit_currents.csv", "load_and_transformers/\ncalculate.py"],
            ["所用电", "results/station_service_loads.csv", "load_and_transformers/\ncalculate.py"],
            ["短路计算", "results/short_circuit/\nshort_circuit_results.json", "short_circuit/calculate.py"],
            ["设备预筛", "results/equipment_selection/\nequipment_selection_results.json", "equipment_selection/\ncalculate.py"],
        ],
        [3.2, 6.6, 5.7],
        8.3,
        "表中路径均相对于 calculations/ 目录。",
    )
    add_references(doc, REFERENCES)

    path = REPORT_DIR / "02_220kV新能源汇集变电所_技术设计计算书.docx"
    finalize_document(doc, path)
    return path


def build_course_summary(data: dict) -> Path:
    doc = new_document("课程设计总结")
    main_sec = start_main_section(doc, SHORT_TITLE + "—课程设计总结")
    add_heading(doc, "课程设计总结", 1, page_break_before=False)
    add_heading(doc, "1 设计任务回顾", 2)
    add_body(
        doc,
        "本次课程设计围绕220kV新能源汇集变电所电气一次部分展开，任务包括主接线、主变和所用变选择、"
        "负荷与持续电流计算、短路计算、主要设备校验、配电装置布置以及三张必交图加一张增强详图。设计过程从任务书"
        "原始数据出发，先冻结运行方式和计算口径，再把同一组基线同步到计算、设备表和CAD图纸。",
    )
    add_heading(doc, "2 主要工作与结果", 2)
    add_bullets(
        doc,
        [
            "确定220/35/10/0.4kV分层接线：前三个电压级均分段分列，0.4kV采用单母线分段暗备用。",
            "完成35kV新能源负荷计算，得到主变校核容量280.286MVA，选2×180MVA，正常负载率77.857%。",
            "明确主变N-1需限发35.780%，同时校核220kV LGJ-400/50导线的41℃课程载流量。",
            "补充任务书未给的10kV方案，选2×31.5MVA T10和2×±12Mvar SVG，补偿后功率因数约0.98147。",
            "采用100MVA标幺法完成220/35/10kV课程短路初算，并区分允许、条件允许和禁止并列场景。",
            "补齐MOA、零序CT、接地开关和35/10kV接地设备包，并固化母联转供时仅保留健康侧1套接地源的联锁。",
            "完成220kV主接线、户外AIS平面、典型断面和L1线路间隔增强详图的DWG/DXF/PDF/PNG底图。",
        ],
    )
    add_heading(doc, "3 设计方法与体会", 2)
    method_paragraph = add_body(
        doc,
        "课程设计中最重要的不是孤立得到一个数值，而是保持任务书、运行方式、计算点、设备职责和图纸表达一致。"
        "例如，35kV和10kV母联的正常状态直接决定短路等值；母联合闸前还必须退出受电段接地源，避免两套"
        "低电阻并联改变接地故障电流；主变N-1限发又会改变220kV线路的持续电流。"
        "如果先画图后冻结这些逻辑，后续会出现大面积返工。因此本项目采用“输入台账—设计基线—计算结果—"
        "设备职责—CAD图纸—文档”的可追溯链条。",
    )
    method_paragraph.paragraph_format.keep_together = True
    boundary_paragraph = add_body(
        doc,
        "另一个重要认识是区分课程假设与工程定值。海拔、污秽、SVG容量、保护时间、变流器短路贡献和AIS几何"
        "都可以为了完成课程设计提出合理且保守的值，但必须写明证据等级和替换条件。对精确设备型号、CT/PT/ZCT"
        "二次参数、35/10kV母线机械、接地网、避雷器和厂家41℃数据，不能因时间有限而虚构“已校验合格”。",
    )
    boundary_paragraph.paragraph_format.keep_together = True
    add_heading(doc, "4 质量控制", 2)
    add_table(
        doc,
        "表1 设计质量控制结果",
        ["检查项", "结果"],
        [
            ["自动化测试", "当前CAD/设备源阶段62项通过；正式再生成后以最新全量结果为准"],
            ["项目健康检查", "当前68条检查通过；正式再生成后重新执行"],
            ["图纸一致性", "四图回路、设备链、编号、净距和几何基线一致"],
            ["公开仓库边界", "任务书、模板、课程资料和个人字段未公开"],
            ["可再生性", "负荷、短路、设备预筛和图纸均有脚本或结构化源数据"],
        ],
        [6.5, 9.0],
        9.8,
    )
    add_heading(doc, "5 后续完善方向", 2, page_break_before=True)
    add_bullets(
        doc,
        [
            "按教师最终口径确认说明书与计算书是否分册手写，以及是否使用右侧教师批阅栏。",
            "依据现行厂家样本复核41℃额定电流、设备外形、基础和端子图。",
            "按GB/T 15544.1-2023补充完整短路计算，并引入新能源、SVG和电动机的精确模型。",
            "补做CT/PT/ZCT负担、避雷器TOV/能量、接地网与接地源联锁、35/10kV母线机械及套管爬距/机械等专项。",
            "根据本项目CAD底图完成最终手绘临摹、打印和提交包核验。",
        ],
        keep_together=True,
    )
    add_note_box(doc, "提交提示", "本总结为公开电子底稿，个人信息和签字在最终手写或私有提交版中补齐。")
    path = REPORT_DIR / "03_220kV新能源汇集变电所_课程设计总结.docx"
    finalize_document(doc, path)
    return path


def add_qa(doc: Document, number: int, question: str, answer: list[str]) -> None:
    add_heading(doc, f"{number}. {question}", 2)
    add_bullets(doc, answer, keep_together=True)


def build_defense_questions(data: dict) -> Path:
    doc = new_document("答辩提纲与问题清单")
    main_sec = start_main_section(doc, SHORT_TITLE + "—答辩提纲")
    add_heading(doc, "答辩提纲与常见问题", 1, page_break_before=False)

    add_heading(doc, "一、90秒开场陈述", 2)
    add_body(
        doc,
        "本设计为220kV新能源汇集变电所电气一次部分初步设计。本站以12回35kV集电线路汇集270MW风电、"
        "光伏和储能，经2×180MVA主变升压后由两回220kV线路送出。主接线采用220kV、35kV、10kV单母线"
        "分段；220kV分段断路器、35/10kV母联正常断开，0.4kV母联闭合并由一台200kVA所用变供电。"
        "35kV综合计算容量为280.286MVA，主变正常负载率77.857%，N-1时需限发35.780%。"
        "为满足无功和辅助系统需求，设置2×31.5MVA T10和2×±12Mvar SVG。短路初算采用100MVA标幺法，"
        "10kV条件性最大综合电流15.638kA，设备按31.5kA等级预筛。35/10kV每段配置ZN接地变+低电阻，"
        "母联转供时仅保留健康侧1套接地源。220kV配电装置采用户外AIS，并完成"
        "三张必交图和SEC-220-L1-01线路间隔增强详图，共四张课程设计底图。",
    )

    add_heading(doc, "二、汇报主线", 2)
    add_bullets(
        doc,
        [
            "题目与原始资料：220/35/10kV、270MW新能源、两回220kV送出。",
            "主接线：为什么选择分段分列，以及各母联正常状态。",
            "容量：2×180MVA主变、2×31.5MVA T10、2×±12Mvar SVG、2×200kVA所用变。",
            "关键计算：280.286MVA、77.857%、35.780%、15.638kA、475.242A。",
            "设备和配电装置：额定等级预筛、CT/PT/ZCT、MOA、母线/绝缘、接地设备包及不设限流电抗器等结论。",
            "边界：哪些是任务书值、哪些是课程假设、哪些必须由厂家和现行标准覆盖。",
        ],
    )

    add_heading(doc, "三、常见答辩问题", 1)
    questions = [
        (
            "为什么220kV侧选单母线分段，而不是双母线？",
            [
                "本期只有两回线路、两台主变和一回预留，单母线分段能把母线故障限制在一段，接线清晰、经济。",
                "双母线检修灵活性更高，但隔离开关多、占地和投资大、倒闸复杂，与本期规模不匹配。",
                "若教师要求母线检修时线路和主变不停电，可升级为双母线不带旁路。",
            ],
        ),
        (
            "2×180MVA主变是否合理？",
            [
                "35kV综合计算容量为280.286MVA，两台均分时每台140.143MVA，负载率77.857%，正常方式合理。",
                "N-1时单台只能覆盖64.220%，但任务书允许新能源汇集站限发，因此通过35.780%限发满足运行。",
            ],
        ),
        (
            "主变N-1和220kV线路N-1谁控制限发？",
            [
                "单回线路在41℃课程载流量475.242A约束下需限发35.390%。",
                "主变N-1需要限发35.780%，略严格；限发后线路电流472.377A，小于课程允许值，余量2.864A。",
                "所以当前控制元件是主变，但线路裕度很小，厂家热额定值必须复核。",
            ],
        ),
        (
            "为什么35kV和10kV母联正常断开？",
            [
                "两台主变和两台T10分别带一段，分列可以限制短路电流并缩小故障影响范围。",
                "母联只在一侧电源隔离且故障清除后用于事故转供，不能把两个健康电源长期并列。",
            ],
        ),
        (
            "35kV或10kV母联事故转供时，接地源怎样切换？",
            [
                "正常分列时每个独立带电母线段各投入1套接地变+低电阻。",
                "母联合闸前先退出受电侧或故障侧接地源，只保留健康电源侧1套；联锁禁止母联闭合且两套同时投入。",
                "母联断开、两段恢复独立供电后，再恢复每段各1套，否则两套低电阻并联会改变目标接地故障电流和保护配合。",
            ],
        ),
        (
            "为什么0.4kV母联正常闭合？",
            [
                "所用变采用暗备用，正常只运行一台，闭合母联后该台可同时带两段低压母线。",
                "另一台所用变及其进线保持断开；切换时先隔离故障进线，再投入备用进线，防止并列。",
            ],
        ),
        (
            "为什么另设35/10.5kV T10，而不用三绕组主变？",
            [
                "任务书给出了220/35kV双绕组和35/10.5kV变压器阻抗，独立T10与给定资料一致。",
                "独立T10可限制10kV短路电流，并使10kV故障不直接迫使主变退出。",
                "2×31.5MVA还能在N-1下承担两套SVG最严吸收工况，负载率约79.17%。",
            ],
        ),
        (
            "SVG容量为什么选2×±12Mvar？",
            [
                "目标功率因数0.98，保守计入10kV辅助无功后需21.8875Mvar。",
                "选24Mvar后容量裕度9.65%，补偿后功率因数约0.98147。",
                "该值是课程冻结值，最终仍由无功电压和谐波专题确定。",
            ],
        ),
        (
            "短路点为什么这样选择？",
            [
                "设备选择主要受各级母线故障控制，因此至少计算220kV、35kV I/II段和10kV I/II段。",
                "另外计算220kV分段断路器条件闭合、健康主变低压侧并列和健康T10并列，用于最大方式和误操作敏感性。",
            ],
        ),
        (
            "为什么禁止并列敏感性不作为设备必选职责？",
            [
                "这些方式在运行规程和联锁中被禁止，不属于正常或允许事故转供方式。",
                "把禁止方式直接作为设备必选职责会掩盖运行边界并导致不必要抬高等级，但其结果必须用于联锁和风险提示。",
            ],
        ),
        (
            "10kV最大短路电流是多少？",
            [
                "单台T10供本段、上游220kV分段条件闭合时，计SVG课程上界为15.638kA。",
                "两台健康T10并列的禁止敏感性为28.472kA；正常设备按31.5kA开断等级预筛。",
            ],
        ),
        (
            "设备热稳定如何校验？",
            [
                "采用Ik²t≤Ith²tr，热等值时间取1.10s。",
                "220kV候选50kA/3s，35kV和10kV候选31.5kA/4s，按条件性最大Ik计算均有较大I²t裕度。",
            ],
        ),
        (
            "35kV 3150A和10kV 2500A选型有什么风险？",
            [
                "35kV主变进线需3117.691A，3150A柜仅余32.309A、约1.04%；10kV进线需1909.586A，2500A柜余590.414A。",
                "两级室内开关柜均按受控≤40℃。35kV余量尤其小，必须依赖厂家温升确认；10kV虽有较大余量，精确柜型和散热条件仍需闭合。",
            ],
        ),
        (
            "CT/PT为什么没有写成精确订货型号？",
            [
                "一次安装位置和变比量级可以由持续电流确定，但准确级、芯数、暂态性能和二次负荷依赖保护、计量和电缆清册。",
                "缺少这些输入时写精确型号会造成虚假闭环，因此本阶段只冻结配置原则。",
            ],
        ),
        (
            "任务书没有逐字列避雷器和零序CT，为什么仍要配置？",
            [
                "任务书要求主要电气设备和互感器完整选择，MOA属于过电压保护完整性，零序CT属于电缆单相接地保护接口。",
                "7回35kV架空馈线入口配置MOA；5回35kV电缆和10kV电缆/SVG回路配置零序CT，职责与三相CT分开。",
                "课程阶段只冻结位置和参数目标，MOA的TOV/能量及ZCT窗口、负担、拐点和精确型号仍待专题。",
            ],
        ),
        (
            "35kV和10kV母线是否已经完成动稳定校验？",
            [
                "没有笼统宣称完成。两级矩形母线当前只完成载流和1.10s热稳定课程预筛。",
                "电动力、支撑绝缘子受力、连接金具和厂家温升仍待精确布置与厂家参数；220kV管母另完成了简化弯曲和电晕预筛。",
            ],
        ),
        (
            "为什么220kV配电装置选户外AIS？",
            [
                "本站回路数量有限、场地课程假设允许，AIS经济、直观且便于扩建和手绘表达。",
                "GIS占地小、环境适应性强，但投资高且本题无紧凑场地约束。",
            ],
        ),
        (
            "图纸中的尺寸能否施工使用？",
            [
                "不能。站区145×90m、14m节距、设备轮廓和构架标高均为课程设计几何。",
                "净距来自课程讲义，正式工程仍须按DL/T 5352-2018全文、真实场址和厂家外形基础图复核。",
            ],
        ),
    ]
    for index, (question, answer) in enumerate(questions, 1):
        add_qa(doc, index, question, answer)

    add_heading(doc, "四、答辩时容易说错的边界", 1, page_break_before=False)
    add_table(
        doc,
        "表1 表述边界",
        ["不建议说", "建议说"],
        [
            ["设备已经最终定型", "额定值等级预筛通过，精确厂家型号和41℃条件待核"],
            ["短路电流符合现行标准最终值", "采用任务书标幺X-only课程初算，最终按GB/T 15544.1-2023复核"],
            ["图纸可以施工", "图纸为课程设计和手绘临摹底图"],
            ["35kV/10kV母联可长期闭合", "仅在故障源隔离且故障清除后事故转供"],
            ["母联合闸后两套接地源仍可同时投入", "合母联前退出受电/故障段接地源，仅保留健康侧1套"],
            ["35/10kV母线机械动稳定已全部完成", "当前只完成载流和热稳；电动力与支撑机械待复核"],
            ["CT/PT型号已选定", "一次变比、芯级/准确级目标已冻结；二次负担、暂态性能和最终型号等待保护计量清册"],
        ],
        [7.4, 8.1],
        9.3,
    )
    path = REPORT_DIR / "05_220kV新能源汇集变电所_答辩问题清单.docx"
    finalize_document(doc, path)
    return path


def finalize_document(doc: Document, path: Path) -> None:
    add_update_fields_setting(doc)
    props = doc.core_properties
    props.title = TITLE
    props.subject = "发电厂电气部分课程设计"
    props.author = "课程设计项目组（公开版）"
    props.last_modified_by = "课程设计项目组（公开版）"
    props.comments = ENGINEERING_NOTE
    path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(path)


def main() -> None:
    data = load_data()
    outputs = [
        build_design_description(data),
        build_calculation_book(data),
        build_course_summary(data),
        build_defense_questions(data),
    ]
    for path in outputs:
        print(path.relative_to(ROOT))


if __name__ == "__main__":
    main()
