DropboxBackupSystem
===================

A simple Python script for interacting with the Dropbox API to automatically backup a user's Dropbox files

Dependencies
============

- Dropbox Python Libraries
- pywin32 for Windows Service creation

Project State
=============

The standalone script, DropboxBackup.py, functions perfectly. The Windows service system is not currently functional,
as the backup script does not run properly

Setup Steps
===========

As this has yet to become an official app for Dropbox, if you'd like to use this script yourself, you will have to create
a full access app on the Dropbox developors page, then create a file called "secrets.txt" in the program's directory. This
file should contain the APP_KEY on the first line, followed by the APP_SECRET key on the next line.

Also, for the DropboxBackupService.py script, you will need a file named "config.txt" which contains the path to your 
backup location. This helps facilitate scheduling via Windows Task Scheduler or some other tool.