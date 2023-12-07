resource "yandex_function_trigger" "task-trigger" {
  name = "vvot${var.account_number}-task"
  message_queue {
    queue_id           = yandex_message_queue.task_queue.arn
    service_account_id = yandex_iam_service_account.service_account37.id
    batch_cutoff       = "0"
    batch_size         = "1"
  }
  function {
    id                 = yandex_function.face_cut_function.id
    service_account_id = yandex_iam_service_account.service_account37.id
  }
}