import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path


# Christina, Colonial, Indian River, Red Clay

BASE_DIR = Path(__file__).resolve().parent.parent
df = pd.read_csv(BASE_DIR / "Student_Discipline.csv")

#df = pd.read_csv('backend/Student_Discipline.csv')
df.columns = ["School Year","District Code","District","School Code","Organization","Race","Gender","Grade","SpecialDemo",
"Geography","SubGroup","Category","Rowstatus","Students","Enrollment","PctEnrollment","Incidents","AvgDuration"]

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

DISTRICTS = {"Christina":"Christina School District", "Colonial":"Colonial School District", "Indian River":"Indian River School District", "Red Clay":"Red Clay Consolidated School District"}

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
def get_outliers(district: str = "Christina"):
    """Schools in district ordered by (Black PctEnrollment − All Students PctEnrollment), biggest difference first."""
    if district not in DISTRICTS:
        district = "Christina"
    district_name = DISTRICTS[district]
    # All rows in this district, In-School only, exclude district-level aggregate
    sub = df[
        (df["District"] == district_name)
        & (df["Organization"] != district_name)
        & (df["Category"] == "In-School Suspension")
    ].copy()
    if sub.empty:
        return []
    # Use most recent year in the data
    latest_year = sub["School Year"].astype(str).max()
    sub = sub[sub["School Year"] == latest_year]
    # PctEnrollment for African American and All Students per Organization
    black = sub[sub["SubGroup"] == "African American"][["Organization", "PctEnrollment"]].rename(
        columns={"PctEnrollment": "black_pct_enrollment"}
    )
    all_stud = sub[sub["SubGroup"] == "All Students"][["Organization", "PctEnrollment"]].rename(
        columns={"PctEnrollment": "all_students_pct_enrollment"}
    )
    merged = black.merge(all_stud, on="Organization", how="outer")
    merged["difference"] = (
        merged["black_pct_enrollment"].fillna(0) - merged["all_students_pct_enrollment"].fillna(0)
    )
    merged = merged.sort_values("difference", ascending=False).reset_index(drop=True)
    merged["school_year"] = latest_year
    return merged.to_dict("records")


@app.get("/")
async def root():
    return {"message": "API is running"}





