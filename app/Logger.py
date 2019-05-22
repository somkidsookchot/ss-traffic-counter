import sys
import requests
import json

class Logger(object):

    def __init__(self):
        self.apiServer = 'http://192.168.1.36:1880/api/logs'
        self.logFile = False
        self.logFilePath = 'logs/log.txt'

    def fetchLogs(self,id):
        r = requests.get(self.apiServer+'/'+id)
        return json.dumps(r.json())

    def fetchCamLog(self,cam):
        r = requests.get(self.apiServer+'/cam/'+cam)
        return json.dumps(r.json())

    def postLog(self,params):
        url = self.apiServer+''
        r = requests.post(url, json=params)
        return r.status_code

    def updateLog(self,id):
        r = requests.put(self.apiServer+'/'+id)
        return r.status_code

    def deleteLog(self,id):
        r = requests.delete(self.apiServer+'/'+id)
        return r.status_code


if __name__ == '__main__':
    logger = Logger()