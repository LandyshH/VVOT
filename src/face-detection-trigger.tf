resource "yandex_function_trigger" "face_detection_function_trigger" {
  name        = var.face_detection_trigger_name
  object_storage {
    bucket_id    = yandex_storage_bucket.photo.id
    create       = true
    delete       = false
    update       = false
    suffix       = ".jpg"
    batch_cutoff = ""
  }
  function {
    id                 = yandex_function.face_detection_function.id
    service_account_id = yandex_iam_service_account.service_account37.id
  }
}