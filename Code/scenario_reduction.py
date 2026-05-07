#!/usr/bin/env python
# coding: utf-8

# In[1]:


import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
import os 
plots_dir = os.path.join(os.getcwd(), 'Plots')
os.makedirs(plots_dir, exist_ok=True)


# In[2]:


# Import montecarlo simulation results

# Load Data for simulation 

num_scenarios = 100000
time_horizon = 20 #  5,10,20
contract_type = 'Baseload'  # Baseload ,PAP

# Load scenarios from CSV files
scenario_pattern = f"{{type}}_scenarios_{time_horizon}y_{num_scenarios}s.csv"

# Load price scenarios
prices_df = pd.read_csv(f"scenarios/{scenario_pattern.format(type='price')}", index_col=0) # Mio EUR/GWh
prices_df.index = pd.to_datetime(prices_df.index)   

prices_mwh = prices_df * 1000  # Convert from EUR/GWh to EUR/MWh

#prices_mwh = prices_mwh + 0.01*prices_mwh.mean().mean()

# Load production scenarios
prod_df = pd.read_csv(f"scenarios/{scenario_pattern.format(type='production')}", index_col=0) # GWh
prod_df.index = pd.to_datetime(prod_df.index)

# Load capture rate scenarios
CR_df = pd.read_csv(f"scenarios/{scenario_pattern.format(type='capture_rate')}", index_col=0)
CR_df.index = pd.to_datetime(CR_df.index)    # Load load scenarios
load_df = pd.read_csv(f"scenarios/{scenario_pattern.format(type='load')}", index_col=0) # GWh
load_df.index = pd.to_datetime(load_df.index)

LR_df = pd.read_csv(f"scenarios/{scenario_pattern.format(type='load_capture_rate')}", index_col=0) # %
LR_df.index = pd.to_datetime(LR_df.index)


# Make P5-P95 Interval of prices
p1 = np.percentile(prices_df.sum(axis=0), 1)
p99 = np.percentile(prices_df.sum(axis=0), 99)
prices_aggregated = prices_df.sum(axis=0)  # Aggregate prices over all scenarios
scenarios_use = prices_aggregated[(prices_aggregated >= p1) & (prices_aggregated <= p99)]
# Filter prices within the P5-P95 range
old_shape = prices_df.shape[1]

test_net_earnings_no_contract_G = (prices_df * prod_df * CR_df) # Mio EUR
lower = prices_df.quantile(0.01, axis=1)  # per-row across scenarios
upper = prices_df.quantile(0.99, axis=1)

within_bounds = prices_df.ge(lower, axis=0) & prices_df.le(upper, axis=0)
scenarios_mask = within_bounds.all(axis=0) & prices_df.notna().all(axis=0)  # treat NaN as violation
cols_keep = scenarios_mask.index[scenarios_mask]

prices_df = prices_df[cols_keep]
prod_df = prod_df[cols_keep]
CR_df = CR_df[cols_keep]
load_df = load_df[cols_keep]
LR_df = LR_df[cols_keep]
prices_mwh = prices_mwh[cols_keep]

print(f"Kept {len(cols_keep)} scenarios, removed {old_shape - len(cols_keep)}.")


# In[3]:


k_clusters = 500  #

# Sample all variables (keep this for extracting representative scenarios later)
prices_sample = prices_df.values.T     # Shape: (scenarios, T)
prod_sample = prod_df.values.T          # Shape: (scenarios, T)
CR_sample = CR_df.values.T              # Shape: (scenarios, T)
consumption_sample = load_df.values.T   # Shape: (scenarios, T)
LR_sample = LR_df.values.T              # Shape: (scenarios, T)

# CORRECTED: Calculate annual revenues as per methodology
pi_G_annual = np.sum(prices_sample * prod_sample * CR_sample, axis=1)      # Shape: (scenarios,)
pi_L_annual = np.sum(-prices_sample * consumption_sample * LR_sample, axis=1)  # Shape: (scenarios,)

# Create 2D feature space as described in methodology
feature_space = np.column_stack([pi_G_annual, pi_L_annual])  # Shape: (scenarios, 2)

# Standardize the 2D revenue data
scaler = StandardScaler()
feature_space_scaled = scaler.fit_transform(feature_space)

print(f"2D Revenue Space Clustering: {num_scenarios} scenarios into {k_clusters} clusters")
print(f"Feature space shape: {feature_space.shape}")
print(f"Features: Generator Revenue (π^G) and Load Cost (π^L)")

# CORRECTED: Print scale information for revenues, not raw variables
print(f"\nRevenue scale analysis before standardization:")
print(f"Generator Revenue (π^G) - Mean: {np.mean(pi_G_annual):.2f}, Std: {np.std(pi_G_annual):.2f}")
print(f"                        Range: [{np.min(pi_G_annual):.2f}, {np.max(pi_G_annual):.2f}]")
print(f"Load Cost (π^L) - Mean: {np.mean(pi_L_annual):.2f}, Std: {np.std(pi_L_annual):.2f}")
print(f"                  Range: [{np.min(pi_L_annual):.2f}, {np.max(pi_L_annual):.2f}]")

# Apply K-means clustering on standardized 2D revenue space
kmeans = KMeans(n_clusters=k_clusters, random_state=42, n_init=10, init='k-means++')
labels = kmeans.fit_predict(feature_space_scaled)
centroids = kmeans.cluster_centers_

# Calculate probabilities for each cluster
unique_labels, counts = np.unique(labels, return_counts=True)
probabilities = counts / len(labels)

print(f"\nCluster Statistics:")
print(f"Number of non-empty clusters: {len(unique_labels)}")
print(f"Cluster size range: [{np.min(counts)}, {np.max(counts)}] scenarios")
print(f"Probability range: [{np.min(probabilities):.6f}, {np.max(probabilities):.6f}]")
print(f"Total probability sum: {np.sum(probabilities):.6f}")

# Find representative scenarios (closest actual scenarios to each centroid)
representative_scenarios = []
representative_probabilities = []

for cluster_id in range(k_clusters):
    # Get all scenarios in this cluster
    cluster_mask = labels == cluster_id
    cluster_indices = np.where(cluster_mask)[0]
    
    # Skip empty clusters
    if len(cluster_indices) == 0:
        print(f"Warning: Cluster {cluster_id} is empty")
        continue
        
    cluster_data_scaled = feature_space_scaled[cluster_mask]
    centroid = centroids[cluster_id]
    
    # Find closest actual scenario to centroid in scaled revenue space
    distances = np.linalg.norm(cluster_data_scaled - centroid, axis=1)
    closest_local_idx = np.argmin(distances)
    closest_global_idx = cluster_indices[closest_local_idx]
    
    representative_scenarios.append(closest_global_idx)
    representative_probabilities.append(len(cluster_indices) / feature_space_scaled.shape[0])

representative_scenarios = np.array(representative_scenarios)
representative_probabilities = np.array(representative_probabilities)

# Extract representative data for all variables using the selected scenarios
repr_prices = prices_sample[representative_scenarios]
repr_prod = prod_sample[representative_scenarios]
repr_CR = CR_sample[representative_scenarios]
repr_consumption = consumption_sample[representative_scenarios]
repr_LR = LR_sample[representative_scenarios]

# Calculate net earnings for representative scenarios (time-series preserved)
repr_net_earnings_G = repr_prices * repr_prod * repr_CR
repr_net_earnings_L = -repr_prices * repr_consumption * repr_LR

# Verify revenue consistency with original clustering space
repr_pi_G_annual = np.sum(repr_net_earnings_G, axis=1)
repr_pi_L_annual = np.sum(repr_net_earnings_L, axis=1)

print(f"\nRepresentative Scenarios Extracted:")
print(f"Number of representative scenarios: {len(representative_scenarios)}")
print(f"Representative probabilities sum: {np.sum(representative_probabilities):.6f}")
print(f"Generator revenue range: [{np.min(repr_pi_G_annual):.2f}, {np.max(repr_pi_G_annual):.2f}]")
print(f"Load cost range: [{np.min(repr_pi_L_annual):.2f}, {np.max(repr_pi_L_annual):.2f}]")

# VERIFICATION: Check that revenue space is preserved
print(f"\nRevenue Space Verification:")
print(f"Original revenue space coverage:")
print(f"  Generator: [{np.min(pi_G_annual):.2f}, {np.max(pi_G_annual):.2f}]")
print(f"  Load: [{np.min(pi_L_annual):.2f}, {np.max(pi_L_annual):.2f}]")
print(f"Representative revenue space coverage:")
print(f"  Generator: [{np.min(repr_pi_G_annual):.2f}, {np.max(repr_pi_G_annual):.2f}]")
print(f"  Load: [{np.min(repr_pi_L_annual):.2f}, {np.max(repr_pi_L_annual):.2f}]")


# In[ ]:





# In[6]:


from scipy.spatial.distance import cdist
from sklearn import metrics

inertias = []
distortions = []
clusters = np.array([4000,5000,6000]).astype(int) # Define specific cluster sizes to test
for k in clusters:
    kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
    kmeans.fit(feature_space_scaled)
    inertias.append(kmeans.inertia_)
    distortions.append(sum(np.min(cdist(feature_space_scaled, kmeans.cluster_centers_, 'euclidean'), axis=1)**2) / feature_space_scaled.shape[0])

plt.figure(figsize=(8, 5))
plt.plot(range(1, len(clusters) + 1), inertias, marker='o')
plt.xlabel('Number of clusters')
plt.ylabel('Inertia (Sum of squared distances)')
plt.title('Elbow Method for Optimal k')
plt.grid(True)
plt.show()

plt.figure(figsize=(8, 5))
plt.plot(range(1, len(clusters) + 1), distortions, marker='o')
plt.xlabel('Number of clusters')
plt.ylabel('Distortion (Average distance to closest centroid)')
plt.title('Distortion for Optimal k')   
plt.grid(True)
plt.show()


# In[4]:


centroids_original = scaler.inverse_transform(centroids)


original_weights = np.ones(len(pi_G_annual))/len(pi_G_annual)
plt.figure(figsize=(16, 12))
# 1. Generator Annual Revenue comparison
plt.subplot(2, 2, 1)
plt.hist(pi_G_annual, weights=original_weights, bins=50, alpha=0.6, label='Original', color='blue', density=True)
plt.hist(repr_pi_G_annual,weights=representative_probabilities, bins=30, alpha=0.8, label='Representative', color='orange', density=True)
plt.hist(centroids_original[:, 0],weights=probabilities, bins=30, alpha=0.5, label='Centroids', color='purple', density=True)

plt.xlabel('Annual Generator Revenue (Mio EUR)')
plt.ylabel('Probability Density')
plt.title('Generator Revenue Distribution')
plt.legend()
plt.grid(True, alpha=0.3)

# 2. Load Annual Cost comparison
plt.subplot(2, 2, 2)
plt.hist(pi_L_annual,weights = original_weights, bins=50, alpha=0.6, label='Original', color='blue', density=True)
plt.hist(repr_pi_L_annual,weights=representative_probabilities, bins=30, alpha=0.8, label='Representative', color='red', density=True)
plt.hist(centroids_original[:, 1],weights=probabilities, bins=30, alpha=0.5, label='Centroids', color='purple', density=True)
plt.xlabel('Annual Load Cost (Mio EUR)')
plt.ylabel('Probability Density')
plt.title('Load Cost Distribution')
plt.legend()
plt.grid(True, alpha=0.3)

# 3. 2D Revenue Space Scatter Plot
plt.subplot(2, 2, 3)
# Plot original scenarios as background
plt.scatter(pi_G_annual, pi_L_annual, alpha=0.3, s=10, color='lightblue', label='Original Scenarios')
# Plot representative scenarios
plt.scatter(repr_pi_G_annual, repr_pi_L_annual, 
           s=representative_probabilities*2000, # Size proportional to probability
           alpha=0.8, color='red', edgecolors='black', linewidth=1,
           label='Representative Scenarios')
plt.xlabel('Generator Revenue (Mio EUR)')
plt.ylabel('Load Cost (Mio EUR)')
plt.title('Load vs Revenue')
plt.legend()
plt.grid(True, alpha=0.3)


# 5. Box plot comparison (Annual Revenues)
plt.subplot(2, 2, 4)
data_to_plot = [pi_G_annual, repr_pi_G_annual, pi_L_annual, repr_pi_L_annual]
labels_box = ['G-Original', 'G-Representative', 'L-Original', 'L-Representative']
colors_box = ['lightblue', 'orange', 'lightcoral', 'red']

box_plot = plt.boxplot(data_to_plot, labels=labels_box, patch_artist=True)
for patch, color in zip(box_plot['boxes'], colors_box):
    patch.set_facecolor(color)
    patch.set_alpha(0.7)

plt.xticks(rotation=45)
plt.ylabel('Annual Revenue/Cost (Mio EUR)')
plt.title('Revenue Distribution Comparison')
plt.grid(True, alpha=0.3)



plt.tight_layout()
plt.show()


# In[7]:


# Save joint clustering results: scenarios and probabilities

# Create time index matching original data
time_index = prices_df.index

# Create directory for reduced scenarios
reduced_dir = 'scenarios'
os.makedirs(reduced_dir, exist_ok=True)

# Define pattern for reduced scenario files
reduced_scenario_pattern = f"{{type}}_scenarios_reduced_{time_horizon}y_{k_clusters}s.csv"

print("Saving joint clustering results in original format...")

# 1. Save reduced price scenarios (consistent for both G and L)
reduced_prices_df = pd.DataFrame(
    repr_prices.T,  # Transpose to get (time, scenarios) format like original
    index=time_index,
    columns=[f'Scenario_{i+1}' for i in range(len(representative_scenarios))]
)
reduced_prices_df.to_csv(f"scenarios/{reduced_scenario_pattern.format(type='price')}")

# 2. Save reduced production scenarios (Generator)
reduced_prod_df = pd.DataFrame(
    repr_prod.T,  # Transpose to get (time, scenarios) format
    index=time_index,
    columns=[f'Scenario_{i+1}' for i in range(len(representative_scenarios))]
)
reduced_prod_df.to_csv(f"scenarios/{reduced_scenario_pattern.format(type='production')}")

# 3. Save reduced capture rate scenarios (Generator)
reduced_CR_df = pd.DataFrame(
    repr_CR.T,  # Transpose to get (time, scenarios) format
    index=time_index,
    columns=[f'Scenario_{i+1}' for i in range(len(representative_scenarios))]
)
reduced_CR_df.to_csv(f"scenarios/{reduced_scenario_pattern.format(type='capture_rate')}")

# 4. Save reduced load scenarios
reduced_load_df = pd.DataFrame(
    repr_consumption.T,  # Transpose to get (time, scenarios) format
    index=time_index,
    columns=[f'Scenario_{i+1}' for i in range(len(representative_scenarios))]
)
reduced_load_df.to_csv(f"scenarios/{reduced_scenario_pattern.format(type='load')}")

# 5. Save reduced load capture rate scenarios
reduced_LR_df = pd.DataFrame(
    repr_LR.T,  # Transpose to get (time, scenarios) format
    index=time_index,
    columns=[f'Scenario_{i+1}' for i in range(len(representative_scenarios))]
)
reduced_LR_df.to_csv(f"scenarios/{reduced_scenario_pattern.format(type='load_capture_rate')}")

# 6. Save scenario probabilities as CSV
probabilities_df =  pd.DataFrame({
    'Centroid_ID': [f'Centroid_{i+1}' for i in range(len(unique_labels))],
    'Probability': representative_probabilities
})

# Save probabilities
prob_filename = f"scenarios/scenario_probabilities_{time_horizon}y_{k_clusters}s.csv"
probabilities_df.to_csv(f"scenarios/{reduced_scenario_pattern.format(type='probabilities')}", index=False)

print(f"Joint clustering results saved:")
print(f"  - {reduced_scenario_pattern.format(type='price')}")
print(f"  - {reduced_scenario_pattern.format(type='production')}")
print(f"  - {reduced_scenario_pattern.format(type='capture_rate')}")
print(f"  - {reduced_scenario_pattern.format(type='load')}")
print(f"  - {reduced_scenario_pattern.format(type='load_capture_rate')}")
print(f"  -  {reduced_scenario_pattern.format(type='probabilities')}")


# In[ ]:




