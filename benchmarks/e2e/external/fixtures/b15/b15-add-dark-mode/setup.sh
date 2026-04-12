#!/usr/bin/env bash
# Setup for b15-add-dark-mode
# Creates a simple Python web app with a settings page lacking dark mode.
set -euo pipefail

mkdir -p templates static

# Settings module — no dark mode setting
cat > settings.py << 'PYTHON'
"""Application settings module."""


class Settings:
    """Application configuration."""

    def __init__(self):
        self.username = "default_user"
        self.language = "en"
        self.notifications_enabled = True
        self.font_size = 14

    def to_dict(self):
        return {
            "username": self.username,
            "language": self.language,
            "notifications_enabled": self.notifications_enabled,
            "font_size": self.font_size,
        }

    def update(self, key, value):
        if hasattr(self, key):
            setattr(self, key, value)
            return True
        return False
PYTHON

# Settings HTML template — no dark mode toggle
cat > templates/settings.html << 'HTML'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Settings</title>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <div class="container">
        <h1>Settings</h1>
        <form id="settings-form" method="POST" action="/settings">
            <div class="form-group">
                <label for="username">Username:</label>
                <input type="text" id="username" name="username" value="{{ username }}">
            </div>
            <div class="form-group">
                <label for="language">Language:</label>
                <select id="language" name="language">
                    <option value="en">English</option>
                    <option value="es">Spanish</option>
                    <option value="fr">French</option>
                </select>
            </div>
            <div class="form-group">
                <label for="notifications">
                    <input type="checkbox" id="notifications" name="notifications_enabled">
                    Enable Notifications
                </label>
            </div>
            <div class="form-group">
                <label for="font_size">Font Size:</label>
                <input type="number" id="font_size" name="font_size" min="10" max="24" value="14">
            </div>
            <button type="submit">Save Settings</button>
        </form>
    </div>
</body>
</html>
HTML

# Stylesheet — light theme only
cat > static/style.css << 'CSS'
body {
    font-family: Arial, sans-serif;
    background-color: #ffffff;
    color: #333333;
    margin: 0;
    padding: 20px;
}

.container {
    max-width: 600px;
    margin: 0 auto;
}

h1 {
    color: #222222;
    border-bottom: 2px solid #eeeeee;
    padding-bottom: 10px;
}

.form-group {
    margin-bottom: 15px;
}

label {
    display: block;
    margin-bottom: 5px;
    font-weight: bold;
}

input[type="text"],
input[type="number"],
select {
    width: 100%;
    padding: 8px;
    border: 1px solid #cccccc;
    border-radius: 4px;
    box-sizing: border-box;
}

button {
    background-color: #4CAF50;
    color: white;
    padding: 10px 20px;
    border: none;
    border-radius: 4px;
    cursor: pointer;
}

button:hover {
    background-color: #45a049;
}
CSS

echo "Setup complete. Web app created with settings page (no dark mode)."
