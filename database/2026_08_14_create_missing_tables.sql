-- 2026-08-14: Create missing RepoRAG tables
-- This SQL file is a reference migration for creating tables used by new features.
-- Prefer running `python backend/scripts/ensure_db.py` which uses SQLAlchemy metadata.create_all
-- to create tables with correct FK ordering. The SQL below uses IF NOT EXISTS as a fallback.

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;

-- Branches
CREATE TABLE IF NOT EXISTS branches (
    id UUID PRIMARY KEY,
    repository_id UUID NOT NULL,
    name VARCHAR(255) NOT NULL,
    commit_sha VARCHAR(100),
    is_protected BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Commits
CREATE TABLE IF NOT EXISTS commits (
    id UUID PRIMARY KEY,
    repository_id UUID NOT NULL,
    sha VARCHAR(100) NOT NULL,
    message TEXT,
    author_name VARCHAR(255),
    author_email VARCHAR(255),
    authored_date TIMESTAMPTZ,
    html_url VARCHAR(1000),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Contributors
CREATE TABLE IF NOT EXISTS contributors (
    id UUID PRIMARY KEY,
    repository_id UUID NOT NULL,
    login VARCHAR(255) NOT NULL,
    contributions INTEGER NOT NULL DEFAULT 0,
    avatar_url VARCHAR(1000),
    html_url VARCHAR(1000),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Analyses
CREATE TABLE IF NOT EXISTS analyses (
    id UUID PRIMARY KEY,
    repository_id UUID NOT NULL,
    analysis_type VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    commit_sha VARCHAR(100),
    summary TEXT,
    result JSONB,
    findings_count INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Embeddings (ensure vector column exists)
CREATE TABLE IF NOT EXISTS embeddings (
    id UUID PRIMARY KEY,
    chunk_id UUID NOT NULL UNIQUE,
    vector VECTOR(1536) NOT NULL,
    provider VARCHAR(100) NOT NULL,
    model VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Optional: create indexes for fk lookup
CREATE INDEX IF NOT EXISTS idx_branches_repository_id ON branches (repository_id);
CREATE INDEX IF NOT EXISTS idx_commits_repository_id ON commits (repository_id);
CREATE INDEX IF NOT EXISTS idx_contributors_repository_id ON contributors (repository_id);
CREATE INDEX IF NOT EXISTS idx_analyses_repository_id ON analyses (repository_id);
