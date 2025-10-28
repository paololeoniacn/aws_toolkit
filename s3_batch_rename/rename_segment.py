#!/usr/bin/env python3
import os
import boto3
from botocore.exceptions import ClientError
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter, defaultdict

s3 = boto3.client("s3")


def str_to_bool(v: str | None, default: bool) -> bool:
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "y")


def rename_segment(
    bucket: str,
    old_segment: str,
    new_segment: str,
    search_prefix: str | None = None,
    dry_run: bool = True,
    max_workers: int = 16,
    allow_collisions: bool = False,
):
    """
    Rinomina tutte le chiavi S3 che contengono `old_segment` sostituendolo con `new_segment`,
    ovunque nel path. Esegue COPY poi DELETE.

    bucket: nome bucket
    old_segment: es. '/old/'  (includere le '/' se vuoi match di cartella)
    new_segment: es. '/new/'
    search_prefix: limita la scansione (es. 'pippo/'). Se None scansiona tutto il bucket
    dry_run: True = stampa piano operativo senza toccare nulla
    max_workers: numero thread di lavoro
    allow_collisions: False = salta casi in cui più chiavi convergono sulla stessa destinazione
    """

    if not bucket:
        raise ValueError("BUCKET mancante")
    if not old_segment:
        raise ValueError("OLD_SEGMENT mancante")
    if new_segment is None:
        raise ValueError("NEW_SEGMENT mancante")
    if old_segment == new_segment:
        print("Nessuna modifica: OLD_SEGMENT == NEW_SEGMENT")
        return

    paginator = s3.get_paginator("list_objects_v2")
    pages = paginator.paginate(Bucket=bucket, Prefix=search_prefix or "")

    ops = []  # (old_key, new_key, size_bytes)
    for page in pages:
        for obj in page.get("Contents", []):
            old_key = obj["Key"]

            if old_segment not in old_key:
                continue

            new_key = old_key.replace(old_segment, new_segment)

            if new_key == old_key:
                continue

            ops.append((old_key, new_key, obj.get("Size", 0)))

    if not ops:
        print("Nessun oggetto da rinominare")
        return

    # Collision detection: più sorgenti -> stessa destinazione
    counts = Counter(nk for _, nk, _ in ops)
    collisions = {nk for nk, c in counts.items() if c > 1}

    if collisions and not allow_collisions:
        by_dest = defaultdict(list)
        for ok, nk, _ in ops:
            if nk in collisions:
                by_dest[nk].append(ok)

        print("[ATTENZIONE] Collisioni rilevate. Verranno SALTATE con ALLOW_COLLISIONS=False")
        for nk, oks in by_dest.items():
            print(f"  DEST: {nk}")
            for ok in oks:
                print(f"    SRC: {ok}")

        # filtra fuori le collisioni
        ops = [t for t in ops if t[1] not in collisions]

    if dry_run:
        for old_key, new_key, _ in ops:
            print(f"[DRY RUN] COPY {old_key} -> {new_key}")
            print(f"[DRY RUN] DELETE {old_key}")
        print(f"Piano: {len(ops)} oggetti. Collisioni: {len(collisions)}")
        return

    moved = 0
    bytes_copied = 0

    def _move_one(old_key: str, new_key: str, size: int):
        copy_source = {"Bucket": bucket, "Key": old_key}

        try:
            s3.copy_object(
                Bucket=bucket,
                Key=new_key,
                CopySource=copy_source,
                MetadataDirective="COPY",  # preserva metadata e tag
            )
        except ClientError as e:
            print(f"ERRORE copia {old_key} -> {new_key}: {e}")
            return 0, 0

        try:
            s3.delete_object(Bucket=bucket, Key=old_key)
        except ClientError as e:
            print(f"ERRORE delete {old_key}: {e}")
            # a questo punto vecchio e nuovo coesistono

        return 1, size

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [pool.submit(_move_one, ok, nk, sz) for ok, nk, sz in ops]
        for fut in as_completed(futures):
            m, b = fut.result()
            moved += m
            bytes_copied += b

    print(f"Oggetti spostati: {moved}")
    print(f"Byte copiati: {bytes_copied}")
    if collisions and not allow_collisions:
        print(f"Saltate collisioni: {len(collisions)} destinazioni")


def env_or_none(name: str):
    v = os.getenv(name)
    if v is None or v == "" or v.lower() == "none":
        return None
    return v


if __name__ == "__main__":
    bucket = os.getenv("BUCKET")
    old_segment = os.getenv("OLD_SEGMENT")
    new_segment = os.getenv("NEW_SEGMENT")

    search_prefix = env_or_none("SEARCH_PREFIX")

    dry_run = str_to_bool(os.getenv("DRY_RUN"), default=True)
    allow_collisions = str_to_bool(os.getenv("ALLOW_COLLISIONS"), default=False)

    max_workers_env = os.getenv("MAX_WORKERS")
    try:
        max_workers = int(max_workers_env) if max_workers_env else 16
    except ValueError:
        max_workers = 16

    rename_segment(
        bucket=bucket,
        old_segment=old_segment,
        new_segment=new_segment,
        search_prefix=search_prefix,
        dry_run=dry_run,
        max_workers=max_workers,
        allow_collisions=allow_collisions,
    )
