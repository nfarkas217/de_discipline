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
# SAFE SYNCHRONOUS LOAD (NO THREADS)
# -----------------------------
@app.on_event("startup")
def load_data():
    global df

    print("Loading dataset from S3...")

    try:
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

        data = data[
            (data["Gender"] == "All Students") &
            (data["Grade"] == "All Students") &
            (data["Category"].isin(["In-School Suspension", "Out-of-School Suspension"]))
        ]

        data["School Year"] = data["School Year"].astype(str)

        df = data

        print("Dataset loaded successfully")

    except Exception as e:
        print("DATA LOAD FAILED:", e)
        df = pd.DataFrame()


# -----------------------------
# ROOT
# -----------------------------
@app.get("/")
def root():
    return {"status": "ok"}


# -----------------------------
# SAFE ACCESSOR
# -----------------------------
def get_df():
    return df


# -----------------------------
# API
# -----------------------------
@app.get("/api/data")
def get_data(category: str, district: str = "Christina", discipline: str = "in_school"):

    data = get_df()

    if data is None or data.empty:
        return {"status": "loading"}

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

    work = data[data["SubGroup"] == mapping[category]]

    result = (
        work.groupby("School Year", as_index=False)["PctEnrollment"]
        .mean()
        .sort_values("School Year")
    )

    return result.to_dict("records")