import cv2
import numpy as np
import os
import time
import sys
from pubnub.pubnub import PubNub, SubscribeListener, SubscribeCallback, PNStatusCategory
from pubnub.pnconfiguration import PNConfiguration 
from pubnub.exceptions import PubNubException 
import pubnub
if(sys.platform != 'win32'):
    import RPi.GPIO as GPIO

# MQTT Settings
pnconf = PNConfiguration()
pnconf.publish_key = 'pub-c-90b929ee-3089-41e3-b543-586d409ea538'
pnconf.subscribe_key = 'sub-c-39a4fa00-9103-4fba-867e-4614ebf67e42' 
pnconf.uuid = "fwefewf12"
pubnub = PubNub(pnconf)
channel = 'CP-IoT'

def my_publish_callback(envelope, status):
    # Check whether request successfully completed or not
    if not status.is_error():
        pass  # Message successfully published to specified channel.
    else:
        print('Error while pushlishing to MQTT')
        pass  # Handle message publish error. Check 'category' property to find out possible issue
        # because of which request did fail.
        # Request can be resent using: [status retry];

class MySubscribeCallback(SubscribeCallback):
    def presence(self, pubnub, presence):
        pass  # handle incoming presence data

    def status(self, pubnub, status):
        if status.category == PNStatusCategory.PNUnexpectedDisconnectCategory:
            pass  # This event happens when radio / connectivity is lost

        elif status.category == PNStatusCategory.PNConnectedCategory:
            # Connect event. You can do stuff like publish, and know you'll get it.
            # Or just use the connected event to confirm you are subscribed for
            # UI / internal notifications, etc
            pubnub.publish().channel('CP-IoT').message('Welcome to CP-IoT MQTT ').pn_async(my_publish_callback)
        elif status.category == PNStatusCategory.PNReconnectedCategory:
            pass
            # Happens as part of our regular operation. This event happens when
            # radio / connectivity is lost, then regained.
        elif status.category == PNStatusCategory.PNDecryptionErrorCategory:
            pass
            # Handle message decryption error. Probably client configured to
            # encrypt messages and on live data feed it received plain text.

    def message(self, pubnub, message):
        # Handle new message stored in message.message
        print(message.message)

pubnub.add_listener(MySubscribeCallback())
pubnub.subscribe().channels('CP-IoT').execute()
print('connected')                                           

def mqtt_send(status) :
    global pubnub
    pubnub.publish().channel("CP-IoT").message({
        'status': status
    }).pn_async(my_publish_callback)
  

# GPIO
def send_signal(line):
    if(sys.platform != 'win32'):
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(line, GPIO.OUT)
        GPIO.output(line, 0)
        GPIO.output(line, 1)

# OpenCV
recognizer = cv2.face.LBPHFaceRecognizer_create()
recognizer.read('trainer/trainer.yml')
cascadePath = "haarcascade_frontalface_default.xml"
faceCascade = cv2.CascadeClassifier(cascadePath);

font = cv2.FONT_HERSHEY_SIMPLEX

id = 0

names = ['Unknwn', 'Owner', 'Unknown'] 

# start video capture
cam = cv2.VideoCapture(0)
cam.set(3, 640) 
cam.set(4, 480)

# Define min window size
minW = cam.get(3)
minH = cam.get(4)

t1 = time.time()
id_list = []
while True:
    ret, img =cam.read()
    gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
    
    faces = faceCascade.detectMultiScale(img)

    for(x,y,w,h) in faces:
        cv2.rectangle(img, (x,y), (x+w,y+h), (0,255,0), 2)
        id, confidence = recognizer.predict(gray[y:y+h,x:x+w])

        # Check if confidence is less them 100 ==> "0" is perfect match 
        if (confidence < 100):
            id = names[id]
            confidence = "  {0}%".format(round(100 - confidence))
        else:
            id = "unknown"
            confidence = "  {0}%".format(round(100 - confidence))
        
        id_list.append(id)

        cv2.putText(img, str(id), (x+5,y-5), font, 1, (255,255,255), 2)
        cv2.putText(img, str(confidence), (x+5,y+h-5), font, 1, (255,255,0), 1)  
    
    cv2.imshow('camera',img) 
    t2 = time.time()
    if(t2 - t1 >= 6):
        break
    k = cv2.waitKey(10) & 0xff # Press 'ESC' for exiting video
    if k == 27:
        break

# Do cleanup
cam.release()
cv2.destroyAllWindows()

count_correct = 0
count_unknown = 0
for id in id_list:
    if(id == 'Owner'):
        count_correct +=1
    else:
        count_unknown +=1

# Results
signal_lines = {'Red': 21, 'Green':17}
if(count_correct >= 10):
    print(' ===== ALLOWED to ENTER ===== ')
    mqtt_send('success to enter')
    send_signal(signal_lines['Green'])
else:
    print(' ===== NOT Allowed ===== ')
    mqtt_send('entry denied')
    send_signal(signal_lines['Red'])
