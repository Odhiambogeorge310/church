# Church Analytics Dashboard

## Setup
```bash
pip install streamlit plotly pandas openpyxl
streamlit run app.py
```
Then open the local URL Streamlit prints (usually http://localhost:8501).

In the sidebar, upload your Excel register (the same columns as your sheet:
Member_ID, First_Name, Last_Name, Gender, Age, Baptismal_Status/Date/Parish,
First_communion_Status/Date, Confirmation_Date/Parish, Marriage_Status/Date/Parish,
Jumuia, Church_Groups, Ministry, Leadership_Position, Tithe, Departed_Congregants).
Until you upload, the dashboard shows realistic sample data so you can explore it.

## KPIs included, and why

| Tab | KPI | Decision it supports |
|---|---|---|
| Overview | Total / Active / Departed members, Avg age, Tithing rate | One-glance health check of the congregation |
| Overview | Sacrament completion rates (Baptism, 1st Communion, Confirmation, Marriage) | How well the community is being spiritually formed |
| Overview | Jumuia & Church Group mix | Where people are concentrated, for resourcing/pastoral visits |
| Sacramental Journey | Funnel + drop-off between stages | Pinpoints exactly where people stop progressing (e.g. Confirmation → Marriage) so catechism/marriage-prep programs can target that gap |
| Sacramental Journey | Sacrament trend over time, top parishes | Growth/decline trends and parish workload |
| Engagement & Leadership | % in a ministry, % in leadership, engagement by group | Finds the volunteer pool and leadership pipeline strength per group |
| Stewardship | Tithing rate overall, by Jumuia, by age band | Targets stewardship teaching where compliance is weakest |
| Retention & Attrition | Attrition/retention rate, departures over time, departures by engagement | Tests whether ministry involvement predicts retention — the most actionable churn insight |
| Demographics | Age distribution, age bands, gender balance | Informs which age-targeted ministries (youth, young adult, senior) to invest in |

## Notes
- All filters (Gender, Church Group, Jumuia, Age range, Active/Departed) apply across every tab.
- The filtered dataset can be exported as CSV from the Demographics tab.
- Column names are matched flexibly (Yes/No and YES/NO are both handled), but keep the same header names as your original file for best results.
