#!/usr/bin/env bash
# Setup for b17-extract-class
# Creates a monolithic app.py with a class that should be extracted.
set -euo pipefail

# Monolithic app.py with multiple classes
cat > app.py << 'PYTHON'
"""Monolithic application module.

This file has grown too large. The EmailService class should be
extracted into its own module.
"""
import re
from datetime import datetime
from typing import Optional


class UserManager:
    """Manages user accounts."""

    def __init__(self):
        self.users = {}

    def create_user(self, username: str, email: str) -> dict:
        if username in self.users:
            raise ValueError(f"User {username} already exists")
        user = {
            "username": username,
            "email": email,
            "created_at": datetime.now().isoformat(),
        }
        self.users[username] = user
        return user

    def get_user(self, username: str) -> Optional[dict]:
        return self.users.get(username)

    def list_users(self) -> list:
        return list(self.users.values())


class EmailService:
    """Handles email composition and sending.

    This class should be extracted to its own module.
    """

    TEMPLATE_WELCOME = "Welcome to our service, {name}!"
    TEMPLATE_RESET = "Click here to reset your password: {link}"
    TEMPLATE_NOTIFICATION = "You have a new notification: {message}"

    def __init__(self, sender: str = "noreply@example.com"):
        self.sender = sender
        self.sent_emails = []
        self.templates = {
            "welcome": self.TEMPLATE_WELCOME,
            "reset": self.TEMPLATE_RESET,
            "notification": self.TEMPLATE_NOTIFICATION,
        }

    def validate_address(self, email: str) -> bool:
        """Validate an email address format."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))

    def compose(self, to: str, subject: str, body: str) -> dict:
        """Compose an email message."""
        if not self.validate_address(to):
            raise ValueError(f"Invalid email address: {to}")
        return {
            "from": self.sender,
            "to": to,
            "subject": subject,
            "body": body,
            "timestamp": datetime.now().isoformat(),
        }

    def send(self, to: str, subject: str, body: str) -> bool:
        """Send an email (simulated)."""
        email = self.compose(to, subject, body)
        self.sent_emails.append(email)
        return True

    def send_template(self, to: str, template_name: str, **kwargs) -> bool:
        """Send an email using a template."""
        if template_name not in self.templates:
            raise ValueError(f"Unknown template: {template_name}")
        body = self.templates[template_name].format(**kwargs)
        subject = f"[{template_name.title()}]"
        return self.send(to, subject, body)

    def get_sent_count(self) -> int:
        """Return count of sent emails."""
        return len(self.sent_emails)

    def get_sent_to(self, email: str) -> list:
        """Return all emails sent to a specific address."""
        return [e for e in self.sent_emails if e["to"] == email]


class TaskTracker:
    """Tracks tasks and their status."""

    def __init__(self):
        self.tasks = []
        self._next_id = 1

    def create_task(self, title: str, assignee: str = None) -> dict:
        task = {
            "id": self._next_id,
            "title": title,
            "assignee": assignee,
            "status": "open",
            "created_at": datetime.now().isoformat(),
        }
        self._next_id += 1
        self.tasks.append(task)
        return task

    def complete_task(self, task_id: int) -> bool:
        for task in self.tasks:
            if task["id"] == task_id:
                task["status"] = "completed"
                return True
        return False

    def get_open_tasks(self) -> list:
        return [t for t in self.tasks if t["status"] == "open"]


class Application:
    """Main application coordinating all services."""

    def __init__(self):
        self.users = UserManager()
        self.email = EmailService()
        self.tasks = TaskTracker()

    def register_user(self, username: str, email: str) -> dict:
        user = self.users.create_user(username, email)
        self.email.send_template(email, "welcome", name=username)
        return user

    def assign_task(self, title: str, username: str) -> dict:
        user = self.users.get_user(username)
        if not user:
            raise ValueError(f"User {username} not found")
        task = self.tasks.create_task(title, username)
        self.email.send_template(
            user["email"], "notification",
            message=f"You have been assigned: {title}"
        )
        return task
PYTHON

# Tests
cat > test_app.py << 'PYTHON'
"""Tests for application classes."""
import pytest
from app import UserManager, EmailService, TaskTracker, Application


class TestUserManager:
    def test_create_user(self):
        um = UserManager()
        user = um.create_user("alice", "alice@example.com")
        assert user["username"] == "alice"
        assert user["email"] == "alice@example.com"

    def test_duplicate_user(self):
        um = UserManager()
        um.create_user("alice", "alice@example.com")
        with pytest.raises(ValueError):
            um.create_user("alice", "alice2@example.com")

    def test_get_user(self):
        um = UserManager()
        um.create_user("alice", "alice@example.com")
        user = um.get_user("alice")
        assert user is not None
        assert um.get_user("missing") is None

    def test_list_users(self):
        um = UserManager()
        um.create_user("alice", "alice@example.com")
        um.create_user("bob", "bob@example.com")
        assert len(um.list_users()) == 2


class TestEmailService:
    def test_validate_address(self):
        es = EmailService()
        assert es.validate_address("user@example.com") is True
        assert es.validate_address("invalid") is False

    def test_compose(self):
        es = EmailService("sender@example.com")
        email = es.compose("to@example.com", "Subject", "Body")
        assert email["from"] == "sender@example.com"
        assert email["to"] == "to@example.com"
        assert email["subject"] == "Subject"

    def test_compose_invalid_address(self):
        es = EmailService()
        with pytest.raises(ValueError):
            es.compose("invalid", "Subject", "Body")

    def test_send(self):
        es = EmailService()
        assert es.send("to@example.com", "Hi", "Hello") is True
        assert es.get_sent_count() == 1

    def test_send_template(self):
        es = EmailService()
        es.send_template("to@example.com", "welcome", name="Alice")
        sent = es.get_sent_to("to@example.com")
        assert len(sent) == 1
        assert "Alice" in sent[0]["body"]

    def test_unknown_template(self):
        es = EmailService()
        with pytest.raises(ValueError):
            es.send_template("to@example.com", "nonexistent")


class TestTaskTracker:
    def test_create_task(self):
        tt = TaskTracker()
        task = tt.create_task("Fix bug")
        assert task["title"] == "Fix bug"
        assert task["status"] == "open"

    def test_complete_task(self):
        tt = TaskTracker()
        task = tt.create_task("Fix bug")
        assert tt.complete_task(task["id"]) is True
        assert tt.get_open_tasks() == []

    def test_complete_nonexistent(self):
        tt = TaskTracker()
        assert tt.complete_task(999) is False


class TestApplication:
    def test_register_user(self):
        app = Application()
        user = app.register_user("alice", "alice@example.com")
        assert user["username"] == "alice"
        assert app.email.get_sent_count() == 1

    def test_assign_task(self):
        app = Application()
        app.register_user("alice", "alice@example.com")
        task = app.assign_task("Fix bug", "alice")
        assert task["assignee"] == "alice"
        # 1 welcome email + 1 task notification
        assert app.email.get_sent_count() == 2
PYTHON

echo "Setup complete. Monolithic app.py with EmailService to extract."
