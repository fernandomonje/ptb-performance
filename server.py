#!/usr/bin/python
import time
import BaseHTTPServer
import json
import time
import datetime
import cgi

# Global Variables Denifitions
# Global Variables Settings

HOST_NAME = '10.200.120.8'
PORT_NUMBER = 9995

class RequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
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
      if s.path == '/get':
        outfile = open('./dummy.file', 'r')
        s.send_response(200)
        s._setCORSHeaders(s, "GET", "application/octet-stream")
        s.wfile.write(outfile.read())
        outfile.close()
      else:
        s.send_response(400, 'Invalid Method. Try GET instead')
        s.end_headers()
      return
    def do_POST(s):
      """ Response for a POST request."""
      spent_time = 0
      if s.path == '/upload/':
        start_request_time = datetime.datetime.now()
        content_length = int(s.headers['Content-Length'])
        file_content = s.rfile.read(content_length)
        s.send_response(200)
        s._setCORSHeaders(s, "POST", "text/html")
        end_request_time = datetime.datetime.now()
        spent_time = (end_request_time - start_request_time).total_seconds()* 1000
      elif s.path == '/commit_data/':
        content_length = int(s.headers['Content-Length'])
        file_content = s.rfile.read(content_length)
        json_loaded = json.loads(file_content)
        print "SPID Recebido: %s" % (json_loaded['spid'])
        print "Upload Bandwidth Recebido: %s" % (json_loaded['upload_bandwidth'])
        print "Download Bandwidth Recebido: %s" % (json_loaded['download_bandwidth'])
        print "Ping Response Time Recebido: %s" % (json_loaded['ping_response_time'])
        #print json_loaded
        s.send_response(200)
        s._setCORSHeaders(s, "POST", "text/html")
      else:
        s.send_response(400, 'Invalid Path.')
        s.end_headers()
      print "Request Total Time: %dms" % (spent_time,)
      return
    def do_PUT(s):
      if s.path == '/put':
        s.send_response(200)
        s._setCORSHeaders(s, "PUT")
        s.wfile.write("{ 'TESTE JSON' : { 'TESTE2': 'TESTE_OK', 'URL' : \'" + s.path + "\'} }")
      return

if __name__ == '__main__':
    server_class = BaseHTTPServer.HTTPServer
    httpd = server_class((HOST_NAME, PORT_NUMBER), RequestHandler)
    print time.asctime(), "Starting Portability Performance Server - %s:%s" % (HOST_NAME, PORT_NUMBER)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    print time.asctime(), "Portability Performance Server stopped - %s:%s" % (HOST_NAME, PORT_NUMBER)
