#!/usr/bin/python
import time
import requests
import json
import time
from datetime import datetime
import re
import pyping
import StringIO
import urllib3

urllib3.disable_warnings()

class Environment:
  def __init__(self, properties):
    self.spid = properties['spid']
    self.server = properties['server']
    self.port = properties['port']
    self.api_version = properties['api_version']
    self.log_size_limit = properties['log_size_limit']
    self.measure_interval = properties['measure_interval']
    self.base_url = properties['base_url']

  def get_spid(self):
    return self.spid
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
  def get_base_url(self):
    return self.base_url

def properties_loader(propertie_file='./client.properties'): 
  properties = json.loads(open('./client.properties', 'r').read())['ptb_client']
  return properties

def download_measure(properties):
  return_data = {}
  url = 'https://' + properties['server'] + ':' + properties['port'] + properties['base_url'] + properties['api_version'] + '/data'
  current_ts = time.time()
  req = requests.get(url, verify=False)
  file = StringIO.StringIO() 
  file.write(req.content)
  file_size = int(req.headers['Content-Length'])/1024
  dl_ts = time.time()
  time_difference = dl_ts - current_ts
  return_data = {'measure': round(file_size / time_difference), 'file' : file}
  return return_data

def upload_measure(properties, dummy_file):
  return_data = {}
  current_ts = time.time()
  post_url = 'https://' + properties['server'] + ':' + properties['port'] + properties['base_url'] + properties['api_version'] + '/data/upload'
  dummy_file.seek(0,2)
  file_size = int(dummy_file.tell()) / 1024
  dummy_file.seek(0,0)
  request = requests.post(post_url, data=dummy_file, headers={"Content-Type": "application/octet-stream", "Content-Length" : str(file_size)}, verify=False)
  up_ts = time.time()
  time_difference = up_ts - current_ts
  return_data = {'measure': round(file_size / time_difference)}
  dummy_file.close()
  return return_data


if __name__ == '__main__':
  properties = properties_loader()
  env = Environment(properties)
  measures = {"spid" : env.get_spid()}
  download = download_measure(properties)
  measures['download_bandwidth'] = round(float(download['measure']) / 1024,2)
  measures['upload_bandwidth'] = round(float(upload_measure(properties, download['file'])['measure']) / 1024,2)
  ping = pyping.ping(env.get_server())
  if ping.ret_code != 0:
    measures['ping_response_time'] = -1
  else:
    measures['ping_response_time'] = round(float(ping.avg_rtt),2)
    measures['ping_packet_loss'] = round(float(ping.packet_lost) / 3 * 100.0, 1)
  send_measure_url = 'https://' + env.get_server() + ':' + env.get_port() + env.get_base_url() + env.get_api_version() + '/carrier/' + env.get_spid() + '/measurement'
  measure_sent_status = requests.post(send_measure_url, data=json.dumps(measures), headers={"Content-Type": "application/json"}, verify=False)
  print measure_sent_status
