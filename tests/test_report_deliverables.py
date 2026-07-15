from __future__ import annotations

import re
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZipFile

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "report"
BASE_TITLE = "220kV新能源汇集变电所电气一次部分初步设计"
DEFENSE_TITLE = f"{BASE_TITLE}答辩汇报"
PUBLIC_AUTHOR = "课程设计项目组（公开版）"

PDF_PAGES = {
    "01_220kV新能源汇集变电所_技术设计说明书.pdf": 20,
    "02_220kV新能源汇集变电所_技术设计计算书.pdf": 17,
    "03_220kV新能源汇集变电所_课程设计总结.pdf": 4,
    "04_220kV新能源汇集变电所_答辩汇报.pdf": 11,
    "05_220kV新能源汇集变电所_答辩问题清单.pdf": 7,
}

DOCX_FILES = (
    "01_220kV新能源汇集变电所_技术设计说明书.docx",
    "02_220kV新能源汇集变电所_技术设计计算书.docx",
    "03_220kV新能源汇集变电所_课程设计总结.docx",
    "05_220kV新能源汇集变电所_答辩问题清单.docx",
)

PPTX_FILE = "04_220kV新能源汇集变电所_答辩汇报.pptx"


def core_properties(archive: ZipFile) -> dict[str, str]:
    root = ET.fromstring(archive.read("docProps/core.xml"))
    return {element.tag.rsplit("}", 1)[-1]: element.text or "" for element in root}


class ReportDeliverableTests(unittest.TestCase):
    def test_expected_report_files_and_reproduction_scripts_exist(self) -> None:
        expected = set(PDF_PAGES) | set(DOCX_FILES) | {PPTX_FILE}
        for name in expected:
            path = REPORT_DIR / name
            self.assertTrue(path.is_file(), name)
            self.assertGreater(path.stat().st_size, 1024, name)

        for name in (
            "build_reports.py",
            "export_reports.ps1",
            "sanitize_public_metadata.py",
        ):
            self.assertTrue((REPORT_DIR / "scripts" / name).is_file(), name)

    def test_pdf_page_counts_and_public_metadata(self) -> None:
        for name, expected_pages in PDF_PAGES.items():
            with self.subTest(name=name):
                reader = PdfReader(REPORT_DIR / name)
                metadata = dict(reader.metadata or {})
                self.assertEqual(len(reader.pages), expected_pages)
                self.assertEqual(metadata.get("/Author"), PUBLIC_AUTHOR)
                expected_title = DEFENSE_TITLE if name.startswith("04_") else BASE_TITLE
                self.assertEqual(metadata.get("/Title"), expected_title)
                self.assertNotEqual(metadata.get("/Title"), "Presentation")

    def test_docx_packages_have_public_privacy_metadata(self) -> None:
        rsid_attribute = re.compile(rb"\s+w:rsid[A-Za-z0-9]*=[\"'][^\"']*[\"']")
        for name in DOCX_FILES:
            with self.subTest(name=name), ZipFile(REPORT_DIR / name) as archive:
                self.assertIsNone(archive.testzip())
                self.assertNotIn("docProps/custom.xml", archive.namelist())
                properties = core_properties(archive)
                self.assertEqual(properties.get("creator", ""), "")
                self.assertEqual(properties.get("lastModifiedBy", ""), "")

                for member in archive.namelist():
                    if member.startswith("word/") and member.endswith(".xml"):
                        self.assertIsNone(rsid_attribute.search(archive.read(member)), member)

    def test_pptx_is_valid_public_and_has_no_generator_theme_name(self) -> None:
        path = REPORT_DIR / PPTX_FILE
        with ZipFile(path) as archive:
            self.assertIsNone(archive.testzip())
            properties = core_properties(archive)
            self.assertEqual(properties.get("title"), DEFENSE_TITLE)
            self.assertEqual(properties.get("creator"), PUBLIC_AUTHOR)
            self.assertEqual(properties.get("lastModifiedBy"), PUBLIC_AUTHOR)

            slide_count = sum(
                1
                for name in archive.namelist()
                if re.fullmatch(r"ppt/slides/slide\d+\.xml", name)
            )
            self.assertEqual(slide_count, 11)

            expected_theme_name = "课程设计主题"
            for name in archive.namelist():
                if not name.startswith("ppt/theme/") or not name.endswith(".xml"):
                    continue
                theme_root = ET.fromstring(archive.read(name))
                for element in theme_root.iter():
                    if element.tag.rsplit("}", 1)[-1] in {"theme", "clrScheme", "fmtScheme"}:
                        self.assertEqual(element.attrib.get("name"), expected_theme_name)

            self.assertIn(expected_theme_name.encode("utf-8"), archive.read("docProps/app.xml"))

            core_xml = archive.read("docProps/core.xml")
            self.assertIn(b"xmlns:dcterms=", core_xml)
            self.assertIn(b'xsi:type="dcterms:W3CDTF"', core_xml)


if __name__ == "__main__":
    unittest.main()
