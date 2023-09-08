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

    bbbid = None

    def __init__(self, config, uri, recording_path):
        self.config = config
        self.uri = uri

        self.recording_path = recording_path
        self.id = self.parse_url(self.uri)
        self.db_conn = psycopg2.connect("dbname="+self.config.env('DB_NAME')+" user="+self.config.env('DB_USERNAME')+" password="+self.config.env('DB_PASSWORD')+" host="+self.config.env('DB_HOST'))

        #if not self.id:
        #    raise Exception("Meeting ID Could not be found from URL: " + uri)
    
    def parse_url(self, url=''):
        r = re.compile(r'[0-9a-f]{40}-[0-9]{13}')
        t = re.compile(r'^/presentation/[0-9a-f]{40}-[0-9]{13}/presentation/[0-9a-f]{40}-[0-9]{13}/thumbnails/(thumb-[1-3].png|images/favicon.png)$')
        try:
            thumb = t.findall(url)
            if thumb:
                return None
            else:
                meetingid = r.findall(url)[0]
                return meetingid
        except:
            return False

    def get_bbbid(self):
        try:
            if self.bbbid is not None:
                return self.bbbid

            metadata_file = open(self.recording_path+'/'+self.id+'/metadata.xml', 'r')
            metadata_xml = metadata_file.read()
            metadata = BeautifulSoup(metadata_xml, 'xml')
            mids = metadata.find_all('meetingId')
            self.bbbid = mids[0].get_text()
            return self.bbbid
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
        cur.execute("SELECT user_id FROM rooms WHERE meeting_id = %s;", (bbbid,))
        res = cur.fetchall()
        
        if not res:
            return False
        
        # get mailaddr of owner
        cur.execute("SELECT email FROM users WHERE id = %s;", (res[0]['user_id'],))
        res = cur.fetchall()
        
        if not res:
            return False
        
        if res[0]['email'] == user:
            return True
        
        return False

    # checks if an authenticating user is the owner of a room
    def check_shared(self, user):
        bbbid = self.get_bbbid()
        if not bbbid:
            return False
        cur = self.db_conn.cursor()

        cur.execute("SELECT id FROM rooms WHERE meeting_id = %s limit 1;", (bbbid,))
        rooms = cur.fetchall()

        cur.execute("SELECT id FROM users WHERE email = %s limit 1;", (user,))
        users = cur.fetchall()

        if not rooms or not users:
            return False

        cur.execute("SELECT user_id FROM shared_accesses WHERE room_id = %s and user_id = %s;", (rooms[0][0], users[0][0]))
        res = cur.fetchall()
        
        if not res:
            return False

        return True

    def user_can_access(self, user):
        return self.check_owner(user) or self.check_shared(user)


    def get_meeting_status(self):
        try:
            # Get visibility status
            cur = self.db_conn.cursor(cursor_factory = psycopg2.extras.RealDictCursor)
            cur.execute("SELECT id, visibility FROM recordings WHERE record_id = %s;", (self.id,))
            res = cur.fetchone()

            if res:
                if res['visibility'] == 'Public':
                    return self.ACCESS_PUBLIC
                elif res['visibility'] == 'Private':
                    return self.ACCESS_PRIVATE
                elif res['visibility'] == 'Published':
                    return self.ACCESS_AUTH
                elif res['visibility'] == 'Unpublished':
                    return None

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

        except Exception as e:
            log(str(e))
        
        return self.ACCESS_PRIVATE

    def has_access_code(self):
        # code to executed until confirmed we still need access code
        bbbid = self.get_bbbid()
        if not bbbid:
            raise Exception("Unable to check for access code")
        
        cur = self.db_conn.cursor(cursor_factory = psycopg2.extras.RealDictCursor)
        
        # Get 'glViewerAccessCode' option ID 
        cur.execute("select id, name from meeting_options where name='glViewerAccessCode' limit 1")
        option = cur.fetchone()
        if not option:
            return None

        # Get room ID from meeting_id
        cur.execute("SELECT id FROM rooms WHERE meeting_id = %s limit 1;", (bbbid,))
        room = cur.fetchone()
        if not room:
            return None

        # Get access code
        cur.execute("select room_id, meeting_option_id, value from room_meeting_options  where meeting_option_id = %s and room_id = %s", (option['id'], room['id']))
        row = cur.fetchone()
        if not row:
            return None

        return row['value']

    def get_access_code(self):
        return self.has_access_code()        
