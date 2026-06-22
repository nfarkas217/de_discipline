import pandas as pd

CATEGORY_DTYPE_MAP = {
    "School Year": "category", "District Code": "category",
    "District": "category", "School Code": "category",
    "Organization": "category", "Race": "category",
    "Gender": "category", "Grade": "category",
    "SpecialDemo": "category", "Geography": "category",
    "SubGroup": "category", "Category": "category",
    "Rowstatus": "category",
}

df = pd.read_csv("backend/Student_Discipline.csv", dtype=CATEGORY_DTYPE_MAP, on_bad_lines="skip")

df.columns = [
    "School Year", "District Code", "District", "School Code", "Organization",
    "Race", "Gender", "Grade", "SpecialDemo", "Geography", "SubGroup", "Category",
    "Rowstatus", "Students", "Enrollment", "PctEnrollment", "Incidents", "AvgDuration"
]

# Filters
df = df[df["Gender"] == "All Students"]
df = df[df["Grade"] == "All Students"]
df = df[df["Category"].isin(["In-School Suspension", "Out-of-School Suspension"])]

# Keep only needed columns
df = df[[
    "School Year", "SubGroup", "District", "Organization",
    "Category", "Rowstatus", "Students", "Enrollment",
    "PctEnrollment", "Incidents", "AvgDuration"
]]

# Normalize School Year
df["School Year"] = df["School Year"].astype(str).str.strip()

# Strip commas THEN cast to float32 (handles numeric NaNs)
for col in ["Students", "Enrollment", "PctEnrollment", "Incidents", "AvgDuration"]:
    df[col] = pd.to_numeric(
        df[col].astype(str).str.replace(",", "", regex=False),
        errors="coerce"
    ).fillna(0).astype("float32")

# Fill categorical NaNs with empty string (can't use 0 on categoricals)
for col in df.select_dtypes("category").columns:
    df[col] = df[col].cat.add_categories("").fillna("")
    df[col] = df[col].cat.remove_unused_categories()

df.to_parquet("backend/Student_Discipline.parquet", index=False)

print(f"Rows: {len(df):,}")
print(f"Memory: {df.memory_usage(deep=True).sum() / 1e6:.1f} MB")
print(f"Columns: {list(df.columns)}")
print(f"\nDistricts included: {df['District'].nunique()}")
print(df["District"].cat.categories.tolist())