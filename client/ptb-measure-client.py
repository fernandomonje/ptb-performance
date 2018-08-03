#!/usr/bin/python
import time
import requests
import json
import time
from datetime import datetime
import re
import pyping
import StringIO

# Global Variables Denifitions
# Global Variables Settings

HOST_NAME = '10.200.120.8'
PORT_NUMBER = 9995
API_VERSION = 'v1'
BASE_URL = '/api/v1'

class Environment:
  def __init__(self, properties):
    self.server = properties['server']
    self.port = properties['port']
    self.api_version = properties['api_version']
    self.log_size_limit = properties['log_size_limit']
    self.measure_interval = properties['measure_interval']

  def get_server(self):
    return self.server
  def get_port(self):
    return self.port
  def get_api_version(self):
    return self.api_version
  def get_log_size_limit(self):
    return self.log_size_limit
  def get_measure_interval(self):
    return self.measure_interval

def get_seconds(datetime):
  time = datetime.split(' ')[4].split(':')
  time_hours = int(time[0])
  time_minutes = int(time[1])
  time_seconds = int(time[2])
  return time_hours*360 + time_minutes*60 + time_seconds

def properties_loader(propertie_file='./client.properties'): 
  properties = json.loads(open('./client.properties', 'r').read())['ptb_client']
  return properties

def download_measure(properties):
  return_data = {}
  url = 'http://' + properties['server'] + ':' + properties['port'] + '/api/' + properties['api_version'] + '/data'
  print url
  current_seconds = int(datetime.now().strftime("%S"))
  req = requests.get(url)
  file = StringIO.StringIO() 
  file.write(req.content)
  file_size = int(req.headers['Content-Length'])/1000
  #dl_seconds = get_seconds(time.asctime())
  dl_seconds = int(datetime.now().strftime("%S"))
  time_difference = dl_seconds - current_seconds
  return_data = {'measure': round(file_size / time_difference), 'file' : file}
  return return_data

def upload_measure(properties, dummy_file):
  return_data = {}
  current_seconds = int(datetime.now().strftime("%S"))
  post_url = 'http://' + properties['server'] + ':' + properties['port'] + '/api/' + properties['api_version'] + '/data/upload'
  request = requests.post(post_url, files=dummy_file)
  dummy_file.seek(0,2)
  file_size = int(dummy_file.tell()) / 1000
  #dl_seconds = get_seconds(time.asctime())
  dl_seconds = int(datetime.now().strftime("%S"))
  time_difference = dl_seconds - current_seconds
  return_data = {'measure': round(file_size / time_difference)}
  dummy_file.close()
  return return_data


if __name__ == '__main__':
  properties = properties_loader()
  env = Environment(properties)
  print env.get_server()
  print env.get_port()
  print env.get_api_version()
  print env.get_log_size_limit()
  print env.get_measure_interval()
  download = download_measure(properties)
  print download['measure']
  upload = upload_measure(properties, download['file'])
  print upload['measure']
  ping = pyping.ping('google.com')
  if ping.ret_code != 0:
    print 'Ping Test Failed.'
  else:
    print ping.avg_rtt
    lost_rate = float(ping.packet_lost) / 3 * 100.0
    print lost_rate
