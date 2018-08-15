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

# Global Variables Denifitions
global DB_USER
global DB_PASS
global DB_HOST
global DB_SCHEMA
global DB_CONNECTION

# Global Variables Settings
DB_USER=''
DB_PASS=''
DB_HOST=''
DB_SCHEMA=''
HOST_NAME = ''
PORT_NUMBER = 9995
API_VERSION = 'v1'
BASE_URL = '/api/v1'
LOG_FILE_NAME = 'ptb_performance_server.log'
LOG_MAX_SIZE_MB = 50 * 1024 * 1024
LOG_LEVEL = 'DEBUG'

serverLogger = logging.getLogger('server-Logger')
defaultLogHandler = RotatingFileHandler(os.path.join(os.path.dirname(os.path.realpath(__file__)), LOG_FILE_NAME), maxBytes=LOG_MAX_SIZE_MB, backupCount=10)
serverLogger.setLevel(eval('logging.' + LOG_LEVEL))
frmt = logging.Formatter('%(asctime)s - [%(levelname)s] - %(message)s')
defaultLogHandler.setFormatter(frmt)
serverLogger.addHandler(defaultLogHandler)

try:
  DB_CONNECTION = cx_Oracle.connect(DB_USER + '/' + DB_PASS + '@' + DB_HOST + '/' + DB_SCHEMA)
except Exception, e:
  serverLogger.error('No connection could be made to database.')
  serverLogger.error('Exception: ' + e)
  serverLogger.error('Server will not start.')
  sys.exit(1)

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
      if s.path == BASE_URL + '/data':
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
      spid_regex = re.compile(BASE_URL + '/carrier/[0-9]{4}/measurement')
      if s.path == BASE_URL + '/data/upload':
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
          except Exception e:
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
                  s.send_response(401, 'Json Missing Parameters.')
                  s.end_headers()
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
            try:
              DB_CONNECTION.commit()
              cur.close()
              s.send_response(200)
              s.setCORSHeaders(s, "POST", "text/html")
            except Exception, e:
              serverLogger.error('Failed to commit data to database: ' + str(e))
              s.send_response(500, 'Internal Server Error')
              s.end_headers()
          else:
            s.send_response(401, 'SPID Inactive at Server.')
            s.end_headers()
      else:
        s.send_response(400, 'Invalid Path.')
        s.end_headers()
      return

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """
       Handle requests in separated thread.
       Added to support multiple requests at the same time.
    """

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
    httpd = server_class((HOST_NAME, PORT_NUMBER), RequestHandler)
    serverLogger.warn('Starting Portability Performance Server - %s:%s' % (HOST_NAME, PORT_NUMBER))
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    DB_CONNECTION.close()
    serverLogger.warn('Portability Performance Server stopped - %s:%s' % (HOST_NAME, PORT_NUMBER))
