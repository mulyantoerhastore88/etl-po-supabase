from fastapi import FastAPI
import pandas as pd
import requests
import io
import os
from supabase import create_client

app = FastAPI()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

FILE_ID = "1aTD-tydMAg-jTA6UTNwPvL7rZM-Gy_sb"
DOWNLOAD_URL = f"https://docs.google.com/uc?export=download&id={FILE_ID}"

@app.get("/")
def run_etl():
    try:
        print("Download file dari Google Drive...")
        response = requests.get(DOWNLOAD_URL)
        file_stream = io.BytesIO(response.content)

        print("Baca Excel...")
        df = pd.read_excel(file_stream, engine="openpyxl")

        print("Cleaning data...")
        df.columns = df.columns.str.strip()
        df = df.astype(str)
        df = df.replace(["nan","NaN","None","NaT","inf","-inf"], "")
        df = df.fillna("")

        records = df.to_dict(orient="records")

        print("Hapus data lama...")
        supabase.table("purchase_order").delete().neq("id", 0).execute()

        print("Insert data baru...")
        batch_size = 500
        total = 0

        for i in range(0, len(records), batch_size):
            batch = records[i:i+batch_size]
            supabase.table("purchase_order").insert(
                [{"data": row} for row in batch]
            ).execute()
            total += len(batch)

        return {"status":"SUCCESS","rows_inserted":total}

    except Exception as e:
        return {"status":"ERROR","message":str(e)}
