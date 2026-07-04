"""Legacy report generator using os.path and string concatenation.

NOTE: To be migrated to pathlib.Path, f-strings, and dataclass patterns.
"""
import os


def ensure_report_dir(base_dir: str, report_name: str) -> str:
    """Create a subdirectory for a named report. Return the path."""
    report_dir = os.path.join(base_dir, report_name)
    if not os.path.isdir(report_dir):
        os.makedirs(report_dir)
    return report_dir


def write_html_report(report_dir: str, title: str, rows: list[list[str]]) -> str:
    """Write a simple HTML report to report_dir/report.html. Return the file path."""
    html = "<html><head><title>" + title + "</title></head><body>"
    html += "<h1>" + title + "</h1>"
    html += "<table>"
    for row in rows:
        html += "<tr>"
        for cell in row:
            html += "<td>" + cell + "</td>"
        html += "</tr>"
    html += "</table></body></html>"
    out_path = os.path.join(report_dir, "report.html")
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(html)
    return out_path


def read_report(path: str) -> str:
    """Return the HTML content of a report file, or empty string if not found."""
    if not os.path.exists(path):
        return ""
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def list_reports(base_dir: str) -> list[str]:
    """Return sorted list of report subdirectory names in base_dir."""
    if not os.path.isdir(base_dir):
        return []
    result = []
    for name in os.listdir(base_dir):
        full = os.path.join(base_dir, name)
        if os.path.isdir(full):
            result.append(name)
    return sorted(result)


def delete_report(report_dir: str) -> bool:
    """Delete the report.html inside report_dir. Return True if deleted."""
    path = os.path.join(report_dir, "report.html")
    if os.path.exists(path):
        os.remove(path)
        return True
    return False
