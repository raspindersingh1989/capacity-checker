-- Capacity Checker database schema
-- Designed from the existing PeoplePlanner-derived spreadsheet columns
--
-- NOTE: sample_data/carers.csv is a single combined file for ease of data entry
-- (carer info repeated on each availability row). In the actual database, we keep
-- carers and their availability windows as two separate, linked tables — this avoids
-- duplicating/risking inconsistent carer info (e.g. skills) across multiple rows.

CREATE TABLE clients (
    client_id       SERIAL PRIMARY KEY,
    full_name       TEXT NOT NULL,          -- e.g. 'Abel, Andrew'
    postcode        TEXT NOT NULL,
    latitude        NUMERIC(9,6),           -- filled in by geocoding step
    longitude       NUMERIC(9,6),
    notes           TEXT,
    created_at      TIMESTAMP DEFAULT now(),
    updated_at      TIMESTAMP DEFAULT now()
);

CREATE TABLE carers (
    carer_id        SERIAL PRIMARY KEY,
    full_name       TEXT NOT NULL,          -- e.g. 'Kaur, Harpreet'
    postcode        TEXT,                   -- carer base/home postcode, optional
    latitude        NUMERIC(9,6),
    longitude       NUMERIC(9,6),
    max_travel_miles NUMERIC(5,2),
    skills          TEXT,                   -- e.g. 'hoist, two-person'
    created_at      TIMESTAMP DEFAULT now(),
    updated_at      TIMESTAMP DEFAULT now()
);

-- Multiple availability windows per carer, e.g. Harpreet:
--   09:00-12:00 core, 13:00-14:00 optional, 16:00-18:00 optional
CREATE TABLE carer_availability (
    availability_id   SERIAL PRIMARY KEY,
    carer_id           INTEGER REFERENCES carers(carer_id),
    day_pattern        TEXT NOT NULL,        -- e.g. 'Mon-Sun', 'Mon-Sun (minus Tues)'
    start_time         TIME NOT NULL,
    end_time           TIME NOT NULL,
    availability_type  TEXT NOT NULL DEFAULT 'core'  -- 'core' or 'optional'
);

-- One row per recurring call, matches your spreadsheet rows directly
CREATE TABLE calls (
    call_id         SERIAL PRIMARY KEY,
    client_id       INTEGER REFERENCES clients(client_id),
    day_pattern     TEXT NOT NULL,          -- e.g. 'Mon-Sun (minus Tues)', 'Thurs'
    start_time      TIME NOT NULL,
    end_time        TIME NOT NULL,
    duration_minutes INTEGER NOT NULL,
    call_type       TEXT,                   -- e.g. 'medication', 'two-person'
    created_at      TIMESTAMP DEFAULT now(),
    updated_at      TIMESTAMP DEFAULT now()
);

-- Current/manual assignment of a carer to a call (Phase 1: tracked, validated)
CREATE TABLE assignments (
    assignment_id   SERIAL PRIMARY KEY,
    call_id         INTEGER REFERENCES calls(call_id),
    carer_id        INTEGER REFERENCES carers(carer_id),
    round_label      TEXT,                  -- e.g. 'Round 1', auto-computed later
    assigned_at     TIMESTAMP DEFAULT now()
);

-- Cached travel times between postcodes, refreshed nightly via Distance Matrix API
CREATE TABLE travel_times (
    from_postcode   TEXT NOT NULL,
    to_postcode     TEXT NOT NULL,
    travel_minutes  NUMERIC(5,1) NOT NULL,
    distance_miles  NUMERIC(5,2),
    last_updated    TIMESTAMP DEFAULT now(),
    PRIMARY KEY (from_postcode, to_postcode)
);

-- Helpful indexes for the capacity-check queries
CREATE INDEX idx_calls_client ON calls(client_id);
CREATE INDEX idx_assignments_carer ON assignments(carer_id);
CREATE INDEX idx_assignments_call ON assignments(call_id);
CREATE INDEX idx_availability_carer ON carer_availability(carer_id);