# Small, cheap GKE cluster for the cloud version of the demo: one zone, two spot e2-medium nodes,
# plus an Artifact Registry repo for the images. `terraform destroy` removes all of it.
terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }
}

variable "project_id" {
  type = string
}

variable "region" {
  type    = string
  default = "asia-south1" # Mumbai
}

variable "zone" {
  type    = string
  default = "asia-south1-a"
}

provider "google" {
  project = var.project_id
  region  = var.region
}

resource "google_container_cluster" "demo" {
  name                     = "canary-demo"
  location                 = var.zone # zonal: one control plane, covered by the GKE free tier
  remove_default_node_pool = true
  initial_node_count       = 1
  deletion_protection      = false
}

resource "google_container_node_pool" "nodes" {
  name       = "nodes"
  cluster    = google_container_cluster.demo.name
  location   = var.zone
  node_count = 2

  node_config {
    machine_type = "e2-medium"
    spot         = true
    disk_size_gb = 30
    oauth_scopes = ["https://www.googleapis.com/auth/cloud-platform"]
  }
}

resource "google_artifact_registry_repository" "images" {
  location      = var.region
  repository_id = "tickets"
  format        = "DOCKER"
}

output "registry" {
  value = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.images.repository_id}"
}

output "get_credentials" {
  value = "gcloud container clusters get-credentials ${google_container_cluster.demo.name} --zone ${var.zone} --project ${var.project_id}"
}
