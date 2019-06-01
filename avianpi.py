#import
from classes import TempImage
from classes import CaptionGenerator
from picamera.array import PiRGBArray
from picamera import PiCamera
from InstagramAPI import InstagramAPI
import tweepy
import argparse
import warnings
import datetime
import imutils
import json
import time
import cv2

#construct the argument parser and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument("-c", "--conf", default="/home/pi/AvianPi/conf.json", help="path to JSON configuration file")
args = vars(ap.parse_args())

#filter warnings, load the configuration
warnings.filterwarnings("ignore")
conf = json.load(open(args["conf"]))

#check if using instagram
if conf["use_instagram"]:
	#login
	instagramAPI = InstagramAPI(conf["instagram_user"], conf["instagram_pwd"])
	login = instagramAPI.login()
	if (login):
		print("Login successful")
	else:
		print("Login error")
	
#initialize the camera and setup a reference to the raw capture
camera = PiCamera()
camera.resolution = tuple(conf["resolution"])
camera.framerate = conf["fps"]
rawCapture = PiRGBArray(camera, size=tuple(conf["resolution"]))

#allow the camera to warmup, then initialize the average frame (avg),
#lastUploaded, and motionCounter
print("[INFO] warming up ...")
time.sleep(conf["camera_warmup_time"])
avg = None
lastUploaded = datetime.datetime.now()
motionCounter = 0

#capture frames from the camera
for f in camera.capture_continuous(rawCapture, format="bgr", use_video_port=True):
	#grab the raw NumPy array representing the image and initialize
	#the timestamp and text
	frame = f.array
	timestamp = datetime.datetime.now()
	text = "No motion"
	
	#resize the frame, convert it to grayscale, and blur it
	frame = imutils.resize(frame, width=500, inter=cv2.INTER_NEAREST)
	gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
	gray = cv2.GaussianBlur(gray, (21, 21), 0)
	
	#if the average frame is None, initialize it
	if avg is None:
		print("[INFO] starting background model ...")
		avg = gray.copy().astype("float")
		rawCapture.truncate(0)
		continue
	
	#accumulate the weighted average between the current frame and 
	#previous frames, then compute the difference between them
	cv2.accumulateWeighted(gray, avg, 0.5)
	frameDelta = cv2.absdiff(gray, cv2.convertScaleAbs(avg))
	
	#threshold the delta image, dilate the thresholded image to fill
	#in the holes.  Then find the the contours of the thresholded image
	thresh = cv2.threshold(frameDelta, conf["delta_thresh"], 255, cv2.THRESH_BINARY)[1]
	thresh = cv2.dilate(thresh, None, iterations=2)
	cnts = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
	cnts = imutils.grab_contours(cnts)
	
	#loop over the contours
	for c in cnts:
		#if the contour is too small ignore
		if cv2.contourArea(c) < conf["min_area"]:
			continue
		
		#Compute the bounding box for the contour, draw it on the frame 
		#and update the text
		(x, y, w, h) = cv2.boundingRect(c)
		cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
		text = "Motion"
		
	#draw the text and timestmp on the frame
	ts = timestamp.strftime("%A %d %B %Y %I:%M:%S%p")
	cv2.putText(frame, ts, (10, frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1)
	
	#check to see if there is motion
	if text == "Motion":
		#check to see if enough time has passed between uploads
		
		if (timestamp - lastUploaded).seconds >= conf["min_upload_seconds"]:
			#increment the montion counter
			motionCounter += 1
			
			#check to see if the number of frames with consistent motion is high enough
			if motionCounter >= conf["min_motion_frames"]:
				if conf["save_image"] or conf["use_instagram"] or conf["use_twitter"]:
			
					#write image to temp file
					t = TempImage()
					cv2.imwrite(t.path, frame)
					
					#create 
					caption = CaptionGenerator()
					caption_text = caption.get_word_one() + " " + caption.get_word_two() + " " + caption.get_word_three() + "."
				
					if conf["save_image"]:                                                                        
						print("[FILE] {}".format(ts))  
						path = "/{base_path}/{timestamp}.jpg".format(base_path=conf["save_base_path"], timestamp=timestamp.strftime("%A%d%B%Y%I:%M:%S%p"))
						print(path)
						cv2.imwrite(path, frame)
					
					if conf["use_instagram"] and login:
						print("[POST INSTAGRAM] {}".format(ts))
						instagramAPI.uploadPhoto(t.path, text)
					
					if conf["use_twitter"]:
						print("[POST TWITTER] {}".format(ts))
						auth = tweepy.OAuthHandler(conf["api_key"], conf["api_pwd"])
						auth.set_access_token(conf["access_token"], conf["access_pwd"])
						api = tweepy.API(auth)
						
						res = api.media_upload(t.path)
						api.update_status(status=caption_text, media_ids=[res.media_id])
						
				#update the last uploaded timestamp amd reset the motion counter
				t.cleanup()
				lastUploaded = timestamp
				motionCounter = 0
	
	else:
		motionCounter = 0
		
	#check to see if the frames should be displayed to the screen
	if conf["show_video"]:
		#display the security feed
		cv2.imshow("Bird Cam", frame)
		key = cv2.waitKey(1) & 0xFF
		
		if key == ord("q"):
			break
	
	#clear the stream in preperation for the next frame
	rawCapture.truncate(0)
