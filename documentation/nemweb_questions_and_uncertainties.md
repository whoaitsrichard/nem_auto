# NEMWEB Data: Questions, Answers, and Uncertainties

> **Context**: This document answers the questions raised in `data_exploration_instructions.md` and documents uncertainties encountered during the research.
>
> **Methodology**: Answers were compiled from three sources:
> 1. **MMS Data Model v5.4 documentation** — the [Package Summary PDF](https://www.nemweb.com.au/Data_Archive/Wholesale_Electricity/MMSDM/2025/MMSDM_2025_01/MMSDM_Historical_Data_SQLLoader/DOCUMENTATION/MMS%20Data%20Model/v5.4/Electricity%20Data%20Model%20Package%20Summary.pdf), [full Data Model Report](https://www.nemweb.com.au/Data_Archive/Wholesale_Electricity/MMSDM/2025/MMSDM_2025_01/MMSDM_Historical_Data_SQLLoader/DOCUMENTATION/MMS%20Data%20Model/v5.4/Electricity%20Data%20Model%20Report.pdf), and PostgreSQL CREATE TABLE scripts from [MMSDM_create_v5.4.zip](https://www.nemweb.com.au/Data_Archive/Wholesale_Electricity/MMSDM/2025/MMSDM_2025_01/MMSDM_Historical_Data_SQLLoader/DOCUMENTATION/MMS%20Data%20Model/v5.4/MMSDM_create_v5.4.zip).
> 2. **AEMO published documentation** — official guides, fact sheets, and market specifications (all URLs cited inline).
> 3. **Web research** — industry publications, academic resources, and open-source tools.

---

## Answers to Specific Questions

### 1. What are the constraint data files?

**Answer**: Constraints in the NEM are **linear inequality equations** used by AEMO's dispatch engine (NEMDE) to represent physical and security limits of the power system. Each constraint takes the form **LHS ≤ RHS** (or ≥, or =).

- **Left Hand Side (LHS)**: A linear combination of decision variables NEMDE controls — generator outputs, interconnector flows, FCAS enablement quantities, and scheduled loads. Each term has a coefficient. For example: `1.0 × OAKEY1SF + 1.0 × OAKEY2SF ≤ 71` limits the combined output of two solar farms to 71 MW.

- **Right Hand Side (RHS)**: A constant or pre-calculated value representing the physical limit, derived from thermal ratings, voltage stability limits, transient stability limits, or measured system conditions.

Constraints ensure dispatch respects:
- Thermal limits on transmission lines and transformers
- Voltage stability limits
- Transient stability limits
- Interconnector transfer limits
- FCAS requirements
- System security requirements (e.g., oscillatory stability)

**The constraint data files in the January 2025 dataset are:**

| File | What it contains |
|------|-----------------|
| `GENCONDATA` | Master table of all constraint definitions: ID, type (≤/≥/=), description, which processes use it, impact, source, limit type, contingency reason |
| `GENCONSET` | Groups of constraints organized into sets |
| `GENCONSETINVOKE` | When each constraint set is active (invocation start/end periods) |
| `GENCONSETTRK` | Tracking/versioning for constraint sets |
| `GENERICCONSTRAINTRHS` | Dynamic RHS formulations |
| `GENERICEQUATIONRHS` | Reusable RHS equation components (using reverse Polish notation) |
| `GENERICEQUATIONDESC` | Descriptions of equation components |
| `SPDCONNECTIONPOINTCONSTRAINT` | LHS coefficients for generators/loads in constraints |
| `SPDINTERCONNECTORCONSTRAINT` | LHS coefficients for interconnectors |
| `SPDREGIONCONSTRAINT` | LHS coefficients for regional demand |
| `DISPATCHCONSTRAINT` | Results: which constraints were binding in each 5-min dispatch interval, with marginal values |
| `PREDISPATCHCONSTRAINT` | Constraint results from pre-dispatch runs |
| `P5MIN_CONSTRAINTSOLUTION` | Constraint results from 5-minute pre-dispatch |
| `CONSTRAINTRELAXATION_OCD` | Constraints relaxed in over-constrained dispatch re-runs |
| `DISPATCH_CONSTRAINT_FCAS_OCD` | FCAS constraints in OCD re-runs |
| `INTERCONNECTORCONSTRAINT` | Interconnector-specific constraint parameters |

**Relevance to project**: Constraint data is important for understanding congestion — when constraints bind, they cause price separation between regions. The `DISPATCHCONSTRAINT` table with `MARGINALVALUE > 0` identifies binding constraints, and cross-referencing with `GENCONDATA` and `SPDCONNECTIONPOINTCONSTRAINT` reveals which generators and interconnectors are involved. This directly relates to the project's interest in understanding why market clearing prices differ across the 5 NEM sub-regions.

**Further reading**:
- [AEMO Constraint FAQ](https://aemo.com.au/en/energy-systems/electricity/national-electricity-market-nem/system-operations/congestion-information-resource/constraint-faq)
- [AEMO Constraint Formulation Guidelines 2025 (PDF)](https://www.aemo.com.au/-/media/files/electricity/nem/security_and_reliability/congestion-information/2025/constraint-formulation-guidelines.pdf)
- [Ampere Labs — How to Decipher NEMDE Constraint Equations](https://amperelabs.com.au/how-to-decipher-nemde-constraint-equation-formulations/)
- [GitHub — susantoj/NEM_constraints](https://github.com/susantoj/NEM_constraints) (Python library for parsing constraint equations)

---

### 2. Are there any files that contain demand forecasts?

**Answer**: **Yes**, several files contain demand forecasts at different time horizons and resolutions.

**Dedicated demand forecast files:**

| File | Description | Resolution | Horizon |
|------|-------------|-----------|---------|
| `DEMANDOPERATIONALFORECAST` | Forecast operational demand per region per interval | 5-minute / 30-minute | Short-term |
| `DEMANDOPERATIONALACTUAL` | Actual operational demand per region (for comparison) | 5-minute / 30-minute | Historical |
| `PERDEMAND` | Regional demand and MR schedule data | Half-hour | Day-ahead |
| `RESDEMANDTRK` | Versioning for PERDEMAND | — | — |

**Demand forecasts embedded in other files:**

| File | Relevant columns |
|------|-----------------|
| `DISPATCHREGIONSUM` | `DEMANDFORECAST` — the demand forecast used in each 5-minute dispatch run; `TOTALDEMAND` — actual total demand |
| `PREDISPATCHREGIONSUM` | Regional demand forecasts from pre-dispatch (up to 40 hours ahead) |
| `P5MIN_REGIONSOLUTION` | Regional capacity and demand from 5-minute pre-dispatch |
| `P5MIN_SCENARIODEMAND` | Demand scenarios (POE10, POE50, POE90) for 5-minute pre-dispatch |
| `PREDISPATCHSCENARIODEMAND` | Demand scenarios for pre-dispatch |

**Probability of Exceedance (POE) scenarios**: AEMO's Demand Forecasting System generates three scenarios:
- **POE10** (10% probability of exceedance — high demand)
- **POE50** (50% — expected/median demand)
- **POE90** (90% — low demand)

**Intermittent generation forecasts** (solar/wind output predictions, which effectively are negative demand):

| File | Description |
|------|-------------|
| `INTERMITTENT_DS_PRED` | Unconstrained Intermittent Generation Forecasts (UIGF) for dispatch |
| `ROOFTOP_PV_FORECAST` | Rooftop solar generation forecast (8 days ahead, half-hourly) |
| `ROOFTOP_PV_ACTUAL` | Actual rooftop solar (for comparison) |

**Additional sources outside this dataset**:
- [AEMO Operational Demand Data](https://www.aemo.com.au/energy-systems/electricity/national-electricity-market-nem/data-nem/operational-demand-data)
- [AEMO Aggregated Price and Demand Data](https://www.aemo.com.au/energy-systems/electricity/national-electricity-market-nem/data-nem/aggregated-data)
- [AEMO Load Forecasting Methodology](https://aemo.com.au/en/energy-systems/electricity/national-electricity-market-nem/nem-forecasting-and-planning/operational-forecasting/load-forecasting-in-pre-dispatch-and-stpasa)

---

### 3. Are there fees for participating in these auctions?

**Answer**: **Yes, but they are ongoing participation fees, not per-bid or per-auction transaction fees.** AEMO recovers its operational costs from market participants through an annual fee structure.

**Fee categories:**

1. **NEM Core Fees** (main operational fee):
   - **Wholesale Participants (generators, IRPs)**: ~22.7% of NEM core costs. Split 50/50 between:
     - A daily rate based on the greater of registered capacity or notified maximum capacity
     - A daily rate based on MWh energy settled
   - **Market Customers (retailers)**: ~62.1% of NEM core costs. Split 50/50 between:
     - A rate per MWh of energy settled in the spot market
     - A fixed component
   - **Transmission Network Service Providers (TNSPs)**: ~17.5% of NEM core costs (~$25.8M in FY2025)

2. **NEM2025 Reform Program Fees**: Additional levy for system upgrades, split 27.5% wholesale participants / 72.5% market customers.

3. **Registration/Application Fees**: One-time fees paid upon registration. Vary by participant category, capacity, and service type.

**Key point**: There is **no per-bid or per-dispatch-interval fee**. Participants pay annual/daily fees for the right to participate, not a fee on each bid submission or auction clearing. The fees are cost-recovery charges for AEMO's market operation services.

**Sources**:
- [AEMO Energy Market Fees and Charges](https://www.aemo.com.au/about/corporate-governance/energy-market-fees-and-charges)
- [AEMO FY25 Budget and Fees (PDF)](https://www.aemo.com.au/-/media/files/about_aemo/energy_market_budget_and_fees/2024/aemo-final-budget-and-fees-fy25.pdf)
- [AEMO Connection and Registration Fees FY26 (PDF)](https://www.aemo.com.au/-/media/files/about_aemo/energy_market_budget_and_fees/2025/connection-and-registration-fees-fact-sheet.pdf)

**In the data**: The files `MARKETFEE`, `MARKETFEEDATA`, and `MARKETFEETRK` in the January 2025 dataset contain fee schedule definitions but not participant-level fee payments.

---

### 4. What are the exact market rules for these FCAS auctions?

**Answer**: FCAS is not auctioned in a separate process — it is **co-optimized with energy** in every 5-minute NEMDE dispatch run. The key rules are:

#### 4.1. The 10 FCAS Markets

Since October 2023 (when Very Fast FCAS was introduced), there are **10 FCAS markets**:

**Contingency FCAS (8 markets)** — respond to sudden frequency deviations (e.g., generator trip):

| Service | Bid Type Code | Response Time | Direction |
|---------|--------------|---------------|-----------|
| Very Fast Raise | RAISE1SEC | 1 second | Raise frequency (↑ generation or ↓ load) |
| Very Fast Lower | LOWER1SEC | 1 second | Lower frequency (↓ generation or ↑ load) |
| Fast Raise | RAISE6SEC | 6 seconds | Raise |
| Fast Lower | LOWER6SEC | 6 seconds | Lower |
| Slow Raise | RAISE60SEC | 60 seconds | Raise |
| Slow Lower | LOWER60SEC | 60 seconds | Lower |
| Delayed Raise | RAISE5MIN | 5 minutes | Raise |
| Delayed Lower | LOWER5MIN | 5 minutes | Lower |

**Regulation FCAS (2 markets)** — continuously correct small second-by-second deviations:

| Service | Direction |
|---------|-----------|
| Regulation Raise (RAISEREG) | Increase output / decrease consumption |
| Regulation Lower (LOWERREG) | Decrease output / increase consumption |

#### 4.2. Bid Structure

FCAS bids use the **same structure as energy bids**:
- **10 price bands** ($/MW) set for the trading day via `BIDDAYOFFER` (prices locked at 12:30 PM day-ahead)
- **10 quantity bands** (MW) per 5-minute interval via `BIDOFFERPERIOD` (can be rebid throughout the day)
- **FCAS trapezium parameters** (per-interval, in `BIDOFFERPERIOD`):
  - `ENABLEMENTMIN` — Minimum energy output (MW) at which FCAS becomes available
  - `ENABLEMENTMAX` — Maximum energy output (MW) at which FCAS can be supplied
  - `LOWBREAKPOINT` — MW where full FCAS quantity starts being available
  - `HIGHBREAKPOINT` — MW where full FCAS quantity stops being available
  - Between breakpoints, unit can provide full `MAXAVAIL`. Between enablement limits and breakpoints, available FCAS ramps linearly to zero.

#### 4.3. Co-Optimization

NEMDE simultaneously optimizes energy dispatch and FCAS enablement to minimize total cost. This means:
- A unit offering both energy and FCAS may be dispatched for energy at a level that permits its FCAS enablement (respecting the trapezium)
- The opportunity cost of withholding energy capacity for FCAS is internalized in the optimization
- FCAS prices reflect this co-optimization — an FCAS service that competes heavily with energy dispatch will clear at a higher price

#### 4.4. Regional Requirements

AEMO sets FCAS requirements on a **regional basis**. Some services have global NEM-wide requirements; others have local regional minimum requirements due to network separation risks (e.g., Tasmania via Basslink, or South Australia via the Heywood interconnector). When the system is intact and uncongested, FCAS can be sourced from any region. When constraints bind, regions may need local FCAS, driving regional price differences.

#### 4.5. Pricing

- Each FCAS service has its own **clearing price per region per 5-minute interval** (visible in `DISPATCHPRICE` and `TRADINGPRICE`)
- Pricing is **marginal/uniform** — all enabled providers receive the same price for a given service in a given region
- FCAS costs are recovered from market customers and generators who cause frequency deviations ("causer pays" principle for regulation; load-based recovery for contingency)

#### 4.6. Settlement

FCAS revenue = (clearing price for service) × (MW enabled) × (5 minutes / 60 minutes).

#### 4.7. Frequency Performance Payments (FPP) — New in 2024

The v5.4 data model introduces the FPP framework, which rewards/penalizes participants based on their **actual frequency response performance** during events, not just their enablement. This is reflected in the `FPP_*` tables in the dataset. Under FPP, providers who respond faster and more accurately earn additional payments; poor performers face deductions.

**Key regulatory documents**:
- [AEMO Market Ancillary Services Specification (MASS) v8.2 (PDF)](https://www.aemo.com.au/-/media/files/electricity/nem/security_and_reliability/ancillary_services/2024/market-ancillary-services-specification---v82-effective-3-june-2024.pdf) — the definitive specification for FCAS services, testing requirements, and verification
- [AEMO FCAS Model in NEMDE (PDF)](https://www.aemo.com.au/-/media/files/electricity/nem/security_and_reliability/dispatch/policy_and_process/fcas-model-in-nemde.pdf) — technical description of how FCAS is modeled in the dispatch engine
- [AEMO Settlements Guide to Ancillary Services (PDF)](https://www.aemo.com.au/-/media/files/electricity/nem/data/ancillary_services/2025/settlements-guide-to-ancillary-services-and-frequency-performance-payments.pdf)
- [National Electricity Rules (NER)](https://energy-rules.aemc.gov.au/ner) — the legal framework; FCAS is covered primarily in Chapter 3 (Market Rules) and Chapter 8 (Transitional)

---

### 5. Is there data on the geographic location for each market participant?

**Answer**: **Partially, from multiple sources.** The NEMWEB dataset itself does not contain latitude/longitude coordinates, but it does contain hierarchical location information that can be cross-referenced.

**What's in the NEMWEB data:**

| File | Location-relevant columns |
|------|--------------------------|
| `DUDETAIL` | `CONNECTIONPOINTID` — the transmission network connection point for each DUID |
| `DUDETAILSUMMARY` | `REGIONID` — which of the 5 NEM regions the DUID is in; `STATIONID` — station identifier |
| `STATION` | Station identifiers and names |
| `STATIONOWNER` | Station ownership |
| `NETWORK_SUBSTATIONDETAIL` | Substation details (may include geographic identifiers) |

**External sources with geographic coordinates:**

1. **AEMO Generation Information spreadsheet** (updated quarterly): Contains station name, DUID, region, technology type, fuel type, nameplate capacity, and **physical location data** (address, and in some versions latitude/longitude). Download from [AEMO Generation Information](https://www.aemo.com.au/energy-systems/electricity/national-electricity-market-nem/nem-forecasting-and-planning/forecasting-and-planning-data/generation-information).

2. **AEMO NEM Generation Maps**: PDF maps showing geographic locations of power stations by region. Available at [AEMO NEM Generation Maps](https://aemo.com.au/en/energy-systems/electricity/national-electricity-market-nem/participate-in-the-market/network-connections/nem-generation-maps).

3. **AEMO NEM Registration and Exemption List**: Lists every registered participant with DUIDs, registration categories, regions, and ancillary service classifications.

4. **Community/third-party datasets**:
   - [OpenNEM](https://opennem.org.au) — open-source project compiling AEMO data with geographic information
   - [GitHub — hsenot/aemo](https://github.com/hsenot/aemo) — includes a `geo.csv` mapping DUIDs to latitude/longitude
   - [GitHub — akxen/egrimod-nem-dataset](https://github.com/akxen/egrimod-nem-dataset) — academic dataset describing NEM topology
   - [Ampere Labs article on building NEM models from public data](https://amperelabs.com.au/can-a-power-system-model-of-the-nem-be-built-from-publicly-available-data/)

---

### 6. Do participants submit bids for specific regions, or do they just submit it to the entire market and the system operator decides which market they take part in?

**Answer**: **Participants submit bids per DUID (Dispatchable Unit Identifier), and each DUID is physically registered in a specific region.** Participants do **not** choose which region to bid into — the region is determined by where the physical asset is connected.

**How it works:**

1. Each generator, load, or battery is registered as a DUID at a specific **connection point** (transmission node) within one of the 5 NEM regions.
2. The DUID's region is fixed at registration — it's a physical attribute, not a bidding choice.
3. Participants submit bids for each of their DUIDs (prices and quantities per band). The bid identifies the DUID, not the region.
4. NEMDE aggregates all bids from all DUIDs across all regions, applies network constraints and interconnector limits, and determines:
   - How much each DUID generates or consumes
   - The clearing price for each region (the Regional Reference Price, RRP)
   - Interconnector flows between regions
5. A participant with assets in multiple regions submits separate bids for each DUID. The bids are independent — different prices and quantities can be set for each unit.

**In the data**: The `DUDETAILSUMMARY` table maps each DUID to its REGIONID. The bid tables (`BIDDAYOFFER`, `BIDOFFERPERIOD`) are keyed by DUID, not by region. The price tables (`DISPATCHPRICE`, `TRADINGPRICE`) are keyed by REGIONID.

**Key implication for the project**: To get "bids per region," you need to join the bid tables (keyed by DUID) with `DUDETAILSUMMARY` (which maps DUID → REGIONID). There is no direct "region" column in the bid tables.

---

## Additional Context: Battery Participation

Since the project involves autobidder systems (likely for batteries), here is how batteries participate in the NEM:

### Registration

Since **3 June 2024**, batteries participate under the **Integrated Resource Provider (IRP)** registration category with **Bidirectional Units (BDUs)**, following the AEMC's "Integrating Energy Storage Systems" (IESS) rule change. A battery operates as a **single Bidirectional Unit with a single DUID** that can both generate (discharge) and consume (charge).

Previously, batteries needed two separate DUIDs (one as Generator for discharge, one as Scheduled Load for charge). In 2024, all 23 previously-operational scheduled batteries transitioned to single BDU DUIDs.

### Bidding for Charging (Buying Energy)

A BDU submits a **2-sided energy bid**:
- **Generation (discharge)**: `DIRECTION = "GEN"` — 10 price bands for selling energy
- **Load (charge)**: `DIRECTION = "LOAD"` — 10 price bands for buying energy

To buy energy for charging, the battery bids as a scheduled load. The price bands represent the **maximum price willing to pay**. NEMDE dispatches loads in merit order from highest willingness-to-pay downward.

### FCAS from Batteries

Batteries can provide all 10 FCAS services. They are particularly suited to fast-response services (Very Fast, Fast contingency) due to sub-second response times. FCAS offers follow the same structure, with the FCAS trapezium coupling FCAS enablement to the battery's energy dispatch level.

**In the data**: Bidirectional units are identified by `DISPATCHTYPE = 'BIDIRECTIONAL'` in `DUDETAIL`, or `UNITTYPE = 'BIDIRECTIONAL'` in `DISPATCHABLEUNIT`. The `DIRECTION` column in `BIDDAYOFFER` / `BIDOFFERPERIOD` distinguishes generation vs. load bids. `MAXSTORAGECAPACITY` in `DUDETAIL` gives the storage capacity in MWh.

**Revenue context**: Historically, approximately **60% of large-scale BESS revenues** in the NEM came from FCAS. The introduction of 5-minute settlement in 2021 led to a **69% increase** in dispatch-weighted prices earned by battery generators in South Australia.

**Sources**:
- [AEMO — Registering a Battery System (PDF)](https://www.aemo.com.au/-/media/files/electricity/nem/participant_information/new-participants/registering-a-battery-system-in-the-nem.pdf)
- [AEMO — Register as an IRP](https://www.aemo.com.au/energy-systems/electricity/national-electricity-market-nem/participate-in-the-market/registration/register-as-an-irp-in-the-nem)
- [WattClarity — NEM Batteries Transitioned to BDUs in 2024](https://wattclarity.com.au/articles/2025/01/nem-batteries-transitioned-to-bidirectional-units-in-2024/)
- [AEMC — IESS Final Determination (PDF)](https://www.aemc.gov.au/sites/default/files/2021-12/1._final_determination_-_integrating_energy_storage_systems_into_the_nem.pdf)

---

## Uncertainties and Open Questions

### A. Data Completeness

1. **BIDOFFERPERIOD vs. BIDPEROFFER_D**: The BIDOFFERPERIOD table (39 files, containing all rebids) is dramatically larger than BIDPEROFFER_D (1 file, dispatch-effective only). It is unclear exactly how large the uncompressed data is, or whether downloading all 39 files for January 2025 is feasible for regular analysis. **Recommendation**: Start with BIDPEROFFER_D for initial analysis; use BIDOFFERPERIOD only when studying rebidding behavior specifically.

2. **RAISE1SEC / LOWER1SEC data**: The Very Fast FCAS markets (1-second response) were introduced in October 2023. The data model includes these bid types, but it is uncertain whether all participants have adopted these new bid types or whether the data is fully populated for January 2025. The `DISPATCHPRICE` table does include `RAISE1SECRRP` and `LOWER1SECRRP` columns, suggesting prices are being cleared.

3. **FPP (Frequency Performance Payments) data**: This is new in v5.4 (November 2024). The 18 FPP-related files may contain incomplete or preliminary data for January 2025 if the framework was not yet fully operational. **Uncertainty**: We have not verified whether FPP was live and generating data in January 2025.

### B. Data Interpretation

4. **INTERVENTION flag**: Many dispatch tables include an `INTERVENTION` column (0 or 1). When AEMO intervenes in the market (e.g., directing a unit to run for system security), a "what-if" dispatch is also run without the intervention to calculate counterfactual prices. It is unclear which `INTERVENTION` value (0 or 1) represents the actual vs. counterfactual run. **This needs clarification from AEMO documentation before filtering data.** Initial reading suggests `INTERVENTION = 0` is the physical dispatch and `INTERVENTION = 1` is the pricing run used for settlement, but this should be confirmed.

5. **RUNNO column**: Dispatch tables include a `RUNNO` column. For most current data `RUNNO = 1`, but historical data may have re-runs. **Assumption**: For January 2025, `RUNNO = 1` should be sufficient.

6. **Price bands ordering**: The data model specifies PRICEBAND1 through PRICEBAND10. It is assumed these must be monotonically increasing (PRICEBAND1 ≤ PRICEBAND2 ≤ ... ≤ PRICEBAND10) per AEMO's bidding rules, but this is not explicitly enforced in the schema. Validation should be performed on actual data.

7. **Bid effective timing**: When a participant rebids during the day, the new quantities take effect from the next dispatch interval after processing. The `OFFERDATETIME` column in BIDOFFERPERIOD records when each rebid was submitted. The relationship between `OFFERDATETIME` and which dispatch interval the rebid first applies to involves processing delays (~20 seconds before gate closure). **For precise rebid timing analysis, the DISPATCHOFFERTRK table is essential** — it records exactly which offer version was used in each dispatch interval.

### C. Scope Gaps

8. **Participant-level revenue/cost data**: The settlement files (`SET_*`) contain aggregate settlement results, but **individual participant-level settlement data is not publicly available** in NEMWEB. We can calculate approximate revenues from dispatch prices × dispatched quantities, but actual settlements include loss factors, ancillary service payments/charges, and other adjustments.

9. **Autobidder identification**: There is **no field in the data** that identifies whether a participant uses an autobidder system. This would need to be inferred from bidding behavior (e.g., frequency of rebids, response patterns to price signals, systematic vs. manual bidding patterns). The `REBIDEXPLANATION` field in BIDDAYOFFER may contain textual clues (e.g., "automated" or "algorithm" in rebid reasons), but this is unstructured text.

10. **State of Charge (SoC) for batteries**: The NEMWEB data does **not** include battery state of charge. `MAXSTORAGECAPACITY` in DUDETAIL gives the total storage capacity, and `ENERGYLIMIT` in BIDOFFERPERIOD may reflect energy constraints, but actual SoC at each interval is not published. SoC would need to be inferred from cumulative dispatch (charge/discharge) over time, with assumptions about efficiency.

11. **Actual FCAS activation vs. enablement**: The dispatch data shows FCAS **enablement** (how much capacity was armed), but **not actual FCAS activation** (how much energy was actually delivered during frequency events). Actual delivery data is in the FPP tables (`FPP_PERFORMANCE`, `FPP_USAGE`) but may be limited.

### D. Data Access and Tools

12. **Recommended Python tools for data access**:
    - [NEMOSIS](https://github.com/UNSW-CEEM/NEMOSIS) — UNSW CEEM tool for downloading and compiling AEMO MMS data. Handles the zip file extraction, CSV parsing, and table joining automatically.
    - [nem-data](https://github.com/ADGEfficiency/nem-data) — alternative Python package for NEM data access.
    - [nempy](https://nempy.readthedocs.io/en/latest/intro.html) — open-source package that replicates NEMDE's co-optimized dispatch algorithm (useful for counterfactual analysis).
    - [OpenNEM](https://opennem.org.au) — browser-based visualization and data download.

13. **Data format**: All files are CSV-formatted inside ZIP archives. The CSV format follows AEMO's MMSDM loader convention:
    - Row 1: `C` (comment) header with table metadata
    - Row 2: `I` (information) header with column names
    - Rows 3+: `D` (data) rows
    - Last row: `C` (comment) footer with row count

    Standard pandas `read_csv()` may need `skiprows` and `skipfooter` parameters, or use NEMOSIS which handles this automatically.

14. **AEMO Data Model v5.6**: There is a [newer version (v5.6, November 2025)](https://tech-specs.docs.public.aemo.com.au/Content/TSP_EMMSDM56_Nov2025/Electricity_Data_Model_v.htm) of the data model documentation available online. The January 2025 data was produced under v5.4, but the v5.6 docs may have updated descriptions. **For January 2025 data, use the v5.4 documentation to avoid confusion.**

### E. Questions for Further Investigation

15. **How are FCAS requirements determined for each region?** AEMO publishes FCAS requirements, but the methodology for setting them (especially local requirements driven by system security) is complex and governed by the MASS and the NER. This affects interpretation of FCAS prices — high regional FCAS prices may reflect tight local requirements rather than overall system scarcity.

16. **What is the "causer pays" mechanism for regulation FCAS cost recovery?** The `FCAS_REGU_USAGE_FACTORS` table in the data contains causer-pays factors, but understanding how these are calculated requires detailed knowledge of the metering and frequency contribution assessment process.

17. **How do interconnector losses affect regional price separation?** The `TRANSMISSIONLOSSFACTOR` and `LOSSFACTORMODEL` tables contain loss factors, but understanding their impact on pricing requires knowledge of how NEMDE incorporates marginal loss factors into the dispatch optimization.

---

## Summary of Key Data Tables for the Project

For quick reference, here are the essential table-to-question mappings:

| Research Question | Primary Tables |
|-------------------|---------------|
| FCAS bid prices per firm | `BIDDAYOFFER` (or `BIDDAYOFFER_D`) filtered on BIDTYPE ∈ {RAISE1SEC, RAISE6SEC, RAISE60SEC, RAISE5MIN, RAISEREG, LOWER1SEC, LOWER6SEC, LOWER60SEC, LOWER5MIN, LOWERREG} |
| FCAS bid quantities per firm per 5-min interval | `BIDOFFERPERIOD` (or `BIDPEROFFER_D`) filtered on same BIDTYPEs |
| Energy bid prices per firm | `BIDDAYOFFER` (or `BIDDAYOFFER_D`) filtered on BIDTYPE = 'ENERGY' |
| Energy bid quantities per firm per 5-min interval | `BIDOFFERPERIOD` (or `BIDPEROFFER_D`) filtered on BIDTYPE = 'ENERGY' |
| Energy clearing price per region | `DISPATCHPRICE` → `RRP` column, keyed by `REGIONID` |
| FCAS clearing prices per region | `DISPATCHPRICE` → `RAISE6SECRRP`, `RAISEREGRRP`, etc. columns |
| Map DUID to region/participant/station | `DUDETAILSUMMARY` |
| Identify batteries | `DUDETAIL` → `DISPATCHTYPE = 'BIDIRECTIONAL'` and/or `MAXSTORAGECAPACITY > 0` |
| Actual dispatch per unit | `DISPATCHLOAD` |
| Demand per region | `DISPATCHREGIONSUM` → `TOTALDEMAND`, `DEMANDFORECAST` |
| Binding constraints (congestion) | `DISPATCHCONSTRAINT` → `MARGINALVALUE > 0` |
