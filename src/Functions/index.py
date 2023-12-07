import boto3
import base64
import requests
from PIL import Image
import io
import json
import os
import ydb
import random
import string

def face_detection_handler(event, context):
    yandex_vision_api_key = os.getenv('yandex_vision_api_key')
    vision_api_uri = os.getenv('vision_api_uri')
    folder_id = os.getenv('folder_id')
    
    image_id = event['messages'][0]['details']['object_id']
    bucket_id = event['messages'][0]['details']['bucket_id']
    
    session = boto3.session.Session()
    s3_client = session.client(
        service_name='s3',
        endpoint_url='https://storage.yandexcloud.net'
    )

    response = s3_client.get_object(Bucket=bucket_id, Key=image_id)
    
    image_data = response['Body'].read()

    base64_image = base64.b64encode(image_data).decode('utf-8')

    headers = {
        'Authorization': f'Api-Key {yandex_vision_api_key}',
        'Content-Type': 'application/json',
        'x-folder-id': folder_id
    }
   
    params = {
        'folderId': folder_id,  
        'analyze_specs': [{
            'content': base64_image,
            'features': [{
                'type': 'FACE_DETECTION'
            }]
        }]
    }

    response = requests.post(vision_api_uri, headers=headers, json=params)
    print(response.text)

    faces = response.json()["results"][-1]["results"][-1]["faceDetection"]["faces"]
    print(faces)
        
    for face in faces:
        coordinates = face['boundingBox']['vertices']
        message_body = json.dumps({
            "image_id": image_id,
            "coordinate": coordinates
        })

        ymq_client = session.client(
            service_name='sqs',
            endpoint_url=os.getenv('queue_uri'),
            region_name='ru-central1'
        )

        print("Отправка сообщения в очередь:", message_body)
        r = ymq_client.send_message(QueueUrl=os.getenv('queue_id'), MessageBody=message_body)
        print("Ответ от SQS:", r)

       
        print(r)


def generate_random_string(length):
    characters = string.ascii_letters + string.digits
    random_string = ''.join(random.choices(characters, k=length))
    return random_string

def proccess_message_db(message, name, session):
    query = f'''
        DECLARE $name AS Utf8;
        DECLARE $photo_id AS Utf8;

        UPSERT INTO `faces` (`name`, `photo_id`)
        VALUES (
            $name,
            $photo_id
        )
        '''

    params = {
        '$name': name,
        '$photo_id': message['image_id']
    }

    query = session.prepare(query)
    return session.transaction().execute(
        query,
        params,
        commit_tx=True,
        settings=ydb.BaseRequestSettings().with_timeout(3).with_operation_timeout(2)
    )

def proccess_message(message):
    session = boto3.session.Session()
    storage = session.client(service_name='s3')

    print('image_id  ', message['image_id'])
    print('photo_bucket_id', os.environ['photo_bucket_id'])
    image = storage.get_object(
        Bucket=os.environ['photo_bucket_id'],
        Key=message['image_id']
    )['Body']

    image = Image.open(io.BytesIO(image.read()))
    
    coordinates = message['coordinate']
    left = int(coordinates[0]['x'])
    top = int(coordinates[0]['y'])
    right = int(coordinates[2]['x'])
    bottom = int(coordinates[2]['y'])
     
    face_image = image.crop((left, top, right, bottom))

    face_image_bytes = io.BytesIO()
    face_image.save(face_image_bytes, format='JPEG')
    face_image_bytes.seek(0)
    key = generate_random_string(10) + '.jpg'

    storage.put_object(
        Bucket=os.environ['faces_bucket_id'],
        Body=face_image_bytes,
        Key=key
    )

    driver = ydb.Driver(
        endpoint=os.environ['ydb_endpoint'],
        database=os.environ['ydb_database'],
        credentials=ydb.iam.MetadataUrlCredentials(),
    )

    driver.wait(fail_fast=True, timeout=5)

    pool = ydb.SessionPool(driver)

    pool.retry_operation_sync(lambda session: proccess_message_db(message, key, session))

def face_cut_handler(event, context):
    for message in event['messages']:
        json_body = message['details']['message']['body']
        message = json.loads(json_body)
        print('message', message)
        proccess_message(message)