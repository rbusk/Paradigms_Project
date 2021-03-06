#Mary Connolly, Ryan Busk

import pygame
from pygame.locals import *
import sys
from city import City, Base
from missile import Missile, Bomb
from explosion import Explosion
from math import sqrt
from twisted.internet.defer import DeferredQueue
import cPickle as pickle

PLAYER = 0

data_queue = DeferredQueue()
command_queue = DeferredQueue()

class Gamespace(object):
	"""Gamespace for the client. Contains objects for the game, game loop, screen, etc."""

	def __init__(self, current_player=0):
		"""Initializes gamespace."""

		self.TYPE = None
		self.roundover = 0 #set to 1 when the round is over
		self.current_player = current_player
		self.turn = 0

		#initialize pygame
		pygame.init()
		self.size = width, height = 640, 480
		self.screen = pygame.display.set_mode(self.size)

		self.initialize_cities() #initialize cities

		self.reset_round() #initializes bases and arrays for explosions, missiles, and bombs

		self.maxbombs = 10 #max number of bombs that can be dropped

		#set speeds of missiles and bombs
		self.bomb_speed = 2
		self.missile_speed = 2

		self.player = 1 #1 or 2, depending on who is playing

		#points for players 1 and 2
		self.p1_points = 0
		self.p2_points = 0

	def draw_images(self):
		"""Render all objects to the screen."""

		#black screen
		black = 0, 0, 0
		self.screen.fill(black)

		#draw cities
		for city in self.cities:
			#only draw if alive
			if city.da == 1:
				city.draw()

		#draw bases
		for base in self.bases:
			base.draw()

		#draw missiles
		for missile in self.missiles:
			missile.draw()

		#draw explosions
		for explosion in self.explosions:
			explosion.draw()

		#draw bombs
		for bomb in self.bombs:
			bomb.draw()

		#draw explosions from bomb
		for explosion in self.bomb_explosions:
			explosion.draw()

		#Display player 1's points
		font = pygame.font.Font(None, 36)
		text = font.render(str(self.p1_points),1,(204,0,0))
		textpos = text.get_rect()
		textpos.x = 0
		textpos.y = 0
		self.screen.blit(text,textpos)

		#Display player 2's points
		font2 = pygame.font.Font(None, 36)
		text2 = font.render(str(self.p2_points),1,(204,0,0))
		textpos2 = text2.get_rect()
		textpos2.x = self.size[0]-40
		textpos2.y = 0
		self.screen.blit(text2,textpos2)

		#Display "Missiles" or "Bombs" to let the player know if he is currently shooting missiles or dropping bombs.
		font3 = pygame.font.Font(None, 36)
		text3 = font.render(str(self.TYPE),1,(204,0,0))
		textpos3 = text3.get_rect()
		textpos3.x = self.size[0]/3
		textpos3.y = 0
		self.screen.blit(text3,textpos3)

		#Display the turn number
		font4 = pygame.font.Font(None, 36)
		text4 = font.render("Turn: " + str(self.turn+1),1,(204,0,0))
		textpos4 = text4.get_rect()
		textpos4.x = (self.size[0]/3)*2
		textpos4.y = 0
		self.screen.blit(text4,textpos4)

		#Render to screen
		pygame.display.flip()

	def ticks(self):
		"""Tick function -- handles events, calls tick on objects, checks for dead objects."""

		#if the round is not over
		if not self.roundover:

			#check for user input
			self.handle_events()

			#draw to the screen
			self.draw_images()

			# call ticks for each object

			i = 0 #iterator

			#call tick on each missile
			while (i < len(self.missiles)):
				self.missiles[i].tick()

				#check if missile is dead; if so, create explosion and pop the missile off of list
				if (self.missiles[i].da == 0):
					explosion = Explosion(self.missiles[i].fx, self.missiles[i].fy, 2, 50, self)
					self.explosions.append(explosion)
					del self.missiles[i]
				else:
					i = i+1

			i = 0

			#call tick on each explosion
			while (i < len(self.explosions)):
				self.explosions[i].tick()

				#check if explosion is dead; if so, pop off of list
				if (self.explosions[i].da == 0):
					del self.explosions[i]
				else:
					i = i+1
			
			i = 0

			#call tick on each explosion from a bomb
			while (i < len(self.bomb_explosions)):
				self.bomb_explosions[i].tick()

				#check if explosion is dead; if so, pop off of list
				if (self.bomb_explosions[i].da == 0):
					del self.bomb_explosions[i]
				else:
					i = i+1

			i = 0

			#call tick on each bomb
			while (i < len(self.bombs)):
				self.bombs[i].tick()

				#check if bomb is dead; if so, create explosion and pop bomb off of list
				#also, make city or base "dead"
				if (self.bombs[i].da == 0):

					dest = self.bombs[i].dest #get destination 0-8 of bomb

					#if destination is a base, set count to 0 since it can't shoot any more missiles
					if (dest % 4 == 0):
						self.bases[dest/4].count = 0

					#else if destination is a city, destroy it by setting da to 0 (dead)
					else:
						if (dest <= 3):
							self.cities[dest-1].da = 0
						else:
							self.cities[dest-2].da = 0

					#create explosion
					explosion = Explosion(self.bombs[i].fx, self.bombs[i].fy, 2, 50, self)
					self.bomb_explosions.append(explosion)
					del self.bombs[i]
				else:
					i = i+1

			#check collisions between bombs and missile explosions
			self.check_collisions()
			
			#check if the round is over
			self.roundover = self.check_round_over()

			if self.roundover:

				#check if the entire game is over
				if self.turn == 1 and self.check_turn_over():
					command_queue.put("Game Over")

				#check if the turn is over
				elif self.check_turn_over():
					command_queue.put("Turn Over")

				#otherwise, the round is over
				else:
					command_queue.put("Round Over")

				#calculate points for whoever is aiming missiles
				self.calculate_points()

				self.draw_images()

	def handle_events(self):
		"""Function to handle user input."""

		for event in pygame.event.get():

			#quit game
			if event.type == QUIT:
				command_queue.put("Exit");
				#sys.exit()

			#If user has pressed a key
			if event.type == KEYDOWN:

				bomb = None
				missile = None

				#get mouse position
				pos = pygame.mouse.get_pos()

				if self.TYPE == "Bombs":

					#if player still has bombs to drop
					if (self.nbombs < self.maxbombs):

						#if 1-9 pressed, set off bomb by creating a new object and adding it to self.bombs
						if event.key == pygame.K_1:
							bomb = Bomb(pos[0], 0, self.bases[0].rect.centerx, self.size[1] - self.city_width, self.bomb_speed, 0)

						if event.key == pygame.K_2:
							bomb = Bomb(pos[0], 0, self.cities[0].rect.centerx, self.size[1] - self.city_width, self.bomb_speed, 1)

						if event.key == pygame.K_3:
							bomb = Bomb(pos[0], 0, self.cities[1].rect.centerx, self.size[1] - self.city_width, self.bomb_speed, 2)

						if event.key == pygame.K_4:
							bomb = Bomb(pos[0], 0, self.cities[2].rect.centerx, self.size[1] - self.city_width, self.bomb_speed, 3)

						if event.key == pygame.K_5:
							bomb = Bomb(pos[0], 0, self.bases[1].rect.centerx, self.size[1] - self.city_width, self.bomb_speed, 4)

						if event.key == pygame.K_6:
							bomb = Bomb(pos[0], 0, self.cities[3].rect.centerx, self.size[1] - self.city_width, self.bomb_speed, 5)

						if event.key == pygame.K_7:
							bomb = Bomb(pos[0], 0, self.cities[4].rect.centerx, self.size[1] - self.city_width, self.bomb_speed, 6)

						if event.key == pygame.K_8:
							bomb = Bomb(pos[0], 0, self.cities[5].rect.centerx, self.size[1] - self.city_width, self.bomb_speed, 7)

						if event.key == pygame.K_9:
							bomb = Bomb(pos[0], 0, self.bases[2].rect.centerx, self.size[1] - self.city_width, self.bomb_speed, 8)

						#if a bomb has been created, add it to the command_queue and to self.bombs
						if bomb != None:
							data = pickle.dumps(bomb)
							command_queue.put(data)
							bomb.gs = self
							self.bombs.append(bomb)
							self.nbombs = self.nbombs + 1

				if self.TYPE == "Missiles":

					#fire missiles from bases with a, s, d. First make sure that there are enough missiles left in the base
					if event.key == pygame.K_a:
						if (self.bases[0].count > 0):
							self.bases[0].count = self.bases[0].count - 1
							missile = Missile(self.bases[0].rect.centerx, self.size[1] - self.city_width, pos[0], pos[1], self.missile_speed, 0)
					
					if event.key == pygame.K_s:
						if (self.bases[1].count > 0):
							self.bases[1].count = self.bases[1].count - 1
							missile = Missile(self.bases[1].rect.centerx, self.size[1] - self.city_width, pos[0], pos[1], self.missile_speed, 1)

					if event.key == pygame.K_d:
						if (self.bases[2].count > 0):
							self.bases[2].count = self.bases[2].count - 1
							missile = Missile(self.bases[2].rect.centerx, self.size[1] - self.city_width, pos[0], pos[1], self.missile_speed, 2)

					#if a missile has been created, add it to the command_queue and to self.missiles
					if missile != None:
						data = pickle.dumps(missile)
						command_queue.put(data)
						missile.gs = self
						self.missiles.append(missile)

	def check_collisions(self):
		"""Check for collisions between each bomb and each explosion. If there is a collision, then the bomb should be destroyed."""

		#for each explosion caused by a missile
		for explosion in self.explosions:

			i = 0

			#iterate through each bomb in self.bombs
			while (i < len(self.bombs)):

				#calculate distance from bomb to explosion
				dx = explosion.pos[0] - self.bombs[i].pos[0]
				dy = explosion.pos[1] - self.bombs[i].pos[1]

				d = sqrt(dx*dx + dy*dy)

				#if bomb is within the explosion, increment self.ncollisions and delete the bomb
				if (explosion.r > d):
					self.ncollisions += 1
					del self.bombs[i]
				else:
					i = i+1


	def initialize_bases(self):
		"""Initialize three Bases, each with 9 missiles."""

		#initialize bases list
		self.bases = []

		#calculate what width/height of each city/base should be
		width = (self.size[0] - 200) / 9

		#initialize each base
		for i in range(0, 9):

			# if i is 0, 4, or 8
			if (i % 4 == 0):
				base = Base(20*(i+1) + i*width, self.size[1] - width,  width, width, 9, self)
				self.bases.append(base)

	def initialize_cities(self):
		"""Initialize 6 cities."""

		self.cities = []
		
		#calculate what width/height of each city/base should be
		width = (self.size[0] - 200) / 9

		#initialize each city
		for i in range(0, 9):

			# if i is not 0, 4, or 8, then create a city
			if (i % 4 != 0):
				city = City(20*(i+1) + i*width, self.size[1] - width,  width, width, self)
				self.cities.append(city)
	
		self.city_width = width

	def check_round_over(self):
		"""Returns 1 if the round is over and 0 if it is not."""

		#check cities -- if they are all dead, then the round is over
		ncities_dead = 0
		for city in self.cities:
			if city.da == 0:
				ncities_dead = ncities_dead + 1

		if ncities_dead == len(self.cities):
			return 1

		#if player 2 has dropped all of his bombs and all of them have exploded, then the round is over
		elif (self.nbombs >= self.maxbombs and len(self.bomb_explosions) == 0 and len(self.bombs) == 0):
			return 1

		else:
			return 0

	def check_turn_over(self):
		"""Returns 1 if the turn is over and 0 if it is not."""

		#check if all of cities are dead -- if so, then the turn is over
		ncities_dead = 0
		for city in self.cities:
			if city.da == 0:
				ncities_dead = ncities_dead + 1

		if ncities_dead == len(self.cities):
			return 1

	def calculate_points(self):
		"""At the end of each round, this function is called to calculate points for the player aiming missiles."""

		points = 0

		if self.TYPE == "Missiles":
			#points for each missile left
			for base in self.bases:
				points = points + base.count

			#points for each city left
			for city in self.cities:
				if city.da == 1:
					points = points + 50

			#points for each collision of a missile explosion with a bomb
			points += self.ncollisions * 5

			self.p1_points += points

		points = 0
		if self.TYPE == "Bombs":
			#points for each base left
			for base in self.bases:
				points = points + base.count

			#points for each city left
			for city in self.cities:
				if city.da == 1:
					points = points + 50

			#points for each collision of a missile explosino with a bomb
			points += self.ncollisions * 5
			self.p2_points += points
		

	def reset_turn(self):
		"""Use to initialize the game or to reset the game when a turn is up."""
		self.turn += 1

		#Change self.TYPE so that whoever was dropping bombs is now shooting missiles and vice versa.
		if self.TYPE == "Missiles":
			self.TYPE = "Bombs"
		elif self.TYPE == "Bombs":
			self.TYPE = "Missiles"

		self.initialize_cities()
		self.reset_round()

	def reset_round(self):
		"""Use to reset bases, missiles, bombs, and explosions for a new round."""

		self.initialize_bases()

		#active bombs missiles and explosions(empty at first)
		self.missiles = []
		self.bombs = []
		self.explosions = []
		self.bomb_explosions = []

		self.nbombs = 0 #keep track of how many bombs have been dropped
		self.roundover = 0
		self.ncollisions = 0 #number of collisions of bombs with missile explosions; use to calculate score

	def game_over(self):
		"""Displays whether the player has won or lost the game. Called once the game is over."""

		if self.p1_points > self.p2_points:
			winner = "YOU WIN"
		elif self.p2_points > self.p1_points:
			winner = "YOU LOSE"
		else:
			winner = "TIE"

		font = pygame.font.Font(None, 100)
		text = font.render(winner,1,(204,0,0))
		textpos = text.get_rect()
		textpos.centerx = self.size[0]/2
		textpos.centery = self.size[1]/2
		self.screen.blit(text,textpos)
		pygame.display.flip()

	def callback(self, data):
		"""Called when the client receives data from the server."""

		#unpickle data
		d = pickle.loads(data)
		d.gs = self

		#determine if object is Missile or Bomb and append to correct list
		if d.TYPE == "Missile":
			self.missiles.append(d)

			#since missile was launched, adjust the count of the base from which it was launched
			if self.bases[d.source].count > 0:
				self.bases[d.source].count -= 1 

		elif d.TYPE == "Bomb":
			self.bombs.append(d)
			self.nbombs = self.nbombs + 1

		data_queue.get().addCallback(self.callback)
