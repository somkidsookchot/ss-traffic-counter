import unittest
import sys
import json
import datetime
sys.path.append("../")
from app import Logger as LoggerClass

class Test(unittest.TestCase):

    logger = LoggerClass.Logger()

    def test_getCamLog(self):
        cam = '1'
        self.assertRegex(self.logger.fetchCamLog(cam),'\[*.') #should return json block

    def test_getLog(self):
        response = {
            "id":1,
            "group_name":"frontgate",
            "name":"cam1",
            "details":{"car":"in"},
            "inserted_date":""
        }
        id = '1'
        data = json.loads(self.logger.fetchLogs(id))
        # Assert response
        self.assertEqual(data, response)
            

    def test_post(self):
        params = {
            "id":6,
            "group_name":"frontgate",
            "name":"cam1",
            "details":json.dumps({"car":"in"}),
            "inserted_date":"2019-05-24 :10:38:00",
        }
        response = {
            "id":6,
            "group_name":"frontgate",
            "name":"cam1",
            "details":json.dumps({"car":"in"}),
            "inserted_date":"2019-05-24 :10:38:00"
        }
        data = json.loads(self.logger.postLog(params))
        # Assert response
        self.assertEqual(data, response)

    def test_put(self):
        id = '6'
        # Assert response
        self.assertEqual(self.logger.updateLog(id),204)

    def test_del(self):
        id = '6'
        self.assertEqual(self.logger.deleteLog(id),204)

if __name__ == '__main__':
    unittest.main()