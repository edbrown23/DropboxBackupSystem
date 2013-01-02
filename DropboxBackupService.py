import os
import cmd
import webbrowser
import time
import pickle

from dropbox import client, rest, session

APP_KEY = '0o0eh7444vn4sq7'
APP_SECRET = 'ckd7bnbb3otlpdu'
ACCESS_TYPE = 'dropbox'

def createParents(path):
    if os.path.isdir(path):
        return 
    head, tail = os.path.split(path)
    createParents(head)
    os.mkdir(head + '/' + tail)
    return

class BackupManager():
    def __init__(self, path, session, client):
        self.sess = session
        self.api_client = client

        self.save_location = path
        if not os.path.isdir(path):
            os.mkdir(path)

    def runManager(self):
        self.local_cursor = self.setupLocalCursor()

        delta_response = self.api_client.delta(self.local_cursor)
        self.local_cursor = delta_response['cursor']
        if delta_response['reset']:
            self.updateLocalFiles(delta_response['entries'])
            while delta_response['has_more']:
                self.printLog('Not Done. Getting next set of files')
                delta_response = self.api_client.delta(self.local_cursor)
                self.local_cursor = delta_response['cursor']
                self.updateLocalFiles(delta_response['entries'])
        else:
            self.updateLocalFiles(delta_response['entries'])
            while delta_response['has_more']:
                delta_response = self.api_client.delta(self.local_cursor)
                self.local_cursor = delta_response['cursor']
                self.updateLocalFiles(delta_response['entries'])
        self.saveCursor(self.local_cursor)

    def updateLocalFiles(self, entries):
        for entry in entries:
            path = entry[0]
            metadata = entry[1]
            if metadata is not None:
                if metadata['is_dir']:
                    createParents(self.save_location + metadata['path'])
                else:
                    head, tail = os.path.split(self.save_location + metadata['path'])
                    if not os.path.isdir(head):
                        createParents(head)
                    if os.path.isfile(self.save_location + metadata['path']):
                        os.remove(self.save_location + metadata['path'])
                    self.getFile(path, self.save_location + metadata['path'])

    def getFile(self, dropbox_path, system_path):
        print "Downloading file from: " + dropbox_path + ". Saving to: " + system_path
        try:
            f, metadata = self.api_client.get_file_and_metadata(dropbox_path)
            out = open(system_path, 'wb')
            out.write(f.read())
            out.close()
        except rest.ErrorResponse as e:
            print e
        except IOError as e:
            print e

    def setupLocalCursor(self):
        try:
            cursor_file = open(self.save_location + '/localPickle', 'r')
            cursor = pickle.load(cursor_file)
            cursor_file.close()
            return cursor
        except IOError:
            return None

    def saveCursor(self, cursor):
        output_file = open(self.save_location + '/localPickle', 'w')
        pickle.dump(cursor, output_file)
        output_file.close()

    def printLog(self, message):
        log = ('\n' + (len(message) * '=') + '\n' + message + '\n' + (len(message) * '=') + '\n')
        print log

class DropboxBackup():
    def __init__(self, app_key, app_secret):
        self.sess = StoredSession(app_key, app_secret, access_type=ACCESS_TYPE)
        self.api_client = client.DropboxClient(self.sess)

        if not self.sess.load_creds():
            self.do_login()

    def do_login(self):
        try:
            self.sess.link()
        except rest.ErrorResponse, e:
            self.stdout.write('Error: %s\n' % str(e))

    def do_mount(self, path = "C:/DropboxBackup"):
        self.backupManager = BackupManager(path, self.sess, self.api_client)

    def start_sync(self):
        self.backupManager.runManager()

class StoredSession(session.DropboxSession):
    """a wrapper around DropboxSession that stores a token to a file on disk"""
    TOKEN_FILE = "token_store.txt"

    def load_creds(self):
        try:
            stored_creds = open(self.TOKEN_FILE).read()
            self.set_token(*stored_creds.split('|'))
            return True
        except IOError:
            return False

    def write_creds(self, token):
        f = open(self.TOKEN_FILE, 'w')
        f.write("|".join([token.key, token.secret]))
        f.close()

    def delete_creds(self):
        os.unlink(self.TOKEN_FILE)

    def link(self):
        request_token = self.obtain_request_token()
        url = self.build_authorize_url(request_token)
        print "url:", url
        print "Please authorize in the browser. After you're done, press enter."
        webbrowser.open(url)
        raw_input()

        self.obtain_access_token(request_token)
        self.write_creds(self.token)

    def unlink(self):
        self.delete_creds()
        session.DropboxSession.unlink(self)

def setupFromConfigFile():
    config = open(os.environ['DROPBACK_CONFIG_LOG'], 'r')
    path = config.readline()
    backup = DropboxBackup(APP_KEY, APP_SECRET)
    backup.do_mount(path)
    return backup

def main():
    backup = setupFromConfigFile()
    backup.start_sync()

if __name__ == '__main__':
    main()