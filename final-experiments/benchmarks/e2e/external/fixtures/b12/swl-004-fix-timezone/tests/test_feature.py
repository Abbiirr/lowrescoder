"""Tests for timezone-aware event scheduling."""
import json
import sys
import os
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app import app


class TestTimezone:
    def setup_method(self):
        self.client = app.test_client()
        # Reset events
        from app import EVENTS
        EVENTS.clear()

    def _create_event(self, title, start_time):
        resp = self.client.post(
            "/api/events",
            json={"title": title, "start_time": start_time},
            content_type="application/json",
        )
        return resp

    def test_create_event_with_utc(self):
        resp = self._create_event("Meeting", "2025-06-15T14:00:00+00:00")
        assert resp.status_code == 201

    def test_display_utc_event_in_utc(self):
        """An event at 14:00 UTC displayed in UTC should show 14:00."""
        self._create_event("Meeting", "2025-06-15T14:00:00+00:00")
        resp = self.client.get("/api/events/1/display_time?tz=UTC")
        data = json.loads(resp.data)
        # The display_time should contain 14:00
        assert "14:00" in data["display_time"]

    def test_display_utc_event_in_offset(self):
        """An event at 14:00 UTC displayed in UTC+5 should show 19:00."""
        self._create_event("Meeting", "2025-06-15T14:00:00+00:00")
        resp = self.client.get("/api/events/1/display_time?tz=UTC%2B05:00")
        data = json.loads(resp.data)
        assert "19:00" in data["display_time"]

    def test_display_with_negative_offset(self):
        """An event at 14:00 UTC displayed in UTC-5 should show 09:00."""
        self._create_event("Meeting", "2025-06-15T14:00:00+00:00")
        resp = self.client.get("/api/events/1/display_time?tz=UTC-05:00")
        data = json.loads(resp.data)
        assert "09:00" in data["display_time"]

    def test_create_with_offset_store_correctly(self):
        """An event created at 10:00+05:00 (= 05:00 UTC) should show 05:00 in UTC."""
        self._create_event("Standup", "2025-06-15T10:00:00+05:00")
        resp = self.client.get("/api/events/1/display_time?tz=UTC")
        data = json.loads(resp.data)
        assert "05:00" in data["display_time"]

    def test_timezone_field_in_response(self):
        self._create_event("Demo", "2025-06-15T12:00:00+00:00")
        resp = self.client.get("/api/events/1/display_time?tz=UTC%2B03:00")
        data = json.loads(resp.data)
        assert "timezone" in data

    def test_event_not_found(self):
        resp = self.client.get("/api/events/999/display_time?tz=UTC")
        assert resp.status_code == 404
