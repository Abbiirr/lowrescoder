#!/usr/bin/env bash
set -euo pipefail

cat > package.json << 'JSON'
{
  "name": "my-web-app",
  "version": "2.0.0",
  "description": "A sample web application",
  "main": "index.js",
  "dependencies": {
    "express": "^4.18.0",
    "lodash": "^4.17.21",
    "axios": "^1.6.0",
    "cors": "^2.8.5"
  },
  "devDependencies": {
    "jest": "^29.7.0",
    "eslint": "^8.56.0"
  }
}
JSON

# Stale lock file: missing axios and cors, has leftover moment
cat > package-lock.json << 'JSON'
{
  "name": "my-web-app",
  "version": "1.5.0",
  "lockfileVersion": 3,
  "requires": true,
  "packages": {
    "": {
      "name": "my-web-app",
      "version": "1.5.0",
      "dependencies": {
        "express": "^4.18.0",
        "lodash": "^4.17.21",
        "moment": "^2.29.0"
      },
      "devDependencies": {
        "jest": "^29.7.0"
      }
    },
    "node_modules/express": {
      "version": "4.18.2",
      "resolved": "https://registry.npmjs.org/express/-/express-4.18.2.tgz",
      "integrity": "sha512-abc123"
    },
    "node_modules/lodash": {
      "version": "4.17.21",
      "resolved": "https://registry.npmjs.org/lodash/-/lodash-4.17.21.tgz",
      "integrity": "sha512-def456"
    },
    "node_modules/moment": {
      "version": "2.29.4",
      "resolved": "https://registry.npmjs.org/moment/-/moment-2.29.4.tgz",
      "integrity": "sha512-ghi789"
    },
    "node_modules/jest": {
      "version": "29.7.0",
      "resolved": "https://registry.npmjs.org/jest/-/jest-29.7.0.tgz",
      "integrity": "sha512-jkl012",
      "dev": true
    }
  }
}
JSON

echo "Setup complete. package-lock.json is out of sync with package.json."
