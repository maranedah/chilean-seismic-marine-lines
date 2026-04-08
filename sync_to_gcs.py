"""
Sync local papers/ and images/ directories to GCS bucket sismica-marina-bucket.

Usage:
    python sync_to_gcs.py              # sync both
    python sync_to_gcs.py --dry-run    # preview without uploading
    python sync_to_gcs.py --papers     # sync only papers/
    python sync_to_gcs.py --images     # sync only images/
"""

import argparse
import os
import sys
from pathlib import Path

from google.cloud import storage
from google.oauth2 import service_account

SA_KEY_PATH = Path(__file__).parent / "sismica-marina-deploy.json"
BUCKET_NAME = "sismica-marina-bucket"
LOCAL_DIRS = {
    "papers": Path("papers"),
    "images": Path("images"),
}


def get_client() -> storage.Client:
    if not SA_KEY_PATH.exists():
        print(f"ERROR: service account key not found at {SA_KEY_PATH}", file=sys.stderr)
        sys.exit(1)
    credentials = service_account.Credentials.from_service_account_file(str(SA_KEY_PATH))
    return storage.Client(credentials=credentials, project=credentials.project_id)


def sync_directory(
    bucket: storage.Bucket,
    local_dir: Path,
    gcs_prefix: str,
    dry_run: bool,
) -> tuple[int, int]:
    """Upload all files in local_dir to gs://bucket/gcs_prefix/.

    Returns (uploaded, skipped) counts.
    """
    if not local_dir.exists():
        print(f"  [SKIP] {local_dir}/ does not exist locally")
        return 0, 0

    existing_blobs: dict[str, str] = {
        blob.name: blob.md5_hash
        for blob in bucket.list_blobs(prefix=gcs_prefix + "/")
    }

    uploaded = skipped = 0
    files = sorted(local_dir.rglob("*"))

    for local_path in files:
        if not local_path.is_file():
            continue

        relative = local_path.relative_to(local_dir)
        blob_name = f"{gcs_prefix}/{relative.as_posix()}"

        blob = bucket.blob(blob_name)

        # Skip if already uploaded with same content (compare MD5)
        if blob_name in existing_blobs:
            import base64
            import hashlib

            local_md5 = base64.b64encode(
                hashlib.md5(local_path.read_bytes()).digest()
            ).decode()
            if local_md5 == existing_blobs[blob_name]:
                skipped += 1
                continue

        if dry_run:
            print(f"  [DRY-RUN] would upload {local_path} → gs://{bucket.name}/{blob_name}")
        else:
            print(f"  Uploading {local_path} → gs://{bucket.name}/{blob_name}")
            blob.upload_from_filename(str(local_path))

        uploaded += 1

    return uploaded, skipped


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync papers/ and images/ to GCS")
    parser.add_argument("--dry-run", action="store_true", help="Preview without uploading")
    parser.add_argument("--papers", action="store_true", help="Sync only papers/")
    parser.add_argument("--images", action="store_true", help="Sync only images/")
    args = parser.parse_args()

    # Default: sync both unless a specific flag is given
    sync_papers = args.papers or (not args.papers and not args.images)
    sync_images = args.images or (not args.papers and not args.images)

    dirs_to_sync = {}
    if sync_papers:
        dirs_to_sync["papers"] = LOCAL_DIRS["papers"]
    if sync_images:
        dirs_to_sync["images"] = LOCAL_DIRS["images"]

    client = get_client()
    bucket = client.bucket(BUCKET_NAME)

    if dry_run := args.dry_run:
        print(f"[DRY-RUN] target bucket: gs://{BUCKET_NAME}\n")
    else:
        print(f"Target bucket: gs://{BUCKET_NAME}\n")

    total_uploaded = total_skipped = 0

    for prefix, local_dir in dirs_to_sync.items():
        print(f"── {local_dir}/ → gs://{BUCKET_NAME}/{prefix}/")
        uploaded, skipped = sync_directory(bucket, local_dir, prefix, dry_run)
        print(f"   {uploaded} uploaded, {skipped} skipped (already up to date)\n")
        total_uploaded += uploaded
        total_skipped += skipped

    print(f"Done. Total: {total_uploaded} uploaded, {total_skipped} skipped.")


if __name__ == "__main__":
    main()
