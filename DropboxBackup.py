import os
import cmd
import webbrowser
import time
import pickle

from dropbox import client, rest, session

APP_KEY = ''
APP_SECRET = ''
ACCESS_TYPE = 'dropbox'

secrets = open('secrets.txt', 'r')
APP_KEY = secrets.readline().rstrip()
APP_SECRET = secrets.readline().rstrip()
secrets.close()

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
        self.running = True
        self.local_cursor = self.setupLocalCursor()
        while self.running:
            delta_response = self.api_client.delta(self.local_cursor)
            self.local_cursor = delta_response['cursor']
            if delta_response['reset']:
                self.printLog('A Reset has been ordered. Ignoring')
                self.updateLocalFiles(delta_response['entries'])
                while delta_response['has_more']:
                    self.printLog('Not Done. Getting next set of files')
                    delta_response = self.api_client.delta(self.local_cursor)
                    self.local_cursor = delta_response['cursor']
                    self.updateLocalFiles(delta_response['entries'])
            else:
                self.updateLocalFiles(delta_response['entries'])
                while delta_response['has_more']:
                    self.printLog('Not Done. Getting next set of files')
                    delta_response = self.api_client.delta(self.local_cursor)
                    self.local_cursor = delta_response['cursor']
                    self.updateLocalFiles(delta_response['entries'])
            self.saveCursor(self.local_cursor)
            self.printLog('Finished Downloading. Sleeping for 10 minutes')
            time.sleep(60 * 10) # Sleep for 10 minutes

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

def command(login_required=True):
    """a decorator for handling authentication and exceptions"""
    def decorate(f):
        def wrapper(self, args):
            if login_required and not self.sess.is_linked():
                self.stdout.write("Please 'login' to execute this command\n")
                return

            try:
                return f(self, *args)
            except TypeError, e:
                self.stdout.write(str(e) + '\n')
            except rest.ErrorResponse, e:
                msg = e.user_error_msg or str(e)
                self.stdout.write('Error: %s\n' % msg)

        wrapper.__doc__ = f.__doc__
        return wrapper
    return decorate

class DropboxBackup(cmd.Cmd):
    def __init__(self, app_key, app_secret):
        cmd.Cmd.__init__(self)
        self.sess = StoredSession(app_key, app_secret, access_type=ACCESS_TYPE)
        self.api_client = client.DropboxClient(self.sess)
        self.current_path = ''
        self.prompt = "DropboxBackup> "
        self.mounted = False

        self.sess.load_creds()

    @command()
    def do_install(self):
        """Setup the program as a service"""
        if self.mounted:
            # TODO Create the windows service and and put this application there
            self.backupManager.runManager()
        else:
            print "You must first mount the backup system using the 'mount' command!"

    @command(login_required=False)
    def do_login(self):
        """log in to a Dropbox account"""
        try:
            self.sess.link()
        except rest.ErrorResponse, e:
            self.stdout.write('Error: %s\n' % str(e))

    @command()
    def do_logout(self):
        """log out of the current Dropbox account"""
        self.sess.unlink()
        self.current_path = ''

    @command()
    def do_mount(self, path = "C:/DropboxBackup"):
        """Mount the backup to the specified path, saving all backup there"""
        self.backupManager = BackupManager(path, self.sess, self.api_client)
        self.mounted = True
        print "Mounted backup to the following folder: " + path

    @command()
    def do_exit(self):
        """Quit the program"""
        return True

class StoredSession(session.DropboxSession):
    """a wrapper around DropboxSession that stores a token to a file on disk"""
    TOKEN_FILE = "token_store.txt"

    def load_creds(self):
        try:
            stored_creds = open(self.TOKEN_FILE).read()
            self.set_token(*stored_creds.split('|'))
            print "[loaded access token]"
        except IOError:
            pass # don't worry if it's not there

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

def readSecretKeys():
    secrets = open('secrets.txt', 'r')
    APP_KEY = secrets.readline().rstrip()
    APP_SECRET = secrets.readline().rstrip()
    #APP_KEY = '0o0eh7444vn4sq7'
    #APP_SECRET = 'ckd7bnbb3otlpdu'

def main():
    #readSecretKeys()
    backup = DropboxBackup(APP_KEY, APP_SECRET)
    backup.cmdloop()

if __name__ == '__main__':
    main()