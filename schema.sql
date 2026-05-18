-- Run this in the Supabase SQL editor ONCE to set up the database.
-- Dashboard → SQL Editor → New query → paste → Run

-- ── Cases table ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS cases (
  case_id         TEXT PRIMARY KEY,
  sha256_hash     TEXT NOT NULL,
  captured_at     TIMESTAMPTZ NOT NULL,
  source_url      TEXT,
  filename        TEXT,
  file_path       TEXT,
  ots_status      TEXT NOT NULL DEFAULT 'pending',
  ots_receipt_b64 TEXT,
  df_status       TEXT,
  df_is_deepfake  BOOLEAN,
  df_confidence   DOUBLE PRECISION,
  df_reason       TEXT,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Enable Row-Level Security (service-role key bypasses it — fine for server use)
ALTER TABLE cases ENABLE ROW LEVEL SECURITY;

-- ── Storage bucket ────────────────────────────────────────────────────────────
-- If the Supabase UI shows "evidence-files" bucket already exists, skip this.
INSERT INTO storage.buckets (id, name, public)
VALUES ('evidence-files', 'evidence-files', false)
ON CONFLICT (id) DO NOTHING;
