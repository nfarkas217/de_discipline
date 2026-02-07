import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
df = pd.read_csv(BASE_DIR / "backend/Student_Discipline.csv")

df.columns = ["School Year","District Code","District","School Code","Organization","Race","Gender","Grade","SpecialDemo",
"Geography","SubGroup","Category","Rowstatus","Students","Enrollment","PctEnrollment","Incidents","AvgDuration"]

# replace NaN values with 0
df = df.fillna(0)

def exportUniqueValues(dataframe, columnName):
    temp = (dataframe[str(columnName)].unique())
    np.savetxt(r'/Users/nfarkas/Desktop/projects/Discipline/' + str(columnName) + '.txt', temp, fmt='%s')
    print("exported")

# need to filter out grades and gender
df = df[df['Grade'] == 'All Students']
df = df[df['Gender'] == 'All Students']
df = df[df['School Year'] == 2015]
df = df[["SubGroup", "District", "Organization", "Category", "Students", "Enrollment", "PctEnrollment", "Incidents", "AvgDuration"]]
df = df[df['Category'] == "Out-of-School Suspension"]

DISTRICTS = {"Christina":"Christina School District", "Colonial":"Colonial School District", "Indian River":"Indian River School District", "Red Clay":"Red Clay Consolidated School District"}
district = "State of Delaware"
district_df = df[df["District"] == district]
org_df = district_df[district_df['Organization'] == district]
rslt_df = org_df[org_df['SubGroup'] == 'Asian']
print(rslt_df[["Students", "Enrollment", "Incidents", "PctEnrollment"]])
