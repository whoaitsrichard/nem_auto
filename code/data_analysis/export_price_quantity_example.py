"""
Export Price and Quantity Bands Example
=======================================

Purpose:
    Creates a merged dataset combining price bands (from BIDDAYOFFER) and
    quantity bands (from BIDOFFERPERIOD) for a specific battery and FCAS service.
    Useful for examining how a unit's bid curve evolves through rebids.

Data:
    - BIDDAYOFFER: Contains price bands (PRICEBAND1-10) set at the day level
    - BIDOFFERPERIOD: Contains quantity bands (BANDAVAIL1-10) for each 5-minute period
    - Joined on DUID, BIDTYPE, SETTLEMENTDATE, OFFERDATE

Output:
    - output/price_and_quantity_ex.csv
        Merged dataset with both price and quantity bands for each bid

Configuration:
    - SELECTED_DUID: Which battery to export (default: HBESS1)
    - SELECTED_BIDTYPE: Which FCAS service (default: RAISE1SEC)
    - MAX_ROWS: Limit output size (default: None for all rows)
"""

import duckdb
import pandas as pd
import sys
from pathlib import Path

# Add parent directory to path for config import
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import BIDDAYOFFER_PATH, BIDOFFERPERIOD_PATH, DUID_MAP_PATH, OUTPUT_DIR

# =============================================================================
# CONFIGURATION
# =============================================================================
SELECTED_DUID = 'HBESS1'  # Hazelwood Battery Energy Storage System
SELECTED_BIDTYPE = 'RAISE1SEC'  # 1-second raise FCAS
MAX_ROWS = None  # Set to integer to limit output, None for all rows

# =============================================================================
# SETUP
# =============================================================================
con = duckdb.connect()
con.execute("SET memory_limit='8GB'")


def aemo_csv_query(filepath):
    """Query template for AEMO CSV format (skip metadata row, filter to data rows)."""
    return f"""
    SELECT *
    FROM read_csv(
        '{filepath}',
        header=true,
        skip=1,
        delim=',',
        quote='"',
        strict_mode=false,
        ignore_errors=true
    )
    WHERE "I" = 'D'
    """


def export_price_quantity_data():
    """Export merged price and quantity band data for selected DUID/BIDTYPE."""
    print("=" * 80)
    print("EXPORT PRICE AND QUANTITY BANDS")
    print("=" * 80)
    print(f"DUID: {SELECTED_DUID}")
    print(f"BIDTYPE: {SELECTED_BIDTYPE}")
    print()

    # Load DUID map for DIRECTION info
    duid_map = pd.read_csv(DUID_MAP_PATH)
    con.register("duid_map", duid_map)

    # Build the merged query
    limit_clause = f"LIMIT {MAX_ROWS}" if MAX_ROWS else ""

    query = f"""
    WITH price_bands AS (
        SELECT
            DUID,
            BIDTYPE,
            SETTLEMENTDATE,
            OFFERDATE,
            TRY_CAST(PRICEBAND1 AS DOUBLE) as PRICEBAND1,
            TRY_CAST(PRICEBAND2 AS DOUBLE) as PRICEBAND2,
            TRY_CAST(PRICEBAND3 AS DOUBLE) as PRICEBAND3,
            TRY_CAST(PRICEBAND4 AS DOUBLE) as PRICEBAND4,
            TRY_CAST(PRICEBAND5 AS DOUBLE) as PRICEBAND5,
            TRY_CAST(PRICEBAND6 AS DOUBLE) as PRICEBAND6,
            TRY_CAST(PRICEBAND7 AS DOUBLE) as PRICEBAND7,
            TRY_CAST(PRICEBAND8 AS DOUBLE) as PRICEBAND8,
            TRY_CAST(PRICEBAND9 AS DOUBLE) as PRICEBAND9,
            TRY_CAST(PRICEBAND10 AS DOUBLE) as PRICEBAND10
        FROM ({aemo_csv_query(BIDDAYOFFER_PATH)})
        WHERE DUID = '{SELECTED_DUID}'
          AND BIDTYPE = '{SELECTED_BIDTYPE}'
    ),
    quantity_bands AS (
        SELECT
            DUID,
            BIDTYPE,
            TRADINGDATE AS SETTLEMENTDATE,
            PERIODID,
            OFFERDATETIME AS OFFERDATE,
            TRY_CAST(BANDAVAIL1 AS DOUBLE) as BANDAVAIL1,
            TRY_CAST(BANDAVAIL2 AS DOUBLE) as BANDAVAIL2,
            TRY_CAST(BANDAVAIL3 AS DOUBLE) as BANDAVAIL3,
            TRY_CAST(BANDAVAIL4 AS DOUBLE) as BANDAVAIL4,
            TRY_CAST(BANDAVAIL5 AS DOUBLE) as BANDAVAIL5,
            TRY_CAST(BANDAVAIL6 AS DOUBLE) as BANDAVAIL6,
            TRY_CAST(BANDAVAIL7 AS DOUBLE) as BANDAVAIL7,
            TRY_CAST(BANDAVAIL8 AS DOUBLE) as BANDAVAIL8,
            TRY_CAST(BANDAVAIL9 AS DOUBLE) as BANDAVAIL9,
            TRY_CAST(BANDAVAIL10 AS DOUBLE) as BANDAVAIL10
        FROM ({aemo_csv_query(BIDOFFERPERIOD_PATH)})
        WHERE DUID = '{SELECTED_DUID}'
          AND BIDTYPE = '{SELECTED_BIDTYPE}'
    )
    SELECT
        q.DUID,
        q.BIDTYPE,
        q.SETTLEMENTDATE,
        q.PERIODID,
        q.OFFERDATE,
        dm.DISPATCHTYPE as DIRECTION,
        q.BANDAVAIL1, q.BANDAVAIL2, q.BANDAVAIL3, q.BANDAVAIL4, q.BANDAVAIL5,
        q.BANDAVAIL6, q.BANDAVAIL7, q.BANDAVAIL8, q.BANDAVAIL9, q.BANDAVAIL10,
        p.PRICEBAND1, p.PRICEBAND2, p.PRICEBAND3, p.PRICEBAND4, p.PRICEBAND5,
        p.PRICEBAND6, p.PRICEBAND7, p.PRICEBAND8, p.PRICEBAND9, p.PRICEBAND10
    FROM quantity_bands q
    INNER JOIN price_bands p
        ON q.DUID = p.DUID
        AND q.BIDTYPE = p.BIDTYPE
        AND q.SETTLEMENTDATE = p.SETTLEMENTDATE
        AND q.OFFERDATE = p.OFFERDATE
    LEFT JOIN duid_map dm ON q.DUID = dm.DUID
    ORDER BY q.DUID, q.SETTLEMENTDATE, q.PERIODID, q.OFFERDATE
    {limit_clause}
    """

    print("Executing query...")
    df = con.execute(query).fetchdf()
    print(f"Retrieved {len(df):,} rows")

    # Show summary
    print(f"\nDate range: {df['SETTLEMENTDATE'].min()} to {df['SETTLEMENTDATE'].max()}")
    print(f"Unique periods: {df['PERIODID'].nunique()}")
    print(f"Unique offer times: {df['OFFERDATE'].nunique()}")

    # Save to CSV
    output_path = OUTPUT_DIR / "price_and_quantity_ex.csv"
    df.to_csv(output_path, index=True)
    print(f"\nSaved: {output_path}")
    print(f"File size: {output_path.stat().st_size / 1024:.1f} KB")

    # Show sample
    print("\nSample rows:")
    print(df.head(10).to_string())

    return df


def main():
    export_price_quantity_data()
    print("\n" + "=" * 80)
    print("EXPORT COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
