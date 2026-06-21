import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import scipy.stats as stats
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path


# Christina, Colonial, Indian River, Red Clay

BASE_DIR = Path(__file__).resolve().parent.parent
df = pd.read_csv(BASE_DIR / "Student_Discipline.csv")

#df = pd.read_csv('backend/Student_Discipline.csv')
df.columns = ["School Year","District Code","District","School Code","Organization","Race","Gender","Grade","SpecialDemo",
"Geography","SubGroup","Category","Rowstatus","Students","Enrollment","PctEnrollment","Incidents","AvgDuration"]

# Clean up key string columns by stripping whitespace to ensure joins and filters work correctly
for col in ["District", "Organization", "SubGroup", "Category"]:
    if df[col].dtype == 'object':
        df[col] = df[col].str.strip()

# replace NaN values with 0
df = df.fillna(0)

# Convert numeric columns (CSV may have commas e.g. "2,133")
for col in ["Students", "Enrollment", "PctEnrollment", "Incidents", "AvgDuration"]:
    df[col] = pd.to_numeric(df[col].astype(str).str.replace(",", "", regex=False), errors="coerce").fillna(0)

# Filter dataset: all years, all gender, all grade; keep both suspension types (district and discipline filtered in API)
df = df[df['Gender'] == 'All Students']
df = df[df['Grade'] == 'All Students']
df = df[df['Category'].isin(['In-School Suspension', 'Out-of-School Suspension'])]

df = df[["School Year", "SubGroup", "District", "Organization", "Category", "Rowstatus", "Students", "Enrollment", "PctEnrollment", "Incidents", "AvgDuration"]]
# Normalize school year to string for consistent API response
df["School Year"] = df["School Year"].astype(str).str.strip()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DISTRICTS = {
    "Christina": "Christina School District",
    "Colonial": "Colonial School District",
    "Indian River": "Indian River School District",
    "Red Clay": "Red Clay Consolidated School District",
    "Capital": "Capital School District",
    "Charter New Castle": "Charter School of New Castle",
    "Milford": "Milford School District",
    "NCC Vo-Tech": "New Castle County Vocational-Technical School District",
    "Seaford": "Seaford School District",
    "Delmar": "Delmar School District",
    "Smyrna": "Smyrna School District",
    "Woodbridge": "Woodbridge School District",
    "Lake Forest": "Lake Forest School District",
    "Laurel": "Laurel School District",
}

DISCIPLINE_OPTIONS = ("in_school", "out_of_school", "both")


@app.get("/api/data")
def get_data(category: str, district: str = "Christina", discipline: str = "in_school"):
    # Filter by district
    if district not in DISTRICTS:
        district = "Christina"
    district_df = df[df["District"] == DISTRICTS[district]]
    district_org_df = district_df[district_df['Organization'] == DISTRICTS[district]]

    # Filter by discipline category
    if discipline not in DISCIPLINE_OPTIONS:
        discipline = "in_school"
    if discipline == "in_school":
        work_df = district_org_df[district_org_df["Category"] == "In-School Suspension"].copy()
    elif discipline == "out_of_school":
        work_df = district_org_df[district_org_df["Category"] == "Out-of-School Suspension"].copy()
    else:  # both: aggregate In-School + Out-of-School by SubGroup and School Year
        both_df = district_org_df[district_org_df["Category"].isin(["In-School Suspension", "Out-of-School Suspension"])]
        work_df = (
            both_df.groupby(["SubGroup", "School Year"], as_index=False)
            .agg({"Students": "sum", "Enrollment": "sum", "Incidents": "sum"})
            .assign(PctEnrollment=lambda x: (x["Students"] / x["Enrollment"].replace(0, np.nan)).fillna(0) * 100)
        )
        work_df["AvgDuration"] = 0
        work_df["Category"] = "Both"

    # Filter by category (SubGroup)
    if category == 'Black':
        rslt_df = work_df[work_df['SubGroup'] == 'African American']
    elif category == 'White':
        rslt_df = work_df[work_df['SubGroup'] == 'White']
    elif category == 'Asian':
        rslt_df = work_df[work_df['SubGroup'] == 'Asian']
    elif category == 'Hispanic':
        rslt_df = work_df[work_df['SubGroup'] == 'Hispanic/Latino']
    elif category == 'Students with Disabilities':
        rslt_df = work_df[work_df['SubGroup'] == 'Students with Disabilities']
    elif category == 'Low-income students':
        rslt_df = work_df[work_df['SubGroup'] == 'Low Income']
    elif category == 'All Students':
        rslt_df = work_df[work_df['SubGroup'] == 'All Students']
    else:
        rslt_df = pd.DataFrame()

    if rslt_df.empty:
        return []

    # Time series: one row per year, sorted by year; mark redacted so frontend can show it
    chart_data = rslt_df[["School Year", "SubGroup", "PctEnrollment", "Students", "Enrollment"]].copy()
    if "Rowstatus" in rslt_df.columns:
        chart_data["redacted"] = (rslt_df["Rowstatus"].astype(str).str.upper() == "REDACTED").values
        chart_data.loc[chart_data["redacted"], "PctEnrollment"] = np.nan
    else:
        chart_data["redacted"] = False
    chart_data = chart_data.rename(columns={"SubGroup": "name", "PctEnrollment": "value"})
    chart_data = chart_data.sort_values("School Year")
    # Convert NaN to None so JSON returns null for redacted values
    out = chart_data.to_dict("records")
    for row in out:
        if row.get("redacted") and "value" in row:
            row["value"] = None
    return out

@app.get("/api/outliers")
def get_outliers(district: str = "Christina", discipline: str = "in_school"):
    """
    Schools in district ordered by (Black PctEnrollment − All Students PctEnrollment), biggest difference first.
    discipline can be 'in_school', 'out_of_school', or 'both'.
    """
    if district not in DISTRICTS:
        district = "Christina"
    district_name = DISTRICTS[district]

    # Identify if the district has individual schools listed
    district_mask = df["District"] == district_name
    has_individual_schools = df[district_mask & (df["Organization"] != district_name)].any().any()

    if has_individual_schools:
        base_sub = df[district_mask & (df["Organization"] != district_name)].copy()
    else:
        base_sub = df[district_mask].copy()

    if discipline == "both":
        sub = (
            base_sub[base_sub["Category"].isin(['In-School Suspension', 'Out-of-School Suspension'])]
            .groupby(["Organization", "School Year", "SubGroup"], as_index=False)
            .agg({"Students": "sum", "Enrollment": "sum", "Incidents": "sum"})
            .assign(PctEnrollment=lambda x: (x["Students"] / x["Enrollment"].replace(0, np.nan)).fillna(0) * 100)
        )
    else:
        cat = "In-School Suspension" if discipline == "in_school" else "Out-of-School Suspension"
        sub = base_sub[base_sub["Category"] == cat].copy()

    if sub.empty:
        return []
    latest_year = sub["School Year"].astype(str).max()
    sub = sub[sub["School Year"] == latest_year]
    # PctEnrollment for African American and All Students per Organization
    black = sub[sub["SubGroup"] == "African American"][["Organization", "PctEnrollment", "Students", "Enrollment"]].rename(
        columns={"PctEnrollment": "black_pct_enrollment", "Students": "black_students", "Enrollment": "black_enrollment"}
    )
    all_stud = sub[sub["SubGroup"] == "All Students"][["Organization", "PctEnrollment", "Students", "Enrollment", "Incidents"]].rename(
        columns={
            "PctEnrollment": "all_students_pct_enrollment",
            "Students": "all_students_students",
            "Enrollment": "all_students_enrollment",
            "Incidents": "all_students_incidents",
        }
    )
    merged = black.merge(all_stud, on="Organization", how="outer")

    # Fill NaN values before calculating difference
    merged["black_pct_enrollment"] = merged["black_pct_enrollment"].fillna(0)
    merged["all_students_pct_enrollment"] = merged["all_students_pct_enrollment"].fillna(0)
    for col in ["black_students", "black_enrollment", "all_students_students", "all_students_enrollment", "all_students_incidents"]:
        merged[col] = merged[col].fillna(0).astype(int)

    merged["difference"] = merged["black_pct_enrollment"] - merged["all_students_pct_enrollment"]
    merged["incident_rate"] = (merged["all_students_incidents"] / merged["all_students_enrollment"].replace(0, np.nan)).fillna(0)

    # --- Statistical Analysis (Risk Ratio, CI, P-value) ---
    # Calculate Non-Black counts
    merged['non_black_students'] = (merged['all_students_students'] - merged['black_students']).clip(lower=0)
    merged['non_black_enrollment'] = (merged['all_students_enrollment'] - merged['black_enrollment']).clip(lower=0)

    def calc_stats(row):
        a = row['black_students']
        n1 = row['black_enrollment']
        c = row['non_black_students']
        n2 = row['non_black_enrollment']

        if n1 <= 0 or n2 <= 0:
            return pd.Series([None, None, None, None])

        # Risk Ratio
        p1 = a / n1
        p2 = c / n2
        rr = p1 / p2 if p2 > 0 else None

        # 95% CI for Risk Ratio
        ci_low, ci_high = None, None
        if a > 0 and c > 0 and rr is not None:
            # SE(ln(RR))
            se = np.sqrt((1/a) - (1/n1) + (1/c) - (1/n2))
            ci_low = np.exp(np.log(rr) - 1.96 * se)
            ci_high = np.exp(np.log(rr) + 1.96 * se)

        # P-value (Chi-square)
        # Contingency table: [[Black Susp, Black Not Susp], [Non-Black Susp, Non-Black Not Susp]]
        obs = np.array([[a, n1 - a], [c, n2 - c]])
        p_val = None
        if (obs >= 0).all():
            try:
                _, p_val, _, _ = stats.chi2_contingency(obs, correction=False)
            except ValueError:
                # Scipy can raise ValueError if a row/column is all zeros.
                p_val = None
        
        return pd.Series([rr, ci_low, ci_high, p_val])

    merged[['risk_ratio', 'ci_low', 'ci_high', 'p_value']] = merged.apply(calc_stats, axis=1)

    merged = merged.sort_values("difference", ascending=False).reset_index(drop=True)
    merged["school_year"] = latest_year

    # Convert to dict and replace any remaining NaN with None
    result = merged.to_dict("records")
    for row in result:
        for key, value in row.items():
            if pd.isna(value):
                row[key] = None

    return result


@app.get("/api/school-deep-dive")
def get_school_deep_dive(school: str):
    """
    Get data for a specific school for the last 3 available years.
    """
    school_df = df[df["Organization"] == school].copy()
    if school_df.empty:
        return []

    # Get the last 3 years of data available for that school
    available_years = sorted(school_df["School Year"].unique(), reverse=True)
    last_three_years = available_years[:3]

    school_df = school_df[school_df["School Year"].isin(last_three_years)]

    if school_df.empty:
        return []

    # Sort for consistent presentation
    school_df = school_df.sort_values(["School Year", "SubGroup", "Category"], ascending=[False, True, True])

    # Convert to dict and replace any remaining NaN with None
    result = school_df.to_dict("records")
    for row in result:
        for key, value in row.items():
            if pd.isna(value):
                row[key] = None
    return result


@app.get("/")
async def root():
    return {"message": "API is running"}
