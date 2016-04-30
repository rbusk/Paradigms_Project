import pygame
from pygame.locals import *
from math import atan2, sin, cos

class Missile(pygame.sprite.Sprite):

	def __init__(self, sx, sy, fx, fy, v, t, gs=None):

		pygame.sprite.Sprite.__init__(self)

		self.gs = gs
		self.pos = sx, sy
		self.start = sx, sy
		self.fy = fy
		self.da = 1

		#calculate dx and dy
		angle = atan2(sy - fy, sx - fx)
		self.dx = -1 * v * cos(angle)
		self.dy = -1 * v * sin(angle)

		self.t = t

	def tick(self):

		#update x and y positions
		x = self.pos[0] + self.dx
		y = self.pos[1] + self.dy

		self.pos = x, y

		#if missile has reached its destination, it should 
		if (self.pos[1] >= self.fy and self.t == "bomb"):
			self.da = 0

		elif (self.pos[1] <= self.fy and self.t == "missile"):
			self.da = 0

	def draw(self):
		pygame.draw.line(self.gs.screen, (0, 255, 0), self.start, self.pos)
