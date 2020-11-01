#!/usr/bin/python3
import os
import secrets
import string
import requests
import boto3
from flask import Flask, request, render_template
import qrcode


app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0


@app.route('/zip', methods=['POST'])
def zip_uri():
    try:
        # get timestamp and user_id
        request_json = request.get_json()
        timestamp = request_json['timestamp']
        user_id = request_json['user_id']
        # timestamp = 2659900
        # user_id = "551411c533835562"
        # fetch the newly generated Pks from the database
        get_newly_generated_pks_url = 'https://c77g8ibwfg.execute-api.us-east-2.amazonaws.com/getNewlyGeneratedPks'
        r = requests.post(get_newly_generated_pks_url, json={"timestamp": timestamp})
        # store the result to a json file
        json_file = open("/home/centos/exposure-notifications-server/examples/export/" + user_id + "-keys.json", "w")
        json_file.write(r.text)
        json_file.close()
        # generate the specific ZIP file
        os.chdir("/home/centos/exposure-notifications-server")
        os.system(
            "go run ./tools/export-generate --user-id=" + user_id + " --signing-key=./examples/export/private.pem --tek-file=./examples/export/" + user_id + "-keys.json")
        # upload the ZIP file to google cloud
        file_name = "tmp/testExport-" + user_id + ".zip"
        bucket= 'contact-tracing-demo'
        object_name = 'zips/'+ user_id + ".zip"
        s3_client = boto3.client('s3')
        s3_client.upload_file(file_name, bucket, object_name, ExtraArgs={'ACL': 'public-read'})

        # storage_client = storage.Client()
        # bucket = storage_client.get_bucket("contact_shield_demo")
        # blob = bucket.blob("zips/"+user_id + ".zip")
        # blob.upload_from_filename("tmp/testExport-" + user_id + ".zip")
        # return the URL of the ZIP file
        return "https://contact-tracing-demo.s3.us-east-2.amazonaws.com/zips/" + user_id + ".zip"
    except Exception as e:
        return 'Error: {}'.format(str(e)), 400


@app.route('/portal')
def home():

    guid = generate_qr_code()
    teletan = createTeleTAN()
    qrcode_path = 'https://contact-tracing-demo.s3.us-east-2.amazonaws.com/qrcodes/'+guid+'.jpg'
    return render_template("index.html", qrcode_path=qrcode_path, teletan=teletan)


def generate_qr_code():
    alphabet = string.ascii_letters + string.digits
    guid = ''.join(secrets.choice(alphabet) for i in range(32))
    full_filename = ('/tmp/'+guid+'.jpg')

    img = qrcode.make(guid)
    print(full_filename)
    img.save(full_filename)

    file_name = '/tmp/'+guid+'.jpg'
    bucket= 'contact-tracing-demo'
    object_name = 'qrcodes/'+guid+'.jpg'

    print(guid)
    s3_client = boto3.client('s3')
    s3_client.upload_file(file_name, bucket, object_name, ExtraArgs={'ACL': 'public-read'})

    return guid


def createTeleTAN():
    create_teletan_url = 'https://uf9taurs10.execute-api.us-east-2.amazonaws.com'
    r = requests.get(create_teletan_url)
    print(r.text)
    print(r.status_code)
    return r.text


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

