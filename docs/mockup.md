# Capacity Checker — Feature Mockup & How It Works

A plain-English walkthrough of the system, written for non-coders. This describes the screens, what data goes in, and what comes out.

---

## 1. The problem this solves

Today: Excel spreadsheet + manual Google Maps checks + manual colour-coding to figure out:
- Which carers have free time
- Which clients are near each other
- Whether a new client/call can be fitted in

Goal: One system that instantly answers "who can take this call, and when?" for 50+ carers and 99+ clients — without needing PeoplePlanner API access.

---

## 2. The data behind it (replaces the spreadsheet)

Based on your real spreadsheet columns, restructured into four linked lists:

### Clients
| Client | Postcode |
|---|---|
| Abel, Andrew | DA2 7HG |
| Adshead, Lois | DA12 5AS |

### Calls (one row per call, same as your spreadsheet rows)
| Client | Days | Start | End | Duration |
|---|---|---|---|---|
| Abel, Andrew | Thurs | 11:00 | 16:00 | 5:00 |
| Adshead, Lois | Mon-Sun (minus Tues) | 09:35 | 10:05 | 0:30 |

### Carers
| Carer | Working Hours | Unavailable windows |
|---|---|---|
| Kaur, Harpreet | 7am–7pm | 8:00–9:00 |
| Sandhu, Rajwant | 7am–17:15pm | — |

### Assignments / Rounds (auto-generated instead of manual colour-coding)
Shows which carer does which calls, in what order, with real travel time between each — calculated automatically instead of the manual 45/30-min interval grid trick.

**Key change from your current spreadsheet:** instead of forcing every call into a fixed 45-min (morning) / 30-min (afternoon) box to avoid double-booking, the system calculates each carer's *actual* free time (shift time − calls − real travel time). This means odd-length calls (20 min, 90 min) are handled correctly without needing an artificial slot grid.

---

## 3. The screens (mockup)

### Screen A — Dashboard
```
┌─────────────────────────────────────────────────────────────┐
│  CAPACITY CHECKER                              Mon 24 July   │
├─────────────────────────────────────────────────────────────┤
│  Total spare capacity today:  14.5 hours across 12 carers    │
│                                                               │
│  🔍  Check availability                                      │
│  Postcode: [ DA12 5AS ] Time: [ 14:00 ] Duration: [ 30 min ] │
│  Day: [ Wednesday ]                    [ CHECK NOW ]         │
└─────────────────────────────────────────────────────────────┘
```

### Screen B — Instant availability result
```
┌─────────────────────────────────────────────────────────────┐
│  Results for DA12 5AS · Wed 14:00 · 30 min                    │
├─────────────────────────────────────────────────────────────┤
│  ✅ Kaur, Harpreet — 6 min travel, fits cleanly               │
│  ✅ Bhachoo, Hardeep — 11 min travel, fits with 4 min spare   │
│  ⚠️  Sandhu, Rajwant — fits, but tight (2 min buffer)         │
│  ❌ 47 other carers — unavailable or too far                  │
│                                                               │
│  [ Assign to Kaur, Harpreet ]                                 │
└─────────────────────────────────────────────────────────────┘
```

### Screen C — Carer day view (replaces manual colour-coded rows)
```
┌─────────────────────────────────────────────────────────────┐
│  Kaur, Harpreet — Monday                                      │
├─────────────────────────────────────────────────────────────┤
│ 07:00 ████ Crouch, Linda (45m)                                │
│ 07:45 ▓▓ travel (5m)                                          │
│ 07:50 ████ Pearce, Lynn (45m)                                 │
│ 08:35 ░░░░░░░░ FREE                                            │
│ 09:00 ⛔ unavailable (8-9 block)                               │
│ ...                                                            │
└─────────────────────────────────────────────────────────────┘
```

### Screen D — Map view
Google Map with client pins colour-coded by round, carer routes drawn between calls, click a pin to see call/carer detail.

### Screen E — Weekly capacity heatmap
```
           Mon    Tue    Wed    Thu    Fri    Sat    Sun
 07-09    🟩🟩    🟨🟨    🟩🟩    🟥🟥    🟩🟩    🟨🟨    🟩🟩
 09-12    🟩🟩    🟩🟩    🟩🟩    🟨🟨    🟩🟩    🟩🟩    🟨🟨
 12-15    🟨🟨    🟩🟩    🟥🟥    🟩🟩    🟩🟩    🟩🟩    🟩🟩
 15-18    🟥🟥    🟨🟨    🟩🟩    🟩🟩    🟥🟥    🟩🟩    🟩🟩

 🟩 plenty spare   🟨 tight   🟥 no capacity
```

---

## 4. How it works, step by step

1. Load current clients/calls/carers from your spreadsheet (CSV export — see `sample_data/`).
2. Geocode each postcode once (Google Maps Geocoding API).
3. Calculate travel times between relevant postcode pairs (Google Maps Distance Matrix API), refreshed nightly not live.
4. Track/validate carer assignments (Phase 1) — warns if a round becomes infeasible; answers "who's free" instantly for new calls.
5. Later phase: auto-suggest optimal assignments instead of just validating them.
6. Update client/carer/call records directly in this system going forward — single source of truth, replacing the spreadsheet.

---

## 5. Google Maps costs (2025 pricing)

| API | Free requests/month | Price after free tier |
|---|---|---|
| Geocoding | 10,000 | $5 per 1,000 |
| Distance Matrix | 10,000 | $5–$15 per 1,000 |
| Directions | 10,000 | $5–$15 per 1,000 |

At 99 clients + 50 carers, with geocoding done once and travel times refreshed nightly (not per-second), you should stay within the free tier most months.
