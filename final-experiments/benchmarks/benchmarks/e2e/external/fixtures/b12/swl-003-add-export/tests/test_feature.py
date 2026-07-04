"""Tests for CSV export endpoint."""
import csv
import io
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app import app


class TestCsvExport:
    def setup_method(self):
        self.client = app.test_client()

    # ---- JSON endpoint still works ----
    def test_json_reports(self):
        resp = self.client.get("/api/reports")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert len(data["reports"]) == 4

    # ---- CSV export ----
    def test_export_endpoint_exists(self):
        resp = self.client.get("/api/reports/export?format=csv")
        assert resp.status_code == 200

    def test_export_content_type(self):
        resp = self.client.get("/api/reports/export?format=csv")
        assert "text/csv" in resp.content_type

    def test_export_has_header_row(self):
        resp = self.client.get("/api/reports/export?format=csv")
        text = resp.data.decode("utf-8")
        reader = csv.reader(io.StringIO(text))
        header = next(reader)
        assert "id" in header
        assert "title" in header
        assert "amount" in header
        assert "date" in header

    def test_export_has_all_rows(self):
        resp = self.client.get("/api/reports/export?format=csv")
        text = resp.data.decode("utf-8")
        reader = csv.reader(io.StringIO(text))
        rows = list(reader)
        # 1 header + 4 data rows
        assert len(rows) == 5

    def test_export_data_matches_json(self):
        json_resp = self.client.get("/api/reports")
        reports = json.loads(json_resp.data)["reports"]

        csv_resp = self.client.get("/api/reports/export?format=csv")
        text = csv_resp.data.decode("utf-8")
        reader = csv.DictReader(io.StringIO(text))
        csv_rows = list(reader)

        for report, row in zip(reports, csv_rows):
            assert str(report["id"]) == row["id"]
            assert report["title"] == row["title"]

    def test_export_without_format_param(self):
        """Endpoint should handle missing format gracefully."""
        resp = self.client.get("/api/reports/export")
        # Should either default to CSV or return a clear error
        assert resp.status_code in (200, 400)
