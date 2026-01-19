import pandas as pd
import duckdb
import matplotlib.pyplot as plt
import numpy as np
import os
import sys
from pathlib import Path

# Add parent directory to path for config import
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import BIDDAYOFFER_PATH, BIDOFFERPERIOD_PATH, DUID_MAP_PATH, FIGURES_DIR

# Create output directory if it doesn't exist
rebids_dir = FIGURES_DIR / 'rebids'
rebids_dir.mkdir(exist_ok=True)

# =============================================================================
# LOAD DATA
# =============================================================================

biddayofferperiod = str(BIDDAYOFFER_PATH)

con = duckdb.connect()
query = f"""
SELECT BIDTYPE, SETTLEMENTDATE, DUID, OFFERDATE FROM read_csv_auto('{biddayofferperiod}',
	header=true,
	skip=1,
	delim=',',
	strict_mode=false,
	ignore_errors=true
)
"""
large_bd_df = con.execute(query).fetchdf()

# =============================================================================
# MERGE WITH PARTICIPANT MAP AND CATEGORIZE BIDDERS
# =============================================================================

participant_map = pd.read_csv(DUID_MAP_PATH)

# Merge bid data with participant map on DUID
merged_df = large_bd_df.merge(participant_map[['DUID', 'DISPATCHTYPE', 'TESLA_AUTOBIDDER', 'PARTICIPANT_NAME']],
                               on='DUID', how='left')

# Exclude VPP bidder (VSSEL1V1)
merged_df = merged_df[merged_df['DUID'] != 'VSSEL1V1']

# Create bidder category based on DISPATCHTYPE and TESLA_AUTOBIDDER
def categorize_bidder(row):
    is_battery = row['DISPATCHTYPE'] == 'BIDIRECTIONAL'
    is_autobidder = row['TESLA_AUTOBIDDER'] == True

    if is_battery and is_autobidder:
        return 'Autobidder Battery'
    elif is_battery and not is_autobidder:
        return 'Non-Autobidder Battery'
    else:
        return 'Non-Battery'

merged_df['BIDDER_CATEGORY'] = merged_df.apply(categorize_bidder, axis=1)

# =============================================================================
# COUNT REBIDS PER AUCTION
# =============================================================================

# Filter for FCAS bids only (exclude ENERGY)
fcas_df = merged_df[merged_df['BIDTYPE'] != 'ENERGY'].copy()

# Count number of bids per auction (SETTLEMENTDATE, DUID, BIDTYPE)
# Number of rebids = total bids - 1 (first bid is not a rebid)
bid_counts = fcas_df.groupby(['BIDDER_CATEGORY', 'BIDTYPE', 'SETTLEMENTDATE', 'DUID']).size().reset_index(name='num_bids')
bid_counts['num_rebids'] = bid_counts['num_bids'] - 1

# Get unique FCAS types and categories
fcas_types = sorted(bid_counts['BIDTYPE'].unique())
all_categories = ['Autobidder Battery', 'Non-Autobidder Battery', 'Non-Battery']
category_colors = ['#1f77b4', '#ff7f0e', '#2ca02c']  # Blue, Orange, Green
battery_categories = ['Autobidder Battery', 'Non-Autobidder Battery']
battery_colors = ['#1f77b4', '#ff7f0e']  # Blue, Orange

# =============================================================================
# SUMMARY STATISTICS
# =============================================================================

print("=" * 80)
print("REBID ANALYSIS: Distribution of Rebids per Auction")
print("=" * 80)

print("\n\nSummary Statistics: Number of Rebids per Auction")
print("-" * 60)

for cat in all_categories:
    cat_data = bid_counts[bid_counts['BIDDER_CATEGORY'] == cat]
    print(f"\n{cat}:")
    print(f"  Total auctions: {len(cat_data)}")
    print(f"  Mean rebids: {cat_data['num_rebids'].mean():.2f}")
    print(f"  Median rebids: {cat_data['num_rebids'].median():.0f}")
    print(f"  Std rebids: {cat_data['num_rebids'].std():.2f}")
    print(f"  Max rebids: {cat_data['num_rebids'].max():.0f}")
    print(f"  % with zero rebids: {(cat_data['num_rebids'] == 0).mean() * 100:.1f}%")

# =============================================================================
# BOX PLOTS: REBID DISTRIBUTION BY CATEGORY (ALL FCAS)
# =============================================================================

fig, ax = plt.subplots(figsize=(10, 6))

plot_data = [bid_counts[bid_counts['BIDDER_CATEGORY'] == cat]['num_rebids'] for cat in all_categories]
bp = ax.boxplot(plot_data, labels=all_categories, patch_artist=True)

for patch, color in zip(bp['boxes'], category_colors):
    patch.set_facecolor(color)
    patch.set_alpha(0.7)

ax.set_title('Distribution of Rebids per Auction by Bidder Category (All FCAS)')
ax.set_ylabel('Number of Rebids')
ax.grid(axis='y', alpha=0.3)

plt.tight_layout()
plt.savefig(rebids_dir / 'rebids_boxplot_all_fcas.png', dpi=150, bbox_inches='tight')
plt.close()

print("\nBox plot saved to 'figures/rebids/rebids_boxplot_all_fcas.png'")

# =============================================================================
# BOX PLOTS: REBID DISTRIBUTION BY CATEGORY AND FCAS TYPE
# =============================================================================

fig, axes = plt.subplots(2, 5, figsize=(18, 10))
axes = axes.flatten()

for i, fcas_type in enumerate(fcas_types):
    ax = axes[i]
    fcas_data = bid_counts[bid_counts['BIDTYPE'] == fcas_type]

    plot_data = [fcas_data[fcas_data['BIDDER_CATEGORY'] == cat]['num_rebids'] for cat in all_categories]

    # Filter out empty data
    plot_data_filtered = []
    labels_filtered = []
    colors_filtered = []
    for j, data in enumerate(plot_data):
        if len(data) > 0:
            plot_data_filtered.append(data)
            labels_filtered.append(all_categories[j][:12])
            colors_filtered.append(category_colors[j])

    if plot_data_filtered:
        bp = ax.boxplot(plot_data_filtered, labels=labels_filtered, patch_artist=True)
        for patch, color in zip(bp['boxes'], colors_filtered):
            patch.set_facecolor(color)
            patch.set_alpha(0.7)

    ax.set_title(fcas_type, fontsize=10)
    ax.tick_params(axis='x', rotation=45, labelsize=7)
    ax.grid(axis='y', alpha=0.3)

plt.suptitle('Distribution of Rebids per Auction by FCAS Type', fontsize=12)
plt.tight_layout()
plt.savefig(rebids_dir / 'rebids_boxplot_by_fcas.png', dpi=150, bbox_inches='tight')
plt.close()

print("Box plots by FCAS type saved to 'figures/rebids/rebids_boxplot_by_fcas.png'")

# =============================================================================
# BAR CHART: MEDIAN REBIDS BY CATEGORY AND FCAS TYPE
# =============================================================================

fig, ax = plt.subplots(figsize=(14, 6))

x = np.arange(len(fcas_types))
width = 0.25

for j, cat in enumerate(all_categories):
    medians = []
    for fcas_type in fcas_types:
        fcas_cat_data = bid_counts[(bid_counts['BIDTYPE'] == fcas_type) &
                                    (bid_counts['BIDDER_CATEGORY'] == cat)]['num_rebids']
        medians.append(fcas_cat_data.median() if len(fcas_cat_data) > 0 else 0)

    ax.bar(x + j * width, medians, width, label=cat, color=category_colors[j], alpha=0.7)

ax.set_xticks(x + width)
ax.set_xticklabels(fcas_types, rotation=45, ha='right')
ax.legend(loc='upper right')

ax.set_title('Median Number of Rebids per Auction by FCAS Type')
ax.set_xlabel('FCAS Type')
ax.set_ylabel('Median Number of Rebids')
ax.grid(axis='y', alpha=0.3)

plt.tight_layout()
plt.savefig(rebids_dir / 'rebids_median_bar_by_fcas.png', dpi=150, bbox_inches='tight')
plt.close()

print("Median rebids bar chart saved to 'figures/rebids/rebids_median_bar_by_fcas.png'")

# =============================================================================
# BAR CHART: MEAN REBIDS BY CATEGORY AND FCAS TYPE
# =============================================================================

fig, ax = plt.subplots(figsize=(14, 6))

x = np.arange(len(fcas_types))
width = 0.25

for j, cat in enumerate(all_categories):
    means = []
    for fcas_type in fcas_types:
        fcas_cat_data = bid_counts[(bid_counts['BIDTYPE'] == fcas_type) &
                                    (bid_counts['BIDDER_CATEGORY'] == cat)]['num_rebids']
        means.append(fcas_cat_data.mean() if len(fcas_cat_data) > 0 else 0)

    ax.bar(x + j * width, means, width, label=cat, color=category_colors[j], alpha=0.7)

ax.set_xticks(x + width)
ax.set_xticklabels(fcas_types, rotation=45, ha='right')
ax.legend(loc='upper right')

ax.set_title('Mean Number of Rebids per Auction by FCAS Type')
ax.set_xlabel('FCAS Type')
ax.set_ylabel('Mean Number of Rebids')
ax.grid(axis='y', alpha=0.3)

plt.tight_layout()
plt.savefig(rebids_dir / 'rebids_mean_bar_by_fcas.png', dpi=150, bbox_inches='tight')
plt.close()

print("Mean rebids bar chart saved to 'figures/rebids/rebids_mean_bar_by_fcas.png'")

# =============================================================================
# HISTOGRAMS: REBID DISTRIBUTION BY CATEGORY
# =============================================================================

fig, axes = plt.subplots(1, 3, figsize=(15, 5))

for i, cat in enumerate(all_categories):
    ax = axes[i]
    cat_data = bid_counts[bid_counts['BIDDER_CATEGORY'] == cat]['num_rebids']

    ax.hist(cat_data, bins=range(0, int(cat_data.max()) + 2), color=category_colors[i],
            alpha=0.7, edgecolor='black')
    ax.set_title(f'{cat}\n(n={len(cat_data)}, median={cat_data.median():.0f})')
    ax.set_xlabel('Number of Rebids')
    ax.set_ylabel('Frequency')
    ax.grid(axis='y', alpha=0.3)

plt.suptitle('Distribution of Rebids per Auction (All FCAS)', fontsize=12)
plt.tight_layout()
plt.savefig(rebids_dir / 'rebids_histogram_by_category.png', dpi=150, bbox_inches='tight')
plt.close()

print("Histograms saved to 'figures/rebids/rebids_histogram_by_category.png'")

# =============================================================================
# BATTERIES ONLY: BOX PLOTS BY FCAS TYPE
# =============================================================================

fig, axes = plt.subplots(2, 5, figsize=(18, 10))
axes = axes.flatten()

for i, fcas_type in enumerate(fcas_types):
    ax = axes[i]
    fcas_data = bid_counts[(bid_counts['BIDTYPE'] == fcas_type) &
                            (bid_counts['BIDDER_CATEGORY'].isin(battery_categories))]

    plot_data = [fcas_data[fcas_data['BIDDER_CATEGORY'] == cat]['num_rebids'] for cat in battery_categories]

    plot_data_filtered = []
    labels_filtered = []
    colors_filtered = []
    for j, data in enumerate(plot_data):
        if len(data) > 0:
            plot_data_filtered.append(data)
            labels_filtered.append(battery_categories[j][:12])
            colors_filtered.append(battery_colors[j])

    if plot_data_filtered:
        bp = ax.boxplot(plot_data_filtered, labels=labels_filtered, patch_artist=True)
        for patch, color in zip(bp['boxes'], colors_filtered):
            patch.set_facecolor(color)
            patch.set_alpha(0.7)

    ax.set_title(fcas_type, fontsize=10)
    ax.tick_params(axis='x', rotation=45, labelsize=7)
    ax.grid(axis='y', alpha=0.3)

plt.suptitle('Distribution of Rebids per Auction - Batteries Only', fontsize=12)
plt.tight_layout()
plt.savefig(rebids_dir / 'rebids_boxplot_batteries_by_fcas.png', dpi=150, bbox_inches='tight')
plt.close()

print("Battery-only box plots saved to 'figures/rebids/rebids_boxplot_batteries_by_fcas.png'")

# =============================================================================
# SUMMARY TABLES
# =============================================================================

print("\n\n" + "=" * 100)
print("SUMMARY TABLE: Mean and Median Rebids by Bidder Category (All FCAS)")
print("=" * 100)

summary_data = []
for cat in all_categories:
    cat_data = bid_counts[bid_counts['BIDDER_CATEGORY'] == cat]
    summary_data.append({
        'Category': cat,
        'N': len(cat_data),
        'Mean': cat_data['num_rebids'].mean(),
        'Median': cat_data['num_rebids'].median(),
        'Std': cat_data['num_rebids'].std(),
        'Max': cat_data['num_rebids'].max(),
        '% Zero Rebids': (cat_data['num_rebids'] == 0).mean() * 100
    })

summary_df = pd.DataFrame(summary_data).set_index('Category')
print("\n" + summary_df.round(2).to_string())

# Per-FCAS type summary
print("\n\n" + "=" * 100)
print("SUMMARY TABLE: Mean Rebids by Bidder Category (Per FCAS Type)")
print("=" * 100)

fcas_summary_data = []
for fcas_type in fcas_types:
    row = {'FCAS': fcas_type}
    for cat in all_categories:
        fcas_cat_data = bid_counts[(bid_counts['BIDTYPE'] == fcas_type) &
                                    (bid_counts['BIDDER_CATEGORY'] == cat)]['num_rebids']
        row[cat] = fcas_cat_data.mean() if len(fcas_cat_data) > 0 else None
    fcas_summary_data.append(row)

fcas_summary_df = pd.DataFrame(fcas_summary_data).set_index('FCAS')
print("\nMean Rebids:")
print(fcas_summary_df.round(2).to_string())

# Median per FCAS
fcas_median_data = []
for fcas_type in fcas_types:
    row = {'FCAS': fcas_type}
    for cat in all_categories:
        fcas_cat_data = bid_counts[(bid_counts['BIDTYPE'] == fcas_type) &
                                    (bid_counts['BIDDER_CATEGORY'] == cat)]['num_rebids']
        row[cat] = fcas_cat_data.median() if len(fcas_cat_data) > 0 else None
    fcas_median_data.append(row)

fcas_median_df = pd.DataFrame(fcas_median_data).set_index('FCAS')
print("\n\nMedian Rebids:")
print(fcas_median_df.round(2).to_string())

# =============================================================================
# =============================================================================
# TRUE REBIDS ANALYSIS (where quantity bands actually change)
# =============================================================================
# =============================================================================

print("\n\n")
print("=" * 100)
print("TRUE REBIDS ANALYSIS: Only counting rebids where quantity bands changed")
print("=" * 100)

# Create output directory for true rebids
true_rebids_dir = rebids_dir / 'true_rebids'
true_rebids_dir.mkdir(exist_ok=True)

# Load quantity bands from BIDOFFERPERIOD
bidofferperiod = str(BIDOFFERPERIOD_PATH)

print("\nLoading quantity bands data...")
quantity_query = f"""
SELECT BIDTYPE, TRADINGDATE AS SETTLEMENTDATE, DUID, OFFERDATETIME AS OFFERDATE,
       PERIODID,
       BANDAVAIL1, BANDAVAIL2, BANDAVAIL3, BANDAVAIL4, BANDAVAIL5,
       BANDAVAIL6, BANDAVAIL7, BANDAVAIL8, BANDAVAIL9, BANDAVAIL10
FROM read_csv_auto('{bidofferperiod}',
    header=true,
    skip=1,
    delim=',',
    strict_mode=false,
    ignore_errors=true
)
WHERE BIDTYPE != 'ENERGY'
"""
quantity_df = con.execute(quantity_query).fetchdf()
print(f"Loaded {len(quantity_df)} quantity band records")

# Merge with participant map
quantity_df = quantity_df.merge(
    participant_map[['DUID', 'DISPATCHTYPE', 'TESLA_AUTOBIDDER']],
    on='DUID', how='left'
)

# Exclude VPP bidder
quantity_df = quantity_df[quantity_df['DUID'] != 'VSSEL1V1']

# Add bidder category
quantity_df['BIDDER_CATEGORY'] = quantity_df.apply(categorize_bidder, axis=1)

# Define quantity bands
quantity_bands = ['BANDAVAIL1', 'BANDAVAIL2', 'BANDAVAIL3', 'BANDAVAIL4', 'BANDAVAIL5',
                  'BANDAVAIL6', 'BANDAVAIL7', 'BANDAVAIL8', 'BANDAVAIL9', 'BANDAVAIL10']

# Sort by auction identifiers and OFFERDATE
quantity_df = quantity_df.sort_values(['DUID', 'SETTLEMENTDATE', 'BIDTYPE', 'OFFERDATE', 'PERIODID']).reset_index(drop=True)

# For each auction (DUID, SETTLEMENTDATE, BIDTYPE), count true rebids
# A true rebid is when at least one quantity band changed from the previous offer
# Using vectorized operations for efficiency

print("Counting true rebids (where quantity bands changed)...")

# Create group identifier
quantity_df['auction_id'] = (
    quantity_df['DUID'].astype(str) + '_' +
    quantity_df['SETTLEMENTDATE'].astype(str) + '_' +
    quantity_df['BIDTYPE'].astype(str) + '_' +
    quantity_df['PERIODID'].astype(str)
)

# For each quantity band, check if it changed from the previous row within the same auction
# First, shift all bands within each auction group
for band in quantity_bands:
    print(band)
    quantity_df[f'{band}_prev'] = quantity_df.groupby('auction_id')[band].shift(1)

# Check if any band changed (comparing current to previous)
# A row is a true rebid if it's not the first in its group AND at least one band changed
quantity_df['is_same_auction'] = quantity_df['auction_id'] == quantity_df['auction_id'].shift(1)

# Check if any band changed
band_changed_cols = []
for band in quantity_bands:
    col_name = f'{band}_changed'
    quantity_df[col_name] = (quantity_df[band] != quantity_df[f'{band}_prev'])
    band_changed_cols.append(col_name)

# A true rebid occurs when: same auction as previous row AND at least one band changed
quantity_df['is_true_rebid'] = quantity_df['is_same_auction'] & quantity_df[band_changed_cols].any(axis=1)

# Count true rebids per auction
true_rebid_counts = quantity_df.groupby(['BIDDER_CATEGORY', 'BIDTYPE', 'SETTLEMENTDATE', 'DUID', 'PERIODID'])['is_true_rebid'].sum().reset_index(name='num_true_rebids')

# Clean up temporary columns
quantity_df = quantity_df.drop(columns=['auction_id', 'is_same_auction', 'is_true_rebid'] +
                                        [f'{band}_prev' for band in quantity_bands] +
                                        band_changed_cols)

print(f"Processed {len(true_rebid_counts)} auctions")

# =============================================================================
# TRUE REBIDS: SUMMARY STATISTICS
# =============================================================================

print("\n\nSummary Statistics: Number of TRUE Rebids per Auction (across all units)")
print("-" * 60)

for cat in all_categories:
    cat_data = true_rebid_counts[true_rebid_counts['BIDDER_CATEGORY'] == cat]
    print(f"\n{cat}:")
    print(f"  Total auctions: {len(cat_data)}")
    print(f"  Mean true rebids per auction: {cat_data['num_true_rebids'].mean():.2f}")
    print(f"  Median true rebids per auction: {cat_data['num_true_rebids'].median():.0f}")
    print(f"  Std true rebids: {cat_data['num_true_rebids'].std():.2f}")
    print(f"  Max true rebids: {cat_data['num_true_rebids'].max():.0f}")
    print(f"  % with zero true rebids: {(cat_data['num_true_rebids'] == 0).mean() * 100:.1f}%")

# =============================================================================
# TRUE REBIDS: PER-UNIT PER-MARKET ANALYSIS
# =============================================================================

print("\n\n" + "=" * 100)
print("TRUE REBIDS: Average per Unit per Market")
print("(For each unit in each FCAS market, what's their average true rebids per auction?)")
print("=" * 100)

# First, calculate average true rebids per unit per market (across all settlement dates)
unit_market_avg = true_rebid_counts.groupby(['BIDDER_CATEGORY', 'BIDTYPE', 'DUID']).agg({
    'num_true_rebids': ['mean', 'median', 'std', 'count']
}).reset_index()
unit_market_avg.columns = ['BIDDER_CATEGORY', 'BIDTYPE', 'DUID', 'mean_rebids', 'median_rebids', 'std_rebids', 'num_auctions']

# Now summarize by category and FCAS type
print("\nMean True Rebids per Unit by Category and FCAS Type:")
print("-" * 80)

for cat in all_categories:
    cat_data = unit_market_avg[unit_market_avg['BIDDER_CATEGORY'] == cat]
    if len(cat_data) == 0:
        continue

    print(f"\n{cat}:")
    print(f"  Number of unique units: {cat_data['DUID'].nunique()}")

    for fcas_type in fcas_types:
        fcas_data = cat_data[cat_data['BIDTYPE'] == fcas_type]
        if len(fcas_data) > 0:
            # Average of each unit's mean rebids
            avg_of_means = fcas_data['mean_rebids'].mean()
            print(f"    {fcas_type}: {avg_of_means:.2f} avg true rebids/auction (across {len(fcas_data)} units)")

# Detailed per-unit breakdown for batteries
print("\n\n" + "=" * 100)
print("DETAILED: Per-Unit True Rebid Statistics (Batteries Only)")
print("=" * 100)

for cat in battery_categories:
    cat_data = unit_market_avg[unit_market_avg['BIDDER_CATEGORY'] == cat]
    if len(cat_data) == 0:
        continue

    print(f"\n{cat}:")
    print("-" * 80)

    # Show each unit's stats
    units = cat_data['DUID'].unique()
    for unit in sorted(units):
        unit_data = cat_data[cat_data['DUID'] == unit]
        print(f"\n  {unit}:")
        for _, row in unit_data.iterrows():
            print(f"    {row['BIDTYPE']}: mean={row['mean_rebids']:.2f}, median={row['median_rebids']:.0f}, n={row['num_auctions']:.0f} auctions")

# =============================================================================
# TRUE REBIDS: BOX PLOTS BY CATEGORY (ALL FCAS)
# =============================================================================

fig, ax = plt.subplots(figsize=(10, 6))

plot_data = [true_rebid_counts[true_rebid_counts['BIDDER_CATEGORY'] == cat]['num_true_rebids'] for cat in all_categories]
bp = ax.boxplot(plot_data, labels=all_categories, patch_artist=True)

for patch, color in zip(bp['boxes'], category_colors):
    patch.set_facecolor(color)
    patch.set_alpha(0.7)

ax.set_title('Distribution of TRUE Rebids per Auction by Bidder Category (All FCAS)')
ax.set_ylabel('Number of True Rebids')
ax.grid(axis='y', alpha=0.3)

plt.tight_layout()
plt.savefig(true_rebids_dir / 'true_rebids_boxplot_all_fcas.png', dpi=150, bbox_inches='tight')
plt.close()

print("\nTrue rebids box plot saved to 'figures/rebids/true_rebids/true_rebids_boxplot_all_fcas.png'")

# =============================================================================
# TRUE REBIDS: BOX PLOTS BY CATEGORY AND FCAS TYPE
# =============================================================================

fig, axes = plt.subplots(2, 5, figsize=(18, 10))
axes = axes.flatten()

for i, fcas_type in enumerate(fcas_types):
    ax = axes[i]
    fcas_data = true_rebid_counts[true_rebid_counts['BIDTYPE'] == fcas_type]

    plot_data = [fcas_data[fcas_data['BIDDER_CATEGORY'] == cat]['num_true_rebids'] for cat in all_categories]

    plot_data_filtered = []
    labels_filtered = []
    colors_filtered = []
    for j, data in enumerate(plot_data):
        if len(data) > 0:
            plot_data_filtered.append(data)
            labels_filtered.append(all_categories[j][:12])
            colors_filtered.append(category_colors[j])

    if plot_data_filtered:
        bp = ax.boxplot(plot_data_filtered, labels=labels_filtered, patch_artist=True)
        for patch, color in zip(bp['boxes'], colors_filtered):
            patch.set_facecolor(color)
            patch.set_alpha(0.7)

    ax.set_title(fcas_type, fontsize=10)
    ax.tick_params(axis='x', rotation=45, labelsize=7)
    ax.grid(axis='y', alpha=0.3)

plt.suptitle('Distribution of TRUE Rebids per Auction by FCAS Type', fontsize=12)
plt.tight_layout()
plt.savefig(true_rebids_dir / 'true_rebids_boxplot_by_fcas.png', dpi=150, bbox_inches='tight')
plt.close()

print("True rebids box plots by FCAS type saved to 'figures/rebids/true_rebids/true_rebids_boxplot_by_fcas.png'")

# =============================================================================
# TRUE REBIDS: BAR CHART - MEDIAN BY CATEGORY AND FCAS TYPE
# =============================================================================

fig, ax = plt.subplots(figsize=(14, 6))

x = np.arange(len(fcas_types))
width = 0.25

for j, cat in enumerate(all_categories):
    medians = []
    for fcas_type in fcas_types:
        fcas_cat_data = true_rebid_counts[(true_rebid_counts['BIDTYPE'] == fcas_type) &
                                           (true_rebid_counts['BIDDER_CATEGORY'] == cat)]['num_true_rebids']
        medians.append(fcas_cat_data.median() if len(fcas_cat_data) > 0 else 0)

    ax.bar(x + j * width, medians, width, label=cat, color=category_colors[j], alpha=0.7)

ax.set_xticks(x + width)
ax.set_xticklabels(fcas_types, rotation=45, ha='right')
ax.legend(loc='upper right')

ax.set_title('Median Number of TRUE Rebids per Auction by FCAS Type')
ax.set_xlabel('FCAS Type')
ax.set_ylabel('Median Number of True Rebids')
ax.grid(axis='y', alpha=0.3)

plt.tight_layout()
plt.savefig(true_rebids_dir / 'true_rebids_median_bar_by_fcas.png', dpi=150, bbox_inches='tight')
plt.close()

print("True rebids median bar chart saved to 'figures/rebids/true_rebids/true_rebids_median_bar_by_fcas.png'")

# =============================================================================
# TRUE REBIDS: BAR CHART - MEAN BY CATEGORY AND FCAS TYPE
# =============================================================================

fig, ax = plt.subplots(figsize=(14, 6))

x = np.arange(len(fcas_types))
width = 0.25

for j, cat in enumerate(all_categories):
    means = []
    for fcas_type in fcas_types:
        fcas_cat_data = true_rebid_counts[(true_rebid_counts['BIDTYPE'] == fcas_type) &
                                           (true_rebid_counts['BIDDER_CATEGORY'] == cat)]['num_true_rebids']
        means.append(fcas_cat_data.mean() if len(fcas_cat_data) > 0 else 0)

    ax.bar(x + j * width, means, width, label=cat, color=category_colors[j], alpha=0.7)

ax.set_xticks(x + width)
ax.set_xticklabels(fcas_types, rotation=45, ha='right')
ax.legend(loc='upper right')

ax.set_title('Mean Number of TRUE Rebids per Auction by FCAS Type')
ax.set_xlabel('FCAS Type')
ax.set_ylabel('Mean Number of True Rebids')
ax.grid(axis='y', alpha=0.3)

plt.tight_layout()
plt.savefig(true_rebids_dir / 'true_rebids_mean_bar_by_fcas.png', dpi=150, bbox_inches='tight')
plt.close()

print("True rebids mean bar chart saved to 'figures/rebids/true_rebids/true_rebids_mean_bar_by_fcas.png'")

# =============================================================================
# TRUE REBIDS: HISTOGRAMS BY CATEGORY
# =============================================================================

fig, axes = plt.subplots(1, 3, figsize=(15, 5))

for i, cat in enumerate(all_categories):
    ax = axes[i]
    cat_data = true_rebid_counts[true_rebid_counts['BIDDER_CATEGORY'] == cat]['num_true_rebids']

    max_val = int(cat_data.max()) if len(cat_data) > 0 and cat_data.max() > 0 else 1
    ax.hist(cat_data, bins=range(0, max_val + 2), color=category_colors[i],
            alpha=0.7, edgecolor='black')
    ax.set_title(f'{cat}\n(n={len(cat_data)}, median={cat_data.median():.0f})')
    ax.set_xlabel('Number of True Rebids')
    ax.set_ylabel('Frequency')
    ax.grid(axis='y', alpha=0.3)

plt.suptitle('Distribution of TRUE Rebids per Auction (All FCAS)', fontsize=12)
plt.tight_layout()
plt.savefig(true_rebids_dir / 'true_rebids_histogram_by_category.png', dpi=150, bbox_inches='tight')
plt.close()

print("True rebids histograms saved to 'figures/rebids/true_rebids/true_rebids_histogram_by_category.png'")

# =============================================================================
# TRUE REBIDS: BATTERIES ONLY BOX PLOTS BY FCAS TYPE
# =============================================================================

fig, axes = plt.subplots(2, 5, figsize=(18, 10))
axes = axes.flatten()

for i, fcas_type in enumerate(fcas_types):
    ax = axes[i]
    fcas_data = true_rebid_counts[(true_rebid_counts['BIDTYPE'] == fcas_type) &
                                   (true_rebid_counts['BIDDER_CATEGORY'].isin(battery_categories))]

    plot_data = [fcas_data[fcas_data['BIDDER_CATEGORY'] == cat]['num_true_rebids'] for cat in battery_categories]

    plot_data_filtered = []
    labels_filtered = []
    colors_filtered = []
    for j, data in enumerate(plot_data):
        if len(data) > 0:
            plot_data_filtered.append(data)
            labels_filtered.append(battery_categories[j][:12])
            colors_filtered.append(battery_colors[j])

    if plot_data_filtered:
        bp = ax.boxplot(plot_data_filtered, labels=labels_filtered, patch_artist=True)
        for patch, color in zip(bp['boxes'], colors_filtered):
            patch.set_facecolor(color)
            patch.set_alpha(0.7)

    ax.set_title(fcas_type, fontsize=10)
    ax.tick_params(axis='x', rotation=45, labelsize=7)
    ax.grid(axis='y', alpha=0.3)

plt.suptitle('Distribution of TRUE Rebids per Auction - Batteries Only', fontsize=12)
plt.tight_layout()
plt.savefig(true_rebids_dir / 'true_rebids_boxplot_batteries_by_fcas.png', dpi=150, bbox_inches='tight')
plt.close()

print("True rebids battery-only box plots saved to 'figures/rebids/true_rebids/true_rebids_boxplot_batteries_by_fcas.png'")

# =============================================================================
# TRUE REBIDS: SUMMARY TABLES
# =============================================================================

print("\n\n" + "=" * 100)
print("SUMMARY TABLE: Mean and Median TRUE Rebids by Bidder Category (All FCAS)")
print("=" * 100)

true_summary_data = []
for cat in all_categories:
    cat_data = true_rebid_counts[true_rebid_counts['BIDDER_CATEGORY'] == cat]
    true_summary_data.append({
        'Category': cat,
        'N': len(cat_data),
        'Mean': cat_data['num_true_rebids'].mean(),
        'Median': cat_data['num_true_rebids'].median(),
        'Std': cat_data['num_true_rebids'].std(),
        'Max': cat_data['num_true_rebids'].max(),
        '% Zero True Rebids': (cat_data['num_true_rebids'] == 0).mean() * 100
    })

true_summary_df = pd.DataFrame(true_summary_data).set_index('Category')
print("\n" + true_summary_df.round(2).to_string())

# Per-FCAS type summary for true rebids
print("\n\n" + "=" * 100)
print("SUMMARY TABLE: Mean TRUE Rebids by Bidder Category (Per FCAS Type)")
print("=" * 100)

true_fcas_summary_data = []
for fcas_type in fcas_types:
    row = {'FCAS': fcas_type}
    for cat in all_categories:
        fcas_cat_data = true_rebid_counts[(true_rebid_counts['BIDTYPE'] == fcas_type) &
                                           (true_rebid_counts['BIDDER_CATEGORY'] == cat)]['num_true_rebids']
        row[cat] = fcas_cat_data.mean() if len(fcas_cat_data) > 0 else None
    true_fcas_summary_data.append(row)

true_fcas_summary_df = pd.DataFrame(true_fcas_summary_data).set_index('FCAS')
print("\nMean True Rebids:")
print(true_fcas_summary_df.round(2).to_string())

# Median per FCAS for true rebids
true_fcas_median_data = []
for fcas_type in fcas_types:
    row = {'FCAS': fcas_type}
    for cat in all_categories:
        fcas_cat_data = true_rebid_counts[(true_rebid_counts['BIDTYPE'] == fcas_type) &
                                           (true_rebid_counts['BIDDER_CATEGORY'] == cat)]['num_true_rebids']
        row[cat] = fcas_cat_data.median() if len(fcas_cat_data) > 0 else None
    true_fcas_median_data.append(row)

true_fcas_median_df = pd.DataFrame(true_fcas_median_data).set_index('FCAS')
print("\n\nMedian True Rebids:")
print(true_fcas_median_df.round(2).to_string())

# =============================================================================
# COMPARISON: REGULAR REBIDS VS TRUE REBIDS
# =============================================================================

print("\n\n" + "=" * 100)
print("COMPARISON: Regular Rebids vs True Rebids")
print("=" * 100)

# Merge the two datasets for comparison
comparison_df = bid_counts[['BIDDER_CATEGORY', 'BIDTYPE', 'SETTLEMENTDATE', 'DUID', 'num_rebids']].merge(
    true_rebid_counts[['BIDDER_CATEGORY', 'BIDTYPE', 'SETTLEMENTDATE', 'DUID', 'num_true_rebids']],
    on=['BIDDER_CATEGORY', 'BIDTYPE', 'SETTLEMENTDATE', 'DUID'],
    how='inner'
)

comparison_df['pct_true'] = (comparison_df['num_true_rebids'] / comparison_df['num_rebids'] * 100).fillna(0)

print("\nPercentage of rebids that are 'true' rebids (quantity bands changed):")
for cat in all_categories:
    cat_data = comparison_df[comparison_df['BIDDER_CATEGORY'] == cat]
    # Only consider auctions with at least 1 rebid
    cat_with_rebids = cat_data[cat_data['num_rebids'] > 0]
    if len(cat_with_rebids) > 0:
        avg_pct = cat_with_rebids['pct_true'].mean()
        print(f"  {cat}: {avg_pct:.1f}% of rebids are true rebids")
