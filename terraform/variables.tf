variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "us-central1"
}

variable "project_name" {
  description = "Project name prefix used for Cloud Run service names"
  type        = string
  default     = "sismica-marina"
}

variable "environment" {
  description = "Deployment environment: prod or dev"
  type        = string
}

variable "backend_image" {
  description = "Fully-qualified backend Docker image URL (registry/project/name:tag)"
  type        = string
}

variable "frontend_image" {
  description = "Fully-qualified frontend Docker image URL (registry/project/name:tag)"
  type        = string
}
