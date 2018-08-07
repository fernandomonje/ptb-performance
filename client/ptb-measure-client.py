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
import logging
from logging.handlers import RotatingFileHandler
import threading
import signal
import os

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
    self.log_level = properties['log_level']
    self.log_file = properties['log_file']
    self.thread_keep_alive = properties['thread_keep_alive']

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
  def get_log_level(self):
    return self.log_level
  def get_log_file(self):
    return self.log_file
  def get_thread_keep_alive(self):
    return self.thread_keep_alive
  def get_current_path(self):
    return os.path.dirname(os.path.realpath(__file__))

def properties_loader(propertie_file='client.properties'): 
  properties = json.loads(open(os.path.dirname(os.path.realpath(__file__)) + '/' + 'client.properties', 'r').read())['ptb_client']
  return properties

def download_measure(env):
  global daemonLogHandler
  t = threading.currentThread()
  return_data = {}
  url = 'https://' + env.get_server() + ':' + env.get_port() + env.get_base_url() + env.get_api_version() + '/data'
  daemonLogHandler.debug('[' + t.name + '] - Starting Download Method using [' + url + ']')
  current_ts = time.time()
  file = StringIO.StringIO()
  try:
    req = requests.get(url, verify=False, timeout=5)
    if req.status_code != 200:
      daemonLogHandler.error('[' + t.name + '] - Received wrong http status [' + req.status_code + ']')
      daemonLogHandler.error('[' + t.name + '] - Download Method Failed.')
      return_data = {'measure': 0}
    else:
      file.write(req.content)
      file_size = int(req.headers['Content-Length'])/1024
      dl_ts = time.time()
      time_difference = dl_ts - current_ts
      daemonLogHandler.info('[' + t.name + '] - Download Method Successed.')
      return_data = {'measure': round(file_size / time_difference), 'file' : file}
  except Exception as e:
    daemonLogHandler.debug('[' + t.name + '] - Download Method Http Request Error: ' + str(e))
    daemonLogHandler.error('[' + t.name + '] - Download Method Failed.')
    return_data = {'measure': 0}
  return return_data

def upload_measure(env, dummy_file):
  global daemonLogHandler
  t = threading.currentThread()
  return_data = {}
  current_ts = time.time()
  post_url = 'https://' + env.get_server() + ':' + env.get_port() + env.get_base_url() + env.get_api_version() + '/data/upload'
  daemonLogHandler.debug('[' + t.name + '] - Starting Upload Method using [' + post_url + ']')
  dummy_file.seek(0,2)
  file_size = int(dummy_file.tell()) / 1024
  dummy_file.seek(0,0)
  try:
    req = requests.post(post_url, data=dummy_file, headers={"Content-Type": "application/octet-stream", "Content-Length" : str(file_size)}, verify=False, timeout=5)
    if req.status_code != 200:
      daemonLogHandler.error('[' + t.name + '] - Received wrong http status [' + req.status_code + ']')
      daemonLogHandler.error('[' + t.name + '] - Upload Method Failed.')
      return_data = {'measure': 0}
    else:
      up_ts = time.time()
      time_difference = up_ts - current_ts
      daemonLogHandler.info('[' + t.name + '] - Upload Method Successed.')
      return_data = {'measure': round(file_size / time_difference)}
  except Exception as e:
    daemonLogHandler.debug('[' + t.name + '] - Upload Method Http Request Error: ' + str(e))
    daemonLogHandler.error('[' + t.name + '] - Upload Method Failed.')
    return_data = {'measure': 0}
  dummy_file.close()
  return return_data

def runTests(env):
  global daemonLogHandler
  t = threading.currentThread()
  __setStop = False
  daemonLogHandler.debug('[' + t.name + '] - Thread successfully started.')
  while getattr(t, "do_run", True):
    measures = {"spid" : env.get_spid()}
    download = download_measure(env)
    if 'file' in download:
      measures['download_bandwidth'] = round(float(download['measure']) / 1024,2)
      daemonLogHandler.debug('[' + t.name + '] - Starting Upload Method since Download Method Successed.')
      upload_bandwidth = upload_measure(env, download['file'])
      if upload_bandwidth['measure'] == 0:
        measures['upload_bandwidth'] = 0.00
      else:
        measures['upload_bandwidth'] = round(float(upload_bandwidth['measure']) / 1024,2)
    else:
      measures['download_bandwidth'] = 0.00
      measures['upload_bandwidth'] = 0.00
    daemonLogHandler.debug('[' + t.name + '] - Starting Ping Test.')
    try:
      ping = pyping.ping(env.get_server())
      if ping.ret_code != 0:
        measures['ping_response_time'] = 0
        daemonLogHandler.error('[' + t.name + '] - Ping Test Failed.')
      else:
        daemonLogHandler.info('[' + t.name + '] - Ping Test Successed.')
        measures['ping_response_time'] = round(float(ping.avg_rtt),2)
        measures['ping_packet_loss'] = round(float(ping.packet_lost) / 3 * 100.0, 1)
    except Exception as e:
      daemonLogHandler.debug('[' + t.name + '] - Ping Exception: ' + str(e))
      daemonLogHandler.error('[' + t.name + '] - Ping Test Failed.')
      measures['ping_response_time'] = 0.00
      measures['ping_packet_loss'] = 100.0
    try:
      send_measure_url = 'https://' + env.get_server() + ':' + env.get_port() + env.get_base_url() + env.get_api_version() + '/carrier/' + env.get_spid() + '/measurement'
      daemonLogHandler.debug('[' + t.name + '] - Sending Measure data to [' + send_measure_url + '].')
      req = requests.post(send_measure_url, data=json.dumps(measures), headers={"Content-Type": "application/json"}, verify=False, timeout=5)
      if req.status_code != 200:
        daemonLogHandler.error('[' + t.name + '] - Received wrong http status [' + req.status_code + ']')
        daemonLogHandler.error('[' + t.name + '] - Failed to send Measure data to Server.')
      else:
        daemonLogHandler.debug('[' + t.name + '] - Successed Sent Measure data to Server')
    except Exception as e:
      daemonLogHandler.debug('[' + t.name + '] - Send Measure Exception: ' + str(e))
      daemonLogHandler.error('[' + t.name + '] - Failed to send measures to Server.')
    daemonLogHandler.info('['+t.name+'] - Thread will sleep for the amount of seconds defined in the measure_interval parameter['+str(env.get_measure_interval())+']')
    timer = 0
    while timer <= env.get_measure_interval():
      time.sleep(1)
      timer += 1
      if not getattr(t, "do_run"):
        daemonLogHandler.debug('[' + t.name + '] - Thread received signal to stop.')
        daemonLogHandler.debug('[' + t.name + '] - Thread is stopping all operations.')
        __setStop = True
        break
    if __setStop:
      break
  daemonLogHandler.debug('[' + t.name + '] - Thread stopped successfully.')
  daemonLogHandler.info('[' + t.name + '] - Thread finished.')

def stopGracefully(signum, frame):
  global mainThreadStops
  global daemonLogHandler
  if signum == 2:
    strSignal = 'SIGINT'
  else:
    strSignal = 'SIGTERM'
  daemonLogHandler.warn('Received ' + strSignal + ' signal. Stopping all process gracefully.')
  for threadObj in threading.enumerate():
    if threadObj.name == 'Worker-Thread':
      threadObj.do_run = False
      threadObj.join(1)
  mainThreadStops = True
  daemonLogHandler.warn('All threads stopped.')

def threadKeepAlive(thread):
  global daemonLogHandler
  threadNameList = []
  daemonLogHandler.info('[ThreadKeepAlive] - Starting Thread Keep Alive Process.')
  for threadObj in threading.enumerate():
    threadNameList.append(threadObj.name)
    if 'Worker-Thread' not in threadNameList:
      daemonLogHandler.warn('[ThreadKeepAlive] - Thread [Worker-Thread] died unexpectedly. Notifying for troubleshooting reasons.')
      return False
  daemonLogHandler.info('[ThreadKeepAlive] - Thread Keep Alive Process Finished.')
  return True

def main():
  global mainThreadStops
  global daemonLogHandler
  global mainThreadStops
  properties = properties_loader()
  env = Environment(properties)
  formatter = logging.Formatter('%(asctime)s [%(levelname)s] - %(message)s')
  daemonLogHandler = logging.getLogger('ptb-performance-daemon')
  hdlr_daemon = RotatingFileHandler(env.get_current_path() + '/' + env.get_log_file(), maxBytes=env.get_log_size_limit() * 1024 * 1024, backupCount=5)
  hdlr_daemon.setFormatter(formatter)
  daemonLogHandler.addHandler(hdlr_daemon)
  daemonLogHandler.setLevel(eval(env.get_log_level()))
  daemonLogHandler.debug('Loaded Parameters:')
  daemonLogHandler.debug('SPID: ' + env.get_spid())
  daemonLogHandler.debug('Server: ' + env.get_server())
  daemonLogHandler.debug('Port: ' + env.get_port())
  daemonLogHandler.debug('API Version: ' + env.get_api_version())
  daemonLogHandler.debug('Base Url: ' + env.get_base_url())
  daemonLogHandler.debug('Measure Interval: ' + str(env.get_measure_interval()))
  daemonLogHandler.debug('Thread Keep Alive: ' + str(env.get_thread_keep_alive()))
  daemonLogHandler.debug('Log File: ' + env.get_log_file())
  daemonLogHandler.debug('Log Level: ' + env.get_log_level())
  daemonLogHandler.debug('Log Size Limit: ' + str(env.get_log_size_limit()))
  mainThreadStops = False
  t = threading.Thread(target=runTests,name="Worker-Thread",  args=(env,))
  daemonLogHandler.info('Starting Thread [' + t.name + '].')
  t.start()
  t.do_run = True
  signal.signal(signal.SIGTERM, stopGracefully)
  signal.signal(signal.SIGINT, stopGracefully)
  KEEP_ALIVE_TIMER = env.get_thread_keep_alive() / 10
  KP_COUNTER = 1
  while True:
    if mainThreadStops:
      break
    if KP_COUNTER < KEEP_ALIVE_TIMER:
      KP_COUNTER += 1
    else:
      if not threadKeepAlive(t):
        daemonLogHandler.warn('Attemping to restart Thread [' + t.name + '].')
        t = threading.Thread(target=runTests,name="Worker-Thread",  args=(env,))
        daemonLogHandler.info('Starting Thread [' + t.name + '].')
        try:
          t.start()
          t.do_run = True
        except Exception as e:
          daemonLogHandler.debug('[' + t.name + '] Thread Error: ' + str(e))
          daemonLogHandler.error('Failed to start Thread [' + t.name + '].')
      KP_COUNTER = 1
    time.sleep(10)
  daemonLogHandler.warn('Process Stopped successfully.')

if __name__ == '__main__':
  main()
