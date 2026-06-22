import pandas as pd
import numpy as np
import scipy.stats as stats
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

S3_URL = "https://de-discipline-bucket.s3.us-east-2.amazonaws.com/Student_Discipline.csv"

df = None


# -----------------------------
# SAFE LAZY LOADER (CRITICAL FIX)
# -----------------------------
def load_data_once():
    global df

    if df is not None:
        return df

    print("Loading dataset from S3 (one-time only)...")

    data = pd.read_csv(
        S3_URL,
        low_memory=False,
        on_bad_lines="skip"
    )

    data.columns = [
        "School Year","District Code","District","School Code","Organization",
        "Race","Gender","Grade","SpecialDemo","Geography","SubGroup","Category",
        "Rowstatus","Students","Enrollment","PctEnrollment","Incidents","AvgDuration"
    ]

    data = data.fillna(0)

    for col in ["Students", "Enrollment", "PctEnrollment", "Incidents", "AvgDuration"]:
        data[col] = pd.to_numeric(
            data[col].astype(str).str.replace(",", "", regex=False),
            errors="coerce"
        ).fillna(0)

    df = data
    return df


def get_df():
    return load_data_once()


# -----------------------------
# HEALTH CHECK (FAST)
# -----------------------------
@app.get("/")
def root():
    return {"status": "ok"}


# -----------------------------
# API: YOUR FULL LOGIC (SAFE)
# -----------------------------
@app.get("/api/data")
def get_data(category: str, district: str = "Christina", discipline: str = "in_school"):

    df_local = get_df()

    district_name = "Christina School District"
    district_df = df_local[df_local["District"] == district_name]

    district_org_df = district_df[district_df["Organization"] == district_name]

    if discipline == "in_school":
        work_df = district_org_df[district_org_df["Category"] == "In-School Suspension"].copy()
    elif discipline == "out_of_school":
        work_df = district_org_df[district_org_df["Category"] == "Out-of-School Suspension"].copy()
    else:
        both_df = district_org_df[
            district_org_df["Category"].isin(["In-School Suspension", "Out-of-School Suspension"])
        ]
        work_df = (
            both_df.groupby(["SubGroup", "School Year"], as_index=False)
            .agg({"Students": "sum", "Enrollment": "sum", "Incidents": "sum"})
        )
        work_df["PctEnrollment"] = (
            work_df["Students"] / work_df["Enrollment"].replace(0, np.nan)
        ).fillna(0) * 100

    mapping = {
        "Black": "African American",
        "White": "White",
        "Asian": "Asian",
        "Hispanic": "Hispanic/Latino",
        "Students with Disabilities": "Students with Disabilities",
        "Low-income students": "Low Income",
        "All Students": "All Students",
    }

    if category not in mapping:
        return []

    rslt_df = work_df[work_df["SubGroup"] == mapping[category]]

    if rslt_df.empty:
        return []

    chart_data = rslt_df[
        ["School Year", "SubGroup", "PctEnrollment", "Students", "Enrollment"]
    ].copy()

    if "Rowstatus" in rslt_df.columns:
        chart_data["redacted"] = (
            rslt_df["Rowstatus"].astype(str).str.upper() == "REDACTED"
        )
        chart_data.loc[chart_data["redacted"], "PctEnrollment"] = np.nan
    else:
        chart_data["redacted"] = False

    chart_data = chart_data.rename(
        columns={"SubGroup": "name", "PctEnrollment": "value"}
    )

    chart_data = chart_data.sort_values("School Year")

    out = chart_data.to_dict("records")

    for row in out:
        if row.get("redacted"):
            row["value"] = None

    return out