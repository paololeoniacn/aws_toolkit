#!/usr/bin/env python3
import os, sys, re, json, argparse, datetime
from dotenv import load_dotenv
import boto3
from botocore.exceptions import BotoCoreError, ClientError

# Flush immediato
sys.stdout.reconfigure(line_buffering=True)

# Env
load_dotenv()
AWS_REGION     = os.getenv("AWS_DEFAULT_REGION", "eu-south-1")
S3_BUCKET_ENV  = os.getenv("S3_BUCKET", "")
S3_PREFIX_ENV  = os.getenv("S3_PREFIX", "")
S3_SUFFIX_ENV = os.getenv("S3_SUFFIX", "")

# Argomenti
parser = argparse.ArgumentParser(description="Conta i file in S3 sotto un prefisso")
parser.add_argument("--bucket", default=S3_BUCKET_ENV, help="Nome bucket S3 (override di S3_BUCKET)")
parser.add_argument("--prefix", default=S3_PREFIX_ENV, help="Prefisso, es: path/to/folder/")
parser.add_argument("--suffix", default=S3_SUFFIX_ENV, help="Conta solo chiavi che finiscono con questo suffisso, es: .gz")
parser.add_argument("--max-keys", type=int, default=1000, help="Dimensione pagina per list_objects_v2")
parser.add_argument("--show-samples", type=int, default=0, help="Mostra N chiavi di esempio")
args = parser.parse_args()

if not args.bucket:
    print("❌ Specifica --bucket o imposta S3_BUCKET nel .env")
    sys.exit(2)

print("-" * 50)
print(f"🌍 AWS_DEFAULT_REGION: {AWS_REGION}")
print(f"🪣 Bucket: {args.bucket}")
print(f"📂 Prefisso: '{args.prefix}'")
print(f"🎯 Suffix: '{args.suffix}'")
print("-" * 50)

s3 = boto3.client("s3", region_name=AWS_REGION)

def iter_objects(bucket: str, prefix: str, max_keys: int):
    """Itera tutti gli oggetti sotto prefix usando la paginazione."""
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix, PaginationConfig={"PageSize": max_keys}):
        for obj in page.get("Contents", []):
            yield obj

def is_file_key(key: str) -> bool:
    """Esclude 'directory markers' che terminano con '/'."""
    return not key.endswith("/")

def main():
    total_files = 0
    total_bytes = 0
    samples = []

    prefixes = [p.strip() for p in args.prefix.split(";") if p.strip()]

    if not prefixes:
        prefixes = [""]  # prefisso vuoto = tutto il bucket

    try:
        for prefix in prefixes:
            print(f"🔎 Analizzo prefisso: {prefix!r}")
            count = 0
            size_sum = 0

            for obj in iter_objects(args.bucket, prefix, args.max_keys):
                key = obj["Key"]
                if not is_file_key(key):
                    continue
                if args.suffix and not key.endswith(args.suffix):
                    continue
                total_files += 1
                total_bytes += obj.get("Size", 0)
                count += 1
                size_sum += obj.get("Size", 0)

                if args.show_samples and len(samples) < args.show_samples:
                    samples.append(key)

            print(f"  ↳ {count} oggetti, {size_sum} bytes")

    except (BotoCoreError, ClientError) as e:
        print(f"❌ Errore AWS: {e}")
        sys.exit(1)

    print("-" * 50)
    print(f"📊 Totale complessivo:")
    print(f"   Oggetti: {total_files}")
    print(f"   Bytes:   {total_bytes}")
    if args.show_samples and samples:
        print("-" * 50)
        print("📋 Esempi:")
        for k in samples:
            print(f" - {k}")


if __name__ == "__main__":
    main()
