"""
Module: build_report_pdf
Purpose: Convert the markdown report draft into a simple PDF artifact.
Inputs: report/report.md.
Outputs: report/report.pdf.
Dependencies: Python standard library only.
"""

from __future__ import annotations

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parent
SOURCE_PATH = ROOT / "report.md"
OUTPUT_PATH = ROOT / "report.pdf"
PAGE_WIDTH = 612
PAGE_HEIGHT = 792
LEFT_MARGIN = 54
TOP_MARGIN = 54
BOTTOM_MARGIN = 54
FONT_SIZE = 10
LINE_HEIGHT = 13
LINES_PER_PAGE = (PAGE_HEIGHT - TOP_MARGIN - BOTTOM_MARGIN) // LINE_HEIGHT


def _wrap_line(text: str, max_width: int = 90) -> list[str]:
	if len(text) <= max_width:
		return [text]

	words = text.split()
	if not words:
		return [text]

	wrapped: list[str] = []
	current = words[0]
	for word in words[1:]:
		if len(current) + 1 + len(word) <= max_width:
			current = f"{current} {word}"
		else:
			wrapped.append(current)
			current = word
	wrapped.append(current)
	return wrapped


def _markdown_to_lines(markdown_text: str) -> list[str]:
	lines: list[str] = []
	for raw_line in markdown_text.splitlines():
		line = raw_line.rstrip()
		if not line:
			lines.append("")
			continue

		if line.startswith("```"):
			continue
		if line.startswith("#"):
			line = line.lstrip("#").strip().upper()
		elif line.startswith("- "):
			line = f"* {line[2:].strip()}"
		elif line.startswith("|"):
			line = re.sub(r"\s*\|\s*", " | ", line.strip("|"))

		lines.extend(_wrap_line(line))

	return lines


def _escape_pdf_text(text: str) -> str:
	return text.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")


def _content_stream(page_lines: list[str]) -> bytes:
	parts = [
		"BT",
		f"/F1 {FONT_SIZE} Tf",
		f"{LEFT_MARGIN} {PAGE_HEIGHT - TOP_MARGIN} Td",
	]
	for index, line in enumerate(page_lines):
		if index > 0:
			parts.append(f"0 -{LINE_HEIGHT} Td")
		parts.append(f"({_escape_pdf_text(line)}) Tj")
	parts.append("ET")
	return "\n".join(parts).encode("latin-1", errors="replace")


def _build_pdf(pages: list[list[str]]) -> bytes:
	page_ids = [4 + page_index * 2 for page_index in range(len(pages))]
	objects: list[bytes] = []
	objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
	objects.append(f"<< /Type /Pages /Kids [{' '.join(f'{page_id} 0 R' for page_id in page_ids)}] /Count {len(page_ids)} >>".encode("ascii"))
	objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

	for page_index, page_lines in enumerate(pages):
		page_id = page_ids[page_index]
		content_id = page_id + 1
		page_obj = (
			f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PAGE_WIDTH} {PAGE_HEIGHT}] "
			f"/Resources << /Font << /F1 3 0 R >> >> /Contents {content_id} 0 R >>"
		)
		content = _content_stream(page_lines)
		content_obj = f"<< /Length {len(content)} >>\nstream\n".encode("ascii") + content + b"\nendstream"
		objects.append(page_obj.encode("ascii"))
		objects.append(content_obj)

	pdf = bytearray(b"%PDF-1.4\n")
	offsets = [0]
	for object_index, obj in enumerate(objects, start=1):
		offsets.append(len(pdf))
		pdf.extend(f"{object_index} 0 obj\n".encode("ascii"))
		pdf.extend(obj)
		pdf.extend(b"\nendobj\n")

	xref_start = len(pdf)
	pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
	pdf.extend(b"0000000000 65535 f \n")
	for offset in offsets[1:]:
		pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
	pdf.extend(
		f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_start}\n%%EOF\n".encode(
			"ascii"
		)
	)
	return bytes(pdf)


def main() -> None:
	if not SOURCE_PATH.exists():
		raise FileNotFoundError(f"Missing report source: {SOURCE_PATH}")

	markdown_text = SOURCE_PATH.read_text(encoding="utf-8")
	all_lines = _markdown_to_lines(markdown_text)
	pages = [all_lines[index : index + LINES_PER_PAGE] for index in range(0, len(all_lines), LINES_PER_PAGE)]
	if not pages:
		pages = [["PakLaw AI Report"]]

	OUTPUT_PATH.write_bytes(_build_pdf(pages))
	print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
	main()