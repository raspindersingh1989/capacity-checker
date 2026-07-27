# Capacity Checker

A system to instantly answer: **"Which carers are free, when, and where?"**

Built to replace a manual Excel + Google Maps process for a home care team
with 50+ carers and 99+ clients.

## What's in this repo

| File | Purpose |
|---|---|
| `docs/mockup.md` | Feature mockup and explanation of how the system works (non-technical) |
| `schema.sql` | Database structure (Postgres) for clients, carers, calls, assignments |
| `sample_data/` | Sample CSVs matching the current spreadsheet format |
| `capacity_checker.py` | Phase 1 logic: checks carer time availability (no travel time yet) |
| `test_capacity_checker.py` | Tests for the logic above |

## Phase 1 (this version): time-only availability

This first version answers availability questions using **time only** —
it does not yet use Google Maps or travel time between postcodes. This lets
the core scheduling logic be tested and trusted before adding location.

### Try it yourself (no coding experience needed)

1. Install Python 3 if you don't have it: https://www.python.org/downloads/
2. Download/clone this repo.
3. Open a terminal in the repo folder and run:
   ```
   python capacity_checker.py
   ```
4. You should see output like:
   ```
   === Free slots for Kaur, Harpreet on Monday ===
     07:00-08:15
     09:00-17:00

   === Who is free Wednesday 14:00 for 30 minutes? ===
     Evans, Amy
     Jackson, Hayley
     ...
   ```

### Run the tests

```
python -m unittest test_capacity_checker.py
```

All tests should pass (`OK` at the end).

## Phase 2 (next step): add Google Maps travel time

Once Phase 1 is confirmed to match your real spreadsheet logic, the next
step is:
1. Geocode every client/carer postcode (Google Maps Geocoding API).
2. Build a travel-time matrix between postcodes (Distance Matrix API).
3. Extend `find_available_carers` to also check that a carer can realistically
   travel from their previous call to the new one in time.

See `docs/mockup.md` for the full picture of where this is heading
(dashboard, map view, weekly capacity heatmap).
