data "archive_file" "zip_code_repo" {
  type        = "zip"
  source_dir  = "../../"
  output_path = "../../dist/function-source.zip"
  excludes = [
    "data",
    "debug",
    "dist",
    "deployment",
    "test",
    "venv",
    ".env",
    "example.env",
    ".gitignore",
    ".pre-commit-config.yaml",
    "CONTRIBUTING.md",
    "example.env",
    "LICENSE",
    "Makefile",
    "pyproject.toml",
    "requirements-dev.txt",
    "README.md",
  ]
}

resource "random_id" "bucket_prefix" {
  byte_length = 8
}

resource "google_storage_bucket" "cf_upload_bucket" {
  name                        = "dqm-cf-code-bucket-${random_id.bucket_prefix.hex}"
  location                    = var.cloud_function_region
  uniform_bucket_level_access = true
  force_destroy               = true
  project                     = var.project_id
  lifecycle_rule {
    condition {
      age = 1
    }
    action {
      type = "Delete"
    }
  }
}

resource "google_storage_bucket_object" "cf_upload_object" {
  name   = "function-source.zip"
  bucket = google_storage_bucket.cf_upload_bucket.name
  source = "../../dist/function-source.zip"
  depends_on = [
    data.archive_file.zip_code_repo
  ]
}

resource "google_cloudfunctions_function" "function" {
  name        = "data-quality-monitor"
  description = "Data quality monitor function to check rules on biquery datasets and log violations"
  runtime     = "python310"
  region      = var.cloud_function_region
  project     = var.project_id


  available_memory_mb   = 256
  source_archive_bucket = google_storage_bucket.cf_upload_bucket.name
  source_archive_object = google_storage_bucket_object.cf_upload_object.name
  trigger_http          = true
  timeout               = 540
  entry_point           = "app"
  service_account_email = google_service_account.main_account.email
  depends_on = [
    google_project_service.cloudfunctions,
    google_project_service.cloudbuild
  ]
}
