data "archive_file" "zip" {
  output_path = "function.zip"
  type        = "zip"
  source_dir  = "Functions"
}

resource "yandex_function" "face_detection_function" {
  name               = "vvot${var.account_number}-face-detection"
  user_hash          = data.archive_file.zip.output_base64sha256
  runtime            = "python312"  
  entrypoint         = "index.face_detection_handler"   
  memory             = "128"
  execution_timeout  = "60"
  service_account_id = yandex_iam_service_account.service_account37.id
  environment = {
    "folder_id"       = var.folder_id,
    "vision_api_uri"   = var.vision_api_uri,
    "storage_api_uri"  = var.storage_api_uri,
    "queue_id" = yandex_message_queue.task_queue.id,
    "queue_uri" : var.queue_uri,
    "yandex_vision_api_key"  = yandex_iam_service_account_api_key.account37.secret_key,
    "AWS_ACCESS_KEY_ID"      = yandex_iam_service_account_static_access_key.service_account37_keys.access_key,
    "AWS_SECRET_ACCESS_KEY"  = yandex_iam_service_account_static_access_key.service_account37_keys.secret_key,
    "AWS_DEFAULT_REGION"         = "ru-central1",
    "AWS_ENDPOINT_URI_S3" = var.storage_api_uri
  }
  content {
    zip_filename = "function.zip"
  }
}
