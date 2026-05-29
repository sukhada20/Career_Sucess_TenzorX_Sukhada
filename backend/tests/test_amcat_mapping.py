"""
Sanity tests for amcat_mapper. Builds a tiny AMCAT-shaped fixture in-memory so
the test runs without requiring the (large, gated-by-Kaggle) raw dataset on disk.
"""

from __future__ import annotations

import os
import sys
import tempfile

import pandas as pd
import pytest

# Make `backend/` importable when invoked from the repo root.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from amcat_mapper import (  # noqa: E402
    TARGET_COLUMNS,
    map_amcat,
    map_course_type,
    map_tier,
    map_region,
    derive_iqi,
    derive_behavioral,
)


def _amcat_fixture() -> pd.DataFrame:
    """Eight rows that exercise the main branches of the mapper."""
    return pd.DataFrame([
        # Placed engineer, tier 1, Karnataka, high scores
        dict(ID=1, Salary=550000, DOJ='2014-07-01', Designation='Software Engineer',
             JobCity='Bangalore', Degree='B.Tech/B.E.', Specialization='computer science & engineering',
             CollegeTier=1, CollegeState='Karnataka', collegeGPA=8.4, GraduationYear=2014,
             English=620, Logical=610, Quant=640,
             Conscientiousness=1.8, Extraversion=0.5, Agreeableness=1.1,
             OpennessToExperience=0.9, nueroticism=-0.2,
             ComputerProgramming=520, ElectronicsAndSemicon=410, MechanicalEngg=0,
             **{'10percentage': 84, '12percentage': 81}),
        # Placed MBA, tier 1, Maharashtra, modest salary
        dict(ID=2, Salary=420000, DOJ='2014-10-15', Designation='Associate Consultant',
             JobCity='Mumbai', Degree='MBA', Specialization='marketing',
             CollegeTier=1, CollegeState='Maharashtra', collegeGPA=7.1, GraduationYear=2014,
             English=580, Logical=520, Quant=540,
             Conscientiousness=1.2, Extraversion=1.5, Agreeableness=0.5,
             OpennessToExperience=0.6, nueroticism=0.0,
             ComputerProgramming=0, ElectronicsAndSemicon=0, MechanicalEngg=0,
             **{'10percentage': 78, '12percentage': 74}),
        # Unplaced engineer (DOJ NaN), tier 2, Tamil Nadu
        dict(ID=3, Salary=0, DOJ=None, Designation=None,
             JobCity=None, Degree='B.Tech/B.E.', Specialization='mechanical engineering',
             CollegeTier=2, CollegeState='Tamil Nadu', collegeGPA=6.4, GraduationYear=2014,
             English=420, Logical=380, Quant=410,
             Conscientiousness=-0.4, Extraversion=-0.2, Agreeableness=0.1,
             OpennessToExperience=-0.5, nueroticism=1.2,
             ComputerProgramming=0, ElectronicsAndSemicon=300, MechanicalEngg=480,
             **{'10percentage': 70, '12percentage': 66}),
        # Late placement (>12m), engineer, tier 2 — should NOT count as placed_12m
        dict(ID=4, Salary=310000, DOJ='2016-09-01', Designation='QA Engineer',
             JobCity='Delhi', Degree='B.E.', Specialization='electronics and communication engineering',
             CollegeTier=2, CollegeState='Delhi', collegeGPA=6.9, GraduationYear=2014,
             English=510, Logical=470, Quant=480,
             Conscientiousness=0.6, Extraversion=0.1, Agreeableness=0.2,
             OpennessToExperience=0.0, nueroticism=0.5,
             ComputerProgramming=410, ElectronicsAndSemicon=460, MechanicalEngg=0,
             **{'10percentage': 75, '12percentage': 71}),
        # Pharmacy → must be dropped (not in our three buckets)
        dict(ID=5, Salary=180000, DOJ='2014-08-01', Designation='Pharmacist',
             JobCity='Hyderabad', Degree='B.Pharm', Specialization='pharmacy',
             CollegeTier=2, CollegeState='Telangana', collegeGPA=6.8, GraduationYear=2014,
             English=480, Logical=450, Quant=420,
             Conscientiousness=0.5, Extraversion=0.4, Agreeableness=0.7,
             OpennessToExperience=0.2, nueroticism=0.1,
             ComputerProgramming=0, ElectronicsAndSemicon=0, MechanicalEngg=0,
             **{'10percentage': 72, '12percentage': 68}),
        # Engineer, 3-month placement (placed_3m=1)
        dict(ID=6, Salary=700000, DOJ='2014-08-15', Designation='Software Engineer',
             JobCity='Bangalore', Degree='B.Tech/B.E.', Specialization='computer science & engineering',
             CollegeTier=1, CollegeState='Karnataka', collegeGPA=9.1, GraduationYear=2014,
             English=720, Logical=680, Quant=710,
             Conscientiousness=2.2, Extraversion=1.7, Agreeableness=1.3,
             OpennessToExperience=1.2, nueroticism=-0.5,
             ComputerProgramming=640, ElectronicsAndSemicon=400, MechanicalEngg=0,
             **{'10percentage': 89, '12percentage': 86}),
        # Nursing, placed
        dict(ID=7, Salary=240000, DOJ='2014-09-15', Designation='Staff Nurse',
             JobCity='Bangalore', Degree='B.Sc Nursing', Specialization='nursing',
             CollegeTier=2, CollegeState='Karnataka', collegeGPA=7.0, GraduationYear=2014,
             English=490, Logical=440, Quant=420,
             Conscientiousness=1.0, Extraversion=0.8, Agreeableness=1.2,
             OpennessToExperience=0.4, nueroticism=0.3,
             ComputerProgramming=0, ElectronicsAndSemicon=0, MechanicalEngg=0,
             **{'10percentage': 78, '12percentage': 75}),
        # Engineer with CGPA stored as percentage (84 → should rescale to 8.4)
        dict(ID=8, Salary=480000, DOJ='2014-11-01', Designation='System Engineer',
             JobCity='Pune', Degree='B.Tech/B.E.', Specialization='information technology',
             CollegeTier=1, CollegeState='Maharashtra', collegeGPA=84.0, GraduationYear=2014,
             English=560, Logical=530, Quant=540,
             Conscientiousness=1.0, Extraversion=0.5, Agreeableness=0.7,
             OpennessToExperience=0.4, nueroticism=0.1,
             ComputerProgramming=470, ElectronicsAndSemicon=380, MechanicalEngg=0,
             **{'10percentage': 80, '12percentage': 77}),
    ])


@pytest.fixture
def mapped_df(tmp_path):
    raw = _amcat_fixture()
    raw_path = tmp_path / 'raw.csv'
    out_path = tmp_path / 'mapped.csv'
    raw.to_csv(raw_path, index=False)
    map_amcat(str(raw_path), str(out_path))
    return pd.read_csv(out_path)


# ─── Schema ────────────────────────────────────────────────────────────
def test_schema_matches_target(mapped_df):
    assert list(mapped_df.columns) == TARGET_COLUMNS

def test_pharm_row_dropped(mapped_df):
    # Original fixture has 8 rows; B.Pharm row (ID=5) must be filtered out
    assert len(mapped_df) == 7
    # And no row should carry a non-allowed course_type
    assert set(mapped_df['course_type'].unique()) <= {'Engineering', 'MBA', 'Nursing'}


# ─── Labels ────────────────────────────────────────────────────────────
def test_placement_labels_correct(mapped_df):
    # The 3-month-placement row (ID=6) should be placed_3m=1
    row6 = mapped_df[mapped_df['student_id'] == 'AMCAT-000006'].iloc[0]
    assert row6['placed_3m'] == 1
    assert row6['placed_6m'] == 1
    assert row6['placed_12m'] == 1

    # Late placement (ID=4) — should be placed but NOT within 12m
    row4 = mapped_df[mapped_df['student_id'] == 'AMCAT-000004'].iloc[0]
    assert row4['placed_3m'] == 0
    assert row4['placed_6m'] == 0
    assert row4['placed_12m'] == 0  # >12 months after June 2014

    # Unplaced (ID=3) — all zeros
    row3 = mapped_df[mapped_df['student_id'] == 'AMCAT-000003'].iloc[0]
    assert row3['placed_3m'] == 0
    assert row3['placed_6m'] == 0
    assert row3['placed_12m'] == 0

def test_no_nan_in_labels_or_cgpa(mapped_df):
    for col in ('placed_3m', 'placed_6m', 'placed_12m', 'cgpa'):
        assert mapped_df[col].notna().all(), f"Found NaN in {col}"


# ─── Derived feature ranges ────────────────────────────────────────────
def test_iqi_in_range(mapped_df):
    assert mapped_df['iqi'].between(0.0, 0.45).all()

def test_behavioral_in_range(mapped_df):
    assert mapped_df['behavioral_activity_score'].between(0, 100).all()

def test_macro_in_range(mapped_df):
    assert mapped_df['macro_climate_index'].between(0.5, 1.0).all()

def test_field_demand_in_range(mapped_df):
    assert mapped_df['field_demand_score'].between(0, 100).all()

def test_cgpa_in_range(mapped_df):
    assert mapped_df['cgpa'].between(4.0, 10.0).all()
    # CGPA stored as percentage in fixture (84.0) should have rescaled to 8.4
    row8 = mapped_df[mapped_df['student_id'] == 'AMCAT-000008'].iloc[0]
    assert 8.0 <= row8['cgpa'] <= 8.5


# ─── Categorical helpers (unit tests) ──────────────────────────────────
def test_map_course_type_branches():
    assert map_course_type('B.Tech/B.E.', 'computer science') == 'Engineering'
    assert map_course_type('MBA', 'finance') == 'MBA'
    assert map_course_type('B.Sc Nursing', 'nursing') == 'Nursing'
    assert map_course_type('B.Pharm', 'pharmacy') is None
    assert map_course_type('B.Com', 'commerce') is None

def test_map_tier():
    assert map_tier(1) == 'A'
    assert map_tier(2) == 'B'
    assert map_tier(3) is None
    assert map_tier(None) is None

def test_map_region_fallback():
    assert map_region('Karnataka') == 'Bengaluru'
    assert map_region('Tamil Nadu') == 'Chennai'
    assert map_region('Mars') == 'Pune'  # safe fallback


# ─── Smoke-test the derivation primitives in isolation ─────────────────
def test_derive_iqi_handles_missing():
    df = pd.DataFrame({'English': [None, 800], 'Logical': [None, 800], 'Quant': [None, 800]})
    iqi = derive_iqi(df)
    assert iqi.iloc[0] == 0.10  # fallback
    assert iqi.iloc[1] == 0.45  # max

def test_derive_behavioral_handles_missing():
    df = pd.DataFrame({'Conscientiousness': [None, 4.0], 'Extraversion': [None, 4.0]})
    b = derive_behavioral(df)
    assert 0 <= b.iloc[0] <= 100
    assert b.iloc[1] == 100  # all-positive maxes out
