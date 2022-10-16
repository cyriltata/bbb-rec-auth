from src.logger import log

import ldap
from ldap import LDAPError

class GLAuthLdap:

    conn = None

    def __init__(self, config):
        self.config = config

    def connect(self):
        if self.conn is not None:
            return

        

        try:
            url = self.protocol() + "top.gwdg.de" + ':' + self.config.env('LDAP_PORT')

            self.conn = ldap.initialize(url)
            self.conn.set_option(ldap.OPT_REFERRALS, 1)
            self.conn.set_option(ldap.OPT_PROTOCOL_VERSION, 3)
            self.conn.simple_bind_s(self.config.env('LDAP_BIND_DN'), self.config.env('LDAP_PASSWORD'))
        except Exception as e:
            log(str(e))

    def protocol(self):
        return 'ldaps://' if self.config.env('LDAP_METHOD') == 'ssl' else 'ldap://'

    def authenticate(self, user, pwd):
        self.connect()
        search_filter = "(&(uid=%s)%s)" % (user, self.config.env('LDAP_FILTER'),)
        result = self.conn.search_s(self.config.env('LDAP_BASE'),  ldap.SCOPE_SUBTREE, search_filter, ['uid', 'mail', 'dn'])

        if not result or len(result) != 1:
            return False

        bindDN = result[0][0]
        try:
            self.conn.simple_bind_s(bindDN, pwd)
            return {
                "dn": bindDN,
                "email": result[0][1]['mail'][0].decode(),
                "uid": result[0][1]['uid'][0].decode()
            }
        except:
            return False
