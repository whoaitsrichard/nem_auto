# Joining `DISPATCHOFFERTRK`, `BIDDAYOFFER`, and `BIDOFFERPERIOD` (NEM / FCAS)
Goal: build an organized panel for **one service** (`BIDTYPE`), for **one unit** (`DUID`), over a chosen **time window**, showing:
- the **initial (Daily) bid** for the market day, and
- **all subsequent rebids** (bid versions),
- plus (optionally) which version was **actually applied** in dispatch each 5-minute interval.

This doc assumes you are using the AEMO MMSDM SQLLoader public archive tables:
- `BIDDAYOFFER` (day-level offer “header”: price bands, metadata, entry type)
- `BIDOFFERPERIOD` (5-minute period-level offer “detail”: band quantities by PERIODID)
- `DISPATCHOFFERTRK` (dispatch-time “tracking”: which offer version was applied each interval)

---

## 1) Key concepts

### Market day vs dispatch interval vs period ID
- A market day has **288 dispatch intervals** (5-minute).
- `BIDOFFERPERIOD.PERIODID ∈ {1,…,288}` indexes the 5-minute periods for that trading day.

### Offer versioning
A “bid version” is identified by **(market day, offer timestamp)**:
- `BIDDAYOFFER.SETTLEMENTDATE` = market day
- `BIDDAYOFFER.OFFERDATE` = offer-version timestamp (when that version was processed/loaded)

Likewise for the period table:
- `BIDOFFERPERIOD.TRADINGDATE` = market day
- `BIDOFFERPERIOD.OFFERDATETIME` = offer-version timestamp

### Daily vs rebid
- `BIDDAYOFFER.ENTRYTYPE` tells you whether a version is:
  - `Daily` (processed before the Day-1 cutoff) or
  - `REBID` (processed after cutoff)

Important: You can see `ENTRYTYPE='REBID'` even though **price bands are fixed** for Day 0; rebids often change **quantities/parameters**, not prices.

---

## 2) What each table contributes

### `BIDDAYOFFER` (day-level)
Use this table to get:
- band prices: `PRICEBAND1 … PRICEBAND10`
- `ENTRYTYPE` (Daily vs REBID)
- rebid metadata (e.g., explanations / timestamps if present)

### `BIDOFFERPERIOD` (5-minute level)
Use this table to get, per offer version:
- band quantities per period: `BANDAVAIL1 … BANDAVAIL10`
- plus enablement/technical parameters that can vary by period

### `DISPATCHOFFERTRK` (dispatch tracking)
Use this table to know, per dispatch interval:
- which offer version was **applied** in dispatch:
  - `BIDSETTLEMENTDATE` (market day)
  - `BIDOFFERDATE` (offer version timestamp)
- and the unit/service it applies to (`DUID`, `BIDTYPE`)
- and the dispatch interval timestamp (`SETTLEMENTDATE`)

---

## 3) Join keys (core)

### A) Join `BIDOFFERPERIOD` ↔ `BIDDAYOFFER` (offer version)
These two describe the *same offer version* (prices + quantities).

Join on:
- `DUID`
- `BIDTYPE`
- market day:
  - `BIDOFFERPERIOD.TRADINGDATE = BIDDAYOFFER.SETTLEMENTDATE`
- offer version time:
  - `BIDOFFERPERIOD.OFFERDATETIME = BIDDAYOFFER.OFFERDATE`

Result: a full offer version object with both:
- `PRICEBANDk` and `BANDAVAILk` (by period)

### B) Join `DISPATCHOFFERTRK` ↔ (`BIDDAYOFFER` / `BIDOFFERPERIOD`) (applied offer)
To label which version dispatch used, join `DISPATCHOFFERTRK` to the offer version by:

- `DUID`
- `BIDTYPE`
- market day:
  - `DISPATCHOFFERTRK.BIDSETTLEMENTDATE = BIDDAYOFFER.SETTLEMENTDATE`
  - `DISPATCHOFFERTRK.BIDSETTLEMENTDATE = BIDOFFERPERIOD.TRADINGDATE`
- offer version time:
  - `DISPATCHOFFERTRK.BIDOFFERDATE = BIDDAYOFFER.OFFERDATE`
  - `DISPATCHOFFERTRK.BIDOFFERDATE = BIDOFFERPERIOD.OFFERDATETIME`

This lets you map each dispatch interval to the exact offer version applied.

---

## 4) Compute `PERIODID` for a dispatch interval timestamp

`BIDOFFERPERIOD` is keyed by `PERIODID`, while `DISPATCHOFFERTRK` gives you a dispatch interval timestamp (commonly `SETTLEMENTDATE`).

For a timestamp `t` within a market day, define:

- `minutes_since_midnight = hour(t)*60 + minute(t)`
- `PERIODID = minutes_since_midnight / 5`  (with an offset depending on convention)

**Important:** AEMO tables often define the dispatch interval timestamp as the **end** of the 5-minute interval. Depending on the table, you may need:
- either `PERIODID = minutes_since_midnight/5`
- or `PERIODID = minutes_since_midnight/5 + 1`

You can sanity check the mapping by verifying that:
- the first interval of the day maps to `PERIODID=1`
- the last interval maps to `PERIODID=288`

When in doubt: compute both and see which yields non-empty joins.

---

## 5) Desired output structure

For one `(DUID, BIDTYPE)` and a time window `[t_start, t_end]`, build:

### A) Offer versions (Daily + Rebids) timeline
A table of offer versions for the market day(s):

- `market_day` (SETTLEMENTDATE)
- `offer_version_time` (OFFERDATE / OFFERDATETIME)
- `ENTRYTYPE` (Daily/REBID)
- `PRICEBAND1..10` (typically constant within a day)
- any rebid explanation fields

Sort by `offer_version_time`:
- first row = initial **Daily** bid
- subsequent rows = **REBID** versions

### B) Offer detail by period (quantities + computed offer price)
For each offer version `v` and period `p`:
- `BANDAVAIL1..10`
- (optional) a computed MW-weighted offer price for that period:
  - `offer_mw = sum_k BANDAVAILk`
  - `offer_price = sum_k PRICEBANDk * BANDAVAILk / offer_mw` (if `offer_mw>0`)

### C) Applied version by dispatch interval (optional but recommended)
For each dispatch interval timestamp `t`:
- `applied_offer_version_time = DISPATCHOFFERTRK.BIDOFFERDATE`
- link to the offer detail (via computed PERIODID and the join keys above)

This gives you:
- “what was offered” (all versions)
- “what was applied” (version actually used at each interval)

---

## 6) Step-by-step recipe (one service, one DUID)

### Step 0: Choose filters
- `DUID = '...'`
- `BIDTYPE = 'RAISE6SEC'` (or any FCAS service)
- `t_start`, `t_end` (dispatch timestamps)
- `market_day(s)` implied by your window

### Step 1: Pull all offer versions (`BIDDAYOFFER`)
Filter:
- `DUID`, `BIDTYPE`
- `SETTLEMENTDATE` in market days of interest

Keep:
- `SETTLEMENTDATE`, `OFFERDATE`, `ENTRYTYPE`
- `PRICEBAND1..10`
- rebid explanation fields (if present)

Sort by `OFFERDATE`.

### Step 2: Pull period-level details (`BIDOFFERPERIOD`)
Filter:
- `DUID`, `BIDTYPE`
- `TRADINGDATE` in the same market days

Keep:
- `TRADINGDATE`, `OFFERDATETIME`, `PERIODID`
- `BANDAVAIL1..10`
- any enablement parameters you care about

### Step 3: Join prices ↔ quantities (offer versions)
Join `BIDOFFERPERIOD` to `BIDDAYOFFER` on:
- `DUID`, `BIDTYPE`
- `TRADINGDATE = SETTLEMENTDATE`
- `OFFERDATETIME = OFFERDATE`

Now every row `(version, period)` has both prices and quantities.

### Step 4 (optional): Identify the applied version (`DISPATCHOFFERTRK`)
Filter `DISPATCHOFFERTRK` on:
- `DUID`, `BIDTYPE`
- `SETTLEMENTDATE` between `t_start` and `t_end`

Keep:
- `SETTLEMENTDATE` (dispatch time)
- `BIDSETTLEMENTDATE` (market day)
- `BIDOFFERDATE` (applied offer version time)

Compute `PERIODID(t)` for each `SETTLEMENTDATE` and join to the (version, period) panel on:
- `DUID`, `BIDTYPE`
- `BIDSETTLEMENTDATE = TRADINGDATE`
- `BIDOFFERDATE = OFFERDATETIME`
- `PERIODID(t) = PERIODID`

This labels each dispatch interval with the exact bid curve that was applied.

---

## 7) Organizing the results “by initial bid then rebids”

Once you have `BIDDAYOFFER` versions sorted by `OFFERDATE`:

- The **initial bid** for a market day is the earliest `OFFERDATE` with `ENTRYTYPE='Daily'`.
- All later `OFFERDATE` rows (usually `ENTRYTYPE='REBID'`) are subsequent rebids.

Recommended organization for reporting:
- Group by `market_day`
  - Section 1: Initial (Daily) offer version summary (band prices)
  - Section 2: Rebid versions list (offer timestamps + explanations)
  - Section 3: For each version, show period-level quantities (or summarize)
  - Section 4 (optional): Applied version timeline by dispatch interval

---

## 8) Common pitfalls

1) **Joining on the wrong “day” column**
- Use `TRADINGDATE` ↔ `SETTLEMENTDATE` for market day alignment.

2) **PERIODID mapping off-by-one**
- Validate the first/last period join to ensure PERIODID aligns with the table convention.

3) **You downloaded only part of `BIDOFFERPERIOD`**
- `BIDOFFERPERIOD` is split across many `FILE##` zips; you need them all for a complete month.

4) **Price bands don’t vary by period**
- For Day 0, expect `PRICEBANDk` constant across versions; rebids mainly alter quantities.

---

## 9) Minimal pseudo-SQL outline

1) Versions:
- `BIDDAYOFFER` filtered by `(DUID, BIDTYPE, market_day range)`

2) Period detail:
- `BIDOFFERPERIOD` filtered by `(DUID, BIDTYPE, market_day range)`

3) Join:
- `BIDOFFERPERIOD` ⋈ `BIDDAYOFFER` on `(DUID, BIDTYPE, TRADINGDATE=SETTLEMENTDATE, OFFERDATETIME=OFFERDATE)`

4) Applied (optional):
- `DISPATCHOFFERTRK` filtered by `(DUID, BIDTYPE, dispatch time range)`
- add computed `PERIODID`
- join to the (version, period) panel using `(DUID, BIDTYPE, BIDSETTLEMENTDATE=TRADINGDATE, BIDOFFERDATE=OFFERDATETIME, PERIODID)`

---

## 10) What you get at the end
A tidy dataset where each row can be:
- (offer version, period): what the participant offered, or
- (dispatch interval): what dispatch applied (via `DISPATCHOFFERTRK`), linked back to the offered curve.

From there you can compute:
- hourly average offered prices (by service)
- on-peak / off-peak averages
- rebid frequency statistics (count of distinct offer versions per day/period)
