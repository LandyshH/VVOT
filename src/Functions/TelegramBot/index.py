import json
import requests
import os
import ydb
import boto3
import string
import random

driver = ydb.Driver(
  endpoint=os.getenv('ydb_endpoint'),
  database=os.getenv('ydb_database'),
  credentials=ydb.iam.MetadataUrlCredentials(),
)

driver.wait(fail_fast=True, timeout=5)
pool = ydb.SessionPool(driver)

def find_name(user_name, session):
  query = f'''
    SELECT * FROM `{os.getenv('ydb_table')}`
    WHERE `user_name` = '{user_name}'
    LIMIT 10
    '''

  query = session.prepare(query)
  
  return session.transaction().execute(
    query,
    commit_tx=True,
    settings=ydb.BaseRequestSettings().with_timeout(3).with_operation_timeout(2)
  )

def get_face(session):
  query = f'''
    SELECT * FROM `{os.getenv('ydb_table')}`
    WHERE `user_name` IS NULL
    LIMIT 1
    '''

  query = session.prepare(query)
  
  return session.transaction().execute(
    query,
    commit_tx=True,
    settings=ydb.BaseRequestSettings().with_timeout(3).with_operation_timeout(2)
  )

def send_photo(telegram_file_id, name, session):
  query = f'''
    UPDATE `{os.getenv('ydb_table')}`
    SET `telegram_file_id` = '{telegram_file_id}'
    WHERE `name` = '{name}'
    '''

  query = session.prepare(query)
  
  return session.transaction().execute(
    query,
    commit_tx=True,
    settings=ydb.BaseRequestSettings().with_timeout(3).with_operation_timeout(2)
  )

def reply(telegram_file_id, user_name, session):
  query = f'''
    UPDATE `{os.getenv('ydb_table')}`
    SET `user_name` = '{user_name}'
    WHERE `telegram_file_id` = '{telegram_file_id}'
    '''

  query = session.prepare(query)
  
  return session.transaction().execute(
    query,
    commit_tx=True,
    settings=ydb.BaseRequestSettings().with_timeout(3).with_operation_timeout(2)
  )

def generate_random_string(length):
    characters = string.ascii_letters + string.digits
    random_string = ''.join(random.choices(characters, k=length))
    return random_string

def handler(event, context):
  token = os.environ["token"]
  update = json.loads(event["body"])
  message = update["message"]
  message_id = message["message_id"]
  chat_id = message["chat"]["id"]
  send_message_url = f'https://api.telegram.org/bot{token}/sendMessage'
  send_photo_url = f'https://api.telegram.org/bot{token}/sendPhoto'
  send_media_group_url = f'https://api.telegram.org/bot{token}/sendMediaGroup'

  if "text" in message and message["text"] == '/getface':
    result = pool.retry_operation_sync(get_face)[0]
    if len(result.rows) == 0:
      requests.get(
        url=send_message_url,
        params={
          "chat_id": chat_id,
          "text": "Нет доступных фотографий лиц",
          "reply_to_message_id": message_id
        }
      )
    else:
      name = result.rows[0].name
      response = requests.post(
        url=send_photo_url,
        data={
          "chat_id": chat_id,
          "photo": f'{os.getenv("face_uri")}/{name}',
          "reply_to_message_id": message_id
        }
      )
      file_id = json.loads(response.text)['result']['photo'][0]['file_id']
      pool.retry_operation_sync(lambda session: send_photo(file_id, name, session))
  elif "text" in message and message["text"].startswith('/find '):
    name = message["text"].split(" ", 1)[1]
    result = pool.retry_operation_sync(lambda session: find_name(name, session))
    if len(result[0].rows) == 0:
      requests.get(
        url=send_message_url,
        params={
          "chat_id": chat_id,
          "text": f'Фото с {name} не найдены' ,
          "reply_to_message_id": message_id
        }
      )
    else:
      links = [f'{os.getenv("photo_uri")}/{row.photo_id}' for row in result[0].rows]
      media_group = json.dumps(
        [{"type": "photo", "media": link} for link in links]
      )
      requests.post(
        url=send_media_group_url,
        data={
          "chat_id": chat_id,
          "media": media_group,
          "reply_to_message_id": message_id
        }
      )
  elif 'reply_to_message' in message and "photo" in message['reply_to_message'] and len(message['reply_to_message']["photo"]) > 0:
    file_id = message['reply_to_message']['photo'][0]['file_id']
    user_defined_name = message['text']
    pool.retry_operation_sync(lambda session: reply(file_id, user_defined_name, session))
    requests.get(
      url=send_message_url,
      params={
        "chat_id": chat_id,
        "text": "Имя записано",
        "reply_to_message_id": message_id
      }
    )
  elif "photo" in message and len(message["photo"]) > 0:
    photos = list(filter(lambda x: x['file_size'] <= 1024 ** 2, message['photo']))
    
    if len(photos) == 0:
      requests.get(
        url=send_message_url,
        params={
          "chat_id": chat_id,
          "text": "Превышен допустимый размер файла" ,
          "reply_to_message_id": message_id
        }
      )
    else:
      photo = max(photos, key=lambda x: x['file_size'])
      get_file_url = f'https://api.telegram.org/bot{token}/getFile?file_id={photo["file_id"]}'
      file_path_response = requests.get(get_file_url)
      file_path = file_path_response.json()['result']['file_path']
      
      file_url = f'https://api.telegram.org/file/bot{token}/{file_path}'
      image_response = requests.get(file_url)

      session = boto3.session.Session()
      storage = session.client(service_name='s3')
      storage.put_object(
        Bucket=os.getenv('photo_bucket'),
        Key=generate_random_string(10) + ".jpg",
        Body=image_response.content
      )

      requests.get(
        url=send_message_url,
        params={
          "chat_id": chat_id,
          "text": "Фото отправлено" ,
          "reply_to_message_id": message_id
        }
      )
  else:
    requests.get(
      url=send_message_url,
      params={
        "chat_id": chat_id,
        "text": "Ошибка" ,
        "reply_to_message_id": message_id
      }
    )

  return {
    "statusCode": 200
  }