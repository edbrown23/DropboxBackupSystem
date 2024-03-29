### Run Python scripts as a service example (ryrobes.com)
### Usage : python WindowsServiceRunner.py install (or / then start, stop, remove)
### Modified from blog post found here: http://ryrobes.com/python/running-python-scripts-as-a-windows-service/

import win32service
import win32serviceutil
import win32api
import win32con
import win32event
import win32evtlogutil
import os, sys, string, time

class aservice(win32serviceutil.ServiceFramework):
    _svc_name_ = "DropboxBackupService"
    _svc_display_name_ = "Dropbox Backup Service"
    _svc_description_ = "Periodically downloads and updates a user's Dropbox files. This service will never delete a file"
         
    def __init__(self, args):
           win32serviceutil.ServiceFramework.__init__(self, args)
           self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)           

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)                    
         
    def SvcDoRun(self):
        import servicemanager      
        servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,servicemanager.PYS_SERVICE_STARTED,(self._svc_name_, '')) 
      
        self.timeout = 640000    #640 seconds / 10 minutes (value is in milliseconds)
        #self.timeout = 120000     #120 seconds / 2 minutes
        # This is how long the service will wait to run / refresh itself (see script below)

        while 1:
            # Wait for service stop signal, if I timeout, loop again
            rc = win32event.WaitForSingleObject(self.hWaitStop, self.timeout)
            # Check to see if self.hWaitStop happened
            if rc == win32event.WAIT_OBJECT_0:
                # Stop signal encountered
                servicemanager.LogInfoMsg("DropboxBackupService - STOPPED!")  #For Event Log
                break
            else:
                try:
                    execfile(backupScriptPath) #Execute the script
                except:
                    pass

def ctrlHandler(ctrlType):
   return True
                  
if __name__ == '__main__':
    if len(sys.argv) != 4:
        print """Three Arguments required. Service command, DropboxBackupService.py location, and config file location. 
              EX: python WindowsServiceRunner.py install C:/DropboxBackupService.py_location C:/config_location"""
    else:
        configPath = sys.argv.pop()
        os.environ['DROPBACK_CONFIG_LOG'] = configPath
        backupScriptPath = sys.argv.pop()
        win32api.SetConsoleCtrlHandler(ctrlHandler, True)   
        win32serviceutil.HandleCommandLine(aservice)