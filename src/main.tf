terraform {
  required_providers {
    yandex = {
      source = "yandex-cloud/yandex"
    }
  }
  required_version = ">= 0.13"
}

locals {
  zone                            = "ru-central1-a"
  service_account_key_file        = "key.json"
  prefix                          = "vvot${var.account_number}"
  photo_faces_database_faces_path = "faces"
}

provider "yandex" {
  service_account_key_file = local.service_account_key_file
  cloud_id                 = var.cloud_id
  folder_id                = var.folder_id
  zone                     = local.zone
}

resource "yandex_iam_service_account" "service_account37" {
  folder_id   = var.folder_id
  name        = "service-account37"
}

resource "yandex_resourcemanager_folder_iam_member" "service_account37_member" {
  folder_id = var.folder_id
  role      = "admin"
  member    = "serviceAccount:${yandex_iam_service_account.service_account37.id}"
}

resource "yandex_iam_service_account_static_access_key" "service_account37_keys" {
  service_account_id = yandex_iam_service_account.service_account37.id
}

resource "yandex_iam_service_account_api_key" "account37" {
  service_account_id = yandex_iam_service_account.service_account37.id
}

resource "yandex_storage_bucket" "photo" {
  access_key = yandex_iam_service_account_static_access_key.service_account37_keys.access_key
  secret_key = yandex_iam_service_account_static_access_key.service_account37_keys.secret_key
  bucket     = "vvot${var.account_number}-photo"
  anonymous_access_flags {
    read = false
    list = false
  }
}

resource "yandex_storage_bucket" "faces" {
  bucket     = "vvot${var.account_number}-faces"
  access_key = yandex_iam_service_account_static_access_key.service_account37_keys.access_key
  secret_key = yandex_iam_service_account_static_access_key.service_account37_keys.secret_key
}

resource "yandex_message_queue" "task_queue" {
  name       = "vvot${var.account_number}-task"
  access_key = yandex_iam_service_account_static_access_key.service_account37_keys.access_key
  secret_key = yandex_iam_service_account_static_access_key.service_account37_keys.secret_key
}

resource "yandex_ydb_database_serverless" "photo_face" {
  name = "vvot${var.account_number}-db-photo-face"
  serverless_database {
    storage_size_limit = 5
  }
}

resource "yandex_ydb_table" "faces" {
  path              = local.photo_faces_database_faces_path
  connection_string = yandex_ydb_database_serverless.photo_face.ydb_full_endpoint
  primary_key       = ["name"]

  column {
    name     = "name"
    type     = "Utf8"
    not_null = true
  }
  column {
    name = "user_name"
    type = "Utf8"
  }

  column {
    name = "photo_id"
    type = "Utf8"
  }

  column {
    name = "telegram_file_id"
    type = "Utf8"
  }
}