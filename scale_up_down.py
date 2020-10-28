#!/usr/bin/python

import requests
import json
import smtplib
import sys
import os
from datetime import datetime
from pytz import timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from string import Template
from email.MIMEMultipart import MIMEMultipart
from email.MIMEBase import MIMEBase
from email.MIMEText import MIMEText
from email.Utils import COMMASPACE, formatdate
from email import Encoders
from datetime import timedelta
import time
import logging
import csv
import ConfigParser

# set the log file name
timestr = time.strftime("%Y%m%d")
log = "/var/lib/jenkins/new-relic/scale_up_down_" + timestr + "_.log"
filepath = "/var/lib/jenkins/new-relic/response_time_" + timestr + ".csv"
config_file_path = "/var/lib/jenkins/new-relic/settings.cnf"

# Enable the logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# create file handler and set level to debug

handler = logging.FileHandler(log)
handler.setLevel(logging.DEBUG)

# create console handler and set level to debug
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)

formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
# add formatter to ch and handler
ch.setFormatter(formatter)
handler.setFormatter(formatter)

# add ch and handler  to logger
logger.addHandler(ch)
logger.addHandler(handler)

# variables

tz_utc = timezone("UTC")
config = ConfigParser.ConfigParser()
config.read(config_file_path)
condition_add_value = int(config.get('settings', 'condition_add_value'))
condition_add_value_first = int(config.get('settings', 'condition_add_value_first'))
condition_add_value_second = int(config.get('settings', 'condition_add_value_second'))
condition_add_value_third = int(config.get('settings', 'condition_add_value_third'))
condition_add_value_fourth = int(config.get('settings', 'condition_add_value_fourth'))
condition_remove_value_first = int(config.get('settings', 'condition_remove_value_first'))
condition_remove_value_second = int(config.get('settings', 'condition_remove_value_second'))
condition_remove_value_third = int(config.get('settings', 'condition_remove_value_third'))
condition_remove_value_fourth = int(config.get('settings', 'condition_remove_value_fourth'))
condition_remove_value_fifth = int(config.get('settings', 'condition_remove_value_fifth'))
condition_remove_value_sixth = int(config.get('settings', 'condition_remove_value_sixth'))
new_relic_tocken = config.get('settings', 'new_relic_tocken')
id = config.get('settings', 'id')
threshold_down_sec = int(config.get('settings', 'threshold_down_sec'))
threshold_up_sec = int(config.get('settings', 'threshold_up_sec'))
on_demand_count = int(config.get('settings', 'on_demand_count'))
group_id = config.get('settings', 'group_id')
token = config.get('settings', 'token')
smtp_server = config.get('settings', 'smtp_server')
smtp_username = config.get('settings', 'smtp_username')
smtp_password = config.get('settings', 'smtp_password')
smtp_port = config.get('settings', 'smtp_port')

url = 'https://api.newrelic.com/v2/applications/' + id + '/metrics/data.json'
scale_up = "/var/lib/jenkins/new-relic/instance_up.txt"
scale_down = "/var/lib/jenkins/new-relic/instance_down.txt"


def get_min_max_spotinst_values():
    url = "https://api.spotinst.io/aws/ec2/group/" + group_id
    headers = {
        "Authorization": "Bearer " + token,
        "Content-Type": "application/json"
    }
    res = requests.get(url, headers=headers)
    result = json.loads(res.content)
    logger.info("Spotinst Json Response from  - %s" % (
        result))
    for item in result['response']['items']:
        min_value = int(item['capacity']['minimum'])
        max_value = int(item['capacity']['maximum'])

    logger.info(" Spot Capacity Minimum Value - %s, Maximum Value - %s" % (
            min_value, max_value))

    return min_value, max_value

try:
    min_count, max_count = get_min_max_spotinst_values()
except Exception as e:
    logger.error("Error while fetching resonse from Spotinst - %s" % (
     e))
    max_count = int(config.get('settings', 'max_count'))
    min_count = int(config.get('settings', 'min_count'))


def csv_data(python_avg):
    f = open(filepath, "a")
    date_time = datetime.now()
    date_time = date_time.strftime("%Y-%m-%d %H:%M:%S")
    writer = csv.writer(f)
    # header
    url = "https://api.spotinst.io/aws/ec2/group/" + group_id
    date_time = datetime.now()
    date_time = date_time.strftime("%Y-%m-%d %H:%M:%S")
    headers = {
        "Authorization": "Bearer " + token,
        "Content-Type": "application/json"
    }
    res = requests.get(url, headers=headers)
    result = json.loads(res.content)
    for item in result['response']['items']:
        target_value_old = item['capacity']['target']
    instance_count = target_value_old + on_demand_count
    writer.writerow([date_time, python_avg[0], instance_count])
    f.close


def smtp_mail(SUBJECT, TEXT):
    FROM = 'bigbasket.alerts@powerupcloud.com'
    TO = ['bigbasket.alerts@powerupcloud.com', 'devops@bigbasket.com', 'rps-engineers+info@bigbasket.com']
    #TO = ['bigbasket.alerts@powerupcloud.com']
    smtp_do_tls = True
    # Create message container - the correct MIME type is multipart/alternative here!
    MESSAGE = MIMEMultipart('alternative')
    MESSAGE['subject'] = SUBJECT
    MESSAGE['To'] = ", ".join(TO)
    MESSAGE['From'] = FROM
    MESSAGE.preamble = """

    Your mail reader does not support the report format.
    Please visit us <a href="http://www.mysite.com">online</a>!"""

    TXT_BODY = MIMEText(TEXT, 'plain')
    MESSAGE.attach(TXT_BODY)

    try:
        # The actual sending of the e-mail
        server = smtplib.SMTP(
            host=smtp_server,
            port=smtp_port,
            timeout=10
        )
        server.set_debuglevel(10)
        server.starttls()
        server.ehlo()
        server.login(smtp_username, smtp_password)
        # Print debugging output when testing
        server.sendmail(FROM, TO, MESSAGE.as_string())
        server.quit()
    except Exception as e:
        logger.exception("Error in shooting email. Reason: %s", e)


def smtp_mail_bb(SUBJECT, TEXT):
    FROM = 'bigbasket.alerts@powerupcloud.com'
    TO = ['devops@bigbasket.com', 'rps-engineers+info@bigbasket.com','bigbasket.alerts@powerupcloud.com']
    smtp_do_tls = True
    # Create message container - the correct MIME type is multipart/alternative here!
    MESSAGE = MIMEMultipart('alternative')
    MESSAGE['subject'] = SUBJECT
    MESSAGE['To'] = ", ".join(TO)
    MESSAGE['From'] = FROM
    MESSAGE.preamble = """

    Your mail reader does not support the report format.
    Please visit us <a href="http://www.mysite.com">online</a>!"""

    TXT_BODY = MIMEText(TEXT, 'plain')
    MESSAGE.attach(TXT_BODY)

    try:
        # The actual sending of the e-mail
        server = smtplib.SMTP(
            host=smtp_server,
            port=smtp_port,
            timeout=10
        )
        server.set_debuglevel(10)
        server.starttls()
        server.ehlo()
        server.login(smtp_username, smtp_password)
        # Print debugging output when testing
        server.sendmail(FROM, TO, MESSAGE.as_string())
        server.quit()
    except Exception as e:
        logger.exception("Error in shooting email. Reason: %s", e)


# scale up funtion
def spot_inst_scaleup(python_avg_value, count):
    sub_python = []
    for value in python_avg_value:
        sub_python.append(str(round(float(value))).split('.')[0])
    logger.info("Scale up triggered")
    # define all the parameters
    url = "https://api.spotinst.io/aws/ec2/group/" + group_id
    date_time = datetime.now()
    date_time = date_time.strftime("%Y-%m-%d %H:%M:%S")
    headers = {
        "Authorization": "Bearer " + token,
        "Content-Type": "application/json"
    }
    res = requests.get(url, headers=headers)
    result = json.loads(res.content)
    print(result)
    for item in result['response']['items']:
        min_value_old = item['capacity']['minimum']
        max_value_old = item['capacity']['maximum']
        target_value_old = item['capacity']['target']

    current = int(target_value_old) + on_demand_count
    sub = max_count - current
    if sub < count:
        count = sub

    target_value = int(target_value_old) + int(count)

    print "target_old - {}".format(target_value_old)
    print "target_new - {}".format(target_value)
    logger.info("Current instance details min - %s, target - %s, max - %s, current - %s" % (
    min_value_old, target_value_old, max_value_old, current))
    if current >= max_count:
        SUB = "[IMP] BB | Scale Up - No instances Added - at " + date_time
        TEXT = "The total number of instances currently " + str(
            current) + " which is  greater than threshold count" + str(
            max_count) + ".  So there are no instances added to reduce the response time. Please check with the Bigbasket team and add it manually if required. Also find the details of response time: Python: " + str(
            python_avg_value)
        smtp_mail(SUB, TEXT)
        logger.info("Scale up - Total instances count has reached max threshold - %s" % (max_count))
        sys.exit(0)
    new = int(target_value) + on_demand_count
    payload = {
        "group": {
            "capacity": {
                "target": target_value
            }
        }
    }
    payload = json.dumps(payload)
    print payload
    try:
        res = requests.put(url, headers=headers, data=payload)
        print res.status_code, res.content
        assert res.status_code == 200
    except Exception as e:
        logger.exception("Scale up - Failed to update the Spot capacity")
        SUB = "BB | Newrelic Spike - FAILED to add instances at - " + date_time
        TEXT = "Hi Team, Failed to add the " + str(
            count) + " instances. Please check what went wrong in Spot function. Also add the instances manually"
        smtp_mail(SUB, TEXT)
    else:
        SUB = "BB | Scale: " + str(current) + " + " + str(count) + " = " + str(new) + " Resp: " + str(
            sub_python) + " ms at - " + date_time
        TEXT = "Hi Team,  We currently have " + str(current) + " instances and added " + str(
            count) + "  more instances to handle the traffic spike. The total count is " + str(
            new) + ". It will add more instances, if the response time has not reduced in the next 5 mins. Also find the details of response time: Python: " + str(
            python_avg_value)
        logger.info("Scale up - Updated the Spot Capacity target - %s, new - %s" % (
        target_value, new))
        smtp_mail_bb(SUB, TEXT)


# scale down function
def spot_inst_scaledown(python_avg_value, count, condition_remove_value):
    sub_python = []
    for value in python_avg_value:
        sub_python.append(str(round(float(value))).split('.')[0])
    logger.info("Scale down triggered")
    # define all the parameters
    url = "https://api.spotinst.io/aws/ec2/group/" + group_id
    date_time = datetime.now()
    date_time = date_time.strftime("%Y-%m-%d %H:%M:%S")
    headers = {
        "Authorization": "Bearer " + token,
        "Content-Type": "application/json"
    }
    res = requests.get(url, headers=headers)
    result = json.loads(res.content)
    print(result)
    for item in result['response']['items']:
        min_value_old = item['capacity']['minimum']
        max_value_old = item['capacity']['maximum']
        target_value_old = item['capacity']['target']

    target_value = int(target_value_old) - int(count)
    if target_value < 0:
        target_value = int(0)

    current = int(target_value_old) + on_demand_count
    logger.info("Current instance details min - %s, target - %s, max - %s, current - %s" % (
    min_value_old, target_value_old, max_value_old, current))
    if current <= min_count:
        SUB = "[IMP] BB | Scale Down - No instances reduced - at " + date_time
        TEXT = "The total number of instances currently " + str(current) + " which is at minimum threshold value " + str(
            min_count) + ".  So there are no instances removed."
        logger.info("Scale down - Total instance count has reached min threshold value %s" % (min_count))
        # smtp_mail(SUB, TEXT)
        sys.exit(0)
    new = int(target_value) + on_demand_count
    payload = {
        "group": {
            "capacity": {
                "target": target_value
            }
        }
    }
    payload = json.dumps(payload)
    try:
        res = requests.put(url, headers=headers, data=payload)
        print res.status_code, res.content
        assert res.status_code == 200
    except Exception as e:
        logger.exception("Scale up - Failed to update the Spot capacity")
        SUB = "BB | Newrelic Spike - FAILED to remove instances at - " + date_time
        TEXT = "Hi Team, Failed to remove the " + str(
            count) + " instances. Please check what went wrong in Spot function. Also remove the instances manually"
        smtp_mail(SUB, TEXT)
    else:
        if new == min_count:
            count = current - new
        SUB = "BB | Scale: " + str(current) + " - " + str(count) + " = " + str(new) + " Resp: " + str(
            sub_python) + " ms at - " + date_time
        TEXT = "Hi Team,  We currently have " + str(current) + " instances and removed " + str(
            count) + "  more instances due to python response time below threshold value " + str(
            condition_remove_value) + " ms. The total instance count is " + str(
            new) + ". Also find the details of response time: Python: " + str(python_avg_value)
        logger.info("Scale down - Updated the Spot Capacity target - %s, new - %s" % (
        target_value, new))
        smtp_mail_bb(SUB, TEXT)


def python_response(TO, FROM):
    # find different component response time
    headers = {
        "X-Api-Key": new_relic_tocken
    }
    data = ['MySQL', 'Elasticsearch', 'Solr', 'External', 'QueueTime']
    data_avg_value = []
    for data in data:
        payload = 'names[]=Datastore/' + data + '/allWeb&names[]=HttpDispatcher&values[]=average_response_time&values[]=call_count&from=' + FROM + '&to=' + TO + ''

        if data == "External":
            payload = 'names[]=External/allWeb&names[]=HttpDispatcher&values[]=average_response_time&values[]=call_count&from=' + FROM + '&to=' + TO + ''
        elif data == "QueueTime":
            payload = 'names[]=WebFrontend/' + data + '&values[]=average_response_time&from=' + FROM + '&to=' + TO + ''
        try:
            res = requests.get(url, headers=headers, params=payload)
            result = json.loads(res.content)
            print result
            if data == "QueueTime":
                avg_value = result['metric_data']['metrics'][0]['timeslices'][0]['values']['average_response_time']
            else:
                web_call_count = result['metric_data']['metrics'][0]['timeslices'][0]['values']['call_count']
                http_call_count = result['metric_data']['metrics'][1]['timeslices'][0]['values']['call_count']
                avg_res_time = result['metric_data']['metrics'][0]['timeslices'][0]['values']['average_response_time']
                avg_value = (avg_res_time * web_call_count) / http_call_count
            data_avg_value.append(avg_value)
        except Exception as e:
            logger.error("Newrelic api call error : %s"(e))
    # find the python response time
    payload = 'names[]=WebTransactionTotalTime&values[]=average_response_time&from=' + FROM + '&to=' + TO + ''
    try:
        res = requests.get(url, headers=headers, params=payload)
        result = json.loads(res.content)
    except Exception as e:
        logger.error("Newrelic api call error : %s"(e))

    avg_value = result['metric_data']['metrics'][0]['timeslices'][0]['values']['average_response_time']
    mysql_avg_value = data_avg_value[0]
    es_avg_value = data_avg_value[1]
    solr_avg_value = data_avg_value[2]
    external_avg_value = data_avg_value[3]
    queuetime_avg_value = data_avg_value[4]
    print ("Total value - %s" % (str(avg_value)))
    print ("mysql_avg_value -  %s" % (str(mysql_avg_value)))
    print ("solr_avg_value -  %s" % (str(solr_avg_value)))
    print ("es_avg_value - %s" % (str(es_avg_value)))
    print ("external_avg_value - %s" % (str(external_avg_value)))
    print ("queuetime_avg_value - %s" % (str(queuetime_avg_value)))
    python_avg_value1 = avg_value - (mysql_avg_value + solr_avg_value + es_avg_value + external_avg_value)
    python_avg_value = python_avg_value1 + queuetime_avg_value
    return python_avg_value


def data_value():
    ADD = False
    REMOVE = False
    tz_utc = timezone("UTC")
    python_avg = []
    start_time = datetime.now(tz_utc)
    # last 5 consecutive values
    for i in range(1, 6):
        sec = 60
        from_time = start_time + timedelta(seconds=-sec)
        FROM = from_time.strftime("%Y-%m-%dT%H:%M:%S")
        TO = start_time.strftime("%Y-%m-%dT%H:%M:%S")
        start_time = from_time
        python_avg_value = python_response(TO, FROM)
        python_avg.append(float(python_avg_value))
    # find the avg of the value
    print python_avg
    avg = sum(python_avg) / len(python_avg)
    python_avg = []
    python_avg.append(avg)
    ## If the response time of python is greater than 400 ms  last 5 min
    print("Python response time is %s ms" % (str(python_avg)))
    if all(float(avg_python) >= condition_add_value_first for avg_python in python_avg):
        ADD = True
        count = 3
    if all(float(avg_python) >= condition_add_value_second for avg_python in python_avg):
        ADD = True
        count = 4
    if all(float(avg_python) >= condition_add_value_third for avg_python in python_avg):
        ADD = True
        count = 8
    if all(float(avg_python) >= condition_add_value_fourth for avg_python in python_avg):
        ADD = True
        count = 10
    # If the response time of python is less than 200 ms last 5 min
    if all(float(avg_python) <= condition_remove_value_first for avg_python in python_avg):
        REMOVE = True
        count = 7
        condition_remove_value = condition_remove_value_first
    # If the response time of python is less than 240 ms last 5 min
    elif all(float(avg_python) <= condition_remove_value_second for avg_python in python_avg):
        REMOVE = True
        count = 6
        condition_remove_value = condition_remove_value_second
    # If the response time of python is less than 280 ms last 5 min
    elif all(float(avg_python) <= condition_remove_value_third for avg_python in python_avg):
        REMOVE = True
        count = 5
        condition_remove_value = condition_remove_value_third
    # If the response time of python is less than 320 ms last 5 min
    elif all(float(avg_python) <= condition_remove_value_fourth for avg_python in python_avg):
        REMOVE = True
        count = 4
        condition_remove_value = condition_remove_value_fourth
    # If the response time of python is less than 320 ms last 5 min
    elif all(float(avg_python) <= condition_remove_value_fifth for avg_python in python_avg):
        REMOVE = True
        count = 3
        condition_remove_value = condition_remove_value_fifth
    # If the response time of python is less than 320 ms last 5 min
    elif all(float(avg_python) <= condition_remove_value_sixth for avg_python in python_avg):
        REMOVE = True
        count = 2
        condition_remove_value = condition_remove_value_sixth

    print ADD
    print REMOVE
    if ADD:
        logger.info(
            "Python response time value is higher than %s ms. Response time is %s ms" % (condition_add_value, python_avg))
        if os.stat(scale_up).st_size != 0:
            f = open(scale_up, "r")
            lineList = f.readlines()
            last_time = lineList[-1].strip()
            print last_time
            f.close()
        current_datetime = datetime.now()
        last_datetime = datetime.strptime(last_time, "%Y-%m-%dT%H:%M:%S")
        diff_date_obj = current_datetime - last_datetime
        sec = diff_date_obj.total_seconds()
        if sec > int(threshold_up_sec):
            logger.info(
                "Scale up cooling period expired. The last activity happened at %s" % str(last_datetime))
            spot_inst_scaleup(python_avg, count)
            add_time = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
            f = open(scale_up, "a+")
            f.write("\n" + add_time)
            f.close()
        else:
            logger.info("The last scale up happened very recently")
    else:
        logger.info("No scale up as Python response time is below %s ms. Response time is %s ms" % (
        condition_add_value, python_avg))

    # For testing
    # REMOVE = True
    if REMOVE:
        logger.info(
            "Python response time value is lesser than %s ms. Response time is %s ms" % (condition_remove_value, python_avg))
        if os.stat(scale_down).st_size != 0:
            f = open(scale_down, "r")
            lineList = f.readlines()
            last_time = lineList[-1].strip()
            print last_time
            f.close()
        current_datetime = datetime.now()
        last_datetime = datetime.strptime(last_time, "%Y-%m-%dT%H:%M:%S")
        diff_date_obj = current_datetime - last_datetime
        sec = diff_date_obj.total_seconds()
        if sec > int(threshold_down_sec):
            logger.info("Scale down cooling period expired. The last activity happened at %s" % str(
                last_datetime))
            spot_inst_scaledown(python_avg, count, condition_remove_value)
            add_time = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
            f = open(scale_down, "a+")
            f.write("\n" + add_time)
            f.close()
        else:
            logger.info("The last scale down happened very recently")
    else:
        logger.info("No scale down as Python response time is above %s ms. Response time is %s ms" % (
        condition_remove_value_sixth, python_avg))
    csv_data(python_avg)


if __name__ == "__main__":
    logger.info("Scale up/down activity started")
    data_value()
    logger.info("Scale up/down activity finished")
