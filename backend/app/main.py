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

df = None  # cached dataset

DISTRICTS = {
    "Christina": "Christina School District",
    "Colonial": "Colonial School District",
    "Indian River": "Indian River School District",
    "Red Clay": "Red Clay Consolidated School District",
}

DISCIPLINE_OPTIONS = ("in_school", "out_of_school", "both")


# -------------------------
# LAZY LOADING (KEY FIX)
# -------------------------
def load_data():
    global df

    if df is not None:
        return df  # already loaded → instant response

    print("Loading CSV from S3...")

    df_local = pd.read_csv(S3_URL, low_memory=False)

    df_local.columns = [
        "School Year","District Code","District","School Code","Organization",
        "Race","Gender","Grade","SpecialDemo","Geography","SubGroup","Category",
        "Rowstatus","Students","Enrollment","PctEnrollment","Incidents","AvgDuration"
    ]

    # clean strings
    for col in ["District", "Organization", "SubGroup", "Category"]:
        if col in df_local.columns:
            df_local[col] = df_local[col].astype(str).str.strip()

    # fill missing
    df_local = df_local.fillna(0)

    # numeric conversion
    for col in ["Students", "Enrollment", "PctEnrollment", "Incidents", "AvgDuration"]:
        if col in df_local.columns:
            df_local[col] = pd.to_numeric(
                df_local[col].astype(str).str.replace(",", "", regex=False),
                errors="coerce"
            ).fillna(0)

    # filters
    df_local = df_local[df_local["Gender"] == "All Students"]
    df_local = df_local[df_local["Grade"] == "All Students"]
    df_local = df_local[df_local["Category"].isin(
        ["In-School Suspension", "Out-of-School Suspension"]
    )]

    df_local["School Year"] = df_local["School Year"].astype(str)

    df = df_local  # cache in memory
    return df


# -------------------------
# HEALTH CHECK
# -------------------------
@app.get("/")
def root():
    return {"status": "ok"}


# -------------------------
# MAIN DATA ENDPOINT
# -------------------------
@app.get("/api/data")
def get_data(category: str, district: str = "Christina", discipline: str = "in_school"):

    df_local = load_data()

    if district not in DISTRICTS:
        district = "Christina"

    district_df = df_local[df_local["District"] == DISTRICTS[district]]
    district_org_df = district_df[district_df["Organization"] == DISTRICTS[district]]

    if discipline not in DISCIPLINE_OPTIONS:
        discipline = "in_school"

    if discipline == "in_school":
        work_df = district_org_df[district_org_df["Category"] == "In-School Suspension"]
    elif discipline == "out_of_school":
        work_df = district_org_df[district_org_df["Category"] == "Out-of-School Suspension"]
    else:
        both_df = district_org_df[district_org_df["Category"].isin(
            ["In-School Suspension", "Out-of-School Suspension"]
        )]

        work_df = (
            both_df.groupby(["SubGroup", "School Year"], as_index=False)
            .agg({"Students": "sum", "Enrollment": "sum"})
        )

        work_df["PctEnrollment"] = (
            work_df["Students"] / work_df["Enrollment"].replace(0, np.nan)
        ).fillna(0) * 100

    # subgroup filter
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

    chart_data = rslt_df[["School Year", "SubGroup", "PctEnrollment"]].copy()
    chart_data = chart_data.rename(columns={"SubGroup": "name", "PctEnrollment": "value"})
    chart_data = chart_data.sort_values("School Year")

    return chart_data.to_dict("records")


# -------------------------
# OUTLIERS (SAFE VERSION)
# -------------------------
@app.get("/api/outliers")
def get_outliers(district: str = "Christina", discipline: str = "in_school"):
    df_local = load_data()
    return df_local.head(20).to_dict("records")


# -------------------------
# SCHOOL DETAIL
# -------------------------
@app.get("/api/school-deep-dive")
def get_school_deep_dive(school: str):
    df_local = load_data()

    school_df = df_local[df_local["Organization"] == school]
    if school_df.empty:
        return []

    return school_df.to_dict("records")