import cv2
import numpy as np
import sys
from time import sleep
from websocket import create_connection
sys.path.append("../")


def on_message(ws, message):
    print(message)

def on_error(ws, error):
    print(error)

def on_close(ws):
    print("### closed ###")

def on_open(ws):
    def run(*args):
        for i in range(3):
            time.sleep(1)
            ws.send("Hello %d" % i)
        #time.sleep(1)
        #ws.close()
        #print("thread terminating...")
    thread.start_new_thread(run, ())

def pega_centro(x, y, w, h):
    x1 = int(w / 2)
    y1 = int(h / 2)
    cx = x + x1
    cy = y + y1
    return cx,cy

def logging(text):
    print(text)

def counter_start(arg):
    #logger = LoggerClass.Logger()

    
    #cur.execute("create table images(id string, img blob)")
    #db.commit()

    #writes array to .yml file
    #fs_write = cv2.FileStorage('new_data.yml', cv2.FILE_STORAGE_WRITE)

    largura_min=80 #Largura minima do retangulo
    altura_min=80 #Altura minima do retangulo

    offset=6 #Erro permitido entre pixel  

    pos_linha=550 #Posição da linha de contagem 

    delay= 60 #FPS do vídeo

    detec = []
    carros= 0
    cap = cv2.VideoCapture("D:/Python/traffic_videos/video.mp4")
    subtracao = cv2.bgsegm.createBackgroundSubtractorMOG()

    while True:
        ret , frame1 = cap.read()
        tempo = float(1/delay)
        sleep(tempo) 
        grey = cv2.cvtColor(frame1,cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(grey,(3,3),5)
        img_sub = subtracao.apply(blur)
        dilat = cv2.dilate(img_sub,np.ones((5,5)))
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        dilatada = cv2.morphologyEx (dilat, cv2. MORPH_CLOSE , kernel)
        dilatada = cv2.morphologyEx (dilatada, cv2. MORPH_CLOSE , kernel)
        
        #img,contours,h = cv2.findContours(dilatada,cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE) // depend on openCV version
        contours, hierarchy = cv2.findContours(dilatada, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        cv2.line(frame1, (25, pos_linha), (1200, pos_linha), (255,127,0), 3) 
        for(i,c) in enumerate(contours):
            (x,y,w,h) = cv2.boundingRect(c)
            validar_contours = (w >= largura_min) and (h >= altura_min)
            if not validar_contours:
                continue

            cv2.rectangle(frame1,(x,y),(x+w,y+h),(0,255,0),2)        
            centro = pega_centro(x, y, w, h)
            detec.append(centro)
            cv2.circle(frame1, centro, 4, (0, 0,255), -1)

            for (x,y) in detec:
                if y<(pos_linha+offset) and y>(pos_linha-offset):
                    carros+=1
                    cv2.line(frame1, (25, pos_linha), (1200, pos_linha), (0,127,255), 3)  
                    detec.remove((x,y))
                    print("Cars detected so far: "+str(carros)) 

                    #Logging
                    #params = {
                    #      "group_name":"frontgate",
                    #      "name":"cam1",
                    #      "details":json.dumps({"car":"in"})
                    #  }
                    # logger.postLog(params)
                    #arr = np.random.rand(5, 5)
                    #fs_write.write("floatdata", arr)
                    ws = create_connection("ws://192.168.1.36:1880/ws/cam1/")
                    ws.send(str(carros))
                    ws.close()
                    
                    
                     
           
        cv2.putText(frame1, "Cars: "+str(carros), (450, 70), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 255),5)
        cv2.imshow("Video Original" , frame1)
        #cur.execute("insert into images values(?,?)",(str(carros),''))
        #db.commit()



        if cv2.waitKey(1) == 27:
            break
        
    cv2.destroyAllWindows()
    cap.release()
    #fs_write.release()

if __name__ == '__main__':
    counter_start(sys.argv[1])