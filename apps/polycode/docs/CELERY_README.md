# Celery Integration for Feature Development

## Overview

This module provides Celery-based background task processing for long-running feature development workflows using CrewAI agents.

## Architecture

### Task Queues

- **feature_dev**: Main feature development tasks (CPU-intensive)
- **webhooks**: GitHub webhook processing (I/O-intensive)
- **monitoring**: Status updates and heartbeat monitoring
- **cleanup**: Periodic task cleanup

### Task Types

#### High-Level Orchestration

- `kickoff_feature_dev_task`: Main entry point for feature development

#### Agent Execution

- `implement_story_task`: Execute developer agent for story implementation
- `test_story_task`: Execute tester agent for validation
- `verify_story_task`: Execute verification agent for code review

#### Webhook Processing

- `process_github_webhook_task`: Process GitHub webhook events asynchronously

#### Utility Tasks

- `update_status_task`: Update GitHub issue/project status
- `flow_heartbeat_task`: Monitor running flows (periodic)
- `cleanup_completed_tasks`: Remove old completed tasks (periodic)

## Setup

### Prerequisites

1. **Redis Server** (required for Celery broker)

   ```bash
   # Using Docker
   docker run -d -p 6379:6379 redis:7-alpine

   # Using system package manager
   apt-get install redis-server  # Debian/Ubuntu
   brew install redis          # macOS
   ```

2. **Environment Variables**

   ```bash
   export REDIS_HOST=localhost
   export REDIS_PORT=6379
   export REDIS_DB=0
   export DATABASE_URL=postgresql://user:pass@localhost/db
   export GITHUB_TOKEN=your_github_token
   export GITHUB_REPO_NAME=demo
   export GITHUB_REPO_OWNER=xeroc
   export GITHUB_PROJECT_ID=1
   ```

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Initialize Celery task tracking database
celery-init-db
```

## Usage

### Starting Celery Workers

#### Start All Workers

```bash
# Start worker for all queues
celery -A src.celery_tasks worker --loglevel=info

# Start with concurrency settings
celery -A src.celery_tasks worker --concurrency=4 --loglevel=info
```

#### Start Specific Queue Workers

```bash
# Feature dev workers (CPU-intensive)
celery -A src.celery_tasks worker -Q feature_dev --concurrency=4 --loglevel=info

# Webhook workers (I/O-intensive)
celery -A src.celery_tasks worker -Q webhooks --concurrency=10 --loglevel=info

# Monitoring workers
celery -A src.celery_tasks worker -Q monitoring --loglevel=info
```

#### Using Project Scripts

```bash
# Start main worker
celery-worker

# Or start specific workers manually
celery -A src.celery_tasks worker -Q feature_dev --concurrency=4
```

### Flower Dashboard (Task Monitoring)

```bash
# Start Flower dashboard
celery -A src.celery_tasks flower

# Or use project script
celery-flower

# Access dashboard at: http://localhost:5555
```

## Configuration

### Task Timeouts and Retries

Tasks are configured with appropriate timeouts and retry policies:

- **Feature Dev**: 2 hours hard limit, 1 hour 50 min soft limit, 3 retries
- **Story Implementation**: 1 hour hard limit, 1 hour soft limit, 2 retries
- **Story Testing**: 30 min hard limit, 30 min soft limit, 2 retries
- **Story Verification**: 15 min hard limit, 15 min soft limit, 1 retry
- **Webhook Processing**: 5 min hard limit, 5 min soft limit, 3 retries

### Exponential Backoff

Failed tasks use exponential backoff for retries:

- Base delay: 60 seconds
- Max delay: 3600 seconds (1 hour)
- Formula: `min(base_delay * (2^retry_count), max_delay)`

## Integration Points

### Webhook Processing

The webhook server automatically uses Celery when available:

```python
# In src/project_manager/webhook.py
if CELERY_AVAILABLE:
    task_result = process_github_webhook_task.delay(payload.model_dump())
    # Returns task_id for tracking
else:
    # Falls back to background tasks
    background_tasks.add_task(process_event)
```

### Flow Runner Integration

The FlowRunner triggers Celery tasks when available:

```python
# In src/project_manager/flow_runner.py
if CELERY_AVAILABLE:
    task_result = kickoff_feature_dev_task.apply_async(args=[issue_number])
    # Returns task_id for async processing
else:
    # Falls back to synchronous processing
    self.on_issue_ready(item)
```

## Monitoring

### Task Status Tracking

All tasks are tracked in the `celery_tasks` database table:

```sql
SELECT task_id, flow_id, task_type, status, created_at, started_at, completed_at
FROM celery_tasks
ORDER BY created_at DESC;
```

### Periodic Tasks

Two periodic tasks run automatically:

1. **Flow Heartbeat** (every 5 minutes)
   - Checks for running tasks
   - Identifies potential timeouts (2+ hours)
   - Monitors task health

2. **Cleanup** (daily)
   - Removes completed/failed tasks older than 7 days
   - Maintains database performance

### Flower Dashboard

Access real-time monitoring at `http://localhost:5555`:

- View active workers and queues
- Monitor task execution
- Check success/failure rates
- View task logs and results

## Troubleshooting

### Common Issues

**Workers not connecting to Redis:**

```bash
# Check Redis is running
redis-cli ping  # Should return PONG

# Check connection string
echo $REDIS_HOST:$REDIS_PORT  # Should match Redis config
```

**Tasks stuck in pending:**

```bash
# Check worker logs
celery -A src.celery_tasks worker --loglevel=debug

# Verify queue routing
celery -A src.celery_tasks inspect active
```

**Database connection errors:**

```bash
# Verify DATABASE_URL is set
echo $DATABASE_URL

# Test database connection
python -c "from sqlalchemy import create_engine; engine = create_engine('$DATABASE_URL'); engine.connect()"
```

### Debug Mode

Enable detailed logging:

```bash
# Celery worker with debug logging
celery -A src.celery_tasks worker --loglevel=debug

# Webhook server with debug logging
LOGLEVEL=DEBUG webhook-server
```

## Production Deployment

### Docker Compose

```yaml
version: '3.8'
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  feature-dev-worker:
    build: .
    command: celery -A src.celery_tasks worker -Q feature_dev --concurrency=4
    depends_on:
      - redis
    environment:
      - REDIS_HOST=redis
      - REDIS_PORT=6379

  webhook-worker:
    build: .
    command: celery -A src.celery_tasks worker -Q webhooks --concurrency=10
    depends_on:
      - redis
    environment:
      - REDIS_HOST=redis
      - REDIS_PORT=6379

  monitoring-worker:
    build: .
    command: celery -A src.celery_tasks worker -Q monitoring --concurrency=2
    depends_on:
      - redis
    environment:
      - REDIS_HOST=redis
      - REDIS_PORT=6379

  flower:
    build: .
    command: celery -A src.celery_tasks flower
    ports:
      - "5555:5555"
    depends_on:
      - redis
    environment:
      - REDIS_HOST=redis
      - REDIS_PORT=6379
```

### Scaling Workers

Scale workers based on load:

```bash
# Scale feature dev workers (CPU-intensive)
celery -A src.celery_tasks worker -Q feature_dev --concurrency=8 --hostname=worker-1
celery -A src.celery_tasks worker -Q feature_dev --concurrency=8 --hostname=worker-2

# Scale webhook workers (I/O-intensive)
celery -A src.celery_tasks worker -Q webhooks --concurrency=20 --hostname=webhook-1
```

## API Reference

### Celery Tasks

See individual task modules for detailed API:

- `src/celery_tasks/flow_orchestration.py`: High-level flow management
- `src/celery_tasks/agent_execution.py`: Individual agent tasks
- `src/celery_tasks/webhook_tasks.py`: Webhook processing
- `src/celery_tasks/utility_tasks.py`: Status and monitoring tasks

### Database Models

- `CeleryTask`: Task tracking model (see `src/persistence/celery_tasks.py`)
- `CeleryTaskTracker`: Database interface for task management
