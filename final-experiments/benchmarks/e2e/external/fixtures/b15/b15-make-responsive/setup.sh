#!/usr/bin/env bash
# Setup for b15-make-responsive
# Creates an HTML/CSS dashboard with fixed-width layout that breaks on mobile.
set -euo pipefail

# Dashboard HTML — no viewport meta, fixed widths
cat > dashboard.html << 'HTML'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Dashboard</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <div class="dashboard">
        <div class="sidebar">
            <h2>Navigation</h2>
            <ul>
                <li><a href="#">Home</a></li>
                <li><a href="#">Reports</a></li>
                <li><a href="#">Users</a></li>
                <li><a href="#">Settings</a></li>
            </ul>
        </div>
        <div class="main-content">
            <h1>Dashboard</h1>
            <div class="stats-row">
                <div class="stat-card">
                    <h3>Total Users</h3>
                    <p class="stat-value">1,234</p>
                </div>
                <div class="stat-card">
                    <h3>Revenue</h3>
                    <p class="stat-value">$45,678</p>
                </div>
                <div class="stat-card">
                    <h3>Orders</h3>
                    <p class="stat-value">567</p>
                </div>
                <div class="stat-card">
                    <h3>Growth</h3>
                    <p class="stat-value">12.5%</p>
                </div>
            </div>
            <div class="data-table">
                <table>
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Name</th>
                            <th>Email</th>
                            <th>Department</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr><td>1</td><td>Alice</td><td>alice@example.com</td><td>Engineering</td><td>Active</td></tr>
                        <tr><td>2</td><td>Bob</td><td>bob@example.com</td><td>Marketing</td><td>Active</td></tr>
                        <tr><td>3</td><td>Charlie</td><td>charlie@example.com</td><td>Sales</td><td>Inactive</td></tr>
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</body>
</html>
HTML

# Stylesheet — all fixed pixel widths, no responsiveness
cat > style.css << 'CSS'
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: Arial, sans-serif;
    background-color: #f4f4f4;
}

.dashboard {
    width: 1200px;
    margin: 0 auto;
    display: flex;
}

.sidebar {
    width: 250px;
    background-color: #2c3e50;
    color: white;
    padding: 20px;
    min-height: 100vh;
}

.sidebar h2 {
    margin-bottom: 20px;
}

.sidebar ul {
    list-style: none;
}

.sidebar li {
    margin-bottom: 10px;
}

.sidebar a {
    color: #ecf0f1;
    text-decoration: none;
}

.main-content {
    width: 950px;
    padding: 20px;
}

.stats-row {
    display: flex;
    gap: 20px;
    margin-bottom: 30px;
}

.stat-card {
    width: 220px;
    background: white;
    padding: 20px;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.stat-value {
    font-size: 28px;
    font-weight: bold;
    color: #2c3e50;
    margin-top: 10px;
}

.data-table {
    background: white;
    border-radius: 8px;
    padding: 20px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

table {
    width: 900px;
    border-collapse: collapse;
}

th, td {
    padding: 12px 15px;
    text-align: left;
    border-bottom: 1px solid #eee;
}

th {
    background-color: #2c3e50;
    color: white;
}
CSS

echo "Setup complete. Dashboard with fixed-width layout created."
