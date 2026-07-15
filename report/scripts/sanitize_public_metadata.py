from __future__ import annotations

import argparse
import re
import shutil
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from pypdf import PdfReader, PdfWriter


CP_NS = "http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
DC_NS = "http://purl.org/dc/elements/1.1/"
DCTERMS_NS = "http://purl.org/dc/terms/"
DCMITYPE_NS = "http://purl.org/dc/dcmitype/"
XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"

ET.register_namespace("cp", CP_NS)
ET.register_namespace("dc", DC_NS)
ET.register_namespace("dcterms", DCTERMS_NS)
ET.register_namespace("dcmitype", DCMITYPE_NS)
ET.register_namespace("xsi", XSI_NS)

BASE_TITLE = "220kV新能源汇集变电所电气一次部分初步设计"
DEFENSE_TITLE = f"{BASE_TITLE}答辩汇报"
PUBLIC_AUTHOR = "课程设计项目组（公开版）"
SUBJECT = "发电厂电气部分课程设计"
PUBLIC_THEME_NAME = "课程设计主题"
PUBLIC_TIMESTAMP = "2026-07-15T00:00:00Z"
DOCX_PAGE_COUNTS = {
    "01_": 20,
    "02_": 17,
    "03_": 4,
    "05_": 7,
}

CUSTOM_CONTENT_TYPE_RE = re.compile(
    rb"<Override\b[^>]*PartName=[\"']/docProps/custom\.xml[\"'][^>]*/>",
    re.IGNORECASE,
)
CUSTOM_RELATIONSHIP_RE = re.compile(
    rb"<Relationship\b[^>]*Type=[\"'][^\"']*/custom-properties[\"'][^>]*/>",
    re.IGNORECASE,
)
RSID_ATTRIBUTE_RE = re.compile(rb"\s+w:rsid[A-Za-z0-9]*=[\"'][^\"']*[\"']")
THEME_NAME_RE = re.compile(
    rb"(<(?:[A-Za-z0-9_]+:)?(?:theme|clrScheme|fmtScheme)\b[^>]*\bname=[\"'])[^\"']*([\"'])",
    re.IGNORECASE,
)
APP_STRING_RE = re.compile(rb"(<vt:lpstr>)([^<]*)(</vt:lpstr>)")


def set_core_text(
    root: ET.Element,
    namespace: str,
    local_name: str,
    value: str,
) -> None:
    node = root.find(f"{{{namespace}}}{local_name}")
    if node is None:
        node = ET.SubElement(root, f"{{{namespace}}}{local_name}")
    node.text = value


def sanitize_core_xml(
    data: bytes,
    *,
    title: str,
    author: str,
    normalize_document_history: bool,
) -> bytes:
    root = ET.fromstring(data)
    set_core_text(root, DC_NS, "title", title)
    set_core_text(root, DC_NS, "creator", author)
    set_core_text(root, CP_NS, "lastModifiedBy", author)
    if normalize_document_history:
        set_core_text(root, CP_NS, "revision", "1")
        set_core_text(root, DCTERMS_NS, "created", PUBLIC_TIMESTAMP)
        set_core_text(root, DCTERMS_NS, "modified", PUBLIC_TIMESTAMP)
        last_printed = root.find(f"{{{CP_NS}}}lastPrinted")
        if last_printed is not None:
            root.remove(last_printed)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def sanitize_docx_app_xml(data: bytes, page_count: int) -> bytes:
    replacements = {
        rb"<Pages>\d+</Pages>": f"<Pages>{page_count}</Pages>".encode("ascii"),
        rb"<TotalTime>\d+</TotalTime>": b"<TotalTime>0</TotalTime>",
        rb"<Company>.*?</Company>": b"<Company></Company>",
    }
    for pattern, replacement in replacements.items():
        data = re.sub(pattern, replacement, data, count=1)
    return data


def sanitize_pptx_app_xml(data: bytes) -> bytes:
    matches = list(APP_STRING_RE.finditer(data))
    if len(matches) < 2:
        raise ValueError("PowerPoint app properties do not contain a theme entry")
    theme_entry = matches[1]
    theme_name = PUBLIC_THEME_NAME.encode("utf-8")
    return (
        data[: theme_entry.start()]
        + theme_entry.group(1)
        + theme_name
        + theme_entry.group(3)
        + data[theme_entry.end() :]
    )


def sanitize_ooxml(path: Path) -> None:
    is_docx = path.suffix.lower() == ".docx"
    is_pptx = path.suffix.lower() == ".pptx"
    title = DEFENSE_TITLE if path.suffix.lower() == ".pptx" else BASE_TITLE
    author = "" if is_docx else PUBLIC_AUTHOR

    with tempfile.NamedTemporaryFile(
        delete=False,
        suffix=path.suffix,
        dir=path.parent,
    ) as handle:
        temp_path = Path(handle.name)

    try:
        with ZipFile(path, "r") as source, ZipFile(
            temp_path,
            "w",
            compression=ZIP_DEFLATED,
        ) as target:
            for info in source.infolist():
                if info.filename == "docProps/custom.xml":
                    continue

                data = source.read(info.filename)
                if info.filename == "docProps/core.xml":
                    data = sanitize_core_xml(
                        data,
                        title=title,
                        author=author,
                        normalize_document_history=is_docx,
                    )
                elif is_docx and info.filename == "docProps/app.xml":
                    prefix = path.name[:3]
                    data = sanitize_docx_app_xml(data, DOCX_PAGE_COUNTS[prefix])
                elif info.filename == "[Content_Types].xml":
                    data = CUSTOM_CONTENT_TYPE_RE.sub(b"", data)
                elif info.filename == "_rels/.rels":
                    data = CUSTOM_RELATIONSHIP_RE.sub(b"", data)
                elif is_docx and info.filename.startswith("word/") and info.filename.endswith(".xml"):
                    data = RSID_ATTRIBUTE_RE.sub(b"", data)
                elif is_pptx and info.filename.startswith("ppt/theme/") and info.filename.endswith(".xml"):
                    theme_name = PUBLIC_THEME_NAME.encode("utf-8")
                    data = THEME_NAME_RE.sub(
                        lambda match: match.group(1) + theme_name + match.group(2),
                        data,
                    )
                elif is_pptx and info.filename == "docProps/app.xml":
                    data = sanitize_pptx_app_xml(data)

                target.writestr(info, data)

        shutil.move(temp_path, path)
    finally:
        temp_path.unlink(missing_ok=True)


def sanitize_pdf(path: Path) -> None:
    reader = PdfReader(path)
    writer = PdfWriter()
    writer.clone_document_from_reader(reader)

    title = DEFENSE_TITLE if path.name.startswith("04_") else BASE_TITLE
    creator = "Microsoft PowerPoint" if path.name.startswith("04_") else "Microsoft Word"
    metadata = dict(reader.metadata or {})
    metadata.update(
        {
            "/Title": title,
            "/Author": PUBLIC_AUTHOR,
            "/Subject": f"{SUBJECT}答辩汇报" if path.name.startswith("04_") else SUBJECT,
            "/Creator": creator,
            "/Producer": creator,
        }
    )
    writer.add_metadata(metadata)

    with tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".pdf",
        dir=path.parent,
    ) as handle:
        temp_path = Path(handle.name)

    try:
        with temp_path.open("wb") as stream:
            writer.write(stream)
        shutil.move(temp_path, path)
    finally:
        temp_path.unlink(missing_ok=True)


def candidate_files(report_dir: Path) -> list[Path]:
    supported = {".docx", ".pptx", ".pdf"}
    return sorted(
        path
        for path in report_dir.iterdir()
        if path.is_file()
        and path.suffix.lower() in supported
        and not path.name.startswith("~$")
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sanitize public metadata in report DOCX, PPTX, and PDF files."
    )
    parser.add_argument(
        "--report-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Directory containing the public report deliverables.",
    )
    parser.add_argument(
        "files",
        nargs="*",
        type=Path,
        help="Optional explicit files. When omitted, all supported files are sanitized.",
    )
    args = parser.parse_args()

    report_dir = args.report_dir.resolve()
    paths = [path.resolve() for path in args.files] or candidate_files(report_dir)
    if not paths:
        raise SystemExit(f"No DOCX, PPTX, or PDF files found in {report_dir}")

    for path in paths:
        if not path.is_file():
            raise FileNotFoundError(path)
        suffix = path.suffix.lower()
        if suffix in {".docx", ".pptx"}:
            sanitize_ooxml(path)
        elif suffix == ".pdf":
            sanitize_pdf(path)
        else:
            raise ValueError(f"Unsupported file type: {path}")
        print(path)


if __name__ == "__main__":
    main()
