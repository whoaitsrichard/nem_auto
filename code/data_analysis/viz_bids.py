'''  Purpose: Visualizes how battery bidders change their FCAS bid curves over time through rebids.                                                              
                                                                                                                                                              
  What it does:                                                                                                                                               
  1. Loads bid data from BIDDAYOFFER (prices) and BIDOFFERPERIOD (quantities) for two selected batteries:                                                     
    - HPR1 (Hornsdale Power Reserve) - an autobidder battery                                                                                                  
    - HVWWBA1 (Hazelwood BESS) - a non-autobidder battery                                                                                                     
  2. Filters to "true rebids" - only keeps bids where quantity bands actually changed from the previous bid (not just resubmissions with identical values)    
  3. Generates bid curve plots for each 5-minute dispatch period showing:                                                                                     
    - X-axis: Cumulative quantity (MW)                                                                                                                        
    - Y-axis: Price ($/MWh)                                                                                                                                   
    - Each rebid within a period is a different colored line (using viridis colormap)                                                                         
    - Shows how the bid curve shifts throughout the period                                                                                                    
  4. Creates two versions of plots:                                                                                                                           
    - Full (all 10 price bands)                                                                                                                               
    - Condensed (bands 1-7 only, for clearer visualization)                                                                                                   
                                                                                                                                                              
  Output: Saves PNG figures to figures/bid_curves/{DUID}/ and figures/bid_curves/{DUID}_condensed/                                                            
                                                                                                                                                              
  Selected FCAS market: RAISEREG (raise regulation service)  
  '''
import pandas as pd
import duckdb
import matplotlib.pyplot as plt
import numpy as np
import os
import sys
from pathlib import Path
from matplotlib.cm import ScalarMappable
from matplotlib.colors import Normalize

# Add parent directory to path for config import
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import BIDDAYOFFER_PATH, BIDOFFERPERIOD_PATH, DUID_MAP_PATH, FIGURES_DIR

# =============================================================================
# CONFIGURATION
# =============================================================================

# File paths (from config)
biddayofferperiod = str(BIDDAYOFFER_PATH)
bidofferperiod = str(BIDOFFERPERIOD_PATH)

# Selected batteries for analysis
selected_autobidder = 'HPR1'  # Hornsdale Power Reserve
selected_non_autobidder = 'HVWWBA1'  # Hazelwood BESS
selected_duids = [selected_autobidder, selected_non_autobidder]

# Selected FCAS type
selected_fcas = 'RAISEREG'

print(f"Selected autobidder: {selected_autobidder}")
print(f"Selected non-autobidder: {selected_non_autobidder}")
print(f"Selected FCAS: {selected_fcas}")

# =============================================================================
# USE DUCKDB FOR EFFICIENT MERGE AND FILTERING
# =============================================================================

con = duckdb.connect()

# Create a single efficient query that:
# 1. Reads both CSVs
# 2. Filters for selected DUIDs and FCAS type early
# 3. Joins price and quantity bands
# 4. Returns only the data we need

duids_str = ", ".join([f"'{d}'" for d in selected_duids])

merged_query = f"""
WITH price_bands AS (
    SELECT
        BIDTYPE, SETTLEMENTDATE, DUID, DIRECTION, OFFERDATE,
        PRICEBAND1, PRICEBAND2, PRICEBAND3, PRICEBAND4, PRICEBAND5,
        PRICEBAND6, PRICEBAND7, PRICEBAND8, PRICEBAND9, PRICEBAND10
    FROM read_csv_auto('{biddayofferperiod}',
        header=true,
        skip=1,
        delim=',',
        strict_mode=false,
        ignore_errors=true
    )
    WHERE DUID IN ({duids_str})
    AND BIDTYPE = '{selected_fcas}'
),
quantity_bands AS (
    SELECT
        BIDTYPE, TRADINGDATE AS SETTLEMENTDATE, DUID, DIRECTION, OFFERDATETIME AS OFFERDATE, PERIODID,
        BANDAVAIL1, BANDAVAIL2, BANDAVAIL3, BANDAVAIL4, BANDAVAIL5,
        BANDAVAIL6, BANDAVAIL7, BANDAVAIL8, BANDAVAIL9, BANDAVAIL10
    FROM read_csv_auto('{bidofferperiod}',
        header=true,
        skip=1,
        delim=',',
        strict_mode=false,
        ignore_errors=true
    )
    WHERE DUID IN ({duids_str})
    AND BIDTYPE = '{selected_fcas}'
)
SELECT
    q.DUID,
    q.BIDTYPE,
    q.SETTLEMENTDATE,
    q.PERIODID,
    q.OFFERDATE,
    q.DIRECTION,
    q.BANDAVAIL1, q.BANDAVAIL2, q.BANDAVAIL3, q.BANDAVAIL4, q.BANDAVAIL5,
    q.BANDAVAIL6, q.BANDAVAIL7, q.BANDAVAIL8, q.BANDAVAIL9, q.BANDAVAIL10,
    p.PRICEBAND1, p.PRICEBAND2, p.PRICEBAND3, p.PRICEBAND4, p.PRICEBAND5,
    p.PRICEBAND6, p.PRICEBAND7, p.PRICEBAND8, p.PRICEBAND9, p.PRICEBAND10
FROM quantity_bands q
INNER JOIN price_bands p
    ON q.DUID = p.DUID
    AND q.SETTLEMENTDATE = p.SETTLEMENTDATE
    AND q.DIRECTION = p.DIRECTION
    AND q.BIDTYPE = p.BIDTYPE
    AND q.OFFERDATE = p.OFFERDATE
ORDER BY q.DUID, q.SETTLEMENTDATE, q.PERIODID, q.OFFERDATE
"""

print("\nExecuting merged query (this may take a moment)...")
merged_df = con.execute(merged_query).fetchdf()
print(f"Merged dataset has {len(merged_df)} records")

# =============================================================================
# FILTER TO ONLY KEEP TRUE REBIDS (where quantity bands actually change)
# =============================================================================

quantity_bands = ['BANDAVAIL1', 'BANDAVAIL2', 'BANDAVAIL3', 'BANDAVAIL4', 'BANDAVAIL5',
                  'BANDAVAIL6', 'BANDAVAIL7', 'BANDAVAIL8', 'BANDAVAIL9', 'BANDAVAIL10']

# Sort by auction identifiers and OFFERDATE
merged_df = merged_df.sort_values(['DUID', 'SETTLEMENTDATE', 'PERIODID', 'OFFERDATE'])

# For each auction (DUID, SETTLEMENTDATE, PERIODID), check if quantity bands changed from previous row
# Keep the first row (initial bid) and any row where at least one BANDAVAIL changed

def filter_true_rebids(group):
    """Keep only rows where quantity bands changed from the previous row (or first row)."""
    if len(group) <= 1:
        return group

    # Always keep the first row (initial bid)
    keep_mask = [True]

    # Compare each subsequent row to the previous one
    for i in range(1, len(group)):
        prev_row = group.iloc[i-1]
        curr_row = group.iloc[i]

        # Check if any quantity band changed
        changed = False
        for band in quantity_bands:
            if prev_row[band] != curr_row[band]:
                changed = True
                break

        keep_mask.append(changed)

    return group[keep_mask]

print("Filtering to keep only true rebids (where quantity bands changed)...")
original_count = len(merged_df)
merged_df = merged_df.groupby(['DUID', 'SETTLEMENTDATE', 'PERIODID'], group_keys=False).apply(filter_true_rebids)
merged_df = merged_df.reset_index(drop=True)
filtered_count = len(merged_df)
print(f"Filtered from {original_count} to {filtered_count} records ({original_count - filtered_count} non-changing rebids removed)")

# Get FCAS types available (for reference)
print(f"\nFCAS type: {selected_fcas}")

# =============================================================================
# CREATE BID CURVE PLOTTING FUNCTION
# =============================================================================

def plot_bid_curve(data, duid, fcas_type, settlement_date, period_id, output_dir):
    """
    Plot bid curves for all rebids in a given period.
    Each rebid is a different line on the same plot.
    X-axis: Cumulative quantity (MW)
    Y-axis: Price ($/MWh)
    """
    fig, ax = plt.subplots(figsize=(10, 6))

    # Get all rebids for this period (different OFFERDATEs)
    rebids = data.sort_values('OFFERDATE')
    num_rebids = len(rebids)

    # Color map for different rebids
    colors = plt.cm.viridis(np.linspace(0, 1, max(num_rebids, 1)))

    price_bands = ['PRICEBAND1', 'PRICEBAND2', 'PRICEBAND3', 'PRICEBAND4', 'PRICEBAND5',
                   'PRICEBAND6', 'PRICEBAND7', 'PRICEBAND8', 'PRICEBAND9', 'PRICEBAND10']
    # quantity_bands is defined globally above

    for i, (idx, row) in enumerate(rebids.iterrows()):
        prices = [row[pb] for pb in price_bands]
        quantities = [row[qb] for qb in quantity_bands]

        # Create step function for bid curve
        # Cumulative quantity on x-axis
        cumulative_qty = np.cumsum([0] + quantities)
        prices_extended = prices + [prices[-1]]  # Extend for step plot

        # Plot as step function
        offer_time = row['OFFERDATE'].strftime('%H:%M') if pd.notna(row['OFFERDATE']) else 'Unknown'
        ax.step(cumulative_qty, prices_extended, where='post', color=colors[i],
                label=f'Rebid {i+1} ({offer_time})', linewidth=1.5, alpha=0.8)

    ax.set_xlabel('Cumulative Quantity (MW)')
    ax.set_ylabel('Price ($/MWh)')
    ax.set_title(f'{duid} - {fcas_type}\nPeriod: {settlement_date} Period {period_id}')
    ax.grid(True, alpha=0.3)


    # Add Viridis colorbar legend in the top left
    sm = ScalarMappable(cmap=plt.cm.viridis, norm=Normalize(vmin=1, vmax=num_rebids))
    sm.set_array([])
    cbar = plt.colorbar(sm, ax=ax, orientation='vertical', fraction=0.05, pad=0.02)
    cbar.set_label('Rebid Index', fontsize=9)
    cbar.ax.yaxis.set_label_position('left')
    cbar.ax.yaxis.set_ticks_position('left')
    cbar.ax.yaxis.set_label_coords(-2.5, 0.5)
    cbar.ax.tick_params(labelsize=8)
    cbar.ax.set_position([0.02, 0.55, 0.02, 0.35])  # [left, bottom, width, height] in figure coordinates

    # Only show legend if reasonable number of rebids
    if num_rebids <= 10:
        ax.legend(loc='upper left', fontsize=8)
    else:
        ax.text(0.02, 0.98, f'{num_rebids} bids shown', transform=ax.transAxes,
                fontsize=10, verticalalignment='top')

    plt.tight_layout()

    # Create filename from settlement_date and period_id
    period_str = pd.to_datetime(settlement_date).strftime('%Y%m%d_%H%M')
    filename = f'{output_dir}/{duid}_{fcas_type}_{period_str}_period{period_id}.png'
    plt.savefig(filename, dpi=100, bbox_inches='tight')
    plt.close()

    return filename

# =============================================================================
# GENERATE BID CURVES FOR SELECTED BATTERIES
# =============================================================================

for duid in selected_duids:
    print(f"\n{'='*60}")
    print(f"Generating bid curves for {duid}")
    print('='*60)

    # Create output directory
    output_dir = FIGURES_DIR / 'bid_curves' / duid
    output_dir.mkdir(parents=True, exist_ok=True)
    output_dir = str(output_dir)  # Convert to string for f-string compatibility

    # Filter for this DUID (already filtered by FCAS in query)
    duid_data = merged_df[merged_df['DUID'] == duid]

    if len(duid_data) == 0:
        print(f"No data found for {duid} - {selected_fcas}")
        continue

    # Get unique periods (SETTLEMENTDATE + PERIODID combinations)
    # PERIODID identifies the 5-minute interval within a day (1-288)
    periods = duid_data[['SETTLEMENTDATE', 'PERIODID']].drop_duplicates()

    print(f"Found {len(periods)} unique periods for {selected_fcas}")

    # Generate bid curves for each period
    count = 0
    for _, period_row in periods.iterrows():
        settlement_date = period_row['SETTLEMENTDATE']
        period_id = period_row['PERIODID']

        period_data = duid_data[
            (duid_data['SETTLEMENTDATE'] == settlement_date) &
            (duid_data['PERIODID'] == period_id)
        ]

        if len(period_data) > 0:
            filename = plot_bid_curve(period_data, duid, selected_fcas, settlement_date, period_id, output_dir)
            count += 1

            if count % 50 == 0:
                print(f"  Generated {count} figures...")

    print(f"Generated {count} bid curve figures for {duid}")
    print(f"Saved to: {output_dir}/")

# =============================================================================
# GENERATE CONDENSED BID CURVES (BANDS 1-6 ONLY)
# =============================================================================

# Define condensed bands (1-6 only)
quantity_bands_condensed = ['BANDAVAIL1', 'BANDAVAIL2', 'BANDAVAIL3', 'BANDAVAIL4', 'BANDAVAIL5', 'BANDAVAIL6', 'BANDAVAIL7']
price_bands_condensed = ['PRICEBAND1', 'PRICEBAND2', 'PRICEBAND3', 'PRICEBAND4', 'PRICEBAND5', 'PRICEBAND6', 'PRICEBAND7']

def plot_bid_curve_condensed(data, duid, fcas_type, settlement_date, period_id, output_dir):
    """
    Plot bid curves for all rebids in a given period (bands 1-7 only).
    Each rebid is a different line on the same plot.
    X-axis: Cumulative quantity (MW)
    Y-axis: Price ($/MWh)
    """
    fig, ax = plt.subplots(figsize=(10, 6))

    # Get all rebids for this period (different OFFERDATEs)
    rebids = data.sort_values('OFFERDATE')
    num_rebids = len(rebids)

    # Color map for different rebids
    colors = plt.cm.viridis(np.linspace(0, 1, max(num_rebids, 1)))

    for i, (idx, row) in enumerate(rebids.iterrows()):
        prices = [row[pb] for pb in price_bands_condensed]
        quantities = [row[qb] for qb in quantity_bands_condensed]

        # Create step function for bid curve
        # Cumulative quantity on x-axis
        cumulative_qty = np.cumsum([0] + quantities)
        prices_extended = prices + [prices[-1]]  # Extend for step plot

        # Plot as step function
        offer_time = row['OFFERDATE'].strftime('%H:%M') if pd.notna(row['OFFERDATE']) else 'Unknown'
        ax.step(cumulative_qty, prices_extended, where='post', color=colors[i],
                label=f'Rebid {i+1} ({offer_time})', linewidth=1.5, alpha=0.8)

    ax.set_xlabel('Cumulative Quantity (MW)')
    ax.set_ylabel('Price ($/MWh)')
    ax.set_title(f'{duid} - {fcas_type} (Bands 1-6)\nPeriod: {settlement_date} Period {period_id}')
    ax.grid(True, alpha=0.3)



    # Add Viridis colorbar legend in the top left
    sm = ScalarMappable(cmap=plt.cm.viridis, norm=Normalize(vmin=1, vmax=num_rebids))
    sm.set_array([])
    cbar = plt.colorbar(sm, ax=ax, orientation='vertical', fraction=0.05, pad=0.02)
    cbar.set_label('Rebid Index', fontsize=9)
    cbar.ax.yaxis.set_label_position('left')
    cbar.ax.yaxis.set_ticks_position('left')
    cbar.ax.yaxis.set_label_coords(-2.5, 0.5)
    cbar.ax.tick_params(labelsize=8)
    cbar.ax.set_position([0.02, 0.55, 0.02, 0.35])  # [left, bottom, width, height] in figure coordinates


    # Only show legend if reasonable number of rebids
    if num_rebids <= 10:
        ax.legend(loc='upper left', fontsize=8)
    else:
        ax.text(0.02, 0.98, f'{num_rebids} bids shown', transform=ax.transAxes,
                fontsize=10, verticalalignment='top')

    plt.tight_layout()

    # Create filename from settlement_date and period_id
    period_str = pd.to_datetime(settlement_date).strftime('%Y%m%d_%H%M')
    filename = f'{output_dir}/{duid}_{fcas_type}_{period_str}_period{period_id}.png'
    plt.savefig(filename, dpi=100, bbox_inches='tight')
    plt.close()

    return filename

# Generate condensed bid curves for each DUID
for duid in selected_duids:
    print(f"\n{'='*60}")
    print(f"Generating CONDENSED bid curves for {duid} (bands 1-7)")
    print('='*60)

    # Create condensed output directory
    output_dir = FIGURES_DIR / 'bid_curves' / f'{duid}_condensed'
    output_dir.mkdir(parents=True, exist_ok=True)
    output_dir = str(output_dir)  # Convert to string for f-string compatibility

    # Filter for this DUID (already filtered by FCAS in query)
    duid_data = merged_df[merged_df['DUID'] == duid]

    if len(duid_data) == 0:
        print(f"No data found for {duid} - {selected_fcas}")
        continue

    # Get unique periods (SETTLEMENTDATE + PERIODID combinations)
    periods = duid_data[['SETTLEMENTDATE', 'PERIODID']].drop_duplicates()

    print(f"Found {len(periods)} unique periods for {selected_fcas}")

    # Generate condensed bid curves for each period
    count = 0
    for _, period_row in periods.iterrows():
        settlement_date = period_row['SETTLEMENTDATE']
        period_id = period_row['PERIODID']

        period_data = duid_data[
            (duid_data['SETTLEMENTDATE'] == settlement_date) &
            (duid_data['PERIODID'] == period_id)
        ]

        if len(period_data) > 0:
            filename = plot_bid_curve_condensed(period_data, duid, selected_fcas, settlement_date, period_id, output_dir)
            count += 1

            if count % 50 == 0:
                print(f"  Generated {count} figures...")

    print(f"Generated {count} condensed bid curve figures for {duid}")
    print(f"Saved to: {output_dir}/")

# =============================================================================
# SUMMARY STATISTICS (TRUE REBIDS ONLY)
# =============================================================================

print("\n" + "="*80)
print("SUMMARY (True Rebids Only - where quantity bands changed)")
print("="*80)

for duid in selected_duids:
    duid_data = merged_df[merged_df['DUID'] == duid]

    if len(duid_data) == 0:
        continue

    # Count true rebids per period (number of rows - 1, since first row is initial bid)
    bid_counts = duid_data.groupby(['SETTLEMENTDATE', 'PERIODID']).size()
    true_rebid_counts = bid_counts - 1  # Subtract 1 for initial bid

    print(f"\n{duid} ({selected_fcas}):")
    print(f"  Total periods: {len(bid_counts)}")
    print(f"  Mean true rebids per period: {true_rebid_counts.mean():.2f}")
    print(f"  Max true rebids in a period: {true_rebid_counts.max()}")
    print(f"  Periods with zero true rebids: {(true_rebid_counts == 0).sum()}")
    print(f"  Periods with 1+ true rebids: {(true_rebid_counts >= 1).sum()}")

# Close DuckDB connection
con.close()
