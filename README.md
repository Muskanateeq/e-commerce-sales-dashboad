# Store Intelligence dashboard

Interactive Streamlit dashboard for the `E-commerce Store Insights.ipynb` analysis.

## Run

```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

The notebook references `Pakistan Largest Ecommerce Dataset.csv`. Put that file next to `app.py`, or upload it from the sidebar when the app starts.

The app cleans blank trailing rows, removes empty `Unnamed:` columns, parses dates, adds order-level metrics, and supports date/category/status/payment filters plus CSV export.
