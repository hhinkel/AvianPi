#import
import random
import uuid
import os

class CaptionGenerator:
	def get_word_one(self):
		return random.choice(("A", "Another", "One more", "A different", "A new"))
	
	def get_word_two(self):
		return random.choice(("bird", "birdfeeder", "avian"))
		
	def get_word_three(self):
		return random.choice(("photo", "image", "picture", "photograph"))
		
class TempImage:
	def __init__(self, basePath="./", ext=".jpg"):
		#construct the file path
		self.path = "{base_path}/{rand}{ext}".format(base_path=basePath, rand=str(uuid.uuid4()), ext=ext)
	
	def cleanup(self):
		#remove the file
		os.remove(self.path)

		
