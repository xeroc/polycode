-- Migration: Add active_specify_flows table

CREATE TABLE active_specify_flows (
    id SERIAL PRIMARY KEY,
    flow_uuid TEXT NOT NULL UNIQUE,           -- repo_owner/repo_name/issue_number
    repo_owner TEXT NOT NULL,
    repo_name TEXT NOT NULL,
    issue_number INTEGER NOT NULL,
    issue_author TEXT NOT NULL,               -- GitHub username to filter comments
    project_config JSONB NOT NULL,            -- Full ProjectConfig for flow instantiation
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_comment_id BIGINT,                   -- Track last processed comment
    UNIQUE(repo_owner, repo_name, issue_number)
);

CREATE INDEX idx_specify_flows_uuid ON active_specify_flows(flow_uuid);
CREATE INDEX idx_specify_flows_repo ON active_specify_flows(repo_owner, repo_name, issue_number);
