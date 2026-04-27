import os
import requests
import pandas as pd
import numpy as np
from fastapi import FastAPI
from supabase import create_client

app = FastAPI()

# =========================
# ENV VARIABLES (Railway)
# =========================
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# =========================
# GOOGLE SHEET CONFIG
# =========================
FILE_ID = "1aTD-tydMAg-jTA6UTNwPvL7rZM-Gy_sb"
SHEET_URL = f"https://docs.google.com/spreadsheets/d/{FILE_ID}/export?format=csv"

TABLE_NAME = "purchase_order"

# =========================
# FUNCTION ETL
# =========================
def run_etl():

    try:
        # =========================
        # EXTRACT
        # =========================
        print("Download file dari Google Drive...")
        response = requests.get(SHEET_URL)
        open("data.csv", "wb").write(response.content)

        df = pd.read_csv("data.csv")
        print("File berhasil dibaca:", len(df), "rows")

        # =========================
        # TRANSFORM
        # =========================
        print("Transform data...")

        # contoh rename kolom biar aman ke postgres
        df.columns = [c.lower().replace(" ", "_") for c in df.columns]

        # =========================
        # CLEAN DATA (SUPER IMPORTANT)
        # =========================
        print("Cleaning NaN & Infinite values...")

        # replace infinite → NaN
        df = df.replace([np.inf, -np.inf], np.nan)

        # replace NaN → None (NULL di Supabase)
        df = df.where(pd.notnull(df), None)

        # force kolom object jadi string (hindari mixed type error)
        for col in df.select_dtypes(include=['object']).columns:
            df[col] = df[col].astype(str)

        print("Total rows after clean:", len(df))

        # convert ke JSON records
        records = df.to_dict(orient="records")

        # =========================
        # LOAD TO SUPABASE
        # =========================
        print("Upload ke Supabase...")

        print("Menghapus data lama...")
        supabase.table(TABLE_NAME).delete().neq("id", 0).execute()

        print("Insert data baru...")
        batch_size = 500
        total_inserted = 0

        for i in range(0, len(records), batch_size):
            batch = records[i:i+batch_size]
            supabase.table(TABLE_NAME).insert(batch).execute()
            total_inserted += len(batch)
            print(f"Inserted {total_inserted} rows...")

        return {
            "status": "SUCCESS",
            "rows_inserted": total_inserted
        }

    except Exception as e:
        return {
            "status": "ERROR",
            "message": str(e)
        }

# =========================
# API ENDPOINT
# =========================
@app.get("/")
def trigger_etl():
    result = run_etl()
    return result
