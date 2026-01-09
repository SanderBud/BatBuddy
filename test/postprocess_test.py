
import pandas as pd
import numpy as np
import pytest
from pandas.testing import assert_series_equal
from source.postprocess import assign_groups, merge_via_graph, overlap_tidy

""" testing grouping of start and end groups """
def test_assign_groups_basic(): 
    df = pd.DataFrame({
        'start_time_ms': [0, 0, 10],
        'end_time_ms': [50, 50, 60],
        'other': ['a', 'b', 'c']
    })
    out = assign_groups(df, threshold=0)  # equal times should be grouped when threshold == 0

    # expected: first two start at same time => same S-group; third different => new S-group
    assert list(out['start_group']) == ['S1', 'S1', 'S2']
    # same for end times
    assert list(out['end_group']) == ['E1', 'E1', 'E2']

""" Testing linking calls using graph theory """
def test_merge_via_graph_connects_linked_nodes():
    # construct rows where start/end groups link across rows to form a single connected component
    df = pd.DataFrame({
        'start_group': ['S1', 'S1', 'S2'],
        'end_group':   ['E1', 'E2', 'E2']
    })
    out = merge_via_graph(df)

    # all nodes (S1, S2, E1, E2) are connected -> all rows map to the same numeric group number
    assert out['group_nr'].nunique() == 1
    # the group numbers should be integers (not NaN)
    assert out['group_nr'].dtype.kind in ('i', 'u')  # integer-like

""" testing whole overlap_tidy function using mock df """
def test_overlap_tidy_filters_and_prefers_highest_confidence():
    df = pd.DataFrame([
        {'filename': 'f1', 'category': 'Feeding buzz', 'start_time_ms': 0, 'end_time_ms': 10, 'confidence': '0.6'},
        {'filename': 'f1', 'category': 'Feeding buzz', 'start_time_ms': 0, 'end_time_ms': 10, 'confidence': '0.9'}, # best for same times
        {'filename': 'f1', 'category': 'Feeding buzz', 'start_time_ms': 100, 'end_time_ms': 110, 'confidence': 0.8}, # separate group
        {'filename': 'f1', 'category': 'Other', 'start_time_ms': 0, 'end_time_ms': 10, 'confidence': 1.0}, # should be filtered out
        {'filename': 'f2', 'category': 'Social call', 'start_time_ms': 5, 'end_time_ms': 15, 'confidence': '0.7'}
    ])

    out = overlap_tidy(df, threshold=0)

    # helper columns must be removed
    assert 'start_group' not in out.columns
    assert 'end_group' not in out.columns
    assert 'group_nr' not in out.columns

    # Expect rows: merged Feeding buzz group (best 0.9), separate Feeding buzz (0.8), and Social call (0.7) => 3 rows
    assert len(out) == 3

    # Ensure filtered category "Other" is gone
    assert not (out['category'] == 'Other').any()

    # Confidence values should be numeric and the best one retained for the merged pair
    # locate the Feeding buzz rows for filename f1
    f1_fb = out[(out['filename'] == 'f1') & (out['category'] == 'Feeding buzz')]
    # there should be two rows (two groups)
    assert len(f1_fb) == 2
    # one of those must have confidence 0.9
    assert np.isclose(f1_fb['confidence'].astype(float).max(), 0.9)

""" testing whole overlap_tidy function using mock df with incorrect values """
def test_overlap_tidy_coerces_non_numeric_confidence_and_handles_missing():
    df = pd.DataFrame([
        {'filename': 'f1', 'category': 'Feeding buzz', 'start_time_ms': 0, 'end_time_ms': 10, 'confidence': '0.3'},
        {'filename': 'f1', 'category': 'Feeding buzz', 'start_time_ms': 0, 'end_time_ms': 10, 'confidence': 'not_a_number'},
    ])
    out = overlap_tidy(df, threshold=0)

    # the 'not_a_number' coerces to NaN and should not be chosen over the numeric 0.3
    assert len(out) == 1
    assert np.isclose(float(out.iloc[0]['confidence']), 0.3)
