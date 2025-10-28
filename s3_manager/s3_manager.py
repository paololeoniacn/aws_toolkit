#!/usr/bin/env python3
import os
import sys
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from dotenv import load_dotenv

def load_env():
    """
    Carica variabili dal file .env se presente.
    In container lo script parte da /app quindi .env verrà copiato lì.
    """
    env_loaded = load_dotenv()
    if not env_loaded:
        print("[INFO] .env non trovato o non caricato. Uso ambiente corrente.")

def get_s3_client():
    """
    Crea il client S3 usando variabili d'ambiente già caricate.
    """
    try:
        session = boto3.session.Session(
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name=os.getenv("AWS_DEFAULT_REGION", "eu-west-1"),
        )
        return session.client("s3")
    except Exception as e:
        print(f"[ERRORE] Creazione client S3 fallita: {e}")
        sys.exit(1)

def list_objects(s3, bucket, prefix=""):
    """
    Lista oggetti nel bucket (filtro opzionale prefix).
    """
    try:
        paginator = s3.get_paginator("list_objects_v2")
        pages = paginator.paginate(Bucket=bucket, Prefix=prefix)

        found = False
        for page in pages:
            if "Contents" in page:
                found = True
                for obj in page["Contents"]:
                    size = obj["Size"]
                    key = obj["Key"]
                    lastmod = obj["LastModified"]
                    print(f"{size:>10} B  {lastmod}  {key}")
        if not found:
            print("[INFO] Nessun oggetto trovato.")
    except ClientError as e:
        print(f"[ERRORE] list_objects: {e}")
    except NoCredentialsError:
        print("[ERRORE] Credenziali AWS mancanti.")

def upload_file(s3, bucket, local_path, dest_key):
    """
    Carica file locale -> s3://bucket/dest_key
    """
    if not os.path.isfile(local_path):
        print(f"[ERRORE] File locale non trovato: {local_path}")
        return
    try:
        s3.upload_file(local_path, bucket, dest_key)
        print(f"[OK] Upload completato: {local_path} -> s3://{bucket}/{dest_key}")
    except ClientError as e:
        print(f"[ERRORE] upload_file: {e}")

def download_file(s3, bucket, key, local_path):
    """
    Scarica s3://bucket/key -> file locale
    """
    try:
        os.makedirs(os.path.dirname(local_path) or ".", exist_ok=True)
        s3.download_file(bucket, key, local_path)
        print(f"[OK] Download completato: s3://{bucket}/{key} -> {local_path}")
    except ClientError as e:
        print(f"[ERRORE] download_file: {e}")
    except FileNotFoundError:
        print(f"[ERRORE] Path locale non valido: {local_path}")

def delete_object(s3, bucket, key):
    """
    Cancella oggetto singolo s3://bucket/key
    """
    try:
        s3.delete_object(Bucket=bucket, Key=key)
        print(f"[OK] Eliminato: s3://{bucket}/{key}")
    except ClientError as e:
        print(f"[ERRORE] delete_object: {e}")

def print_menu():
    print("\n=== S3 Manager ===")
    print("1) Lista oggetti")
    print("2) Upload file")
    print("3) Download file")
    print("4) Elimina oggetto")
    print("5) Esci")

def main():
    load_env()

    bucket = os.getenv("AWS_S3_BUCKET")
    if not bucket:
        print("[ATTENZIONE] Variabile AWS_S3_BUCKET non impostata.")
        bucket = input("Bucket S3 da usare: ").strip()

    s3 = get_s3_client()

    while True:
        print_menu()
        choice = input("Seleziona: ").strip()

        if choice == "1":
            prefix = input("Prefix (ENTER per tutto): ").strip()
            list_objects(s3, bucket, prefix)

        elif choice == "2":
            local_path = input("Percorso file locale (host non container se bind-mountato): ").strip()
            dest_key = input("Key S3 di destinazione (es cartella/file.ext): ").strip()
            upload_file(s3, bucket, local_path, dest_key)

        elif choice == "3":
            key = input("Key S3 da scaricare: ").strip()
            local_path = input("Percorso locale di destinazione (nel container): ").strip()
            download_file(s3, bucket, key, local_path)

        elif choice == "4":
            key = input("Key S3 da eliminare: ").strip()
            conferma = input(f"Confermi eliminazione di s3://{bucket}/{key}? (yes/no): ").strip().lower()
            if conferma == "yes":
                delete_object(s3, bucket, key)
            else:
                print("[INFO] Eliminazione annullata.")

        elif choice == "5":
            print("Uscita.")
            break

        else:
            print("[INFO] Scelta non valida.")

if __name__ == "__main__":
    main()
