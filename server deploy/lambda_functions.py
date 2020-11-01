# Function list:
#   1. createTeleTAN
#   2. getNewlyGeneratedPks
#   3. getRegistrationKeyGUID
#   4. getRegistrationKeyTELETAN
#   5. getTAN
#   6. verifyTAN
#   7. uploadPeriodicKeys

# createTeleTAN

import sys
import logging
import pymysql
import secrets
from hashlib import sha256
import string
#rds settings
rds_host  = "PLEASE ENTER DATABSE ENDPOINT HERE"
name = "PLEASE ENTER USERNAME HERE"
password = "PLEASE ENTER PASSWORD HERE"
db_name = "contact_shield_demo"

digits = string.digits

logger = logging.getLogger()
logger.setLevel(logging.INFO)

try:
    conn = pymysql.connect(rds_host, user=name, passwd=password, db=db_name, connect_timeout=5)
except pymysql.MySQLError as e:
    logger.error("ERROR: Unexpected error: Could not connect to MySQL instance.")
    logger.error(e)
    sys.exit()

logger.info("SUCCESS: Connection to RDS MySQL instance succeeded")

def handler(event, context):

    teletan = ''.join(secrets.choice(digits) for i in range(6))
    teletan_hashed = sha256(teletan.encode('ascii')).hexdigest()
    
    with conn.cursor() as cur:
        cur.execute("insert into registration_keys (source_type, teletan_hashed) values (%s, %s);", ("TELETAN", teletan_hashed))
        conn.commit()
        
    return {
        'statusCode': 200,
        'body':  teletan
    }


# getNewlyGeneratedPks

import sys
import logging
import pymysql
import secrets
from hashlib import sha256
#rds settings
rds_host  = "PLEASE ENTER DATABSE ENDPOINT HERE"
name = "PLEASE ENTER USERNAME HERE"
password = "PLEASE ENTER PASSWORD HERE"
db_name = "contact_shield_demo"

logger = logging.getLogger()
logger.setLevel(logging.INFO)

try:
    conn = pymysql.connect(rds_host, user=name, passwd=password, db=db_name, connect_timeout=5)
except pymysql.MySQLError as e:
    logger.error("ERROR: Unexpected error: Could not connect to MySQL instance.")
    logger.error(e)
    sys.exit()

logger.info("SUCCESS: Connection to RDS MySQL instance succeeded")

def handler(event, context):
    
    timestamp = event['timestamp']
    logger.info(timestamp)
    
    with conn.cursor() as cur:
        cur.execute('select * from periodic_keys where (UNIX_TIMESTAMP(timestamp)*1000) >= %s', (str(timestamp)))
        ResultSet = cur.fetchall()
        keys = []
        
        for result in ResultSet:
            content = {'key': result[11], 'rollingStartNumber': result[2], 'rollingPeriod': result[3], 'transmissionRisk': result[4]}
            keys.append(content)
    
    return {
        'statusCode': 200,
        'body':  keys
    }


# getRegistrationKeyGUID

import sys
import logging
import pymysql
import secrets
from hashlib import sha256
import string
import json
#rds settings
rds_host  = "PLEASE ENTER DATABSE ENDPOINT HERE"
name = "PLEASE ENTER USERNAME HERE"
password = "PLEASE ENTER PASSWORD HERE"
db_name = "contact_shield_demo"

logger = logging.getLogger()
logger.setLevel(logging.INFO)

try:
    conn = pymysql.connect(rds_host, user=name, passwd=password, db=db_name, connect_timeout=5)
except pymysql.MySQLError as e:
    logger.error("ERROR: Unexpected error: Could not connect to MySQL instance.")
    logger.error(e)
    sys.exit()

logger.info("SUCCESS: Connection to RDS MySQL instance succeeded")

def handler(event, context):
    event_json = json.loads(event['body'])
    logger.info(event_json)

    guid = event_json['guid']    
    alphabet = string.ascii_letters + string.digits
    guid_hashed = sha256(guid.encode('ascii')).hexdigest()
    
    with conn.cursor() as cur:
        cur.execute("select registration_key_hashed from registration_keys where source_type = 'GUID' and guid_hashed = %s ", (guid_hashed))
        resultSet = cur.fetchall()
        
        if(len(resultSet) > 0):
            # delete corresponding registration_key and tan
            registration_key_hashed = resultSet[0][0]
            cur.execute("delete from registration_keys where source_type = 'GUID' and guid_hashed = %s", (guid_hashed))
            cur.execute("delete from tans where registration_key_hashed = %s", (registration_key_hashed))
            
        new_registration_key = ''.join(secrets.choice(alphabet) for i in range(32))
        new_registration_key_hashed = sha256(new_registration_key.encode('ascii')).hexdigest()

        cur.execute("insert into registration_keys (registration_key_hashed, source_type, guid_hashed) values (%s, 'GUID', %s)", (new_registration_key_hashed, guid_hashed))

    conn.commit()
    
    return {
        'statusCode': 200,
        'body':  new_registration_key
    }

# getRegistrationKeyTELETAN

import sys
import logging
import pymysql
import secrets
from hashlib import sha256
import string
import json
#rds settings
rds_host  = "PLEASE ENTER DATABSE ENDPOINT HERE"
name = "PLEASE ENTER USERNAME HERE"
password = "PLEASE ENTER PASSWORD HERE"
db_name = "contact_shield_demo"

logger = logging.getLogger()
logger.setLevel(logging.INFO)

try:
    conn = pymysql.connect(rds_host, user=name, passwd=password, db=db_name, connect_timeout=5)
except pymysql.MySQLError as e:
    logger.error("ERROR: Unexpected error: Could not connect to MySQL instance.")
    logger.error(e)
    sys.exit()

logger.info("SUCCESS: Connection to RDS MySQL instance succeeded")

def handler(event, context):
    
    alphabet = string.ascii_letters + string.digits
    teletan = json.loads(event['body'])['teletan']
    teletan_hashed = sha256(teletan.encode('ascii')).hexdigest()

    with conn.cursor() as cur:
        cur.execute("select * from registration_keys " \
        "where source_type = 'TELETAN' " \
        "and registration_key_hashed is NULL " \
        "and teletan_hashed = %s and create_time <  DATE_SUB(current_timestamp, INTERVAL 30 minute)", (teletan_hashed))
        resultSet = cur.fetchall()
        
        if(len(resultSet) > 0):
            # raise Exception("TeleTAN Timeout")
            
            return {
                'statusCode': 305,
                'body':  'TeleTAN Timeout'
            }
            # delete corresponding registration_key and tan

        cur.execute("select * from registration_keys where source_type = 'TELETAN' and registration_key_hashed is NULL and teletan_hashed = %s", (teletan_hashed))
        resultSet = cur.fetchall()
            
        if(len(resultSet) > 0):
            logger.info(resultSet[0][0])
            # generate correspoding registration key
            registration_key = ''.join(secrets.choice(alphabet) for i in range(32))
            registration_key_hashed = sha256(registration_key.encode('ascii')).hexdigest()
            cur.execute("update registration_keys " \
            "set registration_key_hashed = %s, validate_time = current_timestamp " \
            "where source_type = 'TELETAN' and teletan_hashed = %s;", (registration_key_hashed, teletan_hashed))
            conn.commit()
            
        else:
            # raise Exception("TELETAN INVALID")
            return {
                'statusCode': 305,
                'body':  'TELETAN INVALID'
            }


    return {
        'statusCode': 200,
        'body':  registration_key
    }

# getTAN

import sys
import logging
import pymysql
import secrets
from hashlib import sha256
import string
import json
#rds settings
rds_host  = "PLEASE ENTER DATABSE ENDPOINT HERE"
name = "PLEASE ENTER USERNAME HERE"
password = "PLEASE ENTER PASSWORD HERE"
db_name = "contact_shield_demo"

logger = logging.getLogger()
logger.setLevel(logging.INFO)

try:
    conn = pymysql.connect(rds_host, user=name, passwd=password, db=db_name, connect_timeout=5)
except pymysql.MySQLError as e:
    logger.error("ERROR: Unexpected error: Could not connect to MySQL instance.")
    logger.error(e)
    sys.exit()

logger.info("SUCCESS: Connection to RDS MySQL instance succeeded")

def handler(event, context):
    
    alphabet = string.ascii_letters + string.digits
    registration_key = json.loads(event['body'])['registration_key']
    registration_key_hashed = sha256(registration_key.encode('ascii')).hexdigest()
    
    with conn.cursor() as cur:
        cur.execute("select source_type from registration_keys where registration_key_hashed = %s", (registration_key_hashed))
        resultSet = cur.fetchall()
        
        if(len(resultSet) > 0):
            source_type = resultSet[0][0]
            logger.info(source_type)
            is_guid_and_tested_positive = False
            if source_type == "GUID":
              # TODO get test result from testing center
              is_guid_and_tested_positive = True
    
            if is_guid_and_tested_positive or resultSet[0][0] == "TELETAN":
              # generate a new tan for registration_key
              tan = ''.join(secrets.choice(alphabet) for i in range(16))
              tan_hashed = sha256(tan.encode('ascii')).hexdigest()
              cur.execute('delete from tans where registration_key_hashed = "'+str(registration_key_hashed)+'";')
              conn.commit()
    
              cur.execute("insert into tans (registration_key_hashed, tan_hashed) values (%s , %s)", (registration_key_hashed, tan_hashed))
              conn.commit()
         
        return {
            'statusCode': 200,
            'body':  tan
        }

# verifyTAN

import sys
import logging
import pymysql
import secrets
from hashlib import sha256
import json
import string
#rds settings
rds_host  = "PLEASE ENTER DATABSE ENDPOINT HERE"
name = "PLEASE ENTER USERNAME HERE"
password = "PLEASE ENTER PASSWORD HERE"
db_name = "contact_shield_demo"

logger = logging.getLogger()
logger.setLevel(logging.INFO)

alphabet = string.ascii_letters + string.digits

try:
    conn = pymysql.connect(rds_host, user=name, passwd=password, db=db_name, connect_timeout=5)
except pymysql.MySQLError as e:
    logger.error("ERROR: Unexpected error: Could not connect to MySQL instance.")
    logger.error(e)
    sys.exit()

logger.info("SUCCESS: Connection to RDS MySQL instance succeeded")

def handler(event, context):

    tan = json.loads(event['body'])['tan']
    logger.info(tan)
    tan_hashed = sha256(tan.encode('ascii')).hexdigest()
    
    with conn.cursor() as cur:
        cur.execute("select * from tans where tan_hashed = %s and create_time <  DATE_SUB(current_timestamp, INTERVAL 5 minute);", (tan_hashed))
        resultSet = cur.fetchall()
        if(len(resultSet) > 0):
            return {
                'statusCode': 305,
                'body':  'Tan Timeout'
            }
            
        cur.execute("select * from tans where tan_hashed = %s", (tan_hashed))
        resultSet = cur.fetchall()
        if(len(resultSet) > 0):
            cur.execute("delete from tans where tan_hashed = %s", (tan_hashed))
            conn.commit()
            return {
                'statusCode': 200,
                'body':  'Success'
            }
        else:
            return {
                'statusCode': 305,
                'body':  'Verify Failed'
            }


# uploadPeriodicKeys

import sys
import logging
import pymysql
import secrets
from hashlib import sha256
import json
import requests
#rds settings
rds_host  = "PLEASE ENTER DATABSE ENDPOINT HERE"
name = "PLEASE ENTER USERNAME HERE"
password = "PLEASE ENTER PASSWORD HERE"
db_name = "contact_shield_demo"

logger = logging.getLogger()
logger.setLevel(logging.INFO)

verify_url = 'PLEASE ENTER THE INVOKE URL OF THE VERIFYTAN FUNCTION DEFINED ABOVE'

try:
    conn = pymysql.connect(rds_host, user=name, passwd=password, db=db_name, connect_timeout=5)
except pymysql.MySQLError as e:
    logger.error("ERROR: Unexpected error: Could not connect to MySQL instance.")
    logger.error(e)
    sys.exit()

logger.info("SUCCESS: Connection to RDS MySQL instance succeeded")

def handler(event, context):

    event_json = json.loads(event['body'])
    periodic_keys = event_json['periodic_keys']
    api_level = event_json['api_level']
    android_version = event_json['android_version']
    brand = event_json['brand']
    model = event_json['model']
    user_id = event_json['user_id']
    tan = event_json['tan']
    
    payload = {'tan': tan}
    r = requests.post(url = verify_url, json = payload)

    if r.text == 'Success':  
        with conn.cursor() as cur:
            for periodic_key in periodic_keys:
                  pk = periodic_key['pk']
                  valid_time = periodic_key['valid_time']
                  life_time = periodic_key['life_time']
                  risk_level = periodic_key['risk_level']
                  gms_key = periodic_key['gms_key']
                  cur.execute("insert into periodic_keys (pk, valid_time, life_time, risk_level, gms_key, api_level, android_version, brand, model, user_id) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);", 
                  (pk, valid_time, life_time, risk_level, gms_key, api_level, android_version, brand, model, user_id))
                  conn.commit()
            
            return {
                'statusCode': 200,
                'body':  'OK'
            }
            
    else:
        
        return {
            'statusCode': 305,
            'body': 'Validation Failed'
        }





