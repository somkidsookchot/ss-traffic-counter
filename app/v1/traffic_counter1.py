import cv2
import numpy as np
from time import sleep
import datetime
import argparse
import paho.mqtt.client as mqtt #import the client1
import base64

parser = argparse.ArgumentParser(add_help=False)
parser.add_argument('--reset', help='Start and reset counter.')
parser.add_argument('--mqtt', required=True, help='mqtt broker IP address.')
parser.add_argument('--mqtttopic', required=True, help='mqtt topic')
parser.add_argument('--streamurl', required=True, help='Streaming URL of Ip camera')
parser.add_argument('--poscountline', type=int, default=400 ,help='Postion of count line')
parser.add_argument('--delay', help='FPS From video')
parser.add_argument('--savefile', help='xml file path to save counter file')
args = parser.parse_args()

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


width_min=80 #Minimum width of the rectangle
height_min=80 #Minimum height of the rectangle

offset=6 #Permitted pixel error

if (args.poscountline):
    pos_count_line = args.poscountline
else:
    pos_count_line =  550 #Count line position

if (args.delay):
    delay= args.delay
else:
    delay = 60 #FPS from the video

detec = []

# read latest counter from file
if(args.savefile): 
    xml = args.savefile
else:
    xml = "counter.xml"

fs_read = cv2.FileStorage(xml, cv2.FILE_STORAGE_READ)
arr_read = fs_read.getNode('latest_count').mat()      
fs_read.release()

latestDate = int(arr_read[2][0])
if(latestDate != todayInt):
    carin = 0  # keeps track of cars that crossed up
    carout = 0  # keeps track of cars that crossed down
else:
    carout = int(arr_read[0][0])  # keeps track of cars that crossed up
    carin = int(arr_read[1][0])  # keeps track of cars that crossed down

if(args.reset):
    carin = 0  # keeps track of cars that crossed up
    carout = 0  # keeps track of cars that crossed down

    
def catch_center(x, y, w, h):
    x1 = int(w / 2)
    y1 = int(h / 2)
    cx = x + x1
    cy = y + y1
    return cx,cy

cap = cv2.VideoCapture(args.streamurl)

frames_count, fps, width, height = cap.get(cv2.CAP_PROP_FRAME_COUNT), cap.get(cv2.CAP_PROP_FPS), cap.get(
    cv2.CAP_PROP_FRAME_WIDTH), cap.get(cv2.CAP_PROP_FRAME_HEIGHT)

subtracao = cv2.bgsegm.createBackgroundSubtractorMOG()
wdCount = 30
while True:
    ret , image = cap.read()
    if ret:

        width, height = cap.get(cv2.CAP_PROP_FRAME_WIDTH), cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        width = int(width)
        height = int(height)

        tempo = float(1/delay)
        sleep(tempo) 
        grey = cv2.cvtColor(image,cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(grey,(3,3),5)
        img_sub = subtracao.apply(blur)
        dilat = cv2.dilate(img_sub,np.ones((5,5)))
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        dilatada = cv2.morphologyEx (dilat, cv2. MORPH_CLOSE , kernel)
        dilatada = cv2.morphologyEx (dilatada, cv2. MORPH_CLOSE , kernel)
        
        #img,contours,h = cv2.findContours(dilatada,cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE) // depend on openCV version
        contours, hierarchy = cv2.findContours(dilatada, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        cv2.line(image, (0, pos_count_line), (width, pos_count_line), (255,127,0), 3) 
        for(i,c) in enumerate(contours):
            (x,y,w,h) = cv2.boundingRect(c)
            validar_contours = (w >= width_min) and (h >= height_min)
            if not validar_contours:
                continue

            cv2.rectangle(image,(x,y),(x+w,y+h),(0,255,0),2)     

            crop_img = image[y:y+h, x:x+w]
            

            centro = catch_center(x, y, w, h)
            detec.append(centro)
            #cv2.circle(image, centro, 4, (0, 0,255), -1)

            for (x,y) in detec:
                if y<(pos_count_line+offset) and y>(pos_count_line-offset):

                    ret, buffer = cv2.imencode('.jpg', crop_img)
                    jpg_as_text = base64.b64encode(buffer)

                    if(centro[0] > (pos_count_line+offset)):
                        carout+=1
                        client.publish(args.mqtttopic+"/crossedup",carout)
                        client.publish(args.mqtttopic+"/crosseddown",carin)
                        client.publish(args.mqtttopic+"/snapshotout",jpg_as_text)
                    else:
                        carin+=1
                        client.publish(args.mqtttopic+"/crossedup",carout)
                        client.publish(args.mqtttopic+"/crosseddown",carin)
                        client.publish(args.mqtttopic+"/snapshotin",jpg_as_text)

                    
                    

                    cv2.line(image, (0, pos_count_line), (width, pos_count_line), (0,127,255), 3)  
                    detec.remove((x,y))
                    print("Cars in: "+str(carin))    
                    print("Cars out: "+str(carout))

           
        cv2.putText(image, "Cars in: "+str(carin), (20, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255),1)
        cv2.putText(image, "Cars out: "+str(carout), (400, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255),1)
        #cv2.imshow("Detectar",dilatada)

        # displays images and transformations
        cv2.imshow(args.mqtttopic, image)
        cv2.moveWindow(args.mqtttopic, 0, 0)

        #writes array to .yml file
        fs_write = cv2.FileStorage(xml, cv2.FILE_STORAGE_WRITE)
        arr = (carout, carin, todayInt)
        fs_write.write("latest_count", arr)
        fs_write.release()

        wdCount -= 1
        if(wdCount == 0):
            client.publish(args.mqtttopic+"/status",'active')
            client.publish(args.mqtttopic+"/crossedup",carout)
            client.publish(args.mqtttopic+"/crosseddown",carin)
            wdCount = 30

        k = cv2.waitKey(int(1000/fps)) & 0xff  # int(1000/fps) is normal speed since waitkey is in ms
        if k == 27:
            break
    else: # if video is finished then break loop
        client.publish(args.mqtttopic+"/crossedup",carout)
        client.publish(args.mqtttopic+"/crosseddown",carin)
        break

client.publish(args.mqtttopic+"/status","Disconnected")
cap.release()
cv2.destroyAllWindows()
client.loop_start()