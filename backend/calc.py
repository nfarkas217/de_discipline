import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

df = pd.read_csv('Student_Discipline.csv')
df.columns = ["School Year","District Code","District","School Code","Organization","Race","Gender","Grade","SpecialDemo",
"Geography","SubGroup","Category","Rowstatus","Students","Enrollment","PctEnrollment","Incidents","AvgDuration"]

# replace NaN values with 0
df = df.fillna(0)

# set dtypes
dtype={"School Year": int,
    "District Code": int,
    "District" : "string",
    "School Code": int,
    "Organization": "string",
    "Race": "string",
    "Gender": "string",
    "Grade": "string",
    "SpecialDemo": "string",
    "Geography": "string",
    "SubGroup": "string",
    "Category": "string",
    "Rowstatus": "string",
    "Students": int,
    "Enrollment": int,
    "PctEnrollment": float,
    "Incidents": int,
    "AvgDuration": float
    }
"""
# need to filter out grades -- set grade = all students
df = df[df['Grade'] == 'All Students']
# need to filter out districts, set district = "State of Delaware"
df = df[df['District'] == 'State of Delaware']
# gender = All students
df = df[df['Gender'] == 'All Students']

# look at just 2015
df = df[df['School Year'] == 2015]
# Category = In-School Suspension
df = df[df['Category'] == 'In-School Suspension']


# remove redundant columns
df = df[["SubGroup", "Category", "Rowstatus", "Students", "Enrollment"]]

print(df)"""


def exportUniqueValues(dataframe, columnName):
    temp = (dataframe[str(columnName)].unique())
    np.savetxt(r'/Users/nfarkas/Desktop/projects/Discipline/' + str(columnName) + '.txt', temp, fmt='%s')
    print("exported")

# need to filter out grades and gender
df = df[df['Grade'] == 'All Students']
df = df[df['District'] == 'State of Delaware']
df = df[df['Gender'] == 'All Students']
df = df[df['School Year'] == 2023]
df = df[["SubGroup", "Category", "Students", "Enrollment", "PctEnrollment", "Incidents", "AvgDuration"]]
# df = df[df['Category'] == "In-School Suspension"]


# df.loc[((df['col1'] > 10) | (df['col2'] < 8))]

# started homeless and non-homess in 2023
df = df.loc[((df['SubGroup'] == "Non-Homeless") | (df['SubGroup'] == "Homeless") |(df['SubGroup'] == "All Students"))]
print(df)




def sort(dataframe, column):
    return dataframe.sort_values(by = [str(column)])

"""category = 'Black'
if category == 'Black':
    rslt_df = df[df['Race'] == 'African American']
elif category == 'Hispanic':
    rslt_df = df[df['Race'] == 'Hispanic/Latino']
elif category == 'Students with Disabilities':
    rslt_df = df[df['SpecialDemo'] == 'Students with Disabilities']
elif category == 'Low-income students':
    rslt_df = df[df['SpecialDemo'] == 'Low-Income']
else:
    rslt_df = pd.DataFrame()"""

"""
print(rslt_df)
# Aggregate by year for the chart
chart_data = rslt_df.groupby('School Year')['Incidents']
# chart_data = chart_data.rename(columns={'School Year': 'name', 'Incidents': 'value'})
# chart_data = chart_data.sort_values('name')

print(chart_data)
"""






