terraform {
  backend "gcs" {
    # bucket is passed at init time via -backend-config="bucket=..."
    prefix = "terraform/state"
  }

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }

  required_version = ">= 1.9"
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# ── Backend (FastAPI) ─────────────────────────────────────────────────────────

resource "google_cloud_run_v2_service" "backend" {
  name     = "${var.project_name}-backend-${var.environment}"
  location = var.region

  template {
    containers {
      image = var.backend_image

      ports {
        container_port = 8000
      }

      env {
        name  = "GCS_BUCKET"
        value = var.gcs_bucket
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }
    }

    scaling {
      min_instance_count = 0
      max_instance_count = 3
    }
  }
}

resource "google_cloud_run_v2_service_iam_member" "backend_public" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.backend.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# ── Frontend (Next.js) ────────────────────────────────────────────────────────

resource "google_cloud_run_v2_service" "frontend" {
  name     = "${var.project_name}-frontend-${var.environment}"
  location = var.region

  template {
    containers {
      image = var.frontend_image

      ports {
        container_port = 3000
      }

      env {
        name  = "BACKEND_URL"
        # Next.js rewrites in next.config.mjs read this at server startup
        value = google_cloud_run_v2_service.backend.uri
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }
    }

    scaling {
      min_instance_count = 0
      max_instance_count = 3
    }
  }
}

resource "google_cloud_run_v2_service_iam_member" "frontend_public" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.frontend.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
