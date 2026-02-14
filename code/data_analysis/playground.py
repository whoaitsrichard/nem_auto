import pandas as pd
import duckdb
import sys
from pathlib import Path



bidofferperiod = '/Volumes/Rich drive/ai_bidders/data/samples/PUBLIC_ARCHIVE#BIDOFFERPERIOD#FILE01#202510010000.csv'
biddayofferperiod = '/Volumes/Rich drive/ai_bidders/data/samples/PUBLIC_ARCHIVE#BIDDAYOFFER#FILE01#202510010000.csv'
# Read first 10 rows of the CSV file

bidoffer_df = pd.read_csv(bidofferperiod, nrows=10, skiprows=1)
bidday_df = pd.read_csv(biddayofferperiod, nrows=10, skiprows=1)



bidday_df.to_csv("price_band_ex.csv")












con = duckdb.connect()
query = f"""
SELECT ENTRYTYPE, BIDTYPE, SETTLEMENTDATE, DUID, DIRECTION, REBID_EVENT_TIME, OFFERDATE, PRICEBAND1, PRICEBAND2, PRICEBAND3, PRICEBAND4, PRICEBAND5, PRICEBAND6, PRICEBAND7, PRICEBAND8, PRICEBAND9, PRICEBAND10 FROM read_csv_auto('{biddayofferperiod}', 
	header=true, 
	skip=1, 
	delim=',', 
	strict_mode=false, 
	ignore_errors=true
)
"""
large_bd_df = con.execute(query).fetchdf()
# Group by BIDTYPE, SETTLEMENTDATE, DUID, DIRECTION and order by REBID_EVENT_TIME


# biddayofferperiod contains only the price bands for a given day and complete coverage for October 2025.
# First I want to merge the data with the nem_duid_participant_map_2025-10-15.csv to figure out which bidders
# are using Tesla Autobidders. Exclude the VPP bidder since it's a bit different from other battery farms.
# Next group all of the bids into Autobidder Battery, Non-Autobidder Battery, and Non-Battery bidders.

# Now for each group, calculate the percentage breakdown of BIDTYPES they participate in (RAISE1SEC, LOWER1SEC, ENERGY etc)
# Calculate this percentage as a function of total auctions they take place in. So if a bidder participates in 100 auctions
# and places RAISEREG bids in 60 of them, their RAISEREG participation rate is 60%. This is not the same as counting how many
# observations they have since they can rebid for a single auction multiple times. Each rebid should not count as a separate auction participation.

# Load the participant map
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

# Calculate percentage breakdown of BIDTYPE participation for each bidder category
# An auction participation is a unique (SETTLEMENTDATE, DUID, BIDTYPE) combination
# For each category, the percentages across all BIDTYPEs should sum to 100%

# Get unique auction participations per BIDTYPE (SETTLEMENTDATE, DUID, BIDTYPE combinations)
bidtype_participations = merged_df.groupby(['BIDDER_CATEGORY', 'SETTLEMENTDATE', 'DUID', 'BIDTYPE']).size().reset_index(name='count')
test_df = bidtype_participations.reset_index()
# Count total participations per BIDTYPE per category
bidtype_counts = bidtype_participations.groupby(['BIDDER_CATEGORY', 'BIDTYPE']).size().reset_index(name='auction_count')

# Calculate total participations per category (sum across all BIDTYPEs)
total_per_category = bidtype_counts.groupby('BIDDER_CATEGORY')['auction_count'].sum().reset_index(name='total_participations')

# Merge to calculate percentages
bidtype_percentages = bidtype_counts.merge(total_per_category, on='BIDDER_CATEGORY')
bidtype_percentages['participation_pct'] = (bidtype_percentages['auction_count'] / bidtype_percentages['total_participations'] * 100).round(2)

# Pivot to create a summary table with BIDTYPE as columns
participation_summary = bidtype_percentages.pivot(index='BIDDER_CATEGORY',
                                                   columns='BIDTYPE',
                                                   values='participation_pct').fillna(0)

print("BIDTYPE Breakdown (%) for Each Bidder Category (rows sum to 100%):")
print(participation_summary.to_string())

print("\n\nTotal Auction Participations per Category:")
print(total_per_category.to_string(index=False))



# Now for each group and FCAS, calculate the price distribution of the initial bid prices for each band.
# For example, for autobidder batteries placing RAISE1SEC bids, what is the distribution of PRICEBAND1, PRICEBAND2, etc.
# I want the initial bid prices, so the earliest OFFERDATE for each (SETTLEMENTDATE, DUID, BIDTYPE) combination.
# Then plot these distributions using histograms or box plots to visualize differences between bidder categories.

import matplotlib.pyplot as plt

# Filter for FCAS bids only (exclude ENERGY)
fcas_df = merged_df[merged_df['BIDTYPE'] != 'ENERGY'].copy()

# Get initial bids: earliest OFFERDATE for each (SETTLEMENTDATE, DUID, BIDTYPE) combination
fcas_df['OFFERDATE'] = pd.to_datetime(fcas_df['OFFERDATE'])
initial_bids = fcas_df.loc[fcas_df.groupby(['SETTLEMENTDATE', 'DUID', 'BIDTYPE'])['OFFERDATE'].idxmin()]

# Melt price bands into long format for easier plotting
price_bands = ['PRICEBAND1', 'PRICEBAND2', 'PRICEBAND3', 'PRICEBAND4', 'PRICEBAND5',
               'PRICEBAND6', 'PRICEBAND7', 'PRICEBAND8', 'PRICEBAND9', 'PRICEBAND10']
initial_bids_melted = initial_bids.melt(
    id_vars=['BIDDER_CATEGORY', 'BIDTYPE', 'DUID', 'SETTLEMENTDATE'],
    value_vars=price_bands,
    var_name='PRICEBAND',
    value_name='PRICE'
)

# Get unique FCAS types
fcas_types = sorted(initial_bids['BIDTYPE'].unique())
bidder_categories = ['Autobidder Battery', 'Non-Autobidder Battery', 'Non-Battery']
category_colors = ['#1f77b4', '#ff7f0e', '#2ca02c']  # Blue, Orange, Green

# Create one figure per FCAS type with all 10 price bands
for fcas_type in fcas_types:
    fig, ax = plt.subplots(figsize=(14, 6))
    fcas_data = initial_bids_melted[initial_bids_melted['BIDTYPE'] == fcas_type]

    positions = []
    box_data = []
    colors = []

    # For each price band, create grouped box plots for the 3 categories
    for i, band in enumerate(price_bands):
        band_data = fcas_data[fcas_data['PRICEBAND'] == band]
        base_pos = i * 4  # Space between band groups

        for j, cat in enumerate(bidder_categories):
            cat_prices = band_data[band_data['BIDDER_CATEGORY'] == cat]['PRICE'].dropna()
            if len(cat_prices) > 0:
                box_data.append(cat_prices)
                positions.append(base_pos + j)
                colors.append(category_colors[j])

    # Create box plots
    if box_data:
        bp = ax.boxplot(box_data, positions=positions, widths=0.8, patch_artist=True)

        # Color the boxes
        for patch, color in zip(bp['boxes'], colors):
            patch.set_facecolor(color)
            patch.set_alpha(0.7)

    # Set x-axis labels
    band_centers = [i * 4 + 1 for i in range(len(price_bands))]
    ax.set_xticks(band_centers)
    ax.set_xticklabels([f'PB{i+1}' for i in range(len(price_bands))])

    # Add legend
    legend_patches = [plt.Line2D([0], [0], color=c, linewidth=10, alpha=0.7)
                      for c in category_colors]
    ax.legend(legend_patches, bidder_categories, loc='upper left')

    ax.set_title(f'{fcas_type} - Initial Bid Price Distribution by Price Band')
    ax.set_xlabel('Price Band')
    ax.set_ylabel('Price ($/MWh)')
    ax.grid(axis='y', alpha=0.3)

    plt.tight_layout()
    plt.savefig(FIGURES_DIR / f'fcas_price_{fcas_type}.png', dpi=150, bbox_inches='tight')
    plt.close()

print("\nBox plots saved to 'figures/fcas_price_<BIDTYPE>.png' for each FCAS type")

# Second version: Only batteries (exclude Non-Battery) and only price bands 1-8
battery_categories = ['Autobidder Battery', 'Non-Autobidder Battery']
battery_colors = ['#1f77b4', '#ff7f0e']  # Blue, Orange
price_bands_1_8 = ['PRICEBAND1', 'PRICEBAND2', 'PRICEBAND3', 'PRICEBAND4',
                   'PRICEBAND5', 'PRICEBAND6', 'PRICEBAND7', 'PRICEBAND8']

# Filter for batteries only
battery_bids_melted = initial_bids_melted[initial_bids_melted['BIDDER_CATEGORY'].isin(battery_categories)]
battery_bids_melted = battery_bids_melted[battery_bids_melted['PRICEBAND'].isin(price_bands_1_8)]

for fcas_type in fcas_types:
    fig, ax = plt.subplots(figsize=(12, 6))
    fcas_data = battery_bids_melted[battery_bids_melted['BIDTYPE'] == fcas_type]

    positions = []
    box_data = []
    colors = []

    # For each price band, create grouped box plots for the 2 battery categories
    for i, band in enumerate(price_bands_1_8):
        band_data = fcas_data[fcas_data['PRICEBAND'] == band]
        base_pos = i * 3  # Space between band groups

        for j, cat in enumerate(battery_categories):
            cat_prices = band_data[band_data['BIDDER_CATEGORY'] == cat]['PRICE'].dropna()
            if len(cat_prices) > 0:
                box_data.append(cat_prices)
                positions.append(base_pos + j)
                colors.append(battery_colors[j])

    # Create box plots
    if box_data:
        bp = ax.boxplot(box_data, positions=positions, widths=0.8, patch_artist=True)

        # Color the boxes
        for patch, color in zip(bp['boxes'], colors):
            patch.set_facecolor(color)
            patch.set_alpha(0.7)

    # Set x-axis labels
    band_centers = [i * 3 + 0.5 for i in range(len(price_bands_1_8))]
    ax.set_xticks(band_centers)
    ax.set_xticklabels([f'PB{i+1}' for i in range(len(price_bands_1_8))])

    # Add legend
    legend_patches = [plt.Line2D([0], [0], color=c, linewidth=10, alpha=0.7)
                      for c in battery_colors]
    ax.legend(legend_patches, battery_categories, loc='upper left')

    ax.set_title(f'{fcas_type} - Battery Only (PB1-8)')
    ax.set_xlabel('Price Band')
    ax.set_ylabel('Price ($/MWh)')
    ax.grid(axis='y', alpha=0.3)

    plt.tight_layout()
    plt.savefig(FIGURES_DIR / f'batteries_fcas_price_{fcas_type}.png', dpi=150, bbox_inches='tight')
    plt.close()

print("Battery-only plots saved to 'figures/batteries_fcas_price_<BIDTYPE>.png'")

# Third version: Only batteries and only price bands 1-5
price_bands_1_5 = ['PRICEBAND1', 'PRICEBAND2', 'PRICEBAND3', 'PRICEBAND4', 'PRICEBAND5']

# Filter for batteries only and PB1-5
battery_bids_melted_1_5 = initial_bids_melted[initial_bids_melted['BIDDER_CATEGORY'].isin(battery_categories)]
battery_bids_melted_1_5 = battery_bids_melted_1_5[battery_bids_melted_1_5['PRICEBAND'].isin(price_bands_1_5)]

for fcas_type in fcas_types:
    fig, ax = plt.subplots(figsize=(10, 6))
    fcas_data = battery_bids_melted_1_5[battery_bids_melted_1_5['BIDTYPE'] == fcas_type]

    positions = []
    box_data = []
    colors = []

    # For each price band, create grouped box plots for the 2 battery categories
    for i, band in enumerate(price_bands_1_5):
        band_data = fcas_data[fcas_data['PRICEBAND'] == band]
        base_pos = i * 3  # Space between band groups

        for j, cat in enumerate(battery_categories):
            cat_prices = band_data[band_data['BIDDER_CATEGORY'] == cat]['PRICE'].dropna()
            if len(cat_prices) > 0:
                box_data.append(cat_prices)
                positions.append(base_pos + j)
                colors.append(battery_colors[j])

    # Create box plots
    if box_data:
        bp = ax.boxplot(box_data, positions=positions, widths=0.8, patch_artist=True)

        # Color the boxes
        for patch, color in zip(bp['boxes'], colors):
            patch.set_facecolor(color)
            patch.set_alpha(0.7)

    # Set x-axis labels
    band_centers = [i * 3 + 0.5 for i in range(len(price_bands_1_5))]
    ax.set_xticks(band_centers)
    ax.set_xticklabels([f'PB{i+1}' for i in range(len(price_bands_1_5))])

    # Add legend
    legend_patches = [plt.Line2D([0], [0], color=c, linewidth=10, alpha=0.7)
                      for c in battery_colors]
    ax.legend(legend_patches, battery_categories, loc='upper left')

    ax.set_title(f'{fcas_type} - Battery Only (PB1-5)')
    ax.set_xlabel('Price Band')
    ax.set_ylabel('Price ($/MWh)')
    ax.grid(axis='y', alpha=0.3)

    plt.tight_layout()
    plt.savefig(FIGURES_DIR / f'batteries_pb5_fcas_price_{fcas_type}.png', dpi=150, bbox_inches='tight')
    plt.close()

print("Battery-only PB1-5 plots saved to 'figures/batteries_pb5_fcas_price_<BIDTYPE>.png'")

# Also print summary statistics for each category and FCAS type
print("\n\nSummary Statistics for Initial Bid Prices by Category and FCAS Type:")
print("=" * 80)

for cat in bidder_categories:
    print(f"\n{cat}:")
    print("-" * 40)
    cat_data = initial_bids[initial_bids['BIDDER_CATEGORY'] == cat]

    for fcas_type in fcas_types:
        fcas_data = cat_data[cat_data['BIDTYPE'] == fcas_type]
        if len(fcas_data) > 0:
            print(f"\n  {fcas_type} (n={len(fcas_data)}):")
            for band in price_bands:
                prices = fcas_data[band].dropna()
                if len(prices) > 0:
                    print(f"    {band}: median={prices.median():.2f}, mean={prices.mean():.2f}, std={prices.std():.2f}")

# Create summary tables of mean and median price bands across the 3 groups
print("\n\n" + "=" * 100)
print("SUMMARY TABLE: Mean and Median Price Bands by Bidder Category (All FCAS)")
print("=" * 100)

# Calculate mean and median for each category and price band (aggregated across all FCAS types)
all_categories = ['Autobidder Battery', 'Non-Autobidder Battery', 'Non-Battery']

# Build summary dataframes
mean_data = []
median_data = []

for cat in all_categories:
    cat_data = initial_bids[initial_bids['BIDDER_CATEGORY'] == cat]
    mean_row = {'Category': cat}
    median_row = {'Category': cat}

    for band in price_bands:
        prices = cat_data[band].dropna()
        if len(prices) > 0:
            mean_row[band.replace('PRICEBAND', 'PB')] = prices.mean()
            median_row[band.replace('PRICEBAND', 'PB')] = prices.median()
        else:
            mean_row[band.replace('PRICEBAND', 'PB')] = None
            median_row[band.replace('PRICEBAND', 'PB')] = None

    mean_data.append(mean_row)
    median_data.append(median_row)

mean_df = pd.DataFrame(mean_data).set_index('Category')
median_df = pd.DataFrame(median_data).set_index('Category')

print("\nMean Price by Band:")
print(mean_df.round(2).to_string())

print("\n\nMedian Price by Band:")
print(median_df.round(2).to_string())

# Also create per-FCAS type summary tables
print("\n\n" + "=" * 100)
print("SUMMARY TABLE: Mean Price Bands by Bidder Category (Per FCAS Type)")
print("=" * 100)

for fcas_type in fcas_types:
    print(f"\n{fcas_type}:")
    fcas_mean_data = []

    for cat in all_categories:
        cat_fcas_data = initial_bids[(initial_bids['BIDDER_CATEGORY'] == cat) &
                                      (initial_bids['BIDTYPE'] == fcas_type)]
        row = {'Category': cat}

        for band in price_bands:
            prices = cat_fcas_data[band].dropna()
            if len(prices) > 0:
                row[band.replace('PRICEBAND', 'PB')] = prices.mean()
            else:
                row[band.replace('PRICEBAND', 'PB')] = None

        fcas_mean_data.append(row)

    fcas_mean_df = pd.DataFrame(fcas_mean_data).set_index('Category')
    print(fcas_mean_df.round(2).to_string())

# =============================================================================
# PRICE CHANGE ANALYSIS: Final Price - Initial Price
# =============================================================================
print("\n\n" + "=" * 100)
print("PRICE CHANGE ANALYSIS: Change from Initial to Final Bid")
print("=" * 100)

# Get final bids: latest OFFERDATE for each (SETTLEMENTDATE, DUID, BIDTYPE) combination
final_bids = fcas_df.loc[fcas_df.groupby(['SETTLEMENTDATE', 'DUID', 'BIDTYPE'])['OFFERDATE'].idxmax()]

# Merge initial and final bids to calculate price changes
initial_for_merge = initial_bids[['SETTLEMENTDATE', 'DUID', 'BIDTYPE', 'BIDDER_CATEGORY'] + price_bands].copy()
final_for_merge = final_bids[['SETTLEMENTDATE', 'DUID', 'BIDTYPE'] + price_bands].copy()

# Rename price band columns for final bids
final_for_merge = final_for_merge.rename(columns={band: f'{band}_FINAL' for band in price_bands})

# Merge on auction identifiers
price_change_df = initial_for_merge.merge(final_for_merge, on=['SETTLEMENTDATE', 'DUID', 'BIDTYPE'])

# Calculate price changes for each band
for band in price_bands:
    price_change_df[f'{band}_CHANGE'] = price_change_df[f'{band}_FINAL'] - price_change_df[band]

# Melt price changes into long format for plotting
change_cols = [f'{band}_CHANGE' for band in price_bands]
price_change_melted = price_change_df.melt(
    id_vars=['BIDDER_CATEGORY', 'BIDTYPE', 'DUID', 'SETTLEMENTDATE'],
    value_vars=change_cols,
    var_name='PRICEBAND',
    value_name='PRICE_CHANGE'
)
# Clean up PRICEBAND names
price_change_melted['PRICEBAND'] = price_change_melted['PRICEBAND'].str.replace('_CHANGE', '')

# =============================================================================
# BAR CHARTS FOR MEDIAN PRICE CHANGES
# =============================================================================

import numpy as np

# Version 1: All 3 categories, all 10 price bands
for fcas_type in fcas_types:
    fig, ax = plt.subplots(figsize=(14, 6))
    fcas_data = price_change_melted[price_change_melted['BIDTYPE'] == fcas_type]

    x = np.arange(len(price_bands))
    width = 0.25

    for j, cat in enumerate(all_categories):
        medians = []
        for band in price_bands:
            band_data = fcas_data[(fcas_data['PRICEBAND'] == band) &
                                   (fcas_data['BIDDER_CATEGORY'] == cat)]['PRICE_CHANGE'].dropna()
            medians.append(band_data.median() if len(band_data) > 0 else 0)

        ax.bar(x + j * width, medians, width, label=cat, color=category_colors[j], alpha=0.7)

    ax.set_xticks(x + width)
    ax.set_xticklabels([f'PB{i+1}' for i in range(len(price_bands))])
    ax.axhline(y=0, color='red', linestyle='--', alpha=0.5)
    ax.legend(loc='upper left')

    ax.set_title(f'{fcas_type} - Median Price Change (Final - Initial) by Price Band')
    ax.set_xlabel('Price Band')
    ax.set_ylabel('Median Price Change ($/MWh)')
    ax.grid(axis='y', alpha=0.3)

    plt.tight_layout()
    plt.savefig(FIGURES_DIR / f'price_change_{fcas_type}.png', dpi=150, bbox_inches='tight')
    plt.close()

print("\nPrice change bar charts saved to 'figures/price_change_<BIDTYPE>.png'")

# Version 2: Batteries only, PB1-8
for fcas_type in fcas_types:
    fig, ax = plt.subplots(figsize=(12, 6))
    fcas_data = price_change_melted[(price_change_melted['BIDTYPE'] == fcas_type) &
                                     (price_change_melted['BIDDER_CATEGORY'].isin(battery_categories)) &
                                     (price_change_melted['PRICEBAND'].isin(price_bands_1_8))]

    x = np.arange(len(price_bands_1_8))
    width = 0.35

    for j, cat in enumerate(battery_categories):
        medians = []
        for band in price_bands_1_8:
            band_data = fcas_data[(fcas_data['PRICEBAND'] == band) &
                                   (fcas_data['BIDDER_CATEGORY'] == cat)]['PRICE_CHANGE'].dropna()
            medians.append(band_data.median() if len(band_data) > 0 else 0)

        ax.bar(x + j * width, medians, width, label=cat, color=battery_colors[j], alpha=0.7)

    ax.set_xticks(x + width / 2)
    ax.set_xticklabels([f'PB{i+1}' for i in range(len(price_bands_1_8))])
    ax.axhline(y=0, color='red', linestyle='--', alpha=0.5)
    ax.legend(loc='upper left')

    ax.set_title(f'{fcas_type} - Battery Only Median Price Change (PB1-8)')
    ax.set_xlabel('Price Band')
    ax.set_ylabel('Median Price Change ($/MWh)')
    ax.grid(axis='y', alpha=0.3)

    plt.tight_layout()
    plt.savefig(FIGURES_DIR / f'price_change_batteries_{fcas_type}.png', dpi=150, bbox_inches='tight')
    plt.close()

print("Battery-only price change bar charts saved to 'figures/price_change_batteries_<BIDTYPE>.png'")

# Version 3: Batteries only, PB1-5
for fcas_type in fcas_types:
    fig, ax = plt.subplots(figsize=(10, 6))
    fcas_data = price_change_melted[(price_change_melted['BIDTYPE'] == fcas_type) &
                                     (price_change_melted['BIDDER_CATEGORY'].isin(battery_categories)) &
                                     (price_change_melted['PRICEBAND'].isin(price_bands_1_5))]

    x = np.arange(len(price_bands_1_5))
    width = 0.35

    for j, cat in enumerate(battery_categories):
        medians = []
        for band in price_bands_1_5:
            band_data = fcas_data[(fcas_data['PRICEBAND'] == band) &
                                   (fcas_data['BIDDER_CATEGORY'] == cat)]['PRICE_CHANGE'].dropna()
            medians.append(band_data.median() if len(band_data) > 0 else 0)

        ax.bar(x + j * width, medians, width, label=cat, color=battery_colors[j], alpha=0.7)

    ax.set_xticks(x + width / 2)
    ax.set_xticklabels([f'PB{i+1}' for i in range(len(price_bands_1_5))])
    ax.axhline(y=0, color='red', linestyle='--', alpha=0.5)
    ax.legend(loc='upper left')

    ax.set_title(f'{fcas_type} - Battery Only Median Price Change (PB1-5)')
    ax.set_xlabel('Price Band')
    ax.set_ylabel('Median Price Change ($/MWh)')
    ax.grid(axis='y', alpha=0.3)

    plt.tight_layout()
    plt.savefig(FIGURES_DIR / f'price_change_batteries_pb5_{fcas_type}.png', dpi=150, bbox_inches='tight')
    plt.close()

print("Battery-only PB1-5 price change bar charts saved to 'figures/price_change_batteries_pb5_<BIDTYPE>.png'")

# =============================================================================
# SUMMARY TABLES FOR PRICE CHANGES
# =============================================================================
print("\n\n" + "=" * 100)
print("SUMMARY TABLE: Mean and Median Price Change by Bidder Category (All FCAS)")
print("=" * 100)

# Build summary dataframes for price changes
change_cols_clean = [f'{band}_CHANGE' for band in price_bands]
mean_change_data = []
median_change_data = []

for cat in all_categories:
    cat_data = price_change_df[price_change_df['BIDDER_CATEGORY'] == cat]
    mean_row = {'Category': cat}
    median_row = {'Category': cat}

    for band in price_bands:
        change_col = f'{band}_CHANGE'
        changes = cat_data[change_col].dropna()
        if len(changes) > 0:
            mean_row[band.replace('PRICEBAND', 'PB')] = changes.mean()
            median_row[band.replace('PRICEBAND', 'PB')] = changes.median()
        else:
            mean_row[band.replace('PRICEBAND', 'PB')] = None
            median_row[band.replace('PRICEBAND', 'PB')] = None

    mean_change_data.append(mean_row)
    median_change_data.append(median_row)

mean_change_df = pd.DataFrame(mean_change_data).set_index('Category')
median_change_df = pd.DataFrame(median_change_data).set_index('Category')

print("\nMean Price Change by Band:")
print(mean_change_df.round(2).to_string())

print("\n\nMedian Price Change by Band:")
print(median_change_df.round(2).to_string())

# Per-FCAS type summary tables for price changes
print("\n\n" + "=" * 100)
print("SUMMARY TABLE: Mean Price Change by Bidder Category (Per FCAS Type)")
print("=" * 100)

for fcas_type in fcas_types:
    print(f"\n{fcas_type}:")
    fcas_mean_change_data = []

    for cat in all_categories:
        cat_fcas_data = price_change_df[(price_change_df['BIDDER_CATEGORY'] == cat) &
                                         (price_change_df['BIDTYPE'] == fcas_type)]
        row = {'Category': cat}

        for band in price_bands:
            change_col = f'{band}_CHANGE'
            changes = cat_fcas_data[change_col].dropna()
            if len(changes) > 0:
                row[band.replace('PRICEBAND', 'PB')] = changes.mean()
            else:
                row[band.replace('PRICEBAND', 'PB')] = None

        fcas_mean_change_data.append(row)

    fcas_mean_change_df = pd.DataFrame(fcas_mean_change_data).set_index('Category')
    print(fcas_mean_change_df.round(2).to_string())
