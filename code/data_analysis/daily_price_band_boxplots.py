"""
Price Band Variation Analysis: Autobidder vs Non-Autobidder Batteries
=====================================================================

Purpose:
    Compares price band settings between autobidder and non-autobidder batteries
    in FCAS markets to test whether autobidders set more varied price bands.
    Focuses on initial DAILY bids (not rebids) since this represents the baseline
    bidding strategy before intraday adjustments.

Data:
    - BIDDAYOFFER: Contains price bands (PRICEBAND1-10) for each bid submission.
      Filters to ENTRYTYPE='DAILY' to get only initial bids (not rebids).
    - DUID participant map: Identifies which units are batteries (BIDIRECTIONAL)
      and which use Tesla Autobidder software.

Analysis:
    1. Loads all DAILY bids for batteries across 10 FCAS services (RAISE/LOWER
       for 1SEC, 5MIN, 6SEC, 60SEC, REG).
    2. Splits into two groups: Autobidder batteries (4 units) vs Non-autobidder
       batteries (29 units).
    3. Creates box plots comparing price band distributions (bands 1-10) between
       groups. Uses log scale for bands 5-10 due to large value ranges.
    4. Computes per-unit variation metrics: std dev and number of distinct values
       each unit uses for each price band across all their DAILY bids.
    5. Generates summary statistics (mean, std, min, max, quartiles) for each
       price band by group.
    6. Shows example raw price bands for specific units (HPR1 autobidder vs BALB1
       non-autobidder) to illustrate actual bidding patterns.

Output:
    - figures/daily_price_bands/daily_price_band_boxplots.png
        Side-by-side box plots of all 10 price bands, autobidder vs non-autobidder
    - figures/daily_price_bands/daily_price_band_variation_by_unit.png
        Bar charts showing average within-unit variation (std dev and distinct values)
    - output/daily_price_band_stats.csv
        Detailed statistics table for each price band by group

Hypothesis:
    Autobidder batteries may set more varied initial price bands since they rely
    more heavily on quantity rebids (shifting MW between bands) rather than price
    rebids.

Key Finding:
    Autobidders show HIGHER within-unit price band variation (std=570) compared
    to non-autobidders (std=289), but use FEWER distinct values overall. This is
    because autobidders (only 4 units) vary their prices more across days, while
    non-autobidders (29 units) collectively use more distinct values but each
    individual unit is more consistent.
"""

import duckdb
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import sys
from pathlib import Path

# Add parent directory to path for config import
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import DATA_DIR, OUTPUT_DIR, FIGURES_DIR, DUID_MAP_PATH, BIDDAYOFFER_PATH

# Create subdirectory for daily price band figures
DAILY_PB_FIGURES_DIR = FIGURES_DIR / "daily_price_bands"
DAILY_PB_FIGURES_DIR.mkdir(exist_ok=True)

con = duckdb.connect()
con.execute("SET memory_limit='8GB'")


def aemo_csv_query(filepath):
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


def load_daily_bids():
    """Load only DAILY bids for batteries in FCAS services."""
    print("Loading data...")

    # Load DUID map
    duid_map = pd.read_csv(DUID_MAP_PATH)
    duid_map['IS_BATTERY'] = duid_map['DISPATCHTYPE'] == 'BIDIRECTIONAL'
    con.register("duid_map", duid_map)

    # FCAS services
    fcas_services = [
        'RAISE6SEC', 'RAISE60SEC', 'RAISE5MIN', 'RAISE1SEC', 'RAISEREG',
        'LOWER6SEC', 'LOWER60SEC', 'LOWER5MIN', 'LOWER1SEC', 'LOWERREG'
    ]
    fcas_filter = "'" + "','".join(fcas_services) + "'"

    # Query for DAILY bids only, for batteries, in FCAS services
    query = f"""
    WITH bdo AS (
        SELECT
            DUID, BIDTYPE, SETTLEMENTDATE, OFFERDATE, ENTRYTYPE,
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
    )
    SELECT
        bdo.*,
        COALESCE(dm.TESLA_AUTOBIDDER, FALSE) as IS_AUTOBIDDER,
        dm.PARTICIPANT_NAME
    FROM bdo
    JOIN duid_map dm ON bdo.DUID = dm.DUID
    WHERE dm.IS_BATTERY = TRUE
      AND bdo.BIDTYPE IN ({fcas_filter})
      AND bdo.ENTRYTYPE = 'DAILY'
    """

    df = con.execute(query).fetchdf()
    print(f"Loaded {len(df):,} DAILY bid records for batteries")
    print(f"  Autobidder: {df['IS_AUTOBIDDER'].sum():,}")
    print(f"  Non-autobidder: {(~df['IS_AUTOBIDDER']).sum():,}")
    print(f"  Unique DUIDs: {df['DUID'].nunique()}")
    print(f"  Unique market days: {df['SETTLEMENTDATE'].nunique()}")

    return df


def create_boxplot_comparison(df):
    """Create side-by-side box plots for each price band."""
    print("\nCreating box plot figure...")

    # Separate autobidder and non-autobidder data
    autobidder = df[df['IS_AUTOBIDDER'] == True]
    non_autobidder = df[df['IS_AUTOBIDDER'] == False]

    print(f"Autobidder records: {len(autobidder):,} from {autobidder['DUID'].nunique()} units")
    print(f"Non-autobidder records: {len(non_autobidder):,} from {non_autobidder['DUID'].nunique()} units")

    # Price band columns
    price_bands = [f'PRICEBAND{i}' for i in range(1, 11)]

    # Create figure with subplots - 2 rows x 5 columns
    fig, axes = plt.subplots(2, 5, figsize=(20, 10))
    fig.suptitle('Distribution of DAILY (Initial) Price Bands: Autobidder vs Non-Autobidder Batteries\n(FCAS Services, October 2025)',
                 fontsize=14, fontweight='bold')

    axes = axes.flatten()

    # Collect stats for table
    stats_for_title = []

    for i, band in enumerate(price_bands):
        ax = axes[i]

        # Get data for this price band
        auto_data = autobidder[band].dropna()
        non_auto_data = non_autobidder[band].dropna()

        # Create box plot
        bp = ax.boxplot([auto_data, non_auto_data],
                        labels=['Autobidder', 'Non-Auto'],
                        patch_artist=True,
                        showfliers=True,
                        flierprops={'marker': 'o', 'markersize': 3, 'alpha': 0.5})

        # Color the boxes
        bp['boxes'][0].set_facecolor('#3498db')  # Blue for autobidder
        bp['boxes'][1].set_facecolor('#e74c3c')  # Red for non-autobidder

        # Set title with stats
        auto_std = auto_data.std()
        non_auto_std = non_auto_data.std()
        title = f'Band {i+1}\nAuto σ={auto_std:.1f}, Non-Auto σ={non_auto_std:.1f}'
        ax.set_title(title, fontsize=10)
        ax.set_ylabel('Price ($/MWh)')

        stats_for_title.append({
            'band': i+1,
            'auto_mean': auto_data.mean(),
            'auto_std': auto_std,
            'auto_n_distinct': auto_data.nunique(),
            'non_auto_mean': non_auto_data.mean(),
            'non_auto_std': non_auto_std,
            'non_auto_n_distinct': non_auto_data.nunique()
        })

        # Use log scale for higher bands where values span orders of magnitude
        if i >= 4:  # Bands 5-10 typically have much larger values
            ax.set_yscale('log')

    plt.tight_layout()
    plt.subplots_adjust(top=0.88)

    # Save figure
    output_path = DAILY_PB_FIGURES_DIR / "daily_price_band_boxplots.png"
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"\nSaved figure: {output_path}")

    # Print stats table
    print("\nPrice Band Statistics (DAILY bids):")
    print(f"{'Band':<6} {'Auto Mean':>12} {'Auto Std':>12} {'Auto Distinct':>14} {'Non-Auto Mean':>14} {'Non-Auto Std':>13} {'Non-Auto Distinct':>18}")
    print("-" * 95)
    for s in stats_for_title:
        print(f"{s['band']:<6} {s['auto_mean']:>12.2f} {s['auto_std']:>12.2f} {s['auto_n_distinct']:>14} {s['non_auto_mean']:>14.2f} {s['non_auto_std']:>13.2f} {s['non_auto_n_distinct']:>18}")

    return fig


def create_detailed_stats_table(df):
    """Create a detailed statistics table for price bands."""
    print("\nComputing detailed statistics...")

    price_bands = [f'PRICEBAND{i}' for i in range(1, 11)]

    stats_list = []
    for band in price_bands:
        for is_auto, label in [(True, 'Autobidder'), (False, 'Non-Autobidder')]:
            data = df[df['IS_AUTOBIDDER'] == is_auto][band].dropna()
            stats_list.append({
                'Price Band': band.replace('PRICEBAND', 'Band '),
                'Category': label,
                'N': len(data),
                'Mean': data.mean(),
                'Std Dev': data.std(),
                'Min': data.min(),
                'Q25': data.quantile(0.25),
                'Median': data.median(),
                'Q75': data.quantile(0.75),
                'Max': data.max(),
                'N Distinct': data.nunique()
            })

    stats_df = pd.DataFrame(stats_list)

    print("\nDetailed Statistics for DAILY Price Bands:")
    print(stats_df.to_string(index=False))

    # Save to CSV
    stats_df.to_csv(OUTPUT_DIR / "daily_price_band_stats.csv", index=False)
    print(f"\nSaved: {OUTPUT_DIR / 'daily_price_band_stats.csv'}")

    return stats_df


def create_per_unit_variation_plot(df):
    """Show how much each unit varies its price bands across days."""
    print("\nAnalyzing per-unit variation...")

    # For each DUID, calculate the std dev of each price band across all their DAILY bids
    price_bands = [f'PRICEBAND{i}' for i in range(1, 11)]

    variation_data = []
    for duid in df['DUID'].unique():
        duid_data = df[df['DUID'] == duid]
        is_auto = duid_data['IS_AUTOBIDDER'].iloc[0]

        for band in price_bands:
            std = duid_data[band].std()
            cv = duid_data[band].std() / duid_data[band].mean() if duid_data[band].mean() != 0 else 0
            variation_data.append({
                'DUID': duid,
                'IS_AUTOBIDDER': is_auto,
                'Price Band': int(band.replace('PRICEBAND', '')),
                'Std Dev': std,
                'CV': cv,
                'N Distinct': duid_data[band].nunique()
            })

    var_df = pd.DataFrame(variation_data)

    # Create figure showing coefficient of variation by price band
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # Plot 1: Average Std Dev by price band
    ax1 = axes[0]
    auto_std = var_df[var_df['IS_AUTOBIDDER']].groupby('Price Band')['Std Dev'].mean()
    non_auto_std = var_df[~var_df['IS_AUTOBIDDER']].groupby('Price Band')['Std Dev'].mean()

    x = np.arange(1, 11)
    width = 0.35
    ax1.bar(x - width/2, auto_std, width, label='Autobidder (4 units)', color='#3498db')
    ax1.bar(x + width/2, non_auto_std, width, label='Non-Autobidder (29 units)', color='#e74c3c')
    ax1.set_xlabel('Price Band')
    ax1.set_ylabel('Average Std Dev of Price ($/MWh)')
    ax1.set_title('Average Price Band Variation Within Units\n(Std Dev across DAILY bids)', fontweight='bold')
    ax1.set_xticks(x)
    ax1.legend()
    ax1.set_yscale('log')

    # Plot 2: Number of distinct values by price band
    ax2 = axes[1]
    auto_distinct = var_df[var_df['IS_AUTOBIDDER']].groupby('Price Band')['N Distinct'].mean()
    non_auto_distinct = var_df[~var_df['IS_AUTOBIDDER']].groupby('Price Band')['N Distinct'].mean()

    ax2.bar(x - width/2, auto_distinct, width, label='Autobidder (4 units)', color='#3498db')
    ax2.bar(x + width/2, non_auto_distinct, width, label='Non-Autobidder (29 units)', color='#e74c3c')
    ax2.set_xlabel('Price Band')
    ax2.set_ylabel('Average N Distinct Values')
    ax2.set_title('Average Number of Distinct Price Band Values\n(Across DAILY bids per unit)', fontweight='bold')
    ax2.set_xticks(x)
    ax2.legend()

    plt.tight_layout()

    output_path = DAILY_PB_FIGURES_DIR / "daily_price_band_variation_by_unit.png"
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"Saved: {output_path}")

    # Summary table
    summary = var_df.groupby('IS_AUTOBIDDER').agg({
        'Std Dev': 'mean',
        'N Distinct': 'mean'
    }).reset_index()
    summary['IS_AUTOBIDDER'] = summary['IS_AUTOBIDDER'].map({True: 'Autobidder', False: 'Non-Autobidder'})
    print("\nSummary of within-unit price band variation:")
    print(summary.to_string(index=False))

    return var_df


def show_example_price_bands():
    """Show actual price band values for specific units to illustrate the difference."""
    print("\n" + "=" * 80)
    print("EXAMPLE PRICE BANDS FOR SPECIFIC UNITS")
    print("=" * 80)

    # Load full data (not just DAILY) to show examples
    duid_map = pd.read_csv(DUID_MAP_PATH)
    duid_map['IS_BATTERY'] = duid_map['DISPATCHTYPE'] == 'BIDIRECTIONAL'
    con.register("duid_map", duid_map)

    # Create view for examples
    con.execute(f"""
        CREATE OR REPLACE VIEW biddayoffer_example AS
        SELECT
            bdo.DUID, bdo.BIDTYPE, bdo.SETTLEMENTDATE, bdo.OFFERDATE, bdo.ENTRYTYPE,
            TRY_CAST(bdo.PRICEBAND1 AS DOUBLE) as PRICEBAND1,
            TRY_CAST(bdo.PRICEBAND2 AS DOUBLE) as PRICEBAND2,
            TRY_CAST(bdo.PRICEBAND3 AS DOUBLE) as PRICEBAND3,
            TRY_CAST(bdo.PRICEBAND4 AS DOUBLE) as PRICEBAND4,
            TRY_CAST(bdo.PRICEBAND5 AS DOUBLE) as PRICEBAND5,
            TRY_CAST(bdo.PRICEBAND6 AS DOUBLE) as PRICEBAND6,
            TRY_CAST(bdo.PRICEBAND7 AS DOUBLE) as PRICEBAND7,
            TRY_CAST(bdo.PRICEBAND8 AS DOUBLE) as PRICEBAND8,
            TRY_CAST(bdo.PRICEBAND9 AS DOUBLE) as PRICEBAND9,
            TRY_CAST(bdo.PRICEBAND10 AS DOUBLE) as PRICEBAND10
        FROM ({aemo_csv_query(BIDDAYOFFER_PATH)}) bdo
    """)

    # Show HPR1 (autobidder) vs BALB1 (non-autobidder) for RAISE6SEC
    print("\n--- HPR1 (Hornsdale, Autobidder) - RAISE6SEC DAILY price bands ---")
    hpr1 = con.execute("""
        SELECT SETTLEMENTDATE, OFFERDATE, ENTRYTYPE,
               PRICEBAND1, PRICEBAND2, PRICEBAND3, PRICEBAND4, PRICEBAND5,
               PRICEBAND6, PRICEBAND7, PRICEBAND8, PRICEBAND9, PRICEBAND10
        FROM biddayoffer_example
        WHERE DUID = 'HPR1' AND BIDTYPE = 'RAISE6SEC' AND ENTRYTYPE = 'DAILY'
        ORDER BY OFFERDATE
        LIMIT 10
    """).fetchdf()
    print(hpr1.to_string())

    print("\n--- BALB1 (Ballarat Battery, Non-Autobidder) - RAISE6SEC DAILY price bands ---")
    balb1 = con.execute("""
        SELECT SETTLEMENTDATE, OFFERDATE, ENTRYTYPE,
               PRICEBAND1, PRICEBAND2, PRICEBAND3, PRICEBAND4, PRICEBAND5,
               PRICEBAND6, PRICEBAND7, PRICEBAND8, PRICEBAND9, PRICEBAND10
        FROM biddayoffer_example
        WHERE DUID = 'BALB1' AND BIDTYPE = 'RAISE6SEC' AND ENTRYTYPE = 'DAILY'
        ORDER BY OFFERDATE
        LIMIT 10
    """).fetchdf()
    print(balb1.to_string())

    print("\nNote: HPR1 uses identical price bands across all days, while BALB1 shows some variation.")


def main():
    print("=" * 80)
    print("DAILY Price Band Distribution Analysis")
    print("=" * 80)
    print("Testing: Do autobidder batteries set more varied INITIAL price bands?")
    print()

    # Load data
    df = load_daily_bids()

    # Create main comparison box plots
    create_boxplot_comparison(df)

    # Create detailed stats
    stats_df = create_detailed_stats_table(df)

    # Create per-unit variation analysis
    var_df = create_per_unit_variation_plot(df)

    # Show example price bands for specific units
    show_example_price_bands()

    print("\n" + "=" * 80)
    print("CONCLUSION")
    print("=" * 80)

    # Compare overall variation
    auto_data = df[df['IS_AUTOBIDDER']]
    non_auto_data = df[~df['IS_AUTOBIDDER']]

    print("\nOverall price band variation in DAILY bids:")
    print(f"  Autobidder batteries ({auto_data['DUID'].nunique()} units):")
    for i in range(1, 11):
        col = f'PRICEBAND{i}'
        print(f"    Band {i}: std={auto_data[col].std():.2f}, distinct={auto_data[col].nunique()}")

    print(f"\n  Non-autobidder batteries ({non_auto_data['DUID'].nunique()} units):")
    for i in range(1, 11):
        col = f'PRICEBAND{i}'
        print(f"    Band {i}: std={non_auto_data[col].std():.2f}, distinct={non_auto_data[col].nunique()}")

    # Print interpretation
    auto_avg_std = var_df[var_df['IS_AUTOBIDDER']]['Std Dev'].mean()
    non_auto_avg_std = var_df[~var_df['IS_AUTOBIDDER']]['Std Dev'].mean()

    print("\n" + "=" * 80)
    print("INTERPRETATION")
    print("=" * 80)
    print(f"\nAutobidder within-unit avg std: {auto_avg_std:.2f}")
    print(f"Non-autobidder within-unit avg std: {non_auto_avg_std:.2f}")

    if auto_avg_std > non_auto_avg_std * 1.1:
        print("\n>>> HYPOTHESIS SUPPORTED: Autobidders show MORE price band variation")
    elif auto_avg_std < non_auto_avg_std * 0.9:
        print("\n>>> HYPOTHESIS REJECTED: Autobidders show LESS price band variation")
    else:
        print("\n>>> INCONCLUSIVE: Similar price band variation between groups")


if __name__ == "__main__":
    main()
