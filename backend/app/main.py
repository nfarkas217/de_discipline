import threading

import numpy as np
import pandas as pd
import scipy.stats as stats
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

S3_URL = "https://de-discipline-bucket.s3.us-east-2.amazonaws.com/Student_Discipline.parquet"

df = None
df_ready = threading.Event()
df_load_error: str | None = None

# -----------------------------
# DISTRICTS
# -----------------------------
DISTRICTS = {
    "Christina": "Christina School District",
    "Colonial": "Colonial School District",
    "Indian River": "Indian River School District",
    "Red Clay": "Red Clay Consolidated School District",
}

DISCIPLINE_OPTIONS = ("in_school", "out_of_school", "both")


# -----------------------------
# BACKGROUND DATA LOADER
# -----------------------------
def _load_data_background() -> None:
    """Runs in a daemon thread so the health-check endpoint responds immediately."""
    global df, df_load_error

    try:
        print("Loading dataset from S3...")
        data = pd.read_parquet(S3_URL)
        df = data
        print("Dataset loaded successfully.")

    except Exception as exc:
        df_load_error = str(exc)
        print(f"ERROR loading dataset: {exc}")

    finally:
        # Signal readiness regardless of outcome so get_df() doesn't hang forever
        df_ready.set()


@app.on_event("startup")
async def startup_event() -> None:
    thread = threading.Thread(target=_load_data_background, daemon=True)
    thread.start()


def get_df() -> pd.DataFrame:
    """Block until data is ready (up to 2 min), then return it."""
    df_ready.wait(timeout=120)

    if df_load_error:
        raise HTTPException(status_code=503, detail=f"Data load failed: {df_load_error}")

    if df is None:
        raise HTTPException(status_code=503, detail="Data not loaded yet — please retry.")

    return df


# -----------------------------
# HEALTH CHECK  (Railway uses this)
# -----------------------------
@app.get("/health")
def health():
    if not df_ready.is_set():
        raise HTTPException(status_code=503, detail="Data still loading")
    if df_load_error:
        raise HTTPException(status_code=503, detail=f"Data load failed: {df_load_error}")
    return {"status": "ready"}


@app.get("/")
def root():
    return {"status": "ok"}


# -----------------------------
# /api/data
# -----------------------------
@app.get("/api/data")
def get_data(
    category: str = "All Students",
    district: str = "Christina",
    discipline: str = "in_school",
):
    df_local = get_df()

    district_name = DISTRICTS.get(district, DISTRICTS["Christina"])
    district_df = df_local[df_local["District"] == district_name]

    # Discipline filter
    if discipline == "in_school":
        work_df = district_df[district_df["Category"] == "In-School Suspension"].copy()
    elif discipline == "out_of_school":
        work_df = district_df[district_df["Category"] == "Out-of-School Suspension"].copy()
    else:
        work_df = district_df[
            district_df["Category"].isin(["In-School Suspension", "Out-of-School Suspension"])
        ]

        work_df = (
            work_df.groupby(["SubGroup", "School Year"], as_index=False)
            .agg({
                "Students":   "sum",
                "Enrollment": "sum",
                "Incidents":  "sum",
            })
        )

        work_df["PctEnrollment"] = (
            work_df["Students"] / work_df["Enrollment"].replace(0, np.nan)
        ).fillna(0) * 100

    mapping = {
        "Black":                      "African American",
        "White":                      "White",
        "Asian":                      "Asian",
        "Hispanic":                   "Hispanic/Latino",
        "Students with Disabilities": "Students with Disabilities",
        "Low-income students":        "Low Income",
        "All Students":               "All Students",
    }

    if category not in mapping:
        return []

    rslt_df = work_df[work_df["SubGroup"] == mapping[category]]

    if rslt_df.empty:
        return []

    chart_data = rslt_df[
        ["School Year", "SubGroup", "PctEnrollment", "Students", "Enrollment"]
    ].copy()

    # Redaction consistency
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


# -----------------------------
# /api/outliers
# -----------------------------
@app.get("/api/outliers")
def get_outliers(district: str = "Christina", discipline: str = "in_school"):
    df_local = get_df()

    district_name = DISTRICTS.get(district, DISTRICTS["Christina"])
    district_df = df_local[df_local["District"] == district_name]

    base = district_df[district_df["Category"].isin([
        "In-School Suspension",
        "Out-of-School Suspension",
    ])]

    sub = (
        base.groupby(["Organization", "School Year", "SubGroup"], as_index=False)
        .agg({
            "Students":   "sum",
            "Enrollment": "sum",
            "Incidents":  "sum",
        })
    )

    latest_year = sub["School Year"].astype(str).max()
    sub = sub[sub["School Year"].astype(str) == latest_year]

    black = sub[sub["SubGroup"] == "African American"][
        ["Organization", "Students", "Enrollment"]
    ].rename(columns={
        "Students":   "black_students",
        "Enrollment": "black_enrollment",
    })

    all_students = sub[sub["SubGroup"] == "All Students"][
        ["Organization", "Students", "Enrollment", "Incidents"]
    ].rename(columns={
        "Students":   "all_students_students",
        "Enrollment": "all_students_enrollment",
        "Incidents":  "all_students_incidents",
    })

    merged = black.merge(all_students, on="Organization", how="outer").fillna(0)

    merged["difference"] = (
        (merged["black_students"] / merged["black_enrollment"].replace(0, np.nan))
        - (merged["all_students_students"] / merged["all_students_enrollment"].replace(0, np.nan))
    ).fillna(0)

    def calc_stats(row):
        a  = row["black_students"]
        n1 = row["black_enrollment"]
        c  = row["all_students_students"]
        n2 = row["all_students_enrollment"]

        if n1 <= 0 or n2 <= 0:
            return pd.Series([None, None, None])

        p1 = a / n1 if n1 else 0
        p2 = c / n2 if n2 else 0
        rr = (p1 / p2) if p2 else None

        try:
            table   = np.array([[a, n1 - a], [c, n2 - c]])
            _, p_value, _, _ = stats.chi2_contingency(table, correction=False)
        except Exception:
            p_value = None

        return pd.Series([rr, p_value, latest_year])

    merged[["risk_ratio", "p_value", "school_year"]] = merged.apply(calc_stats, axis=1)

    return merged.to_dict("records")


# -----------------------------
# /api/school-deep-dive
# -----------------------------
@app.get("/api/school-deep-dive")
def school_deep_dive(school: str, district: str = "Christina"):
    df_local = get_df()

    district_name = DISTRICTS.get(district, DISTRICTS["Christina"])
    district_df = df_local[df_local["District"] == district_name]

    school_df = district_df[district_df["Organization"] == school].copy()

    if school_df.empty:
        return []

    school_df = school_df.sort_values("School Year", ascending=False)

    # Last 3 years
    years     = school_df["School Year"].unique()[:3]
    school_df = school_df[school_df["School Year"].isin(years)]

    # Redaction consistency
    if "Rowstatus" in school_df.columns:
        school_df["redacted"] = (
            school_df["Rowstatus"].astype(str).str.upper() == "REDACTED"
        )
        school_df.loc[school_df["redacted"], "PctEnrollment"] = np.nan

    return school_df.fillna(0).to_dict("records")
