# Authenticate BigBlueButton recordings with greenlight authenticated with LDAP (GEMI)

This tool is developed specifically for the Georg-Elias-Mueller-Institute of Psychology to restrict BigBlueButton recordings with greenlight authenticated with LDAP.
Feel free to extend / modify the tool to suit your own research institute. Inspired by https://github.com/ichdasich/bbb-rec-perm

## Architecture 

We use the request-auth feature of nginx. When a resource connected to the
recordings is accessed, we trigger an internal auth request to a CGI script
also running on localhost.  This script then checks the local recording 
metadata to find the gl-listed property and also the metadata called "state",
added by our greenlight customizations.

Access to thumbnails and favicons is always granted to ensure proper
presentation in the GL frontend, even if the gl-listed value is set to false,
rendering the recording inaccessible. 

## Access Logic

Access Logic:
- If the recording is "public" and the room has no access code then no auth required
- If the recording is "public" and room has an access code then ask for access code
- If the recording is "unlisted" and room has an access code the ask for access code
- If the recording is "unlisted" and room has no access code then authenticate with ldap credentials
- If the recording is "private" then require authentication with ldap and give access to owner of the room and those the room have been shared with.


The greenlight integration is available at: https://github.com/cyriltata/greenlight/tree/gemi-changes


# Installation Instructions

1. Configure greenlight to use the image from https://github.com/users/cyriltata/packages/container/package/gemi%2Fgreenlight in `docker-compose.yml`

`image: ghcr.io/cyriltata/gemi/greenlight:release-v2.10.0.3`

3. Git clone rec-perm
`git clone https://github.com/cyriltata/rec-auth`

4. Install fcgiwrap if it's missing
`apt-get install fcgiwrap`

5. Install bcrypt
`apt-get install python3-bcrypt`

6. Install psycopg
`apt-get install python3-psycopg2`

7. Install BeautifulSoup
`apt-get install python3-bs4`

8. Install the required python packages:

`pip3 install python-ldap pathlib python-dotenv cryptography`


9. Create a .env file in the root of the directory cloned in step 3 with the following configuration (change values accordingly).
```
#.env

GL_ENV_FILE = /opt/greenlight/.env # path to the greenlight env file
BBB_RECORDING_PATH = /var/bigbluebutton/published/presentation # path to BBB published presentations
```

10. Edit your nginx configuration as follows:

- In the `nginx-config` directory copy `usr/share/bigbluebutton/nginx/rec-auth.nginx` to a similar bigbluebutton nginx configuration path (i.e `/usr/share/bigbluebutton/nginx/rec-auth.nginx` on the server).
- In the same directory you would see nginx configuration files similar to those installed by bigbluebutton. Replace nginx configuration files in /usr/share/bigbluebutton/nginx or modify accordingly.
`cp rec-auth/nginx-conf/usr/share/bigbluebutton/nginx/* /usr/share/bigbluebutton/nginx/`
- In `usr/share/bigbluebutton/nginx/rec-auth.nginx`, set the variable `$rec_auth_root` to the installation path in step 3.


12. Restart nginx.
`sudo service nginx restart`
