# NEMWEB January 2025 Data File Catalog

> **Scope**: All 274 ZIP files in the [NEMWEB MMSDM Historical Data SQLLoader DATA directory](https://www.nemweb.com.au/Data_Archive/Wholesale_Electricity/MMSDM/2025/MMSDM_2025_01/MMSDM_Historical_Data_SQLLoader/DATA/) for January 2025.
>
> **Purpose**: Describe each data file and assess its relevance to our project studying autobidder systems in the NEM, specifically: (1) bid price/quantity bands for FCAS and energy markets per firm, (2) market clearing prices for all 5 NEM regions for every auction, and (3) battery participation in energy and FCAS markets.
>
> **Methodology**: File descriptions were derived from the [MMS Data Model v5.4 documentation](https://www.nemweb.com.au/Data_Archive/Wholesale_Electricity/MMSDM/2025/MMSDM_2025_01/MMSDM_Historical_Data_SQLLoader/DOCUMENTATION/MMS%20Data%20Model/v5.4/), including the Electricity Data Model Package Summary, the full Data Model Report (column-level documentation), and the PostgreSQL CREATE TABLE scripts from `MMSDM_create_v5.4.zip`. Additional context from AEMO's published guides and the National Electricity Rules.
>
> **File naming convention**: All files follow the pattern `PUBLIC_ARCHIVE#<TABLE_NAME>#FILE<NN>#202501010000.zip`. Tables with large data volumes are split across multiple files (e.g., BIDOFFERPERIOD spans FILE01–FILE39). In this catalog, multi-file tables are listed once with the file count noted.

---

## Relevance Legend

| Symbol | Meaning |
|--------|---------|
| **CRITICAL** | Directly required for core project data (bids, clearing prices, participant identification) |
| **HIGH** | Very useful supporting data (demand, constraints, interconnectors, forecasts) |
| **MODERATE** | Potentially useful for extended analysis (settlement, FCAS recovery, network topology) |
| **LOW** | Unlikely to be needed for core analysis (billing, GST, admin, prudentials) |

---

## 1. BIDS PACKAGE — Energy and FCAS Offers

These are the most important files for the project. They contain the actual bid/offer data submitted by participants.

| File | Files | Description | Relevance |
|------|-------|-------------|-----------|
| `BIDDAYOFFER` | 1 | **Day-level bid prices**: Contains the 10 price bands (PRICEBAND1–PRICEBAND10, $/MWh) for each DUID × BIDTYPE × SETTLEMENTDATE. Prices are locked at 12:30 PM the day before. Also includes daily energy constraints, minimum load, fast-start parameters (T1–T4), and rebid explanations. BIDTYPE column distinguishes ENERGY from FCAS types (RAISE6SEC, RAISE60SEC, RAISE5MIN, RAISEREG, LOWER6SEC, LOWER60SEC, LOWER5MIN, LOWERREG, RAISE1SEC, LOWER1SEC). | **CRITICAL** |
| `BIDDAYOFFER_D` | 1 | **Dispatch-effective day-level bid prices** (public version): The prices that were actually used in dispatch (after rebids are resolved). Same structure as BIDDAYOFFER but reflects the final effective offer. | **CRITICAL** |
| `BIDOFFERPERIOD` | 39 | **5-minute period-level bid quantities**: Contains the 10 MW quantity bands (BANDAVAIL1–BANDAVAIL10) for each DUID × BIDTYPE × 5-minute period (PERIODID 1–288). Also includes MAXAVAIL, ramp rates (RAMPUPRATE/RAMPDOWNRATE for energy), and FCAS trapezium parameters (ENABLEMENTMIN, ENABLEMENTMAX, LOWBREAKPOINT, HIGHBREAKPOINT). This is by far the largest dataset (39 files) because it covers every unit × every bid type × every 5-minute interval × every rebid. | **CRITICAL** |
| `BIDPEROFFER_D` | 1 | **Dispatch-effective period-level bid quantities** (public version): The quantities that were actually applicable in dispatch. Corresponds to BIDDAYOFFER_D. | **CRITICAL** |
| `BIDDUIDDETAILS` | 1 | Registration data for each ancillary service a DUID is registered to provide. Validates which bid types each unit can submit. | **HIGH** |
| `BIDDUIDDETAILSTRK` | 1 | Tracking/versioning table for BIDDUIDDETAILS. | LOW |
| `BIDTYPES` | 1 | Static reference table listing all bid types (ENERGY, RAISE6SEC, etc.), number of bands, and price lockdown rules. | **HIGH** |
| `BIDTYPESTRK` | 1 | Tracking/versioning for BIDTYPES. | LOW |

### How to reconstruct bid curves

1. From **BIDDAYOFFER** (or BIDDAYOFFER_D): get PRICEBAND1–PRICEBAND10 for a given DUID + BIDTYPE + SETTLEMENTDATE.
2. From **BIDOFFERPERIOD** (or BIDPEROFFER_D): get BANDAVAIL1–BANDAVAIL10 for the matching DUID + BIDTYPE + period.
3. Pair them: Band *i* = (PRICEBAND*i*, BANDAVAIL*i*). The cumulative sum of BANDAVAIL gives the stepped supply/demand curve.
4. For FCAS bids, also use the trapezium parameters to understand the coupling between FCAS enablement and energy dispatch level.

---

## 2. DISPATCH PACKAGE — 5-Minute Dispatch Results

These files contain the outcomes of each 5-minute dispatch run, including clearing prices.

| File | Files | Description | Relevance |
|------|-------|-------------|-----------|
| `DISPATCHPRICE` | 1 | **5-minute dispatch clearing prices for energy and all FCAS services, per region**. Contains RRP (Regional Reference Price, $/MWh) for energy, plus clearing prices for all 10 FCAS services (RAISE6SECRRP, RAISE60SECRRP, RAISE5MINRRP, RAISEREGRRP, LOWER6SECRRP, LOWER60SECRRP, LOWER5MINRRP, LOWERREGRRP, RAISE1SECRRP, LOWER1SECRRP). Also includes ROP (original price before any capping), administered price cap flags, and price status (FIRM/NOT FIRM). Keyed by REGIONID (NSW1, VIC1, QLD1, SA1, TAS1). | **CRITICAL** |
| `DISPATCHLOAD` | 1 | **5-minute dispatch targets per DUID**: MW dispatched for each unit each interval. Includes initial MW, total cleared, ramp rate, FCAS enablement quantities per service, and availability. Essential for seeing what was actually dispatched vs. what was bid. | **CRITICAL** |
| `DISPATCHREGIONSUM` | 1 | **5-minute regional demand and supply summary**: Total demand, available generation, dispatched generation/load, net interchange, plus FCAS requirement and availability quantities for every service per region. | **HIGH** |
| `DISPATCHINTERCONNECTORRES` | 1 | Interconnector flow results per 5-minute interval: MW flow, losses, import/export limits. | **HIGH** |
| `DISPATCHCONSTRAINT` | 1 | All binding and interconnector constraints for each dispatch interval: constraint ID, RHS value, marginal value ($, >0 = binding), violation degree, LHS value. | **HIGH** |
| `DISPATCHCASESOLUTION` | 1 | Dispatch case metadata: run parameters, solve status, objective function value, total costs, intervention flags. | MODERATE |
| `DISPATCHOFFERTRK` | 1 | Tracking which offer was used for each DUID in each dispatch interval. Links dispatch results back to specific bid submissions. | **HIGH** |
| `DISPATCH_UNIT_SCADA` | 1 | SCADA telemetry data per DUID per interval (actual MW output as measured). | **HIGH** |
| `DISPATCH_LOCAL_PRICE` | 1 | Local marginal prices at individual connection points (vs. regional reference prices). Shows locational pricing effects within a region. | MODERATE |
| `DISPATCH_INTERCONNECTION` | 1 | Interconnector dispatch results with additional detail. | MODERATE |
| `DISPATCH_MNSPBIDTRK` | 1 | Tracking of Market Network Service Provider (MNSP) bids used in dispatch. | LOW |
| `DISPATCH_FCAS_REQ` | 1 | FCAS requirement tracking per constraint per region per bid type. Shows how FCAS costs are attributed to constraints and regions. | **HIGH** |
| `DISPATCH_FCAS_REQ_CONSTRAINT` | 1 | Enhanced FCAS constraint cost/price details (new in v5.4, for Frequency Performance Payments). | MODERATE |
| `DISPATCH_FCAS_REQ_RUN` | 1 | Run-level metadata for FCAS requirement tracking. | LOW |
| `DISPATCH_CONSTRAINT_FCAS_OCD` | 1 | FCAS constraint data from Over-Constrained Dispatch (OCD) re-runs. | LOW |
| `CONSTRAINTRELAXATION_OCD` | 1 | Constraints relaxed during OCD re-runs. | LOW |

---

## 3. TRADING DATA PACKAGE — Settlement Prices

| File | Files | Description | Relevance |
|------|-------|-------------|-----------|
| `TRADINGPRICE` | 1 | **5-minute trading interval prices per region** (settlement prices). Since 5-minute settlement (Oct 2021), these are the actual settlement prices. Contains RRP and all FCAS prices, same structure as DISPATCHPRICE but at trading/settlement granularity. Includes PRICE_STATUS. | **CRITICAL** |
| `TRADINGINTERCONNECT` | 1 | Interconnector flows at trading interval level. | MODERATE |

---

## 4. PRE-DISPATCH PACKAGE — Forward-Looking Forecasts

| File | Files | Description | Relevance |
|------|-------|-------------|-----------|
| `PREDISPATCHPRICE` | 1 | Forecast prices per region from pre-dispatch runs (up to 40 hours ahead). Contains energy and FCAS price forecasts. | **HIGH** |
| `PREDISPATCHREGIONSUM` | 1 | Regional demand/supply forecasts from pre-dispatch. | **HIGH** |
| `PREDISPATCHLOAD` | 1 | Forecast unit-level dispatch from pre-dispatch. | MODERATE |
| `PREDISPATCHCONSTRAINT` | 1 | Forecast binding constraints from pre-dispatch. | MODERATE |
| `PREDISPATCHINTERCONNECTORRES` | 1 | Forecast interconnector flows from pre-dispatch. | MODERATE |
| `PREDISPATCHCASESOLUTION` | 1 | Pre-dispatch case metadata. | LOW |
| `PREDISPATCHOFFERTRK` | 1 | Offer tracking for pre-dispatch. | LOW |
| `PREDISPATCH_FCAS_REQ` | 1 | FCAS requirements in pre-dispatch. | MODERATE |
| `PREDISPATCH_LOCAL_PRICE` | 1 | Local marginal prices from pre-dispatch. | LOW |
| `PREDISPATCH_MNSPBIDTRK` | 1 | MNSP bid tracking for pre-dispatch. | LOW |
| `PREDISPATCHPRICESENSITIVITIES` | 1 | Price sensitivity analysis from pre-dispatch (what-if scenarios). | MODERATE |
| `PREDISPATCHSCENARIODEMAND` | 1 | Demand scenario data for pre-dispatch runs. | MODERATE |
| `PREDISPATCHSCENARIODEMANDTRK` | 1 | Tracking for demand scenarios. | LOW |

---

## 5. P5MIN PACKAGE — 5-Minute Pre-Dispatch

| File | Files | Description | Relevance |
|------|-------|-------------|-----------|
| `P5MIN_REGIONSOLUTION` | 1 | Regional results from 5-minute pre-dispatch: prices, supply, demand, reserves for each region, looking 1 hour ahead at 5-minute resolution. | **HIGH** |
| `P5MIN_CASESOLUTION` | 1 | Case metadata for P5MIN runs. | LOW |
| `P5MIN_CONSTRAINTSOLUTION` | 3 | Constraint solution details from P5MIN (large, split across 3 files). | MODERATE |
| `P5MIN_INTERCONNECTORSOLN` | 1 | Interconnector solution from P5MIN. | MODERATE |
| `P5MIN_LOCAL_PRICE` | 1 | Local marginal prices from P5MIN. | LOW |
| `P5MIN_INTERSENSITIVITIES` | 1 | Interconnector sensitivity analysis. | LOW |
| `P5MIN_PRICESENSITIVITIES` | 1 | Price sensitivity analysis from P5MIN. | MODERATE |
| `P5MIN_SCENARIODEMAND` | 1 | Demand scenarios for P5MIN. | LOW |
| `P5MIN_SCENARIODEMANDTRK` | 1 | Tracking for P5MIN demand scenarios. | LOW |
| `P5MIN_FCAS_REQ_CONSTRAINT` | 4 | FCAS requirement constraints from P5MIN (4 files). | MODERATE |
| `P5MIN_FCAS_REQ_RUN` | 1 | FCAS requirement run metadata for P5MIN. | LOW |

---

## 6. PD7DAY PACKAGE — 7-Day Pre-Dispatch

| File | Files | Description | Relevance |
|------|-------|-------------|-----------|
| `PD7DAY_PRICESOLUTION` | 1 | 7-day ahead price forecasts by region. | MODERATE |
| `PD7DAY_MARKET_SUMMARY` | 1 | 7-day ahead market summary. | MODERATE |
| `PD7DAY_CASESOLUTION` | 1 | Case metadata for 7-day runs. | LOW |
| `PD7DAY_CONSTRAINTSOLUTION` | 5 | Constraint solutions from 7-day runs (5 files). | LOW |
| `PD7DAY_INTERCONNECTORSOLUTION` | 1 | Interconnector solution from 7-day runs. | LOW |
| `PD_FCAS_REQ_CONSTRAINT` | 3 | FCAS requirement constraints from pre-dispatch (3 files). | LOW |
| `PD_FCAS_REQ_RUN` | 1 | FCAS requirement run metadata. | LOW |

---

## 7. DEMAND FORECASTS PACKAGE

| File | Files | Description | Relevance |
|------|-------|-------------|-----------|
| `DEMANDOPERATIONALACTUAL` | 1 | **Actual operational demand** per region per interval. | **HIGH** |
| `DEMANDOPERATIONALFORECAST` | 1 | **Forecast operational demand** per region per interval. | **HIGH** |
| `PERDEMAND` | 1 | Regional demand and MR schedule data per half-hour period. | MODERATE |
| `RESDEMANDTRK` | 1 | Versioning/tracking for PERDEMAND. | LOW |

---

## 8. PARTICIPANT REGISTRATION PACKAGE

| File | Files | Description | Relevance |
|------|-------|-------------|-----------|
| `PARTICIPANT` | 1 | Master table of all registered participants (PARTICIPANTID, class). | **CRITICAL** |
| `PARTICIPANTCLASS` | 1 | Reference table of participant classes (Generator, Customer, IRP, etc.). | **HIGH** |
| `PARTICIPANTCATEGORY` | 1 | Participant category definitions. | MODERATE |
| `PARTICIPANTCATEGORYALLOC` | 1 | Allocation of participants to categories. | MODERATE |
| `DISPATCHABLEUNIT` | 1 | Master table of all DUIDs: unit name, type (LOAD, GENERATOR, BIDIRECTIONAL). | **CRITICAL** |
| `DUDETAIL` | 1 | **Detailed unit registration data**: connection point, registered capacity, max capacity, dispatch type, start type, intermittent flag, semi-schedule flag, ramp rates, and **MAXSTORAGECAPACITY (MWh) for batteries**. | **CRITICAL** |
| `DUDETAILSUMMARY` | 1 | Convenience table joining DUID to REGIONID, STATIONID, PARTICIPANTID, loss factors, price limits, schedule type. | **CRITICAL** |
| `DUALLOC` | 1 | Cross-reference of DUID to physical GENSETID. | MODERATE |
| `STATION` | 1 | Station identifiers and names. | **HIGH** |
| `STATIONOWNER` | 1 | Station ownership details. | **HIGH** |
| `STATIONOWNERTRK` | 1 | Tracking for station ownership changes. | LOW |
| `STATIONOPERATINGSTATUS` | 1 | Operating status of stations. | MODERATE |
| `STADUALLOC` | 1 | Allocation of DUIDs to stations. | MODERATE |
| `GENUNITS` | 1 | Generating unit set details with station linkage. | MODERATE |
| `GENUNITS_UNIT` | 1 | Physical units within a generating unit set. | LOW |

---

## 9. MARKET CONFIGURATION PACKAGE

| File | Files | Description | Relevance |
|------|-------|-------------|-----------|
| `REGION` | 1 | Definition of the 5 NEM regions (NSW1, VIC1, QLD1, SA1, TAS1). | **HIGH** |
| `REGIONSTANDINGDATA` | 1 | Standing data for regions. | MODERATE |
| `REGIONAPC` | 1 | Administered Price Cap data per region. | MODERATE |
| `REGIONAPCINTERVALS` | 1 | Intervals where administered pricing was applied. | MODERATE |
| `INTERCONNECTOR` | 1 | Definition of interconnectors between regions. | **HIGH** |
| `INTERCONNECTORCONSTRAINT` | 1 | Constraint parameters for interconnectors. | MODERATE |
| `LOSSFACTORMODEL` | 1 | Loss factor model definitions. | MODERATE |
| `LOSSMODEL` | 1 | Loss model segment definitions. | LOW |
| `TRANSMISSIONLOSSFACTOR` | 1 | Transmission loss factors per connection point. | MODERATE |
| `MARKET_PRICE_THRESHOLDS` | 1 | Market Price Cap and Cumulative Price Threshold values. | MODERATE |
| `MARKETFEE` | 1 | Market fee definitions. | LOW |
| `MARKETFEEDATA` | 1 | Market fee data. | LOW |
| `MARKETFEETRK` | 1 | Market fee tracking. | LOW |
| `OVERRIDERRP` | 1 | Manual overrides to regional reference prices (rare events). | LOW |

---

## 10. GENERIC CONSTRAINT PACKAGE

| File | Files | Description | Relevance |
|------|-------|-------------|-----------|
| `GENCONDATA` | 1 | **Master table of all generic constraints**: constraint ID, type (<=, >=, =), static RHS value, description, which processes use it (dispatch/predispatch/STPASA/MTPASA), impact description, source, limit type (thermal/voltage/transient stability), reason/contingency. | **HIGH** |
| `GENCONSET` | 1 | Groups constraints into constraint sets. | MODERATE |
| `GENCONSETINVOKE` | 1 | Which constraint sets are active and when (invocation periods). | MODERATE |
| `GENCONSETTRK` | 1 | Tracking for constraint sets. | LOW |
| `GENERICCONSTRAINTRHS` | 1 | Dynamic RHS formulations for constraints (dispatch, predispatch, STPASA). | MODERATE |
| `GENERICEQUATIONDESC` | 1 | Descriptions of reusable RHS equation components. | LOW |
| `GENERICEQUATIONRHS` | 1 | Reusable RHS equation component definitions. | LOW |
| `SPDCONNECTIONPOINTCONSTRAINT` | 1 | **LHS coefficients for generators/loads** in constraint equations. Links specific DUIDs to constraints. | **HIGH** |
| `SPDINTERCONNECTORCONSTRAINT` | 1 | **LHS coefficients for interconnectors** in constraint equations. | MODERATE |
| `SPDREGIONCONSTRAINT` | 1 | **LHS coefficients for regional demand** in constraint equations. | MODERATE |
| `EMSMASTER` | 1 | Energy Management System reference data (used in RHS equations). | LOW |

---

## 11. FPP (FREQUENCY PERFORMANCE PAYMENTS) PACKAGE — New in v5.4

These files relate to the new Frequency Performance Payments framework introduced in 2024, which rewards/penalizes participants based on actual frequency response performance.

| File | Files | Description | Relevance |
|------|-------|-------------|-----------|
| `FPP_RUN` | 1 | FPP run metadata. | MODERATE |
| `FPP_FCAS_SUMMARY` | 1 | FCAS summary under FPP framework. | MODERATE |
| `FPP_PERFORMANCE` | 1 | Actual performance measurements of participants during frequency events. | MODERATE |
| `FPP_HIST_PERFORMANCE` | 1 | Historical performance data. | LOW |
| `FPP_RESIDUAL_PERFORMANCE` | 1 | Residual performance calculations. | LOW |
| `FPP_USAGE` | 1 | FCAS usage/activation data. | MODERATE |
| `FPP_RCR` | 1 | Residual cost recovery for FPP. | LOW |
| `FPP_CONTRIBUTION_FACTOR` | 1 | Contribution factors for FPP cost allocation. | LOW |
| `FPP_EST_PERF_COST_RATE` | 1 | Estimated performance cost rates. | LOW |
| `FPP_EST_RESIDUAL_COST_RATE` | 1 | Estimated residual cost rates. | LOW |
| `FPP_FORECAST_DEFAULT_CF` | 1 | Forecast default contribution factors. | LOW |
| `FPP_FORECAST_RESIDUAL_DCF` | 1 | Forecast residual default contribution factors. | LOW |
| `FPP_P5_FWD_EST_RESIDUALRATE` | 1 | P5MIN forward estimated residual rates. | LOW |
| `FPP_PD_FWD_EST_RESIDUALRATE` | 1 | Pre-dispatch forward estimated residual rates. | LOW |
| `FPP_CONSTRAINT_FREQ_MEASURE` | 1 | Constraint-level frequency measurements. | LOW |
| `FPP_REGION_FREQ_MEASURE` | 1 | Region-level frequency measurements. | LOW |
| `FPP_RESIDUAL_CF` | 1 | Residual contribution factors. | LOW |
| `FCAS_REGU_USAGE_FACTORS` | 1 | Regulation FCAS usage factors (causer pays). | MODERATE |
| `FCAS_REGU_USAGE_FACTORS_TRK` | 1 | Tracking for regulation usage factors. | LOW |

---

## 12. INTERMITTENT GENERATION PACKAGE

| File | Files | Description | Relevance |
|------|-------|-------------|-----------|
| `INTERMITTENT_GEN_SCADA` | 1 | SCADA availability data for every intermittent generating unit (wind/solar). | MODERATE |
| `INTERMITTENT_DS_PRED` | 1 | Unconstrained Intermittent Generation Forecasts (UIGF) for dispatch. | MODERATE |
| `INTERMITTENT_DS_RUN` | 1 | Run metadata for intermittent dispatch forecasts. | LOW |
| `INTERMITTENT_FORECAST_TRK` | 1 | Tracking for intermittent forecasts. | LOW |
| `INTERMITTENT_GEN_LIMIT` | 1 | Generation limits for intermittent units. | LOW |
| `INTERMITTENT_GEN_LIMIT_DAY` | 1 | Daily generation limits for intermittent units. | LOW |
| `INTERMITTENT_CLUSTER_AVAIL` | 1 | Cluster-level availability for intermittent generation. | LOW |
| `INTERMITTENT_CLUSTER_AVAIL_DAY` | 1 | Daily cluster-level availability. | LOW |

---

## 13. ROOFTOP SOLAR

| File | Files | Description | Relevance |
|------|-------|-------------|-----------|
| `ROOFTOP_PV_ACTUAL` | 1 | Estimated actual rooftop solar generation per region per half-hour. | MODERATE |
| `ROOFTOP_PV_FORECAST` | 1 | Regional forecasts of rooftop solar generation (8 days ahead). | MODERATE |

---

## 14. PASA (Projected Assessment of System Adequacy)

### MTPASA (Medium-Term, 2–3 year horizon)

| File | Files | Description | Relevance |
|------|-------|-------------|-----------|
| `MTPASA_CASERESULT` | 1 | Case-level results. | LOW |
| `MTPASA_REGIONRESULT` | 1 | Regional results. | LOW |
| `MTPASA_REGIONSUMMARY` | 1 | Regional summary. | LOW |
| `MTPASA_REGIONAVAILABILITY` | 1 | Regional availability. | LOW |
| `MTPASA_REGIONAVAIL_TRK` | 1 | Tracking for regional availability. | LOW |
| `MTPASA_REGIONITERATION` | 1 | Regional iteration results. | LOW |
| `MTPASA_CONSTRAINTRESULT` | 1 | Constraint results. | LOW |
| `MTPASA_CONSTRAINTSUMMARY` | 1 | Constraint summary. | LOW |
| `MTPASA_DUIDAVAILABILITY` | 1 | DUID-level availability declarations. | LOW |
| `MTPASA_INTERCONNECTORRESULT` | 1 | Interconnector results. | LOW |
| `MTPASA_LOLPRESULT` | 1 | Loss of Load Probability results. | LOW |
| `MTPASA_RESERVELIMIT` | 1 | Reserve limit definitions. | LOW |
| `MTPASA_RESERVELIMIT_REGION` | 1 | Regional reserve limits. | LOW |
| `MTPASA_RESERVELIMIT_SET` | 1 | Reserve limit set definitions. | LOW |

### PDPASA (Pre-Dispatch PASA, 30-minute resolution)

| File | Files | Description | Relevance |
|------|-------|-------------|-----------|
| `PDPASA_CASESOLUTION` | 1 | Case-level PASA solution. | LOW |
| `PDPASA_REGIONSOLUTION` | 1 | Regional PASA results. | MODERATE |
| `PDPASA_CONSTRAINTSOLUTION` | 1 | Constraint solutions. | LOW |
| `PDPASA_INTERCONNECTORSOLN` | 1 | Interconnector solutions. | LOW |

### STPASA (Short-Term PASA, 7-day horizon)

| File | Files | Description | Relevance |
|------|-------|-------------|-----------|
| `STPASA_CASESOLUTION` | 1 | Case-level STPASA solution. | LOW |
| `STPASA_REGIONSOLUTION` | 1 | Regional STPASA results. | MODERATE |
| `STPASA_CONSTRAINTSOLUTION` | 1 | STPASA constraint solutions. | LOW |
| `STPASA_INTERCONNECTORSOLN` | 1 | STPASA interconnector solutions. | LOW |

---

## 15. MNSP (Market Network Service Provider) DATA

| File | Files | Description | Relevance |
|------|-------|-------------|-----------|
| `MNSP_DAYOFFER` | 1 | MNSP day offers (bids for interconnector capacity). | LOW |
| `MNSP_BIDOFFERPERIOD` | 1 | MNSP period-level bid quantities. | LOW |
| `MNSP_INTERCONNECTOR` | 1 | MNSP interconnector definitions. | LOW |
| `MNSP_PARTICIPANT` | 1 | MNSP participant details. | LOW |

---

## 16. SETTLEMENT PACKAGE

| File | Files | Description | Relevance |
|------|-------|-------------|-----------|
| `SET_ANCILLARY_SUMMARY` | 1 | Ancillary service settlement summary. | MODERATE |
| `SET_ENERGY_REGION_SUMMARY` | 1 | Energy settlement summary by region. | MODERATE |
| `SET_FCAS_REGULATION_TRK` | 1 | FCAS regulation settlement tracking. | LOW |
| `SET_NMAS_RECOVERY_RBF` | 1 | Non-Market Ancillary Services recovery. | LOW |
| `SETFCASREGIONRECOVERY` | 1 | FCAS cost recovery by region. | MODERATE |
| `SETINTRAREGIONRESIDUES` | 1 | Intra-regional settlement residues. | LOW |
| `SETIRSURPLUS` | 1 | Inter-regional settlement surplus. | LOW |
| `SETLOCALAREAENERGY` | 1 | Local area energy settlement. | LOW |
| `SETLOCALAREATNI` | 1 | Local area TNI settlement. | LOW |
| `SETCFG_PARTICIPANT_MPF` | 1 | Participant market participation factor config. | LOW |
| `SETCFG_PARTICIPANT_MPFTRK` | 1 | Tracking for participant MPF. | LOW |
| `SETCFG_SAPS_SETT_PRICE` | 1 | Stand-Alone Power Systems settlement price config. | LOW |
| `SETCFG_WDR_REIMBURSE_RATE` | 1 | Wholesale Demand Response reimbursement rate. | LOW |
| `SETCFG_WDRRR_CALENDAR` | 1 | WDR reimbursement calendar. | LOW |

---

## 17. BILLING PACKAGE

| File | Files | Description | Relevance |
|------|-------|-------------|-----------|
| `BILLINGCALENDAR` | 1 | Billing calendar definitions. | LOW |
| `BILLINGDAYTRK` | 1 | Daily billing tracking. | LOW |
| `BILLINGRUNTRK` | 1 | Billing run tracking. | LOW |
| `BILLINGREGIONEXPORTS` | 1 | Regional export billing. | LOW |
| `BILLINGREGIONFIGURES` | 1 | Regional billing figures. | LOW |
| `BILLINGREGIONIMPORTS` | 1 | Regional import billing. | LOW |
| `BILLING_CO2E_PUBLICATION` | 1 | CO2-equivalent emissions publication. | LOW |
| `BILLING_CO2E_PUBLICATION_TRK` | 1 | Tracking for CO2e publication. | LOW |
| `BILLING_DIRECTION_RECON_OTHER` | 1 | Directional reconciliation billing. | LOW |
| `BILLING_NMAS_TST_RECVRY_RBF` | 1 | NMAS test recovery billing. | LOW |
| `BILLING_NMAS_TST_RECVRY_TRK` | 1 | Tracking for NMAS test recovery. | LOW |

---

## 18. ANCILLARY SERVICES PACKAGE

| File | Files | Description | Relevance |
|------|-------|-------------|-----------|
| `ANCILLARY_RECOVERY_SPLIT` | 1 | How ancillary service costs are split for recovery. | MODERATE |

---

## 19. FORCE MAJEURE / MARKET SUSPENSION

| File | Files | Description | Relevance |
|------|-------|-------------|-----------|
| `MARKET_SUSPEND_REGIME_SUM` | 1 | Market suspension regime summary. | LOW |
| `MARKET_SUSPEND_REGION_SUM` | 1 | Market suspension regional summary. | LOW |
| `MARKET_SUSPEND_SCHEDULE` | 1 | Market suspension pricing schedule. | LOW |
| `MARKET_SUSPEND_SCHEDULE_TRK` | 1 | Tracking for suspension schedules. | LOW |
| `MARKETSUSPENSION` | 1 | Market suspension events. | LOW |
| `MARKETSUSREGION` | 1 | Market suspension by region. | LOW |
| `APEVENT` | 1 | Administered Pricing events. | LOW |
| `APEVENTREGION` | 1 | Administered Pricing events by region. | LOW |

---

## 20. NETWORK PACKAGE

| File | Files | Description | Relevance |
|------|-------|-------------|-----------|
| `NETWORK_EQUIPMENTDETAIL` | 1 | Physical network equipment details. | LOW |
| `NETWORK_OUTAGECONSTRAINTSET` | 1 | Constraint sets triggered by network outages. | MODERATE |
| `NETWORK_OUTAGEDETAIL` | 1 | Network outage details. | LOW |
| `NETWORK_OUTAGESTATUSCODE` | 1 | Outage status code definitions. | LOW |
| `NETWORK_RATING` | 1 | Network element ratings. | LOW |
| `NETWORK_STATICRATING` | 1 | Static network ratings. | LOW |
| `NETWORK_SUBSTATIONDETAIL` | 1 | Substation details (geographic information). | MODERATE |

---

## 21. IRAUCTION (Inter-Regional Residue Auction)

| File | Files | Description | Relevance |
|------|-------|-------------|-----------|
| `AUCTION` | 1 | Inter-regional residue auction data. | LOW |
| `NEGATIVE_RESIDUE` | 1 | Negative residue management. | LOW |
| `RESIDUE_CON_FUNDS` | 1 | Residue contract funds. | LOW |
| `RESIDUE_CONTRACTS` | 1 | Residue contract details. | LOW |
| `SRA_FINANCIAL_RUNTRK` | 1 | Settlement Residue Auction financial tracking. | LOW |
| `SRA_PRUDENTIAL_RUN` | 1 | SRA prudential run. | LOW |

---

## 22. MCC (Marginal Constraint Cost) DISPATCH

| File | Files | Description | Relevance |
|------|-------|-------------|-----------|
| `MCC_CASESOLUTION` | 1 | Marginal Constraint Cost re-run case solution. | LOW |
| `MCC_CONSTRAINTSOLUTION` | 1 | Marginal Constraint Cost constraint solution. | LOW |

---

## 23. METER DATA

| File | Files | Description | Relevance |
|------|-------|-------------|-----------|
| `METERDATA_INTERCONNECTOR` | 1 | Metered interconnector flows. | MODERATE |

---

## 24. MISCELLANEOUS / ADMINISTRATIVE

| File | Files | Description | Relevance |
|------|-------|-------------|-----------|
| `ADG_DETAIL` | 1 | Aggregate Dispatch Group detail. | LOW |
| `AGGREGATE_DISPATCH_GROUP` | 1 | Aggregate Dispatch Group definitions. | LOW |
| `AVERAGEPRICE30` | 1 | 30-minute average prices (legacy, pre-5MS). | LOW |
| `DAYTRACK` | 1 | Day-level tracking/metadata. | LOW |
| `GST_BAS_CLASS` | 1 | GST Business Activity Statement class. | LOW |
| `GST_RATE` | 1 | GST rate definitions. | LOW |
| `GST_TRANSACTION_CLASS` | 1 | GST transaction class. | LOW |
| `GST_TRANSACTION_TYPE` | 1 | GST transaction type. | LOW |
| `INSTRUCTIONSUBTYPE` | 1 | Dispatch instruction subtypes. | LOW |
| `INSTRUCTIONTYPE` | 1 | Dispatch instruction types. | LOW |
| `IRFMAMOUNT` | 1 | Inter-Regional Financial Management amounts. | LOW |
| `IRFMEVENTS` | 1 | IRFM events. | LOW |
| `MARKETNOTICETYPE` | 1 | Market notice type definitions. | LOW |
| `PMS_GROUP` | 1 | Power Management System group. | LOW |
| `PMS_GROUPSERVICE` | 1 | PMS group service. | LOW |
| `PRUDENTIALRUNTRK` | 1 | Prudential run tracking. | LOW |
| `SECDEPOSIT_INTEREST_RATE` | 1 | Security deposit interest rates. | LOW |
| `VOLTAGE_INSTRUCTION` | 1 | Voltage/MVAr dispatch instructions. | LOW |
| `VOLTAGE_INSTRUCTION_TRK` | 1 | Tracking for voltage instructions. | LOW |

---

## Summary: Files You Need to Download

### Must-Have (CRITICAL)

These files provide the core data for the project:

| Table | Purpose |
|-------|---------|
| **BIDDAYOFFER** or **BIDDAYOFFER_D** | Price bands (10 bands) per DUID per bid type |
| **BIDOFFERPERIOD** or **BIDPEROFFER_D** | Quantity bands (10 bands) per DUID per 5-min period per bid type |
| **DISPATCHPRICE** | 5-minute clearing prices for energy + all FCAS services, per region |
| **TRADINGPRICE** | 5-minute settlement prices for energy + all FCAS, per region |
| **DISPATCHLOAD** | What was actually dispatched per DUID per interval |
| **PARTICIPANT** | Participant master list |
| **DISPATCHABLEUNIT** | DUID master list (unit type: GENERATOR, LOAD, BIDIRECTIONAL) |
| **DUDETAIL** | Unit registration detail (capacity, type, storage capacity for batteries) |
| **DUDETAILSUMMARY** | DUID → Region → Station → Participant mapping |

### Strongly Recommended (HIGH)

| Table | Purpose |
|-------|---------|
| **DISPATCHREGIONSUM** | Regional demand/supply/FCAS per 5-min interval |
| **DEMANDOPERATIONALACTUAL** | Actual demand per region |
| **DEMANDOPERATIONALFORECAST** | Forecast demand per region |
| **DISPATCHINTERCONNECTORRES** | Interconnector flows (for congestion analysis) |
| **DISPATCHCONSTRAINT** | Binding constraints (for congestion analysis) |
| **DISPATCH_UNIT_SCADA** | Actual MW output per DUID |
| **DISPATCH_FCAS_REQ** | FCAS requirement attribution |
| **DISPATCHOFFERTRK** | Links dispatch to specific bids |
| **PREDISPATCHPRICE** | Forecast prices |
| **PREDISPATCHREGIONSUM** | Forecast demand/supply |
| **P5MIN_REGIONSOLUTION** | 5-min pre-dispatch regional results |
| **GENCONDATA** | Constraint definitions |
| **SPDCONNECTIONPOINTCONSTRAINT** | Which DUIDs appear in which constraints |
| **REGION** | Region definitions |
| **INTERCONNECTOR** | Interconnector definitions |
| **STATION** / **STATIONOWNER** | Station and ownership info |
| **BIDTYPES** / **BIDDUIDDETAILS** | Bid type reference and unit FCAS registration |

### Note on BIDDAYOFFER vs BIDDAYOFFER_D

- **BIDDAYOFFER** + **BIDOFFERPERIOD**: Contains ALL bids including every rebid throughout the day. Much larger (BIDOFFERPERIOD = 39 files). Useful for studying rebidding behavior and autobidder strategies.
- **BIDDAYOFFER_D** + **BIDPEROFFER_D**: Contains only the dispatch-effective bid (the one actually used). Smaller (1 file each). Sufficient if you only need the final bid used in dispatch.

For autobidder research, you likely want **both** — the full rebid history reveals bidding strategies, while the dispatch-effective versions are simpler for matching to dispatch outcomes.
