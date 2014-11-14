from Tkinter import *
import time
import threading
import Queue
from PIL import ImageTk
import json
import dispenser
import RPi.GPIO as gpio
import tweepy
from pushbullet import PushBullet
import sys


#________________ERROR HANDLING______________

pbapi = '4fb5c3185c8cd5e147ff18eadb17dfb5'
pb = PushBullet(pbapi)

def pbullet(header,body):
	push = pb.push_note(header, body)

def errorsend(exctype, value, tb):
	pbullet('Shotbot Error',
	'Type:' + str(exctype) + ' | Value:' + str(value) + ' | Traceback:' + str(tb))
	queue = Queue.Queue()
	queue.put("error")

sys.excepthook = errorsend

#____________SETTINGS_____________________

# Consumer keys and access tokens, used for OAuth
ck = 'vHvp3R6uhQBweMBMSUiXV5W8E'
cs = 'iTztnGLbwikrJgdycfBajolcVKD73VOqEgmsYhoOjixwptrUNQ'
ut = '2770372300-mAKrX5FWEhznT6vi2Ukus2NU2pihVAnlmN1w4QT'
us = 'LXuANUvTB0rUl8QZH884XdvodFgKxf97EcK6jvgJw7pkM'

# OAuth process, using the keys and tokens
auth = tweepy.OAuthHandler(ck, cs)
auth.set_access_token(ut, us)
 
# Creation of the actual interface, using authentication
api = tweepy.API(auth, parser=tweepy.parsers.JSONParser())


#____________PHRASES AND COUNT____________

phrases = []
phrases.append("RonZacapa")
phrases.append("HouseAboveTheClouds")
phrases.append("Zacapa23")
phrases.append("SugarCaneHoneyRum")
phrases.append("SmoothAsSilk")
phrases.append("WorldsBestRum")
phrases.append("LuxuryPersonified")

try:
	phraseonboot = open("bartendro/ui/phrase.txt")
	phrase_number = int(phraseonboot.read())
	phraseonboot.close()
except:
	phrase_number = 0

try:
	shotcountonboot = open("bartendro/ui/shotcount.txt")
	shotcount = int(shotcountonboot.read())
	shotcountonboot.close()
except:
	shotcount = 0	

#____________START GUI____________________

class GuiPart:
	def __init__(self, main, queue, endCommand):
        
		self.queue = queue

		# Set up the GUI
		print "loading ui..."
		# canvas for image
		self.canvas = Canvas(main, width=main.winfo_screenwidth(), height=main.winfo_screenheight())
		self.canvas.grid(row=0, column=0)

		# images
		self.image1 = ImageTk.PhotoImage(file = "bartendro/ui/tbn01.jpg")
		self.image2 = ImageTk.PhotoImage(file = "bartendro/ui/tbn02.jpg")
		self.image3 = ImageTk.PhotoImage(file = "bartendro/ui/tbn03.jpg")

		# set first image on canvas
		self.image_on_canvas = self.canvas.create_image(0, 0, anchor = NW, image = self.image1)
		self.canvas.image = self.image1
		
		# set tweets served
		self.text_on_canvas_count = self.canvas.create_text(960,745, text = shotcount, font = ("helvetica", 70), fill = "white", justify = CENTER)
		self.text_on_canvas_phrase = self.canvas.create_text(960,310, text ="#%s" % phrases[phrase_number], font = ("helvetica", 50), fill = "white", justify = "center")
		
	def processIncoming(self):

		while self.queue.qsize(  ):
			try:
				msg = self.queue.get(0)
				print "queue item received"
				print msg
				if msg[0] == "tweetreceived":
					print "changing to next screen"
					# change image
					self.canvas.itemconfig(self.image_on_canvas, image = self.image2)
					self.canvas.image = self.image2
					# change text 
					self.canvas.delete(self.text_on_canvas_phrase)
					self.canvas.delete(self.text_on_canvas_count)
					self.text_on_canvas_name = self.canvas.create_text(960,370, text = msg[1], font = ("helvetica", 70), fill = "white", justify = CENTER)
										
				if msg[0] == "shotpoured":
					
					print "reverting to first screen"

					#revert to first screen
					self.canvas.itemconfig(self.image_on_canvas, image = self.image1)
					self.canvas.image = self.image1
					# change text 
					self.canvas.delete(self.text_on_canvas_name)
					self.canvas.delete(self.text_on_canvas_count)
					self.text_on_canvas_count = self.canvas.create_text(960,745, text = msg[1], font = ("helvetica", 70), fill = "white", justify = CENTER)
					self.text_on_canvas_phrase = self.canvas.create_text(960,310, text ="#%s" % phrases[phrase_number], font = ("helvetica", 50), fill = "white", justify = "center")
			
				if msg == "error":
					
					print "throwing up error screen"

					#throw up error screen
					self.canvas.itemconfig(self.image_on_canvas, image = self.image3)
					self.canvas.image = self.image3
					
					# remove text
					try: 
						self.canvas.delete(self.text_on_canvas_name)
					except: pass
					try:
						self.canvas.delete(self.text_on_canvas_count)
					except: pass
					try:
						self.canvas.delete(self.text_on_canvas_phrase)
					except: pass

			except Queue.Empty:
				# just on general principles, although we don't
				# expect this branch to be taken in this case
				pass

class ThreadedClient:
	
	def __init__(self, master):

		self.master = master
		
        # Create the queue
		self.queue = Queue.Queue()

        # Set up the GUI part
		self.gui = GuiPart(master, self.queue, self.endApplication)

        # Set up the thread to do asynchronous I/O
        # More threads can also be created and used, if necessary
		self.running = 1
		self.thread1 = threading.Thread(target=self.workflow)
		self.thread1.start(  )
		
        # Start the periodic call in the GUI to check if the queue contains
        # anything
		self.periodicCall(  )
		
	def periodicCall(self):
		
		self.gui.processIncoming(  )
		if not self.running:
            # This is the brutal stop of the system. You may want to do
            # some cleanup before actually shutting it down.
			import sys
			sys.exit(1)
		self.master.after(200, self.periodicCall)
		
		#button and light
		gpio.setmode(gpio.BCM)
		gpio.setup(29, gpio.IN, pull_up_down=gpio.PUD_UP)
		gpio.setup(31, gpio.OUT)
			
	def workflow(self): #MAIN PROGRAM
		
		print "workflow started"
		global phrases
		global phrase_number
		global shotcount
		
		print "Fetching last tweet ID"
		lastTweet = api.search(q='@aficionadobar',result_type = 'recent', count=1)['statuses'][0]
		lastTweetText = lastTweet['text']
		lastTweetId = lastTweet['id']
		print "last tweet ID = " +str(lastTweetId)
		
		while self.running:
			time.sleep(5)
			print "looking for new tweets"
			phrase = phrases[phrase_number].lower()
			searchterm = '@aficionadobar ' + phrase
			try:
				data = api.search(q=searchterm , result_type = 'recent', since_id=lastTweetId, count=1)['statuses']
			except: pass
			if data:
				print "new tweet found"
				tname = data[0]['user']['name']
				print tname
				tweetdata = ("tweetreceived",str(tname))
				self.queue.put(tweetdata)
			
				print "waiting for button press"
				#wait for button press	
				b = True
				gpio.output(31,1)
				while b:
					if not (gpio.input(29)):
						b = False
						gpio.output(31,0)
					time.sleep(0.01)
				
				print "pouring shot"
				#pour shot
				dispenser.dispense()
				
				#increment phrase
				phrase_number = phrase_number + 1
				if phrase_number == len(phrases):
					phrase_number = 0
				savephrase = open("bartendro/ui/phrase.txt","w")
				savephrase.write(str(phrase_number))
				savephrase.close()
				
				#increment shotcount
				shotcount += 1
				saveshotcount = open("bartendro/ui/shotcount.txt","w")
				saveshotcount.write(str(shotcount))
				saveshotcount.close()
				
				msg = ("shotpoured", str(shotcount))
				self.queue.put(msg)
					
				lastTweetId = data[0]['id']	
				gpio.cleanup()
			else:
				print "no new tweets" 		


	def endApplication(self):
		self.running = 0
		
root = Tk(  )
client = ThreadedClient(root)
root.overrideredirect(True)
root.mainloop(  )
