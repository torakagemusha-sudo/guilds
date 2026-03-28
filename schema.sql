PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_migrations (
    name TEXT PRIMARY KEY,
    applied_at TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%fZ', 'now')),
    created_at TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS conversation_state (
    session_id TEXT NOT NULL,
    turn_id INTEGER NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    provenance_hash TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%fZ', 'now')),
    PRIMARY KEY (session_id, turn_id)
);

CREATE INDEX IF NOT EXISTS idx_conversation_state_timestamp
    ON conversation_state (timestamp);

CREATE TABLE IF NOT EXISTS memory_index (
    entry_id TEXT PRIMARY KEY,
    embedding_ref TEXT NOT NULL,
    content_summary TEXT NOT NULL,
    last_accessed TEXT,
    access_count INTEGER NOT NULL DEFAULT 0 CHECK (access_count >= 0),
    ttl INTEGER,
    tags TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_memory_index_last_accessed
    ON memory_index (last_accessed);

CREATE TABLE IF NOT EXISTS evidence_registry (
    evidence_id TEXT PRIMARY KEY,
    source_type TEXT NOT NULL,
    source_ref TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    retrieval_ts TEXT NOT NULL,
    linked_turn_id INTEGER,
    created_at TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_evidence_registry_retrieval_ts
    ON evidence_registry (retrieval_ts);

CREATE TABLE IF NOT EXISTS audit_log (
    event_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    actor TEXT NOT NULL,
    tool_name TEXT,
    args_hash TEXT NOT NULL,
    result_hash TEXT,
    ts TEXT NOT NULL,
    signed INTEGER NOT NULL CHECK (signed IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_audit_log_ts
    ON audit_log (ts);

CREATE TABLE IF NOT EXISTS operator_state (
    operator_id TEXT PRIMARY KEY,
    scope_flags TEXT NOT NULL DEFAULT '{}',
    active_constraints TEXT NOT NULL DEFAULT '[]',
    session_token TEXT,
    expires_at TEXT,
    created_at TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_operator_state_expires_at
    ON operator_state (expires_at);

CREATE TABLE IF NOT EXISTS tool_effect_log (
    effect_id TEXT PRIMARY KEY,
    tool_name TEXT NOT NULL,
    call_args TEXT NOT NULL,
    result_summary TEXT,
    ts TEXT NOT NULL,
    linked_audit_id TEXT,
    created_at TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%fZ', 'now')),
    FOREIGN KEY (linked_audit_id) REFERENCES audit_log(event_id)
);

CREATE INDEX IF NOT EXISTS idx_tool_effect_log_linked_audit
    ON tool_effect_log (linked_audit_id);

CREATE INDEX IF NOT EXISTS idx_tool_effect_log_ts
    ON tool_effect_log (ts);

CREATE TRIGGER IF NOT EXISTS trg_schema_migrations_set_updated_at
AFTER UPDATE ON schema_migrations
FOR EACH ROW
WHEN NEW.updated_at = OLD.updated_at
BEGIN
    UPDATE schema_migrations
    SET updated_at = STRFTIME('%Y-%m-%dT%H:%M:%fZ', 'now')
    WHERE name = OLD.name;
END;

CREATE TRIGGER IF NOT EXISTS trg_conversation_state_set_updated_at
AFTER UPDATE ON conversation_state
FOR EACH ROW
WHEN NEW.updated_at = OLD.updated_at
BEGIN
    UPDATE conversation_state
    SET updated_at = STRFTIME('%Y-%m-%dT%H:%M:%fZ', 'now')
    WHERE session_id = OLD.session_id AND turn_id = OLD.turn_id;
END;

CREATE TRIGGER IF NOT EXISTS trg_memory_index_set_updated_at
AFTER UPDATE ON memory_index
FOR EACH ROW
WHEN NEW.updated_at = OLD.updated_at
BEGIN
    UPDATE memory_index
    SET updated_at = STRFTIME('%Y-%m-%dT%H:%M:%fZ', 'now')
    WHERE entry_id = OLD.entry_id;
END;

CREATE TRIGGER IF NOT EXISTS trg_evidence_registry_set_updated_at
AFTER UPDATE ON evidence_registry
FOR EACH ROW
WHEN NEW.updated_at = OLD.updated_at
BEGIN
    UPDATE evidence_registry
    SET updated_at = STRFTIME('%Y-%m-%dT%H:%M:%fZ', 'now')
    WHERE evidence_id = OLD.evidence_id;
END;

CREATE TRIGGER IF NOT EXISTS trg_operator_state_set_updated_at
AFTER UPDATE ON operator_state
FOR EACH ROW
WHEN NEW.updated_at = OLD.updated_at
BEGIN
    UPDATE operator_state
    SET updated_at = STRFTIME('%Y-%m-%dT%H:%M:%fZ', 'now')
    WHERE operator_id = OLD.operator_id;
END;

CREATE TRIGGER IF NOT EXISTS trg_tool_effect_log_set_updated_at
AFTER UPDATE ON tool_effect_log
FOR EACH ROW
WHEN NEW.updated_at = OLD.updated_at
BEGIN
    UPDATE tool_effect_log
    SET updated_at = STRFTIME('%Y-%m-%dT%H:%M:%fZ', 'now')
    WHERE effect_id = OLD.effect_id;
END;

CREATE TRIGGER IF NOT EXISTS trg_audit_log_prevent_update
BEFORE UPDATE ON audit_log
FOR EACH ROW
BEGIN
    SELECT RAISE(ABORT, 'audit_log rows are immutable');
END;

CREATE TRIGGER IF NOT EXISTS trg_audit_log_prevent_delete
BEFORE DELETE ON audit_log
FOR EACH ROW
BEGIN
    SELECT RAISE(ABORT, 'audit_log rows are immutable');
END;
