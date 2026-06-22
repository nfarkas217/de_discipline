import pandas as pd
import numpy as np
import scipy.stats as stats
import threading
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
df_loading = False


# -----------------------------
# BACKGROUND DATA LOADER
# -----------------------------
def load_dataset():
    global df, df_loading

    if df is not None:
        return

    df_loading = True

    try:
        print("Loading dataset from S3...")

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
        print("FAILED TO LOAD DATA:", e)

    finally:
        df_loading = False


# -----------------------------
# STARTUP (NON-BLOCKING)
# -----------------------------
@app.on_event("startup")
def startup():
    # run in background so Railway doesn't hang
    thread = threading.Thread(target=load_dataset)
    thread.start()


# -----------------------------
# SAFETY ACCESSOR
# -----------------------------
def get_df():
    if df is None:
        return None
    return df


# -----------------------------
# HEALTH CHECK
# -----------------------------
@app.get("/")
def root():
    return {"status": "ok"}


# -----------------------------
# SAFE DATA ENDPOINT
# -----------------------------
@app.get("/api/data")
def get_data(category: str, district: str = "Christina", discipline: str = "in_school"):

    data = get_df()

    if data is None:
        return {"status": "loading", "message": "Dataset still loading, try again in ~10 seconds"}

    # district filter
    district_name = "Christina School District"
    df_local = data[data["District"] == district_name]

    # subgroup filter mapping
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

    work = df_local[df_local["SubGroup"] == mapping[category]]

    result = (
        work.groupby("School Year", as_index=False)["PctEnrollment"]
        .mean()
        .sort_values("School Year")
    )

    return result.to_dict("records")


# -----------------------------
# OUTLIERS (SAFE PLACEHOLDER)
# -----------------------------
@app.get("/api/outliers")
def outliers():
    data = get_df()
    if data is None:
        return {"status": "loading"}
    return data.head(20).to_dict("records")


# -----------------------------
# SCHOOL DETAIL
# -----------------------------
@app.get("/api/school-deep-dive")
def school_deep_dive(school: str):
    data = get_df()
    if data is None:
        return {"status": "loading"}

    df_school = data[data["Organization"] == school]
    return df_school.to_dict("records")