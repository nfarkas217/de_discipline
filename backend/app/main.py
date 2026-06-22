import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
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

df = None

S3_URL = "https://de-discipline-bucket.s3.us-east-2.amazonaws.com/Student_Discipline.csv"

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


@app.on_event("startup")
def load_data():
    global df

    df = pd.read_csv(S3_URL, low_memory=False)

    df.columns = [
        "School Year","District Code","District","School Code","Organization",
        "Race","Gender","Grade","SpecialDemo","Geography","SubGroup","Category",
        "Rowstatus","Students","Enrollment","PctEnrollment","Incidents","AvgDuration"
    ]

    for col in ["District", "Organization", "SubGroup", "Category"]:
        if df[col].dtype == 'object':
            df[col] = df[col].str.strip()

    df = df.fillna(0)

    for col in ["Students", "Enrollment", "PctEnrollment", "Incidents", "AvgDuration"]:
        df[col] = pd.to_numeric(
            df[col].astype(str).str.replace(",", "", regex=False),
            errors="coerce"
        ).fillna(0)

    df = df[df['Gender'] == 'All Students']
    df = df[df['Grade'] == 'All Students']
    df = df[df['Category'].isin(['In-School Suspension', 'Out-of-School Suspension'])]

    df = df[
        ["School Year", "SubGroup", "District", "Organization", "Category",
         "Rowstatus", "Students", "Enrollment", "PctEnrollment", "Incidents", "AvgDuration"]
    ]

    df["School Year"] = df["School Year"].astype(str).str.strip()


def get_df():
    if df is None:
        raise Exception("Data not loaded yet")
    return df


@app.get("/")
def root():
    return {"status": "ok"}


@app.get("/api/data")
def get_data(category: str, district: str = "Christina", discipline: str = "in_school"):
    df_local = get_df()

    if district not in DISTRICTS:
        district = "Christina"

    district_df = df_local[df_local["District"] == DISTRICTS[district]]
    district_org_df = district_df[district_df['Organization'] == DISTRICTS[district]]

    if discipline not in DISCIPLINE_OPTIONS:
        discipline = "in_school"

    if discipline == "in_school":
        work_df = district_org_df[district_org_df["Category"] == "In-School Suspension"].copy()
    elif discipline == "out_of_school":
        work_df = district_org_df[district_org_df["Category"] == "Out-of-School Suspension"].copy()
    else:
        both_df = district_org_df[district_org_df["Category"].isin(
            ["In-School Suspension", "Out-of-School Suspension"]
        )]

        work_df = (
            both_df.groupby(["SubGroup", "School Year"], as_index=False)
            .agg({"Students": "sum", "Enrollment": "sum", "Incidents": "sum"})
        )

        work_df["PctEnrollment"] = (
            work_df["Students"] / work_df["Enrollment"].replace(0, np.nan)
        ).fillna(0) * 100

        work_df["AvgDuration"] = 0
        work_df["Category"] = "Both"

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
        return []

    chart_data = rslt_df[["School Year", "SubGroup", "PctEnrollment"]].copy()
    chart_data = chart_data.rename(columns={"SubGroup": "name", "PctEnrollment": "value"})
    chart_data = chart_data.sort_values("School Year")

    return chart_data.to_dict("records")


@app.get("/api/outliers")
def get_outliers(district: str = "Christina", discipline: str = "in_school"):
    df_local = get_df()
    return df_local.head(10).to_dict("records")


@app.get("/api/school-deep-dive")
def get_school_deep_dive(school: str):
    df_local = get_df()

    school_df = df_local[df_local["Organization"] == school].copy()
    if school_df.empty:
        return []

    return school_df.to_dict("records")