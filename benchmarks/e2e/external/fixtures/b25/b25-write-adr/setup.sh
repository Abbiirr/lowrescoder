#!/usr/bin/env bash
set -euo pipefail

mkdir -p project

cat > project/context.md << 'EOF'
# Decision Context: Authentication Strategy

## Background
We are building a SaaS platform with a React frontend (SPA) and a Python (FastAPI) backend deployed across 3 regions. Currently no authentication — we need to add it before launch.

## Constraints
- Must support mobile apps (iOS/Android) in addition to web
- Backend is stateless and horizontally scaled (5-20 instances)
- Users authenticate with email + password (no SSO requirement yet)
- Must support "remember me" (long-lived sessions up to 30 days)
- Team of 4 developers, timeline: 3 weeks to implement
- Security audit in 2 months — must be defensible

## Stakeholder Concerns
- **CTO:** Wants stateless backend, no sticky sessions
- **Security Lead:** Wants token revocation capability
- **Mobile Lead:** Wants simple token-based auth for apps
- **Product:** Wants "remember me" and multi-device support
EOF

cat > project/option_jwt.md << 'EOF'
# Option 1: JWT (JSON Web Tokens)

## Description
Issue signed JWT access tokens (short-lived, 15 min) and refresh tokens (long-lived, 30 days). Stored in httpOnly cookies for web, secure storage for mobile.

## Pros
- Stateless — no server-side session storage needed
- Works well with horizontal scaling
- Standard format, well-understood
- Works natively for mobile apps

## Cons
- Cannot revoke individual tokens (until they expire)
- Token size larger than session IDs
- Refresh token rotation adds complexity
- Need to handle token refresh flow in frontend

## Implementation Effort
2-3 weeks for a senior developer
EOF

cat > project/option_session.md << 'EOF'
# Option 2: Server-Side Sessions (Redis)

## Description
Store sessions in Redis. Issue opaque session IDs to clients. All session validation happens server-side.

## Pros
- Easy to revoke (delete from Redis)
- Small token size (just a session ID)
- Full control over session state
- Simple to implement

## Cons
- Requires Redis infrastructure (added dependency)
- Not truly stateless (contradicts CTO's preference)
- Requires sticky sessions or shared session store
- Less convenient for mobile apps (cookie handling)

## Implementation Effort
1-2 weeks for a senior developer
EOF

cat > project/option_oauth.md << 'EOF'
# Option 3: OAuth 2.0 Delegation (Auth0/Okta)

## Description
Delegate authentication to a third-party provider (Auth0 or Okta). Use their SDKs for login flows.

## Pros
- Battle-tested security (pass the security audit easily)
- Built-in MFA, SSO, social login
- Reduces implementation effort for auth flows
- Handles token management, revocation, etc.

## Cons
- Monthly cost ($0.05-$0.10 per user per month)
- Vendor lock-in
- Less control over auth flows
- Latency for token validation (network call to provider)
- May be overkill for email+password only

## Implementation Effort
1 week for integration, ongoing vendor management
EOF

cat > project/adr_template.md << 'EOF'
# ADR-NNN: [Title]

## Status
[Proposed | Accepted | Deprecated | Superseded]

## Context
<!-- What is the issue? Why do we need to make this decision? -->

## Decision Drivers
<!-- Key factors influencing the decision -->

## Considered Options
1. [Option 1]
2. [Option 2]
3. [Option 3]

## Decision
<!-- Which option was chosen and why? -->

## Consequences

### Positive
<!-- Good things that come from this decision -->

### Negative
<!-- Downsides and risks of this decision -->

### Neutral
<!-- Things that change but are neither good nor bad -->

## Follow-up Actions
<!-- What needs to happen to implement this decision? -->
EOF

echo "Setup complete. Context and 3 authentication options ready for ADR."
