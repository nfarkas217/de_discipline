import pandas as pd
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
aggregated = None


# -------------------------
# LOAD + PRECOMPUTE ONCE
# -------------------------
def load_data():
    global df, aggregated

    if df is not None:
        return

    print("Loading dataset...")

    df = pd.read_csv(S3_URL, low_memory=False)

    df.columns = [
        "School Year","District Code","District","School Code","Organization",
        "Race","Gender","Grade","SpecialDemo","Geography","SubGroup","Category",
        "Rowstatus","Students","Enrollment","PctEnrollment","Incidents","AvgDuration"
    ]

    df = df.fillna(0)

    # PRECOMPUTE (THIS IS THE FIX)
    aggregated = (
        df.groupby(["School Year", "SubGroup"], as_index=False)["PctEnrollment"]
        .mean()
    )

    print("Dataset loaded + precomputed")


@app.on_event("startup")
def startup():
    load_data()


# -------------------------
# HEALTH CHECK
# -------------------------
@app.get("/")
def root():
    return {"status": "ok"}


# -------------------------
# FAST API (NO HEAVY OPS)
# -------------------------
@app.get("/api/data")
def get_data(category: str):

    if aggregated is None:
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

    result = aggregated[
        aggregated["SubGroup"] == mapping[category]
    ].sort_values("School Year")

    return result.to_dict("records")