"""
AMCAT → PlacementIQ feature mapper.

Reads the raw AMCAT / AMEO dataset (Kaggle: mayank1897/ameo-amcat-dataset) and
produces a CSV in the same schema as data/synthetic_students.csv so it is a
drop-in replacement for model_pipeline.py.

Usage
-----
1. One-time AMCAT download (requires Kaggle API token at ~/.kaggle/kaggle.json):

       python -c "import kagglehub; print(kagglehub.dataset_download('mayank1897/ameo-amcat-dataset'))"

   Copy the resulting CSV to backend/data/amcat_raw.csv.

2. Run the mapper:

       cd backend && python amcat_mapper.py

3. Retrain on the mapped data:

       cd backend && python model_pipeline.py --source amcat
"""

from __future__ import annotations

import argparse
import os
import sys
import pandas as pd
import numpy as np


# Target schema — must match data/synthetic_students.csv exactly so the mapped
# CSV is a drop-in replacement for the training pipeline.
TARGET_COLUMNS = [
    'student_id', 'course_type', 'institute_tier', 'region', 'cgpa',
    'internship_months', 'employer_tier', 'iqi', 'behavioral_activity_score',
    'field_demand_score', 'macro_climate_index', 'monthly_emi',
    'placed_3m', 'placed_6m', 'placed_12m', 'actual_salary',
]


# ─── Column name aliasing ──────────────────────────────────────────────
# AMCAT releases vary in casing and spelling (notably the Big Five fields).
# This map collapses every observed variant onto a canonical name.
ALIAS = {
    'id':                         'ID',
    'salary':                     'Salary',
    'doj':                        'DOJ',
    'designation':                'Designation',
    'jobcity':                    'JobCity',
    'degree':                     'Degree',
    'specialization':             'Specialization',
    'collegetier':                'CollegeTier',
    'collegestate':               'CollegeState',
    'collegegpa':                 'collegeGPA',
    'graduationyear':             'GraduationYear',
    '10percentage':               'tenth_pct',
    '12percentage':               'twelfth_pct',
    'english':                    'English',
    'logical':                    'Logical',
    'quant':                      'Quant',
    'computerprogramming':        'ComputerProgramming',
    'electronicsandsemicon':      'ElectronicsAndSemicon',
    'mechanicalengg':             'MechanicalEngg',
    'conscientiousness':          'Conscientiousness',
    'extraversion':               'Extraversion',
    'agreeableness':              'Agreeableness',
    'openesstoexperience':        'Openness',
    'opennesstoexperience':       'Openness',
    'openness_to_experience':     'Openness',
    'openess_to_experience':      'Openness',  # AMCAT 2015 release spelling
    'nueroticism':                'Neuroticism',  # AMCAT misspells it
    'neuroticism':                'Neuroticism',
}


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Rename incoming columns to a stable canonical set."""
    rename = {}
    for col in df.columns:
        key = col.strip().lower().replace(' ', '')
        if key in ALIAS:
            rename[col] = ALIAS[key]
    return df.rename(columns=rename)


# ─── Categorical mappings ──────────────────────────────────────────────
def map_course_type(degree: str, specialization: str) -> str | None:
    d = (str(degree) or '').lower()
    s = (str(specialization) or '').lower()
    if 'mba' in d or 'mba' in s or 'pgdm' in d:
        return 'MBA'
    if 'nursing' in d or 'nursing' in s or 'b.sc nursing' in d:
        return 'Nursing'
    if any(t in d for t in ('b.tech', 'btech', 'b.e.', 'b.e ', 'be ', 'bachelor of engineering', 'm.tech', 'mtech')):
        return 'Engineering'
    if 'engineering' in s or 'engineer' in s:
        return 'Engineering'
    return None  # drop rows that don't fit our three buckets


def map_tier(amcat_tier) -> str | None:
    """AMCAT CollegeTier is 1 or 2 → A / B."""
    try:
        t = int(float(amcat_tier))
    except (TypeError, ValueError):
        return None
    return {1: 'A', 2: 'B'}.get(t)


# State → existing six-region buckets. Anything outside the canonical six
# collapses to the geographically nearest bucket so we don't drop the row.
STATE_TO_REGION = {
    'karnataka': 'Bengaluru', 'kerala': 'Bengaluru', 'goa': 'Bengaluru',
    'maharashtra': 'Mumbai',
    'delhi': 'Delhi NCR', 'haryana': 'Delhi NCR', 'punjab': 'Delhi NCR',
    'uttar pradesh': 'Delhi NCR', 'rajasthan': 'Delhi NCR',
    'uttarakhand': 'Delhi NCR', 'himachal pradesh': 'Delhi NCR',
    'jammu and kashmir': 'Delhi NCR',
    'telangana': 'Hyderabad', 'andhra pradesh': 'Hyderabad',
    'tamil nadu': 'Chennai', 'pondicherry': 'Chennai', 'puducherry': 'Chennai',
    'west bengal': 'Chennai', 'odisha': 'Chennai', 'orissa': 'Chennai',
    'jharkhand': 'Chennai', 'bihar': 'Delhi NCR',
    'madhya pradesh': 'Mumbai', 'chhattisgarh': 'Mumbai', 'gujarat': 'Mumbai',
}


def map_region(state) -> str:
    if not isinstance(state, str):
        return 'Pune'
    s = state.strip().lower()
    return STATE_TO_REGION.get(s, 'Pune')


# ─── Derived features ──────────────────────────────────────────────────
def derive_placement_labels(doj: pd.Series, graduation_year: pd.Series) -> pd.DataFrame:
    """Return placed_3m, placed_6m, placed_12m as 0/1 ints."""
    # DOJ may be a date string or NaN. GraduationYear is an int.
    doj_parsed = pd.to_datetime(doj, errors='coerce')
    grad_year = pd.to_numeric(graduation_year, errors='coerce')

    # Convention from the plan: "graduate in June of GraduationYear"
    months = (doj_parsed.dt.year - grad_year) * 12 + (doj_parsed.dt.month - 6)
    # months is NaN for unplaced rows → treat as never placed
    months = months.where(doj_parsed.notna(), other=np.nan)

    placed_3m  = ((months <= 3)  & months.notna()).astype(int)
    placed_6m  = ((months <= 6)  & months.notna()).astype(int)
    placed_12m = ((months <= 12) & months.notna()).astype(int)
    return pd.DataFrame({
        'placed_3m':  placed_3m,
        'placed_6m':  placed_6m,
        'placed_12m': placed_12m,
        '_months_to_placement': months,
    })


def _col_or_zeros(df: pd.DataFrame, col: str) -> pd.Series:
    """Return df[col] coerced to numeric, or a length-matched zero series if missing."""
    if col in df.columns:
        return pd.to_numeric(df[col], errors='coerce')
    return pd.Series(0.0, index=df.index, dtype=float)


def derive_iqi(df: pd.DataFrame) -> pd.Series:
    """IQI from AMCAT aptitude tests, scaled to [0, 0.45]."""
    eng   = _col_or_zeros(df, 'English')
    log   = _col_or_zeros(df, 'Logical')
    quant = _col_or_zeros(df, 'Quant')

    # AMCAT scores are on a 0–900-ish scale. Use 800 as the doc-stated max but
    # clip aggressively so a single outlier doesn't pin everyone to 0.45.
    MAX = 800.0
    score = ((eng / MAX).clip(0, 1)
             + (log / MAX).clip(0, 1)
             + (quant / MAX).clip(0, 1)) / 3.0
    iqi = (score * 0.45).clip(lower=0, upper=0.45)
    return iqi.fillna(0.10)  # conservative default for missing test rows


def derive_behavioral(df: pd.DataFrame) -> pd.Series:
    """Big Five → 0..100 behavioral activity score."""
    c = _col_or_zeros(df, 'Conscientiousness').fillna(0)
    e = _col_or_zeros(df, 'Extraversion').fillna(0)
    a = _col_or_zeros(df, 'Agreeableness').fillna(0)
    o = _col_or_zeros(df, 'Openness').fillna(0)
    n = _col_or_zeros(df, 'Neuroticism').fillna(0)

    raw = 2.0 * c + 1.5 * e + 1.0 * a + 0.5 * o - 1.5 * n
    # Per the plan: shift by +8, divide by 16, multiply by 100, clip to [0, 100]
    score = ((raw + 8.0) / 16.0 * 100.0).clip(lower=0, upper=100)
    return score.fillna(50)


def derive_field_demand(df: pd.DataFrame) -> pd.Series:
    """Target-encoded per Specialization. Higher = more in-demand."""
    if 'Specialization' not in df.columns:
        return pd.Series(70.0, index=df.index)

    spec_placement = df.groupby('Specialization')['placed_6m'].mean()
    spec_salary    = df.groupby('Specialization')['Salary'].median()

    sal_norm = (spec_salary - spec_salary.min()) / max(1.0, (spec_salary.max() - spec_salary.min()))
    place_norm = spec_placement  # already in [0, 1]

    blended = (0.6 * place_norm + 0.4 * sal_norm).fillna(0) * 100.0
    blended = blended.clip(lower=0, upper=100)
    return df['Specialization'].map(blended).fillna(70.0)


def derive_macro_climate(df: pd.DataFrame) -> pd.Series:
    """Target-encoded per GraduationYear, scaled to [0.5, 1.0]."""
    if 'GraduationYear' not in df.columns:
        return pd.Series(0.65, index=df.index)

    by_year_sal = df.groupby('GraduationYear')['Salary'].median()
    by_year_pl  = df.groupby('GraduationYear')['placed_6m'].mean()

    sal_n = (by_year_sal - by_year_sal.min()) / max(1.0, (by_year_sal.max() - by_year_sal.min()))
    pl_n  = by_year_pl  # already 0–1

    blended = (0.5 * sal_n.fillna(0) + 0.5 * pl_n.fillna(0)).clip(0, 1)
    macro = (0.5 + 0.5 * blended).clip(lower=0.5, upper=1.0)
    return df['GraduationYear'].map(macro).fillna(0.65)


def synth_monthly_emi(tier: pd.Series, seed: int = 42) -> pd.Series:
    rng = np.random.default_rng(seed)
    base = tier.map({'A': 18000, 'B': 14000, 'C': 10000, 'D': 8000}).fillna(12000).astype(float)
    noise = rng.normal(0, 2500, size=len(tier))
    out = (base + noise).clip(lower=5000, upper=35000)
    # Round to the nearest 500
    return (np.round(out / 500.0) * 500.0).astype(int)


def derive_employer_tier(salary: pd.Series) -> pd.Series:
    """Coarse mapping from observed CTC into the same buckets the engine uses."""
    out = pd.Series('MNC', index=salary.index, dtype=object)
    s = pd.to_numeric(salary, errors='coerce').fillna(0)
    out[s >= 1_200_000] = 'Unicorn'
    out[(s >= 500_000) & (s < 1_200_000)] = 'MNC'
    out[(s >= 300_000) & (s < 500_000)]   = 'MidSize'  # not in the current encoder; we'll fold to 'SME'
    out[s < 300_000]                       = 'Startup'
    # The existing encoder only knows MNC / Startup / SME / None — fold MidSize → SME,
    # Unicorn → MNC so we stay schema-compatible.
    out = out.replace({'MidSize': 'SME', 'Unicorn': 'MNC'})
    # Unplaced rows (salary 0 or NaN) → 'None'
    out[s <= 0] = 'None'
    return out


# ─── Main mapping ──────────────────────────────────────────────────────
def map_amcat(raw_path: str, out_path: str) -> pd.DataFrame:
    print(f"Reading raw AMCAT from {raw_path} ...")
    df = pd.read_csv(raw_path)
    print(f"  raw rows: {len(df):,}  |  raw cols: {len(df.columns)}")

    df = normalize_columns(df)

    # Required columns — fail fast if AMCAT release shape differs.
    required = ['Salary', 'Degree', 'Specialization', 'CollegeTier', 'collegeGPA', 'GraduationYear']
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise RuntimeError(f"AMCAT raw is missing expected columns: {missing}\nGot: {list(df.columns)}")

    # ── Course type filter (drops B.Pharm / B.Com / etc.) ──────────────
    df['course_type'] = df.apply(lambda r: map_course_type(r.get('Degree'), r.get('Specialization')), axis=1)
    before = len(df)
    df = df[df['course_type'].notna()].copy()
    print(f"  filtered to course_type in {{Engineering, MBA, Nursing}}: {len(df):,} / {before:,}")

    # ── Tier filter (drop unknowns) ────────────────────────────────────
    df['institute_tier'] = df['CollegeTier'].apply(map_tier)
    df = df[df['institute_tier'].notna()].copy()

    # ── Region ─────────────────────────────────────────────────────────
    state_col = 'CollegeState' if 'CollegeState' in df.columns else ('JobCity' if 'JobCity' in df.columns else None)
    df['region'] = df[state_col].apply(map_region) if state_col else 'Pune'

    # ── CGPA ───────────────────────────────────────────────────────────
    cgpa = pd.to_numeric(df['collegeGPA'], errors='coerce').fillna(7.0)
    cgpa = cgpa.where(cgpa <= 10, cgpa / 10.0)  # rescale percentage to 0-10
    df['cgpa'] = cgpa.clip(lower=4.0, upper=10.0).round(2)

    # ── Salary (annual INR CTC, AMCAT native) ──────────────────────────
    df['actual_salary'] = pd.to_numeric(df['Salary'], errors='coerce').fillna(0).clip(lower=0).astype(int)

    # ── Placement labels ───────────────────────────────────────────────
    labels = derive_placement_labels(
        df['DOJ'] if 'DOJ' in df.columns else pd.Series([pd.NaT] * len(df), index=df.index),
        df['GraduationYear'],
    )
    df[['placed_3m', 'placed_6m', 'placed_12m']] = labels[['placed_3m', 'placed_6m', 'placed_12m']]

    # ── Derived features ───────────────────────────────────────────────
    df['iqi'] = derive_iqi(df).round(3)
    df['behavioral_activity_score'] = derive_behavioral(df).round().astype(int)
    df['field_demand_score'] = derive_field_demand(df).round().astype(int)
    df['macro_climate_index'] = derive_macro_climate(df).round(2)

    # ── Internship months (AMCAT doesn't carry this — synthesize from
    # GraduationYear + IQI as a weak proxy, mostly so the column exists). ──
    rng = np.random.default_rng(7)
    base_months = (df['iqi'] * 13).round().clip(lower=0, upper=12).astype(int)
    df['internship_months'] = base_months + rng.integers(0, 2, size=len(df))
    df['internship_months'] = df['internship_months'].clip(lower=0, upper=12)

    # ── Employer tier, EMI ─────────────────────────────────────────────
    df['employer_tier'] = derive_employer_tier(df['actual_salary'])
    df['monthly_emi'] = synth_monthly_emi(df['institute_tier'])

    # ── ID ─────────────────────────────────────────────────────────────
    df['student_id'] = [f"AMCAT-{int(i):06d}" for i in df['ID']] if 'ID' in df.columns else \
                       [f"AMCAT-{i:06d}" for i in range(len(df))]

    out = df[TARGET_COLUMNS].copy()

    # ── Final sanity ───────────────────────────────────────────────────
    out = out.dropna(subset=['placed_3m', 'placed_6m', 'placed_12m', 'cgpa'])
    out['placed_3m']  = out['placed_3m'].astype(int)
    out['placed_6m']  = out['placed_6m'].astype(int)
    out['placed_12m'] = out['placed_12m'].astype(int)

    os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
    out.to_csv(out_path, index=False)

    print()
    print("--- Mapped dataset stats --------------------------")
    print(f"  rows written: {len(out):,}  ->  {out_path}")
    print(f"  placed_3m  : {out['placed_3m'].mean():.1%}")
    print(f"  placed_6m  : {out['placed_6m'].mean():.1%}")
    print(f"  placed_12m : {out['placed_12m'].mean():.1%}")
    placed = out[out['actual_salary'] > 0]
    if len(placed):
        print(f"  median salary (placed): INR {placed['actual_salary'].median():,.0f}/yr")
    print(f"  course_type mix      : {dict(out['course_type'].value_counts())}")
    print(f"  institute_tier mix   : {dict(out['institute_tier'].value_counts())}")
    print(f"  region mix           : {dict(out['region'].value_counts())}")
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Map AMCAT raw CSV → PlacementIQ training shape')
    parser.add_argument('--raw',    default='data/amcat_raw.csv',    help='Path to raw AMCAT CSV')
    parser.add_argument('--out',    default='data/amcat_mapped.csv', help='Path to write mapped CSV')
    args = parser.parse_args(argv)

    if not os.path.exists(args.raw):
        print(f"!! Missing {args.raw}.\n"
              "   Download it first (one-time):\n"
              "     python -c \"import kagglehub; print(kagglehub.dataset_download('mayank1897/ameo-amcat-dataset'))\"\n"
              "   then copy the resulting CSV to backend/data/amcat_raw.csv\n",
              file=sys.stderr)
        return 1

    map_amcat(args.raw, args.out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
