import cv2
import numpy as np
import dlib
import datetime
import argparse
import paho.mqtt.client as mqtt #import the client1
import base64
from trackerclass.centroidtracker import CentroidTracker
from trackerclass.trackableobject import TrackableObject
import imutils
from imutils.video import VideoStream
from imutils.video import FPS

parser = argparse.ArgumentParser(add_help=False)
parser.add_argument('--reset', help='Start and reset counter.')
parser.add_argument('--mqtt', required=True, help='mqtt broker IP address.')
parser.add_argument('--mqtttopic', required=True, help='mqtt topic')
parser.add_argument('--streamurl', required=True, help='Streaming URL of Ip camera')
parser.add_argument('--poscountline', type=int, default=180 ,help='Postion of count line')
parser.add_argument('--delay', help='FPS From video', default=100)
parser.add_argument('--savefile', help='xml file path to save counter file', default="counter.xml")
parser.add_argument("-s", "--skip-frames", type=int, default=3,
    help="# of skip frames between detections")
args = parser.parse_args()

pos_count_line = args.poscountline

def on_disconnect(client, userdata, rc):
    client.publish(args.mqtttopic+"/status","Disconnected")
    if rc != 0:
        print ("Unexpected MQTT disconnection. Will auto-reconnect")

broker_address = args.mqtt
client = mqtt.Client(args.mqtttopic) #create new instance
client.connect(broker_address) #connect to broker
client.on_disconnect = on_disconnect
client.loop_start()
client.publish(args.mqtttopic+"/status","active")

def to_integer(dt_time):
    return 10000*dt_time.year + 100*dt_time.month + dt_time.day

today = datetime.datetime.now()
todayInt = to_integer(datetime.datetime.now())
#todayInt = to_integer(datetime.date(2019,5,15))
startCount = today.strftime("%Y-%m-%d %H:%M:%S")

carCascade = cv2.CascadeClassifier("carhaar.xml")

fs_read = cv2.FileStorage(args.savefile, cv2.FILE_STORAGE_READ)
arr_read = fs_read.getNode('latest_count').mat()      
fs_read.release()

latestDate = int(arr_read[2][0])
if(latestDate != todayInt):
    totalDown = 0  # keeps track of cars that crossed up
    totalUp = 0  # keeps track of cars that crossed down
else:
    totalUp = int(arr_read[0][0])  # keeps track of cars that crossed up
    totalDown = int(arr_read[1][0])  # keeps track of cars that crossed down

if(args.reset):
    totalDown = 0  # keeps track of cars that crossed up
    totalUp = 0  # keeps track of cars that crossed down

    
ct = CentroidTracker(maxDisappeared=40, maxDistance=50)
trackers = []
trackableObjects = {}
currentCarID = 0
totalFrames = 0
carTracker = {}
carFirstPos = {}

cap = cv2.VideoCapture(args.streamurl)
while True:
    ret , frame = cap.read()
    if ret:
        frame = imutils.resize(frame, width=500)
        # tempo = float(1/delay)
        # sleep(tempo) 

        (height, width) = frame.shape[:2]

        # initialize the current status along with our list of bounding
        # box rectangles returned by either (1) our object detector or
        # (2) the correlation trackers
        status = "Waiting"
        rects = []

        # check to see if we should run a more computationally expensive
        # object detection method to aid our tracker
        if totalFrames % args.skip_frames == 0:

            # set the status and initialize our new set of object trackers
            status = "Detecting"
            trackers = []

            # convert the frame to a blob and pass the blob through the
            # network and obtain the detections
            #blob = cv2.dnn.blobFromImage(frame, 0.007843, (W, H), 127.5)
            #net.setInput(blob)
            #detections = net.forward()
            grey = cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)
            detections = carCascade.detectMultiScale(grey, 1.1, 13, 18, (24, 24))

            # loop over the detections
            for (_x,_y,_w,_h) in detections:

                x = int(_x)
                y = int(_y)
                w = int(_w)
                h = int(_h)

                # construct a dlib rectangle object from the bounding
                # box coordinates and then start the dlib correlation
                # tracker
                tracker = dlib.correlation_tracker()
                tracker.start_track(frame, dlib.rectangle(x, y, x + w, y + h))

                # add the tracker to our list of trackers so we can
                # utilize it during skip frames
                trackers.append(tracker)

        else:
            # loop over the trackers
            for tracker in trackers:
                # set the status of our system to be 'tracking' rather
                # than 'waiting' or 'detecting'
                status = "Tracking"

                # update the tracker and grab the updated position
                tracker.update(frame)
                pos = tracker.get_position()

                # unpack the position object
                startX = int(pos.left())
                startY = int(pos.top())
                endX = int(pos.right())
                endY = int(pos.bottom())
                t_w = int(pos.width())
                t_h = int(pos.height())

                # add the bounding box coordinates to the rectangles list
                rects.append((startX, startY, endX, endY))
            

        
        # use the centroid tracker to associate the (1) old object
        # centroids with (2) the newly computed object centroids
        objects = ct.update(rects)

        # loop over the tracked objects
        for (objectID, centroid) in objects.items():
            # check to see if a trackable object exists for the current
            # object ID
            to = trackableObjects.get(objectID, None)

            # if there is no existing trackable object, create one
            if to is None:
                to = TrackableObject(objectID, centroid)

            # otherwise, there is a trackable object so we can utilize it
            # to determine direction
            else:
                # the difference between the y-coordinate of the *current*
                # centroid and the mean of *previous* centroids will tell
                # us in which direction the object is moving (negative for
                # 'up' and positive for 'down')
                y = [c[1] for c in to.centroids]
                direction = centroid[1] - np.mean(y)
                to.centroids.append(centroid)

                # check to see if the object has been counted or not
                if not to.counted:
                    rect = 50
                    
                    crop_img = frame[centroid[1]-rect:centroid[1]+rect, centroid[0]-rect:centroid[0]+rect]
                    if crop_img.size != 0:
                        ret, buffer = cv2.imencode('.jpg', crop_img)
                        jpg_as_text = base64.b64encode(buffer)
                    else:
                        jpg_as_text = ""

                    #cv2.rectangle(frame,(centroid[0]-rect,centroid[1]-rect),(centroid[0]+rect,centroid[1]+rect),(0,255,0),1)

                    # if the direction is negative (indicating the object
                    # is moving up) AND the centroid is above the center
                    # line, count the object
                    if direction < 0 and centroid[1] < pos_count_line:
                        totalUp += 1
                        to.counted = True
                        client.publish(args.mqtttopic+"/crossedup",totalUp)
                        client.publish(args.mqtttopic+"/crosseddown",totalDown)
                        client.publish(args.mqtttopic+"/snapshotout",jpg_as_text)
                        client.publish("/statusUpdate",'update data')

                    # if the direction is positive (indicating the object
                    # is moving down) AND the centroid is below the
                    # center line, count the object
                    elif direction > 0 and centroid[1] > pos_count_line:
                        totalDown += 1
                        to.counted = True
                        client.publish(args.mqtttopic+"/crossedup",totalUp)
                        client.publish(args.mqtttopic+"/crosseddown",totalDown)
                        client.publish(args.mqtttopic+"/snapshotin",jpg_as_text)
                        client.publish("/statusUpdate",'update data')

            # store the trackable object in our dictionary
            trackableObjects[objectID] = to

            # draw both the ID of the object and the centroid of the
            # object on the output frame
            #text = "ID {}".format(objectID)
            #cv2.putText(frame, text, (centroid[0] - 10, centroid[1] - 10),cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            cv2.circle(frame, (centroid[0], centroid[1]), 4, (0, 255, 0), -1)

        # construct a tuple of information we will be displaying on the
        # frame
        info = [
            ("Up", totalUp),
            ("Down", totalDown),
            ("Status", status),
        ]

        # draw a horizontal line in the center of the frame -- once an
        # object crosses this line we will determine whether they were
        # moving 'up' or 'down'
        cv2.line(frame, (0, pos_count_line), (width, pos_count_line), (0, 255, 255), 2)


        # loop over the info tuples and draw them on our frame
        for (i, (k, v)) in enumerate(info):
            text = "{}: {}".format(k, v)
            cv2.putText(frame, text, (10, height - ((i * 20) + 20)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

        # displays images and transformations
        cv2.imshow(args.mqtttopic, frame)
        #cv2.moveWindow(args.mqtttopic, 0, 0)

        #writes array to .yml file
        fs_write = cv2.FileStorage(args.savefile, cv2.FILE_STORAGE_WRITE)
        arr = (totalUp, totalDown, todayInt)
        fs_write.write("latest_count", arr)
        fs_write.release()

        if totalFrames % 30 == 0:
            client.publish(args.mqtttopic+"/status",'active')
            client.publish(args.mqtttopic+"/crossedup",totalUp)
            client.publish(args.mqtttopic+"/crosseddown",totalDown)
            client.publish("/statusUpdate",'update data')

        totalFrames += 1

        k = cv2.waitKey(1) & 0xff  # int(1000/fps) is normal speed since waitkey is in ms
        if k == 27:
            break
    else: # if video is finished then break loop
        client.publish(args.mqtttopic+"/crossedup",totalUp)
        client.publish(args.mqtttopic+"/crosseddown",totalDown)
        break


client.publish(args.mqtttopic+"/status","Disconnected")
cap.release()
cv2.destroyAllWindows()
client.loop_start()