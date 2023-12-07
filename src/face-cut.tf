data "archive_file" "face_cut_function_zip" {
  output_path = "face_cut_function.zip"
  type        = "zip"
  source_dir  = "Functions"
}

resource "yandex_function" "face_cut_function" {
  name               = "vvot${var.account_number}-face-cut"
  user_hash          = data.archive_file.face_cut_function_zip.output_base64sha256
  runtime            = "python312"
  entrypoint         = "index.face_cut_handler"
  memory             = "128"
  execution_timeout  = "60"
  service_account_id = yandex_iam_service_account.service_account37.id
  environment = {
    "AWS_ACCESS_KEY_ID" : yandex_iam_service_account_static_access_key.service_account37_keys.access_key,
    "AWS_SECRET_ACCESS_KEY" : yandex_iam_service_account_static_access_key.service_account37_keys.secret_key,
    "AWS_ENDPOINT_URL_S3" : var.storage_api_uri,
    "faces_bucket_id" : yandex_storage_bucket.faces.id,
    "ydb_endpoint" : "grpcs://${yandex_ydb_database_serverless.photo_face.ydb_api_endpoint}",
    "ydb_database" : yandex_ydb_database_serverless.photo_face.database_path,
    "photo_bucket_id"  : yandex_storage_bucket.photo.id
  }
  content {
    zip_filename = data.archive_file.face_cut_function_zip.output_path
  }
}