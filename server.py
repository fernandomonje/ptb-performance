#!/usr/bin/python
import time
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from SocketServer import ThreadingMixIn
import threading
import simplejson
import time
import datetime
import re
import StringIO
import cx_Oracle
import sys
import logging
from logging.handlers import RotatingFileHandler
import os
import threading

# Global Variables Denifitions
global DB_CONNECTION
global serverLogger


# Global Variables Settings
LOG_FILE_NAME = 'ptb_performance_server.log'
LOG_MAX_SIZE_MB = 50 * 1024 * 1024
LOG_LEVEL = 'DEBUG'

def set_logger(env):
  global serverLogger
  serverLogger = logging.getLogger('server-Logger')
  defaultLogHandler = RotatingFileHandler(os.path.join(os.path.dirname(os.path.realpath(__file__)), \
    env.get_log_file()), maxBytes=env.get_log_size_limit() * 1024 * 1024, backupCount=env.get_log_backup_count())
  serverLogger.setLevel(eval(env.get_log_level()))
  frmt = logging.Formatter('%(asctime)s - [%(levelname)s] - %(message)s')
  defaultLogHandler.setFormatter(frmt)
  serverLogger.addHandler(defaultLogHandler)

class Environment:
  """
    Class to used to to represent all environment related information

    Attributes
    ----------
    host : str
       the host address to start the server
    port : str
       the server port
    api_version : str
       the api_version to be used in requests
    log_size_limit : int
       the log size limit in MB
    base_url : str
       the base url to be used in requests
    log_level : str
       the log level to be used in the log handler (INFO, ERROR, DEBUG, WARN)
    log_file : str
       the log file name to be used in the log handler
    log_backup_count : int
       the log backup count for log rotate propouses
    db_check_interval : int
       the amount of seconds to wait between db status checks
    db_host : str
       the database hostname / ip string
    db_schema : str
       the database schema name
    db_user : str
       the database user
    db_password : str
       the database password

    Methods
    -------
    get_host
       returns the host string value
    get_port
       returns the port int value
    get_api_version
       returns the api_version string value
    get_log_size_limit
       returns the log_size_limit int value
    get_db_check_interval
       returns the db_check_interval int value
    get_base_url
       return the base_url string value
    get_log_level
       return the log_level string value
    get_log_file
       return the log_file string value
    get_log_backup_count
       return the log backup count int value
    get_db_host
       return the database hostname string value
    get_db_schema
       return the database schema string value
    get_db_user
       return the database user string value
    get_db_password
       return the database password string value

  """
  def __init__(self, properties):
    self.host = properties['host']
    self.port = properties['port']
    self.api_version = properties['api_version']
    self.log_size_limit = properties['log_size_limit']
    self.db_check_interval = properties['db_check_interval']
    self.base_url = properties['base_url']
    self.log_level = properties['log_level']
    self.log_file = properties['log_file']
    self.log_backup_count = properties['log_backup_count']
    self.db_host = properties['database_host']
    self.db_schema = properties['database_schema']
    self.db_user = properties['database_user']
    self.db_password = properties['database_password']

  def get_host(self):
    return self.host
  def get_port(self):
    return self.port
  def get_api_version(self):
    return self.api_version
  def get_log_size_limit(self):
    return self.log_size_limit
  def get_log_backup_coun(self):
    return self.log_backup_count
  def get_db_check_interval(self):
    return self.db_check_interval
  def get_base_url(self):
    return self.base_url
  def get_log_level(self):
    return self.log_level
  def get_log_file(self):
    return self.log_file
  def get_log_backup_count(self):
    return self.log_backup_count
  def get_db_host(self):
    return self.db_host
  def get_db_schema(self):
    return self.db_schema
  def get_db_user(self):
    return self.db_user
  def get_db_password(self):
    return self.db_password

def properties_loader(propertie_file='server.properties'):
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
  properties = simplejson.loads(open(os.path.join(os.path.dirname(os.path.realpath(__file__)), propertie_file), 'r').read())['ptb_server']
  return properties

def create_db_connection(env):
  global DB_CONNECTION
  try:
    DB_CONNECTION = cx_Oracle.connect(env.get_db_user() + '/' + env.get_db_password() + '@' + env.get_db_host() + '/' + env.get_db_schema())
  except Exception, e:
    serverLogger.error('No connection could be made to database.')
    serverLogger.error('Exception: ' + e)
    serverLogger.error('Server will not start.')
    sys.exit(1)

def check_db_connection():
  global DB_CONNECTION
  try:
    cur = DB_CONNECTION.cursor()
    cur.execute('SELECT SYSDATE FROM DUAL')
    cur.close()
    serverLogger.info('DB Connection Test was Successful.')
    return True
  except Exception, e:
    serverLogger.error('DB Connection Test error.')
    serverLogger.debug('Error: ' + str(e))
    return False

def recreate_db_connection(env):
  global DB_CONNECTION
  serverLogger.info('Error encontered when testing the database connection. The connection will be reacreated.')
  try:
    DB_CONNECTION.close()
  except Exception, e:
    serverLogger.error('Error when trying to close database connection. Continuing to recreate database connection.')
  create_db_connection(env)

class RequestHandler(BaseHTTPRequestHandler):
    """The request handler

       ...

       Inherit from BaseHTTPRequestHandler, with some overridden methods.
       The log_message method was overridden to use an external logger.
       The server only handle two methods: GET and POST, in very particular contexts.

       ...

       Methods
       -------
       log_message( format, *args)
          The log_message method was overridden to use an external logger.
       real_address_string()
          Return the real IP address of the request if the server is behind a
          Reverse Proxy.
       check_spid_status(spid)
          Check the current status of a given SPID.
       setCORSHeaders(res, method, content="application/json")
          Put several header parameters in the response object to be returned
          to the client.
       do_GET()
          Handle the GET request method.
       do_POST()
          Handle the POST request method.

    """
    server_version = 'Portability Performance Server/1.0'
    sys_version = ''

    def log_message(self, format, *args):
      """Override the default log_message method to use external logger.

         Parameters
         ----------
         format : is a standard printf-style format string where the additional arguments are applied as inputs to the formatting.
      """
      serverLogger.info("%s - - %s" % (self.real_address_string(),format%args))

    def real_address_string(self):
      """
         Since the server will be running behind a Reverse Proxy, we need
         to get the real ip address of the request. The real ip address is
         supplied in the 'X-Forwarded-For' header parameter.

         Returns
         ----------
         str
            the ip address string
      """
      if 'X-Forwarded-For' in self.headers:
        return self.headers['X-Forwarded-For']
      else:
        return self.address_string()

    def check_spid_status(self, spid):
      """
         Open an database cursor using the default database connection, then
         query for the status of a given SPID.

         Parameters
         ----------
         spid : str
            the SPID to be used in the database query

         Returns
         ----------
         bool
            A boolean value indicating the status of the SPID given as parameter
      """
      query = 'SELECT COUNT(1) FROM PTB_MEASURE_SPID WHERE spid = :spid AND STATUS = 1'
      try:
        cur = DB_CONNECTION.cursor()
        cur.execute(query, {'spid':  spid})
        status = cur.fetchone()
        cur.close()
        if status[0] == 1:
          return True
        else:
          return False
      except Exception, e:
        serverLogger.error('Exception ocurred in database operation: ' + str(e))
        return False

    def setCORSHeaders(self, res, method, content="application/json"):
      """
         Set some security related header parameters and the content-type

         Parameters
         ----------
         res
           the response object to the request
         method : str
           string value to be set as allowed method
         content : str
           string value to be set as content-type
      """
      res.send_header("Access-Control-Allow-Origin", "*");
      res.send_header("Access-Control-Allow-Methods", method);
      res.send_header("Access-Control-Allow-Headers", "accept, content-type");
      res.send_header("Content-type", content)
      res.end_headers()

    def do_GET(s):
      """Response for a GET method request.

         Only allow to get the '/api/<version>/data' context and serve a dummy file.

         Returns
         ----------
         response
            The response object
      """
      if s.path == env.get_base_url() + '/' + env.get_api_version() + '/data':
        try:
          outfile = open('./dummy.file', 'r')
          outfile.seek(0,2)
          file_size = int(outfile.tell())
          s.send_response(200)
          s.send_header("Content-Length", file_size)
          s.setCORSHeaders(s, "GET", "application/octet-stream")
          outfile.seek(0,0)
          s.wfile.write(outfile.read())
          outfile.close()
        except Exception, e:
          serverLogger.error('Exception in GET method: ' + str(e))
          s.send_response(500, 'Internal Server Error')
          s.end_headers()
      else:
        s.send_response(400, 'Invalid Method. Try GET instead')
        s.end_headers()
      return
    def do_POST(s):
      """Response for a POST method request.

         only alow two contexts:
            * '/api/<version>/data/upload' : used to receive the dummy data
            * '/api/<version>/carrier/<spid>/measurement' used to receive the
              json with the measure information.

         For the measurement receiving there is some validations done to grant that
         only enabled SPID could send measurements

         Returns
         ----------
         response
            The response object
      """
      spid_regex = re.compile(env.get_base_url() + '/' + env.get_api_version() + '/carrier/[0-9]{4}/measurement')
      if s.path == env.get_base_url() + '/' + env.get_api_version() + '/data/upload':
        try:
          content_length = int(s.headers['Content-Length'])
          file_content = StringIO.StringIO()
          file_content.write(s.rfile.read(content_length))
          file_content.seek(0,2)
          file_content.close()
          s.send_response(200)
          s.setCORSHeaders(s, "POST", "text/html")
        except Exception, e:
          serverLogger.error('Exception in POST method: ' + str(e))
          try:
            s.send_response(500, 'Internal Server Error')
            s.end_headers()
          except Exception, e:
            serverLogger.error('Exception in POST method when trying to send request status: ' + str(e))
      elif spid_regex.search(s.path):
        url_spid = s.path.split('/')[4]
        json_loaded = []
        content_length = int(s.headers['Content-Length'])
        file_content = s.rfile.read(content_length)
        try:
          json_loaded = simplejson.loads(file_content)
        except Exception, e:
          serverLogger.error('Cold not read json: ' + str(e))
          s.send_response(500, 'Internal Server Error')
          s.end_headers()
        if json_loaded['spid'] != url_spid:
          s.send_response(401, 'Invalid SPID from Request o End Point.')
          s.end_headers()
        else:
          if s.check_spid_status(url_spid):
            try:
              cur = DB_CONNECTION.cursor()
              params_list = [ 'spid',
                              'upload_bandwidth',
                              'download_bandwidth',
                              'ping_response_time',
                              'ping_packet_loss',]
              for param in params_list:
                if not param in json_loaded:
                  s.end_headers()
                  s.send_response(401, 'Json Missing Parameters.')
                  return
              cur.prepare('INSERT INTO SCADA.PTB_MEASURE_DATA (SPID, DATETIME, UPLOAD_BANDWIDTH, DOWNLOAD_BANDWIDTH, \
                           PING_RESPONSE_TIME, PING_PACKET_LOSS) VALUES (:SPID, SYSDATE, :UPLOAD_BANDWIDTH, :DOWNLOAD_BANDWIDTH, \
                           :PING_RESPONSE_TIME, :PING_PACKET_LOSS)')
              cur.execute(None, {'SPID': json_loaded['spid'],
                                 'UPLOAD_BANDWIDTH': str(json_loaded['upload_bandwidth']),
                                 'DOWNLOAD_BANDWIDTH' : str(json_loaded['download_bandwidth']),
                                 'PING_RESPONSE_TIME' : str(json_loaded['ping_response_time']),
                                 'PING_PACKET_LOSS' : str(json_loaded['ping_packet_loss'])})
            except Exception, e:
              serverLogger.error('Failed to get/save data from json to database: ' + str(e))
              s.send_response(500, 'Internal Server Error')
              s.end_headers()
              recreate_db_connection()
              return
            try:
              DB_CONNECTION.commit()
              cur.close()
              s.setCORSHeaders(s, "POST", "text/html")
              s.send_response(200)
            except Exception, e:
              serverLogger.error('Failed to commit data to database: ' + str(e))
              s.send_response(500, 'Internal Server Error')
              s.end_headers()
              recreate_db_connection()
              return
          else:
            s.send_response(401, 'SPID Inactive at Server.')
            s.end_headers()
      else:
        s.send_response(400, 'Invalid Path.')
        s.end_headers()
      return

def DatabaseMonitoringThread(env):
  __setStop = False
  t = threading.currentThread()
  serverLogger.debug('[' + t.getName() + '] - Thread successfully started.')
  while getattr(t, "do_run", True):
    if not check_db_connection():
      recreate_db_connection(env)
    timer = 0
    while timer < env.get_db_check_interval():
      time.sleep(1)
      timer += 1
      if not getattr(t, "do_run"):
        serverLogger.debug('[' + t.getName() + '] - Thread received signal to stop.')
        serverLogger.debug('[' + t.getName() + '] - Thread is stopping all operations.')
        __setStop = True
        break
    if __setStop:
      break
  serverLogger.debug('[' + t.getName() + '] - Thread stopped successfully.')
  serverLogger.info('[' + t.getName() + '] - Thread finished.')

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
  """
       Handle requests in separated thread.
       Added to support multiple requests at the same time.
  """
  def set_environment(self, env):
    self.env = env

if __name__ == '__main__':
    """The main program function.

       ...

       It will instantiate a server class and server forever using the hostname/ip and port supplied.
       The server_class variable will contains the server class to be used.
       If there is a keyboard interruption the server will stops.
       Additionally when the server stops, the Oracle database connection will be closed.
       There is a default logger used to handle log messages.
    """
    server_class = ThreadedHTTPServer
    properties = properties_loader()
    env = Environment(properties)
    set_logger(env)
    httpd = server_class((env.get_host(), env.get_port()), RequestHandler)
    httpd.set_environment(env)
    serverLogger.warn('Starting Portability Performance Server - %s:%s' % (env.get_host(), env.get_port()))
    create_db_connection(env)
    t = threading.Thread(target=DatabaseMonitoringThread,name="db-monitoring-Thread", args=(env,))
    serverLogger.info('Starting Thread [' + t.getName() + '].')
    t.start()
    t.do_run = True
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    t.do_run = False
    t.join(1)
    httpd.server_close()
    DB_CONNECTION.close()
    serverLogger.warn('Portability Performance Server stopped - %s:%s' % (env.get_host(), env.get_port()))
