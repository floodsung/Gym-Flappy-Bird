import gym
from gym import error, spaces, utils
from gym.utils import seeding
import numpy as np
import sys
import random
import pygame
import flappy_bird_utils
import pygame.surfarray as surfarray
from pygame.locals import *
from itertools import cycle

class FlappyBirdEnv(gym.Env):
    metadata = {'render.modes': ['human']}

    


    def __init__(self,is_demo=False):
        self.is_demo = is_demo
        self.fps = 30
        self.screenwidth  = 288
        self.screenheight = 512

        pygame.init()
        self.fpsclock = pygame.time.Clock()
        self.screen = pygame.display.set_mode((self.screenwidth, self.screenheight))
        pygame.display.set_caption('Flappy Bird')

        self.images, self.sounds, self.hitmasks = flappy_bird_utils.load()
        self.pipegapsize = 100 # gap between upper and lower part of pipe
        self.basey = self.screenheight * 0.79

        self.player_width = self.images['player'][0].get_width()
        self.player_height = self.images['player'][0].get_height()
        self.pipe_width = self.images['pipe'][0].get_width()
        self.pipe_height = self.images['pipe'][0].get_height()
        self.backgroud_width = self.images['background'].get_width()

        self.player_index_gen = cycle([0, 1, 2, 1])

        # actions and observation space
        self.action_space = spaces.Discrete(2)
        self.observation_space = spaces.Box(low=0, high=255, shape=(self.screenheight, self.screenwidth, 3), dtype=np.uint8)


    def step(self, input_actions):
        pygame.event.pump()

        reward = 0.1
        terminal = False

        

        # input_actions[0] == 1: do nothing
        # input_actions[1] == 1: flap the bird
        if input_actions == 1:
            if self.playery > -2 * self.player_height:
                self.playerVelY = self.playerFlapAcc
                self.playerFlapped = True
                #self.sounds['wing'].play()

        # check for score
        playerMidPos = self.playerx + self.player_width / 2
        for pipe in self.upperPipes:
            pipeMidPos = pipe['x'] + self.pipe_width / 2
            if pipeMidPos <= playerMidPos < pipeMidPos + 4:
                self.score += 1
                #self.sounds['point'].play()
                reward = 1

        # playerIndex basex change
        if (self.loopIter + 1) % 3 == 0:
            self.playerIndex = next(self.player_index_gen)
        self.loopIter = (self.loopIter + 1) % 30
        self.basex = -((-self.basex + 100) % self.baseShift)

        # player's movement
        if self.playerVelY < self.playerMaxVelY and not self.playerFlapped:
            self.playerVelY += self.playerAccY
        if self.playerFlapped:
            self.playerFlapped = False
        self.playery += min(self.playerVelY, self.basey - self.playery - self.player_height)
        if self.playery < 0:
            self.playery = 0

        # move pipes to left
        for uPipe, lPipe in zip(self.upperPipes, self.lowerPipes):
            uPipe['x'] += self.pipeVelX
            lPipe['x'] += self.pipeVelX

        # add new pipe when first pipe is about to touch left of screen
        if 0 < self.upperPipes[0]['x'] < 5:
            newPipe = self._getRandomPipe()
            self.upperPipes.append(newPipe[0])
            self.lowerPipes.append(newPipe[1])

        # remove first pipe if its out of the screen
        if self.upperPipes[0]['x'] < -self.pipe_width:
            self.upperPipes.pop(0)
            self.lowerPipes.pop(0)

        # check if crash here
        isCrash= self._checkCrash({'x': self.playerx, 'y': self.playery,
                                 'index': self.playerIndex},
                                self.upperPipes, self.lowerPipes)
        if isCrash:
            #self.sounds['hit'].play()
            #self.sounds['die'].play()
            terminal = True
            self.__init__()
            reward = -1

        # draw sprites
        
        self.screen.blit(self.images['background'], (0,0))

        for uPipe, lPipe in zip(self.upperPipes, self.lowerPipes):
            self.screen.blit(self.images['pipe'][0], (uPipe['x'], uPipe['y']))
            self.screen.blit(self.images['pipe'][1], (lPipe['x'], lPipe['y']))

        self.screen.blit(self.images['base'], (self.basex, self.basey))
        # print score so player overlaps the score
        # showScore(self.score)
        self.screen.blit(self.images['player'][self.playerIndex],
                    (self.playerx, self.playery))

        image_data = pygame.surfarray.array3d(pygame.display.get_surface())
        
        #print self.upperPipes[0]['y'] + self.pipe_height - int(self.basey * 0.2)
        return image_data, reward, terminal,{}


    def reset(self):
        self.score = self.playerIndex = self.loopIter = 0
        self.playerx = int(self.screenwidth * 0.2)
        self.playery = int((self.screenheight - self.player_height) / 2)
        self.basex = 0
        self.baseShift = self.images['base'].get_width() - self.backgroud_width

        newPipe1 = self._getRandomPipe()
        newPipe2 = self._getRandomPipe()
        self.upperPipes = [
            {'x': self.screenwidth, 'y': newPipe1[0]['y']},
            {'x': self.screenwidth + (self.screenwidth / 2), 'y': newPipe2[0]['y']},
        ]
        self.lowerPipes = [
            {'x': self.screenwidth, 'y': newPipe1[1]['y']},
            {'x': self.screenwidth + (self.screenwidth / 2), 'y': newPipe2[1]['y']},
        ]

        # player velocity, max velocity, downward accleration, accleration on flap
        self.pipeVelX = -4
        self.playerVelY    =  0    # player's velocity along Y, default same as playerFlapped
        self.playerMaxVelY =  10   # max vel along Y, max descend speed
        self.playerMinVelY =  -8   # min vel along Y, max ascend speed
        self.playerAccY    =   1   # players downward accleration
        self.playerFlapAcc =  -7   # players speed on flapping
        self.playerFlapped = False # True when player flaps


        image_data,_,_,_ = self.step(0)

        return image_data


    def render(self, mode='human', close=False):
        pygame.display.update()
        if self.is_demo:
            self.fpsclock.tick(self.fps)

    def _getRandomPipe(self):
        """returns a randomly generated pipe"""
        # y of gap between upper and lower pipe
        gapYs = [20, 30, 40, 50, 60, 70, 80, 90]
        index = random.randint(0, len(gapYs)-1)
        gapY = gapYs[index]

        gapY += int(self.basey * 0.2)
        pipeX = self.screenwidth + 10

        return [
            {'x': pipeX, 'y': gapY - self.pipe_height},  # upper pipe
            {'x': pipeX, 'y': gapY + self.pipegapsize},  # lower pipe
        ]


    def _showScore(self,score):
        """displays score in center of screen"""
        scoreDigits = [int(x) for x in list(str(score))]
        totalWidth = 0 # total width of all numbers to be printed

        for digit in scoreDigits:
            totalWidth += self.images['numbers'][digit].get_width()

        Xoffset = (self.screenwidth - totalWidth) / 2

        for digit in scoreDigits:
            self.screen.blit(self.images['numbers'][digit], (Xoffset, self.screenheight * 0.1))
            Xoffset += self.images['numbers'][digit].get_width()


    def _checkCrash(self,player, upperPipes, lowerPipes):
        """returns True if player collders with base or pipes."""
        pi = player['index']
        player['w'] = self.images['player'][0].get_width()
        player['h'] = self.images['player'][0].get_height()

        # if player crashes into ground
        if player['y'] + player['h'] >= self.basey - 1:
            return True
        else:

            playerRect = pygame.Rect(player['x'], player['y'],
                          player['w'], player['h'])

            for uPipe, lPipe in zip(upperPipes, lowerPipes):
                # upper and lower pipe rects
                uPipeRect = pygame.Rect(uPipe['x'], uPipe['y'], self.pipe_width, self.pipe_height)
                lPipeRect = pygame.Rect(lPipe['x'], lPipe['y'], self.pipe_width, self.pipe_height)

                # player and upper/lower pipe hitmasks
                pHitMask = self.hitmasks['player'][pi]
                uHitmask = self.hitmasks['pipe'][0]
                lHitmask = self.hitmasks['pipe'][1]

                # if bird collided with upipe or lpipe
                uCollide = self._pixelCollision(playerRect, uPipeRect, pHitMask, uHitmask)
                lCollide = self._pixelCollision(playerRect, lPipeRect, pHitMask, lHitmask)

                if uCollide or lCollide:
                    return True

        return False

    def _pixelCollision(self,rect1, rect2, hitmask1, hitmask2):
        """Checks if two objects collide and not just their rects"""
        rect = rect1.clip(rect2)

        if rect.width == 0 or rect.height == 0:
            return False

        x1, y1 = rect.x - rect1.x, rect.y - rect1.y
        x2, y2 = rect.x - rect2.x, rect.y - rect2.y

        for x in range(rect.width):
            for y in range(rect.height):
                if hitmask1[x1+x][y1+y] and hitmask2[x2+x][y2+y]:
                    return True
        return False
