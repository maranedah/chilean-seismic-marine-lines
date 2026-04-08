"""
Sync local data/ directories to GCS bucket sismica-marina-bucket.

Usage:
    python src/tools/sync_to_gcs.py              # sync jsons + images + low-res previews
    python src/tools/sync_to_gcs.py --dry-run    # preview without uploading
    python src/tools/sync_to_gcs.py --papers     # sync only data/extracted_jsons/
    python src/tools/sync_to_gcs.py --images     # sync images + low-res previews
    python src/tools/sync_to_gcs.py --previews   # sync only low-res previews
    python src/tools/sync_to_gcs.py --workers N  # parallel upload workers (default: 16)
"""

import argparse
import base64
import hashlib
import io
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock

from google.cloud import storage
from google.oauth2 import service_account

# Key lives at the project root (3 levels up from src/tools/)
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
SA_KEY_PATH = _PROJECT_ROOT / "sismica-marina-deploy.json"
BUCKET_NAME = "sismica-marina-bucket"
LOCAL_DIRS = {
    "data/extracted_jsons": _PROJECT_ROOT / "data" / "extracted_jsons",
    "data/extracted_images": _PROJECT_ROOT / "data" / "extracted_images",
}
LOW_RES_GCS_PREFIX = "data/extracted_images_low_res"
LOW_RES_MAX_BYTES = 200_000   # 0.2 MB
LOW_RES_MAX_DIM   = 1200      # px — cap longest edge before quality reduction


def get_client() -> storage.Client:
    if not SA_KEY_PATH.exists():
        print(f"ERROR: service account key not found at {SA_KEY_PATH}", file=sys.stderr)
        sys.exit(1)
    credentials = service_account.Credentials.from_service_account_file(str(SA_KEY_PATH))
    return storage.Client(credentials=credentials, project=credentials.project_id)


# ── helpers ────────────────────────────────────────────────────────────────────

def _md5(data: bytes) -> str:
    return base64.b64encode(hashlib.md5(data).digest()).decode()


def _md5_file(path: Path) -> str:
    return _md5(path.read_bytes())


def _compress_to_jpeg(path: Path, max_bytes: int = LOW_RES_MAX_BYTES) -> bytes:
    """Return JPEG bytes for path, scaled and quality-reduced to fit under max_bytes."""
    from PIL import Image  # local import — Pillow only needed for this function

    img = Image.open(path).convert("RGB")

    # Cap the longest edge
    if img.width > LOW_RES_MAX_DIM or img.height > LOW_RES_MAX_DIM:
        img.thumbnail((LOW_RES_MAX_DIM, LOW_RES_MAX_DIM), Image.LANCZOS)

    # Binary-search JPEG quality to hit the size target
    lo, hi = 10, 92
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=hi, optimize=True)
    if buf.tell() <= max_bytes:
        return buf.getvalue()

    while hi - lo > 2:
        mid = (lo + hi) // 2
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=mid, optimize=True)
        if buf.tell() <= max_bytes:
            lo = mid
        else:
            hi = mid

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=lo, optimize=True)
    return buf.getvalue()


# ── full-resolution sync ───────────────────────────────────────────────────────

def sync_directory(
    bucket: storage.Bucket,
    local_dir: Path,
    gcs_prefix: str,
    dry_run: bool,
    workers: int,
) -> tuple[int, int]:
    """Upload all files in local_dir to gs://bucket/gcs_prefix/ in parallel."""
    if not local_dir.exists():
        print(f"  [SKIP] {local_dir}/ does not exist locally")
        return 0, 0

    existing: dict[str, str] = {
        blob.name: blob.md5_hash
        for blob in bucket.list_blobs(prefix=gcs_prefix + "/")
    }

    files = [p for p in sorted(local_dir.rglob("*")) if p.is_file()]

    to_upload: list[tuple[Path, str]] = []
    skipped = 0
    for local_path in files:
        blob_name = f"{gcs_prefix}/{local_path.relative_to(local_dir).as_posix()}"
        if blob_name in existing and _md5_file(local_path) == existing[blob_name]:
            skipped += 1
        else:
            to_upload.append((local_path, blob_name))

    if dry_run:
        for local_path, blob_name in to_upload:
            print(f"  [DRY-RUN] would upload {local_path} → gs://{bucket.name}/{blob_name}")
        return len(to_upload), skipped

    print_lock = Lock()
    uploaded = errors = 0

    def _upload_file(local_path: Path, blob_name: str) -> bool:
        try:
            bucket.blob(blob_name).upload_from_filename(str(local_path))
            with print_lock:
                print(f"  Uploaded {local_path.name} → {blob_name}")
            return True
        except Exception as exc:
            with print_lock:
                print(f"  ERROR {local_path.name}: {exc}", file=sys.stderr)
            return False

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_upload_file, lp, bn): (lp, bn) for lp, bn in to_upload}
        for future in as_completed(futures):
            if future.result():
                uploaded += 1
            else:
                errors += 1

    if errors:
        print(f"  {errors} file(s) failed", file=sys.stderr)
    return uploaded, skipped


# ── low-res preview sync ───────────────────────────────────────────────────────

def sync_low_res_previews(
    bucket: storage.Bucket,
    local_images_dir: Path,
    dry_run: bool,
    workers: int,
) -> tuple[int, int]:
    """Compress first 3 figures per paper to JPEG <0.5 MB and upload to LOW_RES_GCS_PREFIX."""
    if not local_images_dir.exists():
        print(f"  [SKIP] {local_images_dir}/ does not exist locally")
        return 0, 0

    existing: dict[str, str] = {
        blob.name: blob.md5_hash
        for blob in bucket.list_blobs(prefix=LOW_RES_GCS_PREFIX + "/")
    }

    # Collect (paper_id, source_path, blob_name) for the first 3 figures of each paper
    tasks: list[tuple[str, Path, str]] = []

    for paper_dir in sorted(local_images_dir.iterdir()):
        if not paper_dir.is_dir():
            continue
        paper_id = paper_dir.name
        figures_json = paper_dir / "figures.json"

        if figures_json.exists():
            try:
                figures = json.loads(figures_json.read_text(encoding="utf-8")).get("figures", [])
                figure_names = [
                    Path(f["path"].replace("\\", "/")).name
                    for f in figures[:3]
                    if f.get("path")
                ]
            except Exception:
                figure_names = []
        else:
            figure_names = []

        # Fallback: first 3 image files sorted by name
        if not figure_names:
            figure_names = [
                p.name for p in sorted(paper_dir.iterdir())
                if p.is_file() and p.suffix.lower() in {".png", ".jpg", ".jpeg"}
            ][:3]

        for name in figure_names:
            src = paper_dir / name
            if not src.exists():
                continue
            stem = Path(name).stem
            blob_name = f"{LOW_RES_GCS_PREFIX}/{paper_id}/{stem}.jpg"
            tasks.append((paper_id, src, blob_name))

    if dry_run:
        for _, src, blob_name in tasks:
            print(f"  [DRY-RUN] would compress+upload {src.name} → gs://{bucket.name}/{blob_name}")
        return len(tasks), 0

    print_lock = Lock()
    uploaded = skipped = errors = 0

    def _process(paper_id: str, src: Path, blob_name: str) -> str:
        """Returns 'uploaded', 'skipped', or 'error'."""
        try:
            jpeg_bytes = _compress_to_jpeg(src)
        except Exception as exc:
            with print_lock:
                print(f"  ERROR compressing {src.name}: {exc}", file=sys.stderr)
            return "error"

        remote_md5 = existing.get(blob_name)
        if remote_md5 and _md5(jpeg_bytes) == remote_md5:
            return "skipped"

        try:
            blob = bucket.blob(blob_name)
            blob.upload_from_string(jpeg_bytes, content_type="image/jpeg")
            size_kb = len(jpeg_bytes) // 1024
            with print_lock:
                print(f"  Preview {paper_id}/{src.name} → {blob_name} ({size_kb} KB)")
            return "uploaded"
        except Exception as exc:
            with print_lock:
                print(f"  ERROR uploading {blob_name}: {exc}", file=sys.stderr)
            return "error"

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_process, pid, src, bn): bn for pid, src, bn in tasks}
        for future in as_completed(futures):
            outcome = future.result()
            if outcome == "uploaded":
                uploaded += 1
            elif outcome == "skipped":
                skipped += 1
            else:
                errors += 1

    if errors:
        print(f"  {errors} file(s) failed", file=sys.stderr)
    return uploaded, skipped


# ── main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Sync data/ to GCS")
    parser.add_argument("--dry-run",  action="store_true", help="Preview without uploading")
    parser.add_argument("--papers",   action="store_true", help="Sync only data/extracted_jsons/")
    parser.add_argument("--images",   action="store_true", help="Sync data/extracted_images/ + low-res previews")
    parser.add_argument("--previews", action="store_true", help="Sync only low-res previews")
    parser.add_argument("--workers",  type=int, default=16, help="Parallel upload workers (default: 16)")
    args = parser.parse_args()

    do_all = not (args.papers or args.images or args.previews)
    sync_papers   = do_all or args.papers
    sync_images   = do_all or args.images
    sync_previews = do_all or args.images or args.previews

    client = get_client()
    bucket = client.bucket(BUCKET_NAME)
    label = "[DRY-RUN] " if args.dry_run else ""
    print(f"{label}Target bucket: gs://{BUCKET_NAME}  ({args.workers} workers)\n")

    total_uploaded = total_skipped = 0

    if sync_papers:
        prefix = "data/extracted_jsons"
        local  = LOCAL_DIRS[prefix]
        print(f"── {local}/ → gs://{BUCKET_NAME}/{prefix}/")
        u, s = sync_directory(bucket, local, prefix, args.dry_run, args.workers)
        print(f"   {u} uploaded, {s} skipped\n")
        total_uploaded += u; total_skipped += s

    if sync_images:
        prefix = "data/extracted_images"
        local  = LOCAL_DIRS[prefix]
        print(f"── {local}/ → gs://{BUCKET_NAME}/{prefix}/")
        u, s = sync_directory(bucket, local, prefix, args.dry_run, args.workers)
        print(f"   {u} uploaded, {s} skipped\n")
        total_uploaded += u; total_skipped += s

    if sync_previews:
        local = LOCAL_DIRS["data/extracted_images"]
        print(f"── low-res previews → gs://{BUCKET_NAME}/{LOW_RES_GCS_PREFIX}/")
        u, s = sync_low_res_previews(bucket, local, args.dry_run, args.workers)
        print(f"   {u} uploaded, {s} skipped\n")
        total_uploaded += u; total_skipped += s

    print(f"Done. Total: {total_uploaded} uploaded, {total_skipped} skipped.")


if __name__ == "__main__":
    main()
