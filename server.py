#!/usr/bin/python
import time
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from SocketServer import ThreadingMixIn
import threading
import json
import time
import datetime
import re
import StringIO

# Global Variables Denifitions
# Global Variables Settings

HOST_NAME = '10.200.120.8'
PORT_NUMBER = 9995
API_VERSION = 'v1'
BASE_URL = '/api/v1'

class RequestHandler(BaseHTTPRequestHandler):
    server_version = 'Portability Performance Server/1.0'
    sys_version = ''

    def _setCORSHeaders(self, res, method, content="application/json"):
      res.send_header("Access-Control-Allow-Origin", "*");
      res.send_header("Access-Control-Allow-Methods", method);
      res.send_header("Access-Control-Allow-Headers", "accept, content-type");
      res.send_header("Content-type", content)
      res.end_headers()

    def do_HEAD(s):
      s.send_response(200)
      s._setCORSHeaders(s, "PUT,POST,GET")
      s.send_header("Content-type", "application/json")
      s.end_headers()
      return
    def do_GET(s):
      """Response for a GET request."""
      if s.path == BASE_URL + '/data':
        outfile = open('./dummy.file', 'r')
        #time.sleep(5)
        outfile.seek(0,2)
        file_size = int(outfile.tell())
        s.send_response(200)
        s.send_header("Content-Length", file_size)
        s._setCORSHeaders(s, "GET", "application/octet-stream")
        outfile.seek(0,0)
        s.wfile.write(outfile.read())
        outfile.close()
      else:
        s.send_response(400, 'Invalid Method. Try GET instead')
        s.end_headers()
      return
    def do_POST(s):
      """ Response for a POST request."""
      spid_regex = re.compile(BASE_URL + '/carrier/[0-9]{4}/measurement')
      if s.path == BASE_URL + '/data/upload':
        start_request_time = datetime.datetime.now()
        content_length = int(s.headers['Content-Length'])
        file_content = StringIO.StringIO()
        file_content.write(s.rfile.read(content_length))
        file_content.seek(0,2)
        file_content.close()
        s.send_response(200)
        s._setCORSHeaders(s, "POST", "text/html")
        end_request_time = datetime.datetime.now()
      elif spid_regex.search(s.path):
        url_spid = s.path.split('/')[4]
        content_length = int(s.headers['Content-Length'])
        file_content = s.rfile.read(content_length)
        json_loaded = json.loads(file_content)
        if json_loaded['spid'] != url_spid:
          s.send_response(401, 'Invalid SPID.')
          s.end_headers()
        else:
          print "SPID Recebido: %s" % (json_loaded['spid'])
          print "Upload Bandwidth Recebido: %s" % (json_loaded['upload_bandwidth'])
          print "Download Bandwidth Recebido: %s" % (json_loaded['download_bandwidth'])
          print "Ping Response Time Recebido: %s" % (json_loaded['ping_response_time'])
          print "Ping Packet Lost Avg: %s" % (json_loaded['ping_packet_loss'])
          s.send_response(200)
          s._setCORSHeaders(s, "POST", "text/html")
      else:
        s.send_response(400, 'Invalid Path.')
        s.end_headers()
      return

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""

if __name__ == '__main__':
    server_class = ThreadedHTTPServer
    httpd = server_class((HOST_NAME, PORT_NUMBER), RequestHandler)
    print time.asctime(), "Starting Portability Performance Server - %s:%s" % (HOST_NAME, PORT_NUMBER)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    print time.asctime(), "Portability Performance Server stopped - %s:%s" % (HOST_NAME, PORT_NUMBER)
