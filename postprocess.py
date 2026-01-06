import os, glob
import numpy as np
import pandas as pd
import networkx as nx

""" Finds instances where calls start or end at the same time, and groups these in start-groups or end-groups """
def assign_groups(g, threshold):
    g = g.copy()

    # Assign group number to calls that start at the same time 
    gs = g.sort_values('start_time_ms')
    diffs = gs['start_time_ms'].diff().fillna(threshold + 1)  # first row always new group
    start_ids = (diffs > threshold).cumsum()
    g.loc[gs.index, 'start_group'] = ['S' + str(i) for i in start_ids]

    # Assign group number to calls that end at the same time 
    ge = g.sort_values('end_time_ms')
    diffs2 = ge['end_time_ms'].diff().fillna(threshold + 1)
    end_ids = (diffs2 > threshold).cumsum()
    g.loc[ge.index, 'end_group'] = ['E' + str(i) for i in end_ids]

    return g

""" Merges calls that start or end at the same time by linking start and end times using graph theory """
def merge_via_graph(g):
    G = nx.Graph()
    edges = list(zip(g['start_group'], g['end_group']))
    G.add_edges_from(edges)
    comp_map = {}
    for cid, comp in enumerate(nx.connected_components(G), start=1):
        for node in comp:
            comp_map[node] = cid # assigns group nr to linked nodes (starts and ends of calls that start or end at the same time)
    g['group_nr'] = g['start_group'].map(comp_map)
    return g

""" Finds calls (within the same category and file) that start or end at the same time and merges these """
def overlap_tidy(df, threshold=5):
    df = df.copy()

    # Only keep Feeding buzz and Social call categories
    df = df[df['category'] != "Other"]

    # Check if calls (within a file and the same category) start or end at the same time and assign these to the same group number  
    df_out = []
    counter = 1
    for (fname, cat), g in df.groupby(['filename', 'category'], group_keys=False):
        g2 = assign_groups(g, threshold)
        g3 = merge_via_graph(g2)
        g2['filename'] = fname
        g2['category'] = cat
        df_out.append(g3)
    df = pd.concat(df_out, ignore_index=True)

    # When calls start or end at the same time, take the one with the highest confidence
    df_out = []
    for (fname, cat, group_nr), g in df.groupby(['filename', 'category', 'group_nr'], group_keys=False):
        best_row = g.nlargest(1, 'confidence')
        best_row = best_row.copy()
        best_row['filename'] = fname
        best_row['category'] = cat
        best_row['group_nr'] = group_nr
        df_out.append(best_row)
    df_out = pd.concat(df_out, ignore_index=True)

    # Remove helper columns and return
    return df_out.drop(columns=['start_group', 'end_group', 'group_nr'])


if __name__ == "__main__":
    path = R"data\comparison_accuracies_models\files_sampled_E2_500\output_0016_retrain_03_overlap_1-500.csv"

    df = pd.read_csv(path)
    df_h = df.head()

    print(df_h)
    print(df.shape)

    df_tidy = overlap_tidy(df, threshold=5)

    print(df_tidy.head())
    print(df_tidy.shape)

    path_dest = R"data\comparison_accuracies_models\files_sampled_E2_500\output_0016_retrain_03_overlap_1-500_tidy_python.csv"
    df_tidy.to_csv(path_dest, index=False)
