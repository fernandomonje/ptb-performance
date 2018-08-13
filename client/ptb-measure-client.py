#!/usr/bin/python
import time
import requests
import json
import time
from datetime import datetime
import pyping
import StringIO
import urllib3
import logging
from logging.handlers import RotatingFileHandler
import threading
import signal
import os

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class Environment:
  """
    Class to used to to represent all environment related information

    Attributes
    ----------
    spid : str
       the SPID value
    server : str
       the server address to send requests
    port : str
       the server port
    api_version : str
       the api_version to be used in requests
    log_size_limit : int
       the log size limit in MB
    measure_interval : int
       the amount of seconds to wait between each measure
    base_url : str
       the base url to be used in requests
    log_level : str
       the log level to be used in the log handler (INFO, ERROR, DEBUG, WARN)
    log_file : str
       the log file name to be used in the log handler
    thread_keep_alive : int
       the amount of seconds to wait between thread keep alive checks
 
    Methods
    -------
    get_spid
       returns the SPID string value
    get_primary_server
       returns the primary server string value
    get_secondary_server
       returns the secondary server string value
    get_port
       returns the port string value
    get_api_version
       returns the api_version string value
    get_log_size_limit
       returns the log_size_limit int value
    get_measure_interval
       returns the measure_interval int value
    get_block_window_start
       returns the start of the measurement block window
    get_block_window_end
       returns the end of the measurement block window
    get_base_url
       return the base_url string value
    get_log_level
       return the log_level string value
    get_log_file
       return the log_file string value
    get_thread_keep_alive
       return the thread_keep_alive int value
    get_current_path
       return the os path of the program
    get_block_window_status
       return a boolean indicating if the current time is blocked for measurements gathering
   
  """
  def __init__(self, properties):
    self.spid = properties['spid']
    self.primary_server = properties['primary_server']
    self.secondary_server = properties['secondary_server']
    self.port = properties['port']
    self.api_version = properties['api_version']
    self.log_size_limit = properties['log_size_limit']
    self.measure_interval = properties['measure_interval']
    self.block_window_start = properties['measurement_block_window_start']
    self.block_window_end = properties['measurement_block_window_end']
    self.base_url = properties['base_url']
    self.log_level = properties['log_level']
    self.log_file = properties['log_file']
    self.thread_keep_alive = properties['thread_keep_alive']

  def get_spid(self):
    return self.spid
  def get_primary_server(self):
    return self.primary_server
  def get_secondary_server(self):
    return self.secondary_server
  def get_port(self):
    return self.port
  def get_api_version(self):
    return self.api_version
  def get_log_size_limit(self):
    return self.log_size_limit
  def get_measure_interval(self):
    return self.measure_interval
  def get_block_window_start(self):
    return self.block_window_start
  def get_block_window_end(self):
    return self.block_window_end
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
  def get_block_window_status(self):
    if self.block_window_start == "0" or self.block_window_end == "0":
      return False
    else:
      today_date = datetime.now().strftime('%d/%m/%Y')
      try:
        block_window_start = time.mktime(datetime.strptime(today_date + ' ' + self.block_window_start + ':00', '%d/%m/%Y %H:%M').timetuple())
        block_window_end   = time.mktime(datetime.strptime(today_date + ' ' + self.block_window_end + ':00', '%d/%m/%Y %H:%M').timetuple())
        if time.time() >= block_window_start and time.time() <= block_window_end:
          return True
        else:
          return False
      except Exception as e:
        daemonLogHandler.error('Failed to determine the measurement block window, considering no block window.')
        return False
        

def properties_loader(propertie_file='client.properties'): 
  """The properties Loader
     
     ...
 
     Load the properties from a given json file

     Parameters
     ----------
     propertie_file : str, optional
        the propertie file name to be used (default is 'client.properties')
        
     Returns
     -------
     json
        json object containing all the values from the properties file
  """
  properties = json.loads(open(os.path.join(os.path.dirname(os.path.realpath(__file__)), propertie_file), 'r').read())['ptb_client']
  return properties

def download_measure(env):
  """Download Measure Method

     ...
 
     Run the download measurement, based on the server, port, 
     base_url and API version parameters from the env object.
     The downloaded data is stored in an StringIO object to
     generate the measurement and to be passed to the upload method.

     Parameters
     ----------
     env : Environment
        Environment object containing the parameters to be used in
        the measurement.

     Returns
     -------
     dict
       A dictionary contaning the measurement data and the StringIO
       object as a file to be used in the upload method.
  """
  global daemonLogHandler
  t = threading.currentThread()
  return_data = {}
  url = 'https://' + env.get_primary_server() + ':' + env.get_port() + env.get_base_url() + env.get_api_version() + '/data'
  daemonLogHandler.debug('[' + t.name + '] - Starting Download Method using [' + url + ']')
  current_ts = time.time()
  file = StringIO.StringIO()
  try:
    req = requests.get(url, verify=False, timeout=5)
    if req.status_code != 200:
      daemonLogHandler.error('[' + t.name + '] - Received wrong http status [' + str(req.status_code) + ']')
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
  """Upload Measure Method

     Run the upload measurement, based on the server, port,
     base_url and API version parameters from the env object.
     The data to be uploaded come from the dummy_file parameter

     ...

     Parameters
     ----------
     env : Environment
        Environment object containing the parameters to be used in
        the measurement.

     dummy_file : file (StringIO)
        The file object to be used in the upload process.
        This file come from the download method and is kept
        in memory until the upload method is finished.

     Returns
     -------
     dict
       A dictionary contaning the measurement data.
  """
  global daemonLogHandler
  t = threading.currentThread()
  return_data = {}
  current_ts = time.time()
  post_url = 'https://' + env.get_primary_server() + ':' + env.get_port() + env.get_base_url() + env.get_api_version() + '/data/upload'
  daemonLogHandler.debug('[' + t.name + '] - Starting Upload Method using [' + post_url + ']')
  dummy_file.seek(0,2)
  file_size = int(dummy_file.tell()) / 1024
  dummy_file.seek(0,0)
  try:
    req = requests.post(post_url, data=dummy_file, headers={"Content-Type": "application/octet-stream", "Content-Length" : str(file_size)}, verify=False, timeout=5)
    if req.status_code != 200:
      daemonLogHandler.error('[' + t.name + '] - Received wrong http status [' + str(req.status_code) + ']')
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
  """The runTests method

     The runTests is the method that efectively run the measurement
     methods (download, upload, ping) and send the measurement data
     to the server in a json format.
     This is a thread method that stay in a infinite loop, so its kept running until the main 
     process is stopped.

     ...

     Parameters
     ----------
     env : Environment
        Environment object containing the parameters to be used in
        the measurement.
  """
  global daemonLogHandler
  t = threading.currentThread()
  __setStop = False
  daemonLogHandler.debug('[' + t.name + '] - Thread successfully started.')
  while getattr(t, "do_run", True):
    if env.get_block_window_status():
      daemonLogHandler.info('[' + t.name + '] - Currently in a measurement window blocked.')
    else:
      daemonLogHandler.info('[' + t.name + '] - Currently not in a measurement window blocked.')
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
        ping = pyping.ping(env.get_primary_server())
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
        send_measure_url = 'https://' + env.get_primary_server() + ':' + env.get_port() + env.get_base_url() + env.get_api_version() + '/carrier/' + env.get_spid() + '/measurement'
        daemonLogHandler.debug('[' + t.name + '] - Sending Measure data to [' + send_measure_url + '].')
        req = requests.post(send_measure_url, data=json.dumps(measures), headers={"Content-Type": "application/json"}, verify=False, timeout=5)
        if req.status_code != 200:
          daemonLogHandler.error('[' + t.name + '] - Received wrong http status [' + str(req.status_code) + ']')
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
  """Signal handler method
  
     Handle the signals to stop the main processes and all the
     threads.

     ...

     Parameters
     ----------
     signum : int
        the signal number to be handled

     frame : str
        the method name used in the call (self) 
  """
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

def threadKeepAlive():
  """The thread keep alive method

     This method checks the state of the runTests thread.
     Since the thread should be running all the time, if the
     thread for any reason is not responding, this method
     sinalize the main thread to restart the runTests thread.

     ...

     Returns
     -------
     bool
        A boolean value indicating the status of the thread
  """
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
  """The main program
     
     The main program is responsible for invoke all the base methods
     like instantiate the Environment object, define logging information
     start the runTests thread and control the thread keep alive method
     execution time. This method handle the external signals passed to
     the program to stop the program and all threads, invoking the
     stioGracefully method.

     ...

  """
  global mainThreadStops
  global daemonLogHandler
  global mainThreadStops
  properties = properties_loader()
  env = Environment(properties)
  formatter = logging.Formatter('%(asctime)s [%(levelname)s] - %(message)s')
  daemonLogHandler = logging.getLogger('ptb-performance-daemon')
  hdlr_daemon = RotatingFileHandler(os.path.join(env.get_current_path(), env.get_log_file()), maxBytes=env.get_log_size_limit() * 1024 * 1024, backupCount=5)
  hdlr_daemon.setFormatter(formatter)
  daemonLogHandler.addHandler(hdlr_daemon)
  daemonLogHandler.setLevel(eval(env.get_log_level()))
  daemonLogHandler.debug('Loaded Parameters:')
  daemonLogHandler.debug('SPID: ' + env.get_spid())
  daemonLogHandler.debug('Server: ' + env.get_primary_server())
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
      if not threadKeepAlive():
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
