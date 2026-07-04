#!/usr/bin/env bash
set -euo pipefail

mkdir -p project

cat > project/requirements.md << 'EOF'
# Project Requirements: Inventory Management System

## Overview
A multi-user inventory management system for a mid-size warehouse with 50 concurrent users, ~500K product records, and real-time stock tracking.

## Functional Requirements
- FR1: Multi-user concurrent access (50+ simultaneous users)
- FR2: ACID transactions for stock updates (debit/credit must be atomic)
- FR3: Complex reporting queries (joins across products, orders, suppliers)
- FR4: Full-text search on product descriptions
- FR5: Role-based access control (admin, manager, warehouse staff)

## Non-Functional Requirements
- NFR1: 99.9% uptime (production system)
- NFR2: Response time < 200ms for stock queries
- NFR3: Must run on company-managed Linux servers (no cloud dependency)
- NFR4: Team has SQL expertise but limited NoSQL experience
- NFR5: Budget for infrastructure: moderate (can afford dedicated DB server)
- NFR6: Data integrity is critical (financial audit requirements)

## Data Characteristics
- 500K product records, growing ~10% per year
- 2M order records per year
- Relational data: products → categories, orders → line items → products
- Schema is well-defined and unlikely to change frequently
EOF

cat > project/proposal_sqlite.md << 'EOF'
# Proposal A: SQLite

## Overview
Use SQLite as the embedded database. Zero configuration, serverless.

## Pros
- Zero setup, no separate server process
- Excellent for reads, very fast for small datasets
- No administration overhead
- Free, public domain

## Cons
- Limited concurrent write support (single writer)
- No built-in user access control
- Not designed for network access (embedded only)
- No replication or clustering

## Fit Assessment
- Good for prototypes, single-user apps, embedded systems
- Less suitable for multi-user production systems
EOF

cat > project/proposal_postgres.md << 'EOF'
# Proposal B: PostgreSQL

## Overview
Use PostgreSQL as the relational database server. Industry-standard RDBMS.

## Pros
- Full ACID compliance with MVCC for concurrent access
- Excellent support for complex queries and joins
- Built-in full-text search
- Role-based access control built in
- Mature replication and backup tools
- Team already has SQL expertise
- Free, open source

## Cons
- Requires server administration
- More complex setup than SQLite
- Vertical scaling has limits (though sufficient for 500K records)
- Schema migrations require planning

## Fit Assessment
- Excellent for multi-user transactional systems
- Strong fit for relational data with complex queries
- Industry standard for inventory/ERP systems
EOF

cat > project/proposal_mongo.md << 'EOF'
# Proposal C: MongoDB

## Overview
Use MongoDB as a document database. Flexible schema, horizontal scaling.

## Pros
- Flexible schema (good for evolving data models)
- Horizontal scaling (sharding)
- Good for semi-structured or nested data
- Rich query language for documents

## Cons
- No native multi-document ACID transactions (added in 4.0 but with caveats)
- Joins are expensive (data is denormalized)
- Team has no NoSQL experience (learning curve)
- Data integrity less strict than RDBMS
- Full-text search less mature than PostgreSQL
- Higher memory usage for equivalent data

## Fit Assessment
- Best for rapidly evolving schemas, content management, IoT data
- Less ideal for financial/inventory systems requiring strict integrity
EOF

cat > project/answer_template.md << 'EOF'
# Database Selection Decision

## Evaluation Summary

### Option A: SQLite
- Fit score (1-10):
- Key strength:
- Key weakness:

### Option B: PostgreSQL
- Fit score (1-10):
- Key strength:
- Key weakness:

### Option C: MongoDB
- Fit score (1-10):
- Key strength:
- Key weakness:

## Decision
**Selected option:**

## Justification
<!-- Reference specific requirements (FR1, NFR2, etc.) to justify your choice -->

## Trade-offs Acknowledged
<!-- What are we giving up by not choosing the other options? -->

## Risk Mitigation
<!-- Any risks with the chosen option and how to mitigate them -->
EOF

echo "Setup complete. Three database proposals ready for evaluation."
