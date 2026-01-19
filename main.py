import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from fastapi import FastAPI


df = pd.read_csv('Student_Discipline.csv')
df.columns = ["School Year","District Code","District","School Code","Organization","Race","Gender","Grade","SpecialDemo",
"Geography","SubGroup","Category","Rowstatus","Students","Enrollment","PctEnrollment","Incidents","AvgDuration"]

# replace NaN values with 0
df = df.fillna(0)

# Filter dataset to just Delaware, just 2015, all gender, all grade, just in school suspension
df = df[df['District'] == 'State of Delaware']
df = df[df['School Year'] == 2025]
df = df[df['Gender'] == 'All Students']
df = df[df['Grade'] == 'All Students']
df = df[df['Category'] == 'In-School Suspension']

df = df[["SubGroup", "Category", "Students", "Enrollment", "PctEnrollment", "Incidents", "AvgDuration"]]

app = FastAPI()

@app.get("/api/data")
def get_data(category: str):
    # Filter by category
    if category == 'Black':
        rslt_df = df[df['SubGroup'] == 'African American']
    elif category == 'Hispanic':
        rslt_df = df[df['SubGroup'] == 'Hispanic/Latino']
    elif category == 'Students with Disabilities':
        rslt_df = df[df['SubGroup'] == 'Students with Disabilities']
    elif category == 'Low-income students':
        rslt_df = df[df['SubGroup'] == 'Low Income']
    elif category == 'All Students':
        rslt_df = df[df['SubGroup'] == 'All Students']
    else:
        rslt_df = pd.DataFrame()

    # Aggregate by year for the chart
    chart_data = rslt_df.reset_index()
    chart_data = chart_data.rename(columns={'SubGroup': 'name', 'PctEnrollment': 'value'})
    chart_data = chart_data.sort_values('name')

    return chart_data.to_dict('records')

@app.get("/")
async def root():
    return {"message": "API is running"}





