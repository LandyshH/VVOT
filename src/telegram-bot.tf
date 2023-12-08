resource "yandex_api_gateway" "default" {
  name        = "vvot${var.account_number}-apigw"
  spec        = <<-EOT
      openapi: "3.0.0"
      info:
        version: 1.0.0
        title: API
      paths:
        /faces/{face}:
          get:
            parameters:
              - name: face
                in: path
                description: User name to appear in greetings
                required: true
                schema:
                  type: string
            x-yc-apigateway-integration:
              type: object_storage
              bucket: ${yandex_storage_bucket.faces.id}
              object: '{face}'
              error_object: error.html
              service_account_id: ${yandex_iam_service_account.service_account37.id}
        /photo/{photo}:
          get:
            parameters:
              - name: photo
                in: path
                description: User name to appear in greetings
                required: true
                schema:
                  type: string
            x-yc-apigateway-integration:
              type: object_storage
              bucket: ${yandex_storage_bucket.photo.id}
              object: '{photo}'
              error_object: error.html
              service_account_id: ${yandex_iam_service_account.service_account37.id}
  EOT
}

data "archive_file" "telegram_bot_function_zip" {
  output_path = "telegram_bot_function.zip"
  type        = "zip"
  source_dir  = "Functions/TelegramBot"
}

resource "yandex_function" "telegram_bot" {
  name               = "vvot${var.account_number}-2023-boot"
  user_hash          = data.archive_file.telegram_bot_function_zip.output_base64sha256
  runtime            = "python312"
  entrypoint         = "index.handler"
  memory             = "128"
  execution_timeout  = "60"
  service_account_id = yandex_iam_service_account.service_account37.id
  environment = {
    "token" : var.bot_token,
    "ydb_endpoint" : "grpcs://${yandex_ydb_database_serverless.photo_face.ydb_api_endpoint}",
    "ydb_database" : yandex_ydb_database_serverless.photo_face.database_path,
    "ydb_table" : var.ydb_table,
    "face_uri" : "https://${yandex_api_gateway.default.id}.apigw.yandexcloud.net/faces",
    "photo_uri" : "https://${yandex_api_gateway.default.id}.apigw.yandexcloud.net/photo",
    "photo_bucket" : yandex_storage_bucket.photo.id,
    "AWS_ACCESS_KEY_ID" : yandex_iam_service_account_static_access_key.service_account37_keys.access_key,
    "AWS_SECRET_ACCESS_KEY" : yandex_iam_service_account_static_access_key.service_account37_keys.secret_key,
    "AWS_ENDPOINT_URL_S3" : var.storage_api_uri
  }
  content {
    zip_filename = data.archive_file.telegram_bot_function_zip.output_path
  }
}

resource "yandex_function_iam_binding" "telegram_bot_iam_binding" {
  function_id = yandex_function.telegram_bot.id
  role        = "serverless.functions.invoker"

  members = [
    "system:allUsers",
  ]
}

data "http" "webhook" {
  url = "https://api.telegram.org/bot${var.bot_token}/setWebhook?url=https://functions.yandexcloud.net/${yandex_function.telegram_bot.id}"
}

