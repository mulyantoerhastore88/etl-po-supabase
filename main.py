import pandas as pd
import requests
import io
from fastapi import FastAPI
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

app = FastAPI()

# ENV VARIABLES (nanti isi di Railway)
FILE_ID = "1aTD-tydMAg-jTA6UTNwPvL7rZM-Gy_sb"
SUPABASE_URL = "https://xpahnvlkwmgenkehcmtb.supabase.co"
SUPABASE_KEY = "SUPABASE_ANON_KEY"

def download_xlsx():
    creds = service_account.Credentials.from_service_account_info(
        eval(open("service_account.json").read()),
        scopes=["https://www.googleapis.com/auth/drive"]
    )
    service = build("drive", "v3", credentials=creds)
    request = service.files().get_media(fileId=FILE_ID)

    file = io.BytesIO()
    downloader = MediaIoBaseDownload(file, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()

    file.seek(0)
    return file

def transform(file):
    df = pd.read_excel(file)

    df.columns = [
        "purch_organization","material","short_text","plant","purchasing_document",
        "order_type","purchasing_group","supplier","supplier_name","name_1",
        "order_quantity","order_unit","currency","your_reference","document_date",
        "storage_location","storage_location_desc","issuing_storage_location",
        "issuing_storage_location_desc","release_indicator","final_approved_date",
        "delivery_date","confirm_quantity","quantity_delivered","delivery_completed",
        "posting_date","po_status_description","po_remarks","item","net_order_price"
    ]

    df = df.fillna("")
    return df

def upload_to_supabase(df):
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }

    requests.delete(f"{SUPABASE_URL}/rest/v1/purchase_order?id=gt.0", headers=headers)

    data = df.to_dict(orient="records")
    requests.post(f"{SUPABASE_URL}/rest/v1/purchase_order", headers=headers, json=data)

@app.get("/")
def run_etl():
    file = download_xlsx()
    df = transform(file)
    upload_to_supabase(df)
    return {"status": "Supabase updated"}
