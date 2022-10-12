import requests
import os
import sys, cgi
import base64
from http import cookies

from src.config import GLAuthConfig
from src.bbb import GLAuthBBBMeeting
from src.ldapconn import GLAuthLdap

from src.logger import log



"""
Access Logic:
* If access is public and room has no access code then no auth required
* If access is public and room has an access code then ask for access code
* If access is unlisted and room has an access code the ask for access code
* If access is unlisted and room has no access code then authenticate
* If access is private then require authentication and give access to owner and shares

FIX ME:
- LDAP URL in .env file not working
- postgredb host set to locahost
"""

class GLAuth:

  config = None
  auth_errors = []
  auth_cookie_name = 'GLAuth_GEMI'
  auth_msg = None

  def __init__(self, env_file = '.env', recording_path = '/var/bigbluebutton/published/presentation/'):
    self.config = GLAuthConfig(env_file)
    self.recording_path = recording_path
  
  def do_auth(self):
    form = cgi.FieldStorage()
    target = form.getvalue('target',  self.config.os('HTTP_X_ORIGINAL_URI', self.config.os('REQUEST_URI')))
    target = target.replace('/rec-auth', '')

    if self.authenticated(target):
      self.response_ok()
    elif (self.config.os('SCRIPT_ACTION') == 'login'):
      self.login(form, target)
    else:
      log("SEND unauthorized " + target)
      self.unauthorized(target);

  def login(self, form, target):

    if self.config.os('REQUEST_METHOD') == 'POST' or self.is_public_meeting(target):
      target = form.getvalue('target', target)
      authenticated_cookie = self.authenticate(form, target);

      if authenticated_cookie:
        form_html = self.config.get_html('redirect').replace('TARGET', target)
        self.response(200, form_html, {
          'Status': '200 OK',
          'Content-type': 'text/html',
          'Set-Cookie': self.auth_cookie_name + "=" + authenticated_cookie + "; path=/; httponly"
        })

      else:
        self.unauthorized(target)
    else:
      form_html = self.login_form(target)
      self.response_ok(form_html)
  
  def login_form(self, target):
    meeting = GLAuthBBBMeeting(self.config, target, self.recording_path)
    meeting_bbb_id = meeting.get_bbbid();

    if not meeting_bbb_id:
      return ""

    if meeting.has_access_code() and meeting.get_meeting_status() == GLAuthBBBMeeting.ACCESS_PUBLIC:
      form_html = self.config.get_html('code').replace('TARGET', target)
    elif meeting.has_access_code() and meeting.get_meeting_status() == GLAuthBBBMeeting.ACCESS_AUTH:
      form_html = self.config.get_html('code').replace('TARGET', target)
    elif not meeting.has_access_code() and meeting.get_meeting_status() == GLAuthBBBMeeting.ACCESS_AUTH:
      form_html = self.config.get_html('login').replace('TARGET', target)
    else:
      form_html = self.config.get_html('login').replace('TARGET', target)
    
    return form_html


  def authenticate(self, form, ref_target):
    user = form.getvalue('username')
    passwd = form.getvalue('password')
    target = form.getvalue('target', ref_target)
    access_code = form.getvalue('access_code')

    meeting = GLAuthBBBMeeting(self.config, target, self.recording_path)
    meeting_bbb_id = meeting.get_bbbid();
    if not meeting_bbb_id:
      # Recording is not accessible or missing params
      self.auth_msg = 'Recording is not accessible or missing credentials'
      return False

    
    # Perform authentication based on the above explained scenario
    auth_string = None
    if self.is_public_meeting(ref_target):
      auth_string = 'PUBAUTH:public' + ':' + target
    elif meeting.has_access_code() and meeting.get_meeting_status() == GLAuthBBBMeeting.ACCESS_PUBLIC:
      # authenticate only with access code only
      if (self.authenticate_code(form, meeting)):
        auth_string = 'CODEAUTH:' + access_code + ':' + target

    elif meeting.has_access_code() and meeting.get_meeting_status() == GLAuthBBBMeeting.ACCESS_AUTH:
      # authenticate only with access code only
      if (self.authenticate_code(form, meeting)):
        auth_string = 'CODEAUTH:' + access_code + ':' + target

    elif not meeting.has_access_code() and meeting.get_meeting_status() == GLAuthBBBMeeting.ACCESS_AUTH:
      # authenticate only with login only
      if (self.authenticate_ldap(form, meeting, False)):
        auth_string = 'LDAPAUTH:' + user + ':'  + target

    else:
      # authenticate with login and permission to access the room
      if (self.authenticate_ldap(form, meeting, True)):
        auth_string = 'LDAPAUTH:' + user + ':' + target

    if not auth_string:
      return False

    auth_string = auth_string + ':' + meeting.get_meeting_status()

    return base64.b64encode(self.ensure_bytes(auth_string)).decode()
  
  def authenticate_code(self, form, meeting):
    access_code = meeting.get_access_code()
    return access_code and access_code == form.getvalue('access_code')

  def authenticate_ldap(self, form, meeting, with_permission = False):
    ldap = GLAuthLdap(self.config)

    ldap_authenticated = ldap.authenticate(form.getvalue('username'), form.getvalue('password'))
    if not ldap_authenticated:
      return False
    elif ldap_authenticated and not with_permission:
      return True

    return ldap_authenticated and meeting.user_can_access(form.getvalue('username'));

  #@TODO Do proper authentication using server files for cookie
  def authenticated(self, target):
    auth_cookie = self.config.os('HTTP_COOKIE')
    target = self.config.os('HTTP_X_ORIGINAL_URI', target)

    if auth_cookie:
      cookie = cookies.SimpleCookie()
      cookie.load(auth_cookie)
      if self.auth_cookie_name in cookie and cookie[self.auth_cookie_name].value:
        cookie_value = base64.b64decode(cookie[self.auth_cookie_name].value).decode('utf-8')
        log(cookie_value)
        parts = cookie_value.split(':')
        ref_meeting = GLAuthBBBMeeting(self.config, target, self.recording_path)
        cookie_meeting = GLAuthBBBMeeting(self.config, parts[-2], self.recording_path)

        if ref_meeting.id and cookie_meeting.id and ref_meeting.id != cookie_meeting.id:
          return False

        if ref_meeting.id and ref_meeting.get_meeting_status() != parts[-1]:
          return False
        
        return True

    return False
  
  def validate_cookie(self, cookie, target):
    if not cookie:
      return False
    
    cookie = base64.b64decode(cookie).decode('utf-8')
    parts = cookie.split(':')
    return parts[-1] == target


    return True

  
  def is_public_meeting(self, target):
    try:
      meeting = GLAuthBBBMeeting(self.config, target, self.recording_path)
      if not meeting.has_access_code() and meeting.get_meeting_status() == GLAuthBBBMeeting.ACCESS_PUBLIC:
        return True
    except:
      pass

    return False

  def unauthorized(self, target = '/'):
    form_html = self.login_form(target);
    self.response(401, form_html, {
      'Status': '401 Unauthorized',
    })

  def response(self, code, content = None, headers = {}):

    response = "HTTP/1.0 "+ str(code) + "\n"
    for h in headers:
      if (h == 'Status'):
        response += h + ": " + headers[h] + "\n"
      else:
        response += h + ": " + headers[h] + "\r\n"

    if content:
      response += "\n" + content

    print(response)
    exit(0)

  def response_ok(self, content = ""):
    self.response(200, content, {
      'Status': '200 OK',
      'Content-type': 'text/html',
    })

  def ensure_bytes(self, data):
    return data if sys.version_info.major == 2 else data.encode("utf-8")
    

