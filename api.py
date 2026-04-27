from fastapi import FastAPI
from supabase import create_client
import os

app = FastAPI()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ================================
# ROOT TEST
# ================================
@app.get("/")
def root():
    return {"status": "API RUNNING"}

# ================================
# GET ALL DATA (limit)
# ================================
@app.get("/po")
def get_all_po(limit: int = 100):
    res = supabase.table("purchase_order").select("data").limit(limit).execute()
    return res.data

# ================================
# FILTER BY MATERIAL
# ================================
@app.get("/po/material/{material}")
def get_by_material(material: str):
    res = supabase.rpc(
        "filter_material",
        {"mat": material}
    ).execute()
    return res.data

# ================================
# FILTER BY PLANT
# ================================
@app.get("/po/plant/{plant}")
def get_by_plant(plant: str):
    res = supabase.rpc(
        "filter_plant",
        {"plt": plant}
    ).execute()
    return res.data

# ================================
# SUMMARY KPI
# ================================
@app.get("/summary")
def summary():
    res = supabase.rpc("summary_dashboard").execute()
    return res.data
