from fastapi import FastAPI
import pandas as pd
import requests
import io
import os
from supabase import create_client

app = FastAPI()

# ENV dari Railway
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Google Sheet ID
FILE_ID = "1aTD-tydMAg-jTA6UTNwPvL7rZM-Gy_sb"
DOWNLOAD_URL = f"https://docs.google.com/spreadsheets/d/{FILE_ID}/export?format=xlsx"

@app.get("/")
def run_etl():
    try:
        # =============================
        # 1. DOWNLOAD GOOGLE SHEET
        # =============================
        print("Download file dari Google Sheet...")
        response = requests.get(DOWNLOAD_URL)
        file_stream = io.BytesIO(response.content)

        # =============================
        # 2. READ EXCEL (FIX ENGINE)
        # =============================
        print("Baca Excel...")
        df = pd.read_excel(file_stream, engine="openpyxl")

        # =============================
        # 3. CLEAN DATA (ANTI NAN ERROR)
        # =============================
        print("Cleaning data...")

        # rapikan nama kolom
        df.columns = df.columns.str.strip()

        # convert semua kolom ke string (JSON safe)
        df = df.astype(str)

        # hapus nilai aneh dari excel/pandas
        df = df.replace([
            "nan", "NaN", "None", "NaT", "inf", "-inf"
        ], "")

        # hapus numpy NaN asli
        df = df.fillna("")

        # convert ke JSON records
        records = df.to_dict(orient="records")

        # =============================
        # 4. DELETE DATA LAMA
        # =============================
        print("Hapus data lama di Supabase...")
        supabase.table("purchase_order").delete().neq("id", 0).execute()

        # =============================
        # 5. INSERT DATA BARU (BATCH)
        # =============================
        print("Insert data baru...")
        batch_size = 500
        total_inserted = 0

        for i in range(0, len(records), batch_size):
            batch = records[i:i+batch_size]
            supabase.table("purchase_order").insert(
                [{"data": row} for row in batch]
            ).execute()
            total_inserted += len(batch)

        # =============================
        # DONE
        # =============================
        return {
            "status": "SUCCESS",
            "rows_inserted": total_inserted
        }

    except Exception as e:
        return {
            "status": "ERROR",
            "message": str(e)
        }
