import os, glob
import numpy as np
import pandas as pd
import networkx as nx

# assign start_group / end_group within each filename+category
def assign_groups(g):
    g = g.copy()
    # start groups (sorted by start_time_ms)
    gs = g.sort_values('start_time_ms')
    diffs = gs['start_time_ms'].diff().fillna(threshold + 1)  # first row always new group
    start_flags = (diffs > threshold).astype(int)
    start_ids = np.cumsum(start_flags)
    g.loc[gs.index, 'start_group'] = ['S' + str(i) for i in start_ids]

    # end groups (sorted by end_time_ms)
    ge = g.sort_values('end_time_ms')
    diffs2 = ge['end_time_ms'].diff().fillna(threshold + 1)
    end_flags = (diffs2 > threshold).astype(int)
    end_ids = np.cumsum(end_flags)
    g.loc[ge.index, 'end_group'] = ['E' + str(i) for i in end_ids]

    return g

# merge start/end groups by computing connected components of the graph (per filename+category)
def merge_via_graph(g):
    G = nx.Graph()
    edges = list(zip(g['start_group'], g['end_group']))
    G.add_edges_from(edges)
    comp_map = {}
    for cid, comp in enumerate(nx.connected_components(G), start=1):
        for node in comp:
            comp_map[node] = cid
    g['group_nr'] = g['start_group'].map(comp_map)
    return g


def overlap_tidy(df, threshold=5):
    df = df.copy()
    # ensure numeric
    df['start_time_ms'] = pd.to_numeric(df['start_time_ms'], errors='coerce')
    df['end_time_ms']   = pd.to_numeric(df['end_time_ms'], errors='coerce')
    df['confidence']    = pd.to_numeric(df['confidence'], errors='coerce')
    df = df.dropna(subset=['start_time_ms', 'end_time_ms', 'confidence']).copy()

    df = df.groupby(['filename', 'category'], group_keys=False).apply(assign_groups)

    df = df.groupby(['filename', 'category'], group_keys=False).apply(merge_via_graph)

    # pick best prediction (max confidence) per merged group
    df_out = (df.groupby(['filename', 'category', 'group_nr'], group_keys=False)
                .apply(lambda x: x.nlargest(1, 'confidence'))
                .reset_index(drop=True))

    # drop helper columns and return
    return df_out.drop(columns=['start_group', 'end_group', 'group_nr'])


if __name__ == "__main__":
    
    overlap_tidy(df, threshold=5)