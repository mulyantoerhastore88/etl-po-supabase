import pandas as pd
import requests
import io
import os
import json
import numpy as np
from fastapi import FastAPI
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from supabase import create_client, Client

app = FastAPI()

# ==============================
# ENV VARIABLES (SET DI RAILWAY)
# ==============================

FILE_ID = "1aTD-tydMAg-jTA6UTNwPvL7rZM-Gy_sb"
SUPABASE_URL = "https://xpahnvlkwmgenkehcmtb.supabase.co"
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
SERVICE_ACCOUNT_JSON = os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ==============================
# GOOGLE DRIVE AUTH
# ==============================

def get_drive_service():
    service_account_info = json.loads(SERVICE_ACCOUNT_JSON)

    creds = service_account.Credentials.from_service_account_info(
        service_account_info,
        scopes=["https://www.googleapis.com/auth/drive"]
    )

    return build("drive", "v3", credentials=creds)

# ==============================
# DOWNLOAD XLSX FROM DRIVE
# ==============================

def download_xlsx():
    service = get_drive_service()

    request = service.files().get_media(fileId=FILE_ID)

    file = io.BytesIO()
    downloader = MediaIoBaseDownload(file, request)
    done = False

    while not done:
        status, done = downloader.next_chunk()

    file.seek(0)
    return file

# ==============================
# TRANSFORM EXCEL → DATAFRAME
# ==============================

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

# ==============================
# FULL REFRESH SUPABASE
# ==============================

def upload_to_supabase(df):
    # 1. Bersihkan data agar kompatibel dengan JSON
    # Ubah semua kolom datetime menjadi string (ISO format)
    for col in df.select_dtypes(include=['datetime64', 'datetime64[ns]']).columns:
        df[col] = df[col].astype(str)
    
    # Ubah nilai NaN/None menjadi None standar python (bukan np.nan)
    # dan ubah Infinity menjadi null
    df = df.replace([np.inf, -np.inf], None)
    df = df.where(pd.notnull(df), None)

    # 2. Konversi ke list of dictionaries
    data = df.to_dict(orient="records")
    
    print(f"Menghapus data lama...")
    # Delete all data (Truncate) - Tidak lagi bergantung pada kolom 'id'
    # Perintah ini akan menghapus SEMUA baris di tabel
    supabase.table("purchase_order").delete().gt("purchasing_document", "").execute() 
    # Catatan: .gt("purchasing_document", "") digunakan sebagai trik untuk menghapus semua baris
    # jika tabel tidak punya id. Jika kolom purchasing_document bisa kosong, 
    # cara paling aman di Supabase Python Client untuk "truncate" tanpa ID spesifik 
    # adalah dengan delete() saja jika didukung, atau delete().neq('some_col', 'impossible_value').
    # Alternatif paling robust jika cara di atas gagal lagi:
    # Hapus satu per satu tidak efisien, jadi kita asumsikan ada setidaknya satu kolom yang selalu terisi.
    # Jika error masih terjadi, ganti baris delete di atas dengan:
    # supabase.rpc('truncate_table').execute() -> Butuh fungsi custom SQL di Supabase.
    
    # KOREKSI FINAL: Cara paling aman tanpa asumsi kolom dan tanpa RPC custom:
    # Kita akan insert langsung dengan mode 'upsert' jika ada unique constraint, 
    # TAPI karena ini full refresh, kita HARUS hapus dulu.
    # Mari coba hapus dengan kondisi yang pasti benar untuk semua baris (misal: kolom apapun IS NOT NULL)
    # Namun, syntax delete() di postgrest-py seringkali butuh filter.
    # Solusi terbaik: Gunakan kolom pertama yang ada di data sebagai filter dummy.
    if len(data) > 0:
        first_key = next(iter(data[0]))
        # Hapus semua baris dimana kolom pertama tidak NULL (asumsi semua baris punya data)
        supabase.table("purchase_order").delete().not_.is_(first_key, None).execute()
    
    print(f"Mengunggah {len(data)} baris ke Supabase...")
    # Insert new data
    response = supabase.table("purchase_order").insert(data).execute()
    
    print(f"Status upload: {response}")
    return response

# ==============================
# API ENDPOINT (TRIGGER ETL)
# ==============================

@app.get("/")
def run_etl():
    try:
        file = download_xlsx()
        df = transform(file)
        upload_to_supabase(df)
        return {"status": "Supabase updated successfully"}
    except Exception as e:
        print(f"TERJADI ERROR: {str(e)}")
        raise e
