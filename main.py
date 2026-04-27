from fastapi import FastAPI
import pandas as pd
import requests
import io
import os
from supabase import create_client

app = FastAPI()

# ambil ENV dari Railway
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# FILE GOOGLE SHEET (excel)
FILE_ID = "1aTD-tydMAg-jTA6UTNwPvL7rZM-Gy_sb"
DOWNLOAD_URL = f"https://docs.google.com/spreadsheets/d/{FILE_ID}/export?format=xlsx"

@app.get("/")
def run_etl():
    try:
        print("Download file dari Google Sheet...")
        response = requests.get(DOWNLOAD_URL)
        file_stream = io.BytesIO(response.content)

        print("Baca Excel...")
        df = pd.read_excel(file_stream)

        print("Cleaning data (anti NaN error)...")

        # bersihkan nama kolom
        df.columns = df.columns.str.strip()

        # convert semua ke string supaya JSON aman
        df = df.astype(str)

        # hapus value aneh dari excel/pandas
        df = df.replace([
            "nan","NaN","None","NaT","inf","-inf"
        ], "")

        # replace numpy NaN asli
        df = df.fillna("")

        # convert ke JSON records
        records = df.to_dict(orient="records")

        print("Hapus data lama di Supabase...")
        supabase.table("purchase_order").delete().neq("id", 0).execute()

        print("Insert data baru...")
        batch_size = 500
        total_inserted = 0

        for i in range(0, len(records), batch_size):
            batch = records[i:i+batch_size]
            supabase.table("purchase_order").insert(
                [{"data": row} for row in batch]
            ).execute()
            total_inserted += len(batch)

        return {
            "status": "SUCCESS",
            "rows_inserted": total_inserted
        }

    except Exception as e:
        return {
            "status": "ERROR",
            "message": str(e)
        }
