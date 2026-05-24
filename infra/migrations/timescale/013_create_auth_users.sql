-- Migration 013: create auth.auth_users reference table and seed 5 persona rows.
-- File: infra/migrations/timescale/013_create_auth_users.sql
-- Phase 10 — Plan 10-03 (SRV-01 dev-mode persona seeding)
--
-- Purpose:
--   Provides a DB-level reference for the 5 dev-mode persona users defined in
--   svc_api_gateway.security.jwt.SEEDED_USERS.
--   NO password hashes are stored here — plaintext credentials live in code only
--   (dev-mode seed, documented in jwt.py). Phase 11 replaces this table with a
--   real identity-provider integration (Keycloak).
--
-- Idempotent: safe to re-run.
--   CREATE SCHEMA IF NOT EXISTS  — no-op if schema exists
--   CREATE TABLE IF NOT EXISTS   — no-op if table exists
--   INSERT ... ON CONFLICT DO NOTHING — no-op if rows already present
--
-- Schema choice: `auth` — dedicated namespace for identity concerns, separate from
--   `audit`, `maintenance`, `scm`, etc. (isolation principle).
--
-- Columns:
--   email         TEXT PRIMARY KEY — matches the `sub` + `email` JWT claim
--   role          TEXT NOT NULL    — matches the `role` JWT claim
--   display_name  TEXT NOT NULL    — human-readable name for UI display
--   created_at    TIMESTAMPTZ      — seeding timestamp
--
-- Constraint: no UNIQUE beyond PK (email is already unique as PK).

CREATE SCHEMA IF NOT EXISTS auth;

CREATE TABLE IF NOT EXISTS auth.auth_users (
    email        TEXT        PRIMARY KEY,
    role         TEXT        NOT NULL,
    display_name TEXT        NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Seed the 5 dev-mode persona rows (10-UI-SPEC Dev-Mode JWT table).
-- ON CONFLICT DO NOTHING ensures re-runs are safe (idempotent).
-- No passwords stored here — see svc_api_gateway.security.jwt.SEEDED_USERS.

INSERT INTO auth.auth_users (email, role, display_name) VALUES
    ('operator@mantis.it',   'operator',         'Luca Bianchi'),
    ('supervisor@mantis.it', 'shift-supervisor',  'Anna Rossi'),
    ('technician@mantis.it', 'technician',        'Marco Ferrari'),
    ('cio@mantis.it',        'manager',           'Elena Greco'),
    ('admin@mantis.it',      'admin',             'Admin')
ON CONFLICT (email) DO NOTHING;
