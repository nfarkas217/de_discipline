import pandas as pd
import numpy as np
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
# LAZY LOAD (ONLY WHEN NEEDED)
# -----------------------------
def get_data():
    global df

    if df is not None:
        return df

    print("Loading dataset (first request only)...")

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

        df = data
        return df

    except Exception as e:
        print("LOAD FAILED:", e)
        return pd.DataFrame()


# -----------------------------
# HEALTH CHECK (FAST)
# -----------------------------
@app.get("/")
def root():
    return {"status": "ok"}


# -----------------------------
# API (SAFE)
# -----------------------------
@app.get("/api/data")
def get_data_api(category: str):

    data = get_data()

    if data.empty:
        return {"status": "loading"}

    mapping = {
        "Black": "African American",
        "White": "White",
        "Asian": "Asian",
        "Hispanic": "Hispanic/Latino",
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