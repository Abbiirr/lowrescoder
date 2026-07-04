#!/usr/bin/env bash
set -euo pipefail

mkdir -p project

cat > project/requirements.md << 'EOF'
# Notification Microservice Requirements

## Overview
A notification service that sends email, SMS, and push notifications triggered by events from 5 upstream services. Expected volume: 10K-50K notifications/day, growing to 500K/day within 2 years.

## Functional Requirements
- R1: Send email, SMS, and push notifications
- R2: Support templated messages with variable substitution
- R3: Retry failed deliveries (up to 3 attempts with exponential backoff)
- R4: Track delivery status (sent, delivered, failed, bounced)
- R5: Rate limiting per channel (email: 100/sec, SMS: 10/sec, push: 1000/sec)

## Non-Functional Requirements
- R6: Handle 500K notifications/day at peak (within 2 years)
- R7: 99.95% delivery success rate
- R8: Maximum 5-second latency from trigger to send attempt
- R9: Team of 3 backend engineers (Python, some Go experience)
- R10: Budget: $500/month infrastructure initially, scaling to $2K/month
- R11: Must integrate with existing Kubernetes cluster
EOF

cat > project/arch_a.md << 'EOF'
# Architecture A: Event-Driven with Message Queue

## Overview
Upstream services publish events to RabbitMQ. Notification workers consume events, render templates, and dispatch via channels.

## Components
1. **RabbitMQ** — message broker with exchange per event type
2. **Worker Pool** — Python workers (3 per channel: email, SMS, push)
3. **Template Engine** — Jinja2 templates stored in PostgreSQL
4. **Status Tracker** — PostgreSQL table for delivery tracking
5. **Dead Letter Queue** — failed messages after 3 retries

## Scalability
- Horizontal: add more workers per queue
- RabbitMQ clustering for HA
- Handles burst traffic naturally (queue absorbs spikes)

## Pros
- Decoupled: upstream services don't wait for notification delivery
- Natural retry mechanism (requeue failed messages)
- Handles traffic spikes via queue buffering
- Rate limiting via consumer prefetch

## Cons
- Added infrastructure complexity (RabbitMQ cluster)
- Operational overhead (monitoring queues, managing dead letters)
- Team needs to learn RabbitMQ operations
- Message ordering not guaranteed across workers

## Cost Estimate
- RabbitMQ: $100/month (managed) or $50/month (self-hosted on K8s)
- Workers: $150/month (3x small pods)
- PostgreSQL: $50/month
- **Total: $250-300/month initially**
EOF

cat > project/arch_b.md << 'EOF'
# Architecture B: REST API with Polling

## Overview
Upstream services call a REST API to submit notification requests. A scheduler polls the database for pending notifications and dispatches them.

## Components
1. **REST API** — Flask API to accept notification requests
2. **PostgreSQL** — stores pending notifications, templates, delivery status
3. **Scheduler** — cron-like process polls DB every 5 seconds for pending items
4. **Dispatcher** — processes pending notifications sequentially

## Scalability
- Vertical: increase API server and scheduler resources
- Multiple API replicas behind load balancer
- Scheduler is single-instance (to avoid duplicate sends)

## Pros
- Simple architecture (REST + database + cron)
- Team already knows Flask/PostgreSQL
- Easy to debug (all state in database)
- No additional infrastructure (no message broker)

## Cons
- Polling adds latency (up to 5-second delay from poll interval)
- Scheduler is a single point of failure
- Burst traffic hits API directly (no buffering)
- Rate limiting requires custom implementation
- Single scheduler limits throughput at scale

## Cost Estimate
- API server: $100/month (2 replicas)
- PostgreSQL: $50/month
- Scheduler: $50/month (1 pod)
- **Total: $200/month initially**
EOF

cat > project/eval_template.md << 'EOF'
# Architecture Evaluation

## Evaluation Criteria

### Scalability (weight: high)
- Architecture A:
- Architecture B:

### Cost (weight: medium)
- Architecture A:
- Architecture B:

### Complexity (weight: medium)
- Architecture A:
- Architecture B:

### Reliability (weight: high)
- Architecture A:
- Architecture B:

### Team Fit (weight: medium)
- Architecture A:
- Architecture B:

## Scorecard
| Criterion | Weight | Arch A | Arch B |
|-----------|--------|--------|--------|
| Scalability | high | /10 | /10 |
| Cost | medium | /10 | /10 |
| Complexity | medium | /10 | /10 |
| Reliability | high | /10 | /10 |
| Team Fit | medium | /10 | /10 |

## Winner
**Selected architecture:**

## Justification
<!-- Reference specific requirements -->

## Migration Path
<!-- How to evolve the chosen architecture as scale grows -->
EOF

echo "Setup complete. Two architecture proposals ready for evaluation."
