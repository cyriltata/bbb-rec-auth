from src.logger import log

import re
import base64
import bcrypt
from bs4 import BeautifulSoup
import psycopg2
import psycopg2.extras

# Greenlight access levels for recordings


class GLAuthBBBMeeting:

    # Access to recording without authentication
    ACCESS_PUBLIC = 'true'

    #Allow access only to users with a GL account
    ACCESS_AUTH = 'false'

    #Allow access only to the owner of the recording and those with access to room
    ACCESS_PRIVATE = 'private'

    def __init__(self, config, uri, recording_path):
        self.config = config
        self.uri = uri

        self.recording_path = recording_path
        self.id = self.parse_url(self.uri)
        self.db_conn = psycopg2.connect("dbname="+self.config.env('DB_NAME')+" user="+self.config.env('DB_USERNAME')+" password="+self.config.env('DB_PASSWORD')+" host=localhost")

        #if not self.id:
        #    raise Exception("Meeting ID Could not be found from URL: " + uri)
    
    def parse_url(self, url=''):
        r = re.compile(r'[0-9a-f]{40}-[0-9]{13}')
        t = re.compile(r'^/presentation/[0-9a-f]{40}-[0-9]{13}/presentation/[0-9a-f]{40}-[0-9]{13}/thumbnails/(thumb-[1-3].png|images/favicon.png)$')
        try:
            thumb = t.findall(url)
            if thumb:
                logfile.write('Thumbnail found\n')
                return False
            else:
                meetingid = r.findall(url)[0]
                return meetingid
        except:
            return False

    def get_bbbid(self):
        try:
            metadata_file = open(self.recording_path+'/'+self.id+'/metadata.xml', 'r')
            metadata_xml = metadata_file.read()
            metadata = BeautifulSoup(metadata_xml, 'xml')
            mids = metadata.find_all('meetingId')
            return mids[0].get_text()
        except:
            return False
        return False

    # checks if an authenticating user is the owner of a room
    def check_owner(self, user):
        bbbid = self.get_bbbid()
        if not bbbid:
            return False
    
        cur = self.db_conn.cursor(cursor_factory = psycopg2.extras.RealDictCursor)
        
        # Get owner of room
        cur.execute("SELECT user_id FROM rooms WHERE bbb_id = %s;", (bbbid,))
        res = cur.fetchall()
        
        if not res:
            return False
        
        # get mailaddr of owner
        cur.execute("SELECT username FROM users WHERE id = %s;", (res[0]['user_id'],))
        res = cur.fetchall()
        
        if not res:
            return False
        
        if res[0]['username'] == user:
            return True
        
        return False

    # checks if an authenticating user is the owner of a room
    def check_shared(self, user):
        bbbid = self.get_bbbid()
        if not bbbid:
            return False
        cur = self.db_conn.cursor()
        
        cur.execute("SELECT id FROM rooms WHERE bbb_id = %s;", (bbbid,))
        res = cur.fetchall()

        if not res:
            return False

        cur.execute("SELECT user_id FROM shared_accesses WHERE room_id = %s;", (res[0][0],))
        res = cur.fetchall()
        
        if not res:
            return False
        
        for uid in res:
            cur.execute("SELECT username FROM users WHERE id = %s;", (uid[0],))
            tmp_res = cur.fetchall()

            if not tmp_res:
                return False
            
            if tmp_res[0][0] == user:
                return True
        
        return False

    def user_can_access(self, user):
        return self.check_owner(user) or self.check_shared(user)


    def get_meeting_status(self):
        try:
            status = None
            gl_status = None
            metadata_file = open(self.recording_path+'/'+self.id+'/metadata.xml', 'r')
            metadata_xml = metadata_file.read()
            metadata = BeautifulSoup(metadata_xml, 'xml')
            meta = metadata.find_all('meta')
            meta = meta[0]
            state = meta.find('state')
            
            if (state):
                status = state.get_text();

            gl_listed = meta.find('gl-listed')
            if gl_listed:
                gl_status = gl_listed.get_text()
            
            if  status == 'private':
                return self.ACCESS_PRIVATE
            if gl_status == self.ACCESS_PUBLIC or status == 'published':
                return self.ACCESS_PUBLIC
            if gl_status == self.ACCESS_AUTH or state == 'unlisted':
                return self.ACCESS_AUTH

        except:
            pass
        
        return self.ACCESS_PRIVATE

    def has_access_code(self):
        bbbid = self.get_bbbid()
        if not bbbid:
            raise Exception("Unable to check for access code")
    
        cur = self.db_conn.cursor(cursor_factory = psycopg2.extras.RealDictCursor)
        
        # Get owner of room
        cur.execute("SELECT access_code FROM rooms WHERE bbb_id = %s;", (bbbid,))
        res = cur.fetchall()
        if not res:
            return None
        
        return res[0]['access_code']

    def get_access_code(self):
        return self.has_access_code()        