from __future__ import division

import sys
import sdl2
import sdl2.ext
import random
import math

GREEN = sdl2.ext.Color(0, 255, 0)
PURPLE = sdl2.ext.Color(255, 0, 255)

maxX = 1024
maxY = 800
visionDistance = 150
minNeighborDistance = 20
minFalconDistance = 175
minWallDistance = 40
sepForce = 2.0
wallSepForce = 4
alignForce = 0.2
cohesiveForce = 0.2
numInteractionPartners = 7 # neighbors to actually consider
centerAttraction = 0.05
fov = 2.0 * math.pi

sparrowSpeed = 2.5
falconSpeed = 8
turnSpeed = math.pi / 16

numSparrows = 60

# Draws all of the agents, with their headings, onto the given surface
def drawAgents(agents, surface):
    pixelview = sdl2.ext.PixelView(surface)
    for agent in agents:
        normedVelX = agent.velX / agent.speed;
        normedVelY = agent.velY / agent.speed;
        drawLine(int(agent.posX), int(agent.posY), int(agent.posX + normedVelX * agent.width), int(agent.posY + normedVelY * agent.width), agent.color, pixelview)
    del pixelview


# Borrowed from https://gist.github.com/arti95/6264890
def drawLine(x0, y0, x1, y1, color, pixelview):
    #print "x0:{} y0:{} x1:{} y1:{}".format(x0, y0, x1, y1)
    """draw a line 
    
    http://en.wikipedia.org/wiki/Bresenham%27s_line_algorithm"""
    #sdl2ext.fill(winsurf, BLACK)
    #pixelview[event.motion.y][event.motion.x] = WHITE
    
    # dont draw put of screen
    # this check should be in "while true" loop but for some reason it 
    # didn't work there
    x0 = 0 if x0 < 0 else x0
    x0 = maxX -1 if x0 >= maxX else x0
    x1 = 0 if x1 < 0 else x1
    x1 = maxX -1 if x1 >= maxX else x1
    y0 = 0 if y0 < 0 else y0
    y0 = maxY -1 if y0 >= maxY else y0
    y1 = 0 if y1 < 0 else y1
    y1 = maxY -1 if y1 >= maxY else y1
    
    
    dx = abs(x1-x0)
    dy = abs(y1-y0) 
    sx = 1 if (x0 < x1) else -1
    sy = 1 if (y0 < y1) else -1
    err = dx-dy
 
    while True:
        pixelview[y0][x0] = color
        if x0 == x1 and y0 == y1: break
        e2 = 2*err
        if e2 > -dy:
           err = err - dy
           x0  = x0 + sx
        if x0 == x1 and y0 == y1: 
            pixelview[y0][x0] = color
            break
        if e2 < dx: 
            err = err + dx
            y0  =y0 + sy 

class Agent:
    def __init__(self, posX, posY, speed, heading, color, width, height, name = ''):
        self.posX = posX
        self.posY = posY
        self.speed = speed
        self.heading = heading
        self.velX = self.speed * math.cos(self.heading)
        self.velY = self.speed * math.sin(self.heading)
        self.color = color
        self.width = width
        self.height = height
        self.name = name
        self.invisible = False

    def turnLeft(self, mag):
        # Change heading and velocity direction accordingly
        self.heading -= mag * turnSpeed
        self.velX = self.speed * math.cos(self.heading)
        self.velY = self.speed * math.sin(self.heading)

    def turnRight(self, mag):
        # Change heading and velocity direction accordingly
        self.heading += mag * turnSpeed
        self.velX = self.speed * math.cos(self.heading)
        self.velY = self.speed * math.sin(self.heading)

    def updatePosition(self):
        self.posX += self.velX
        self.posY += self.velY
        # Clamp
        self.posX = min(maxX - 10, max(self.posX, 10))
        self.posY = min(maxY - 10, max(self.posY, 10))

        self.heading = self.heading % (math.pi*2) # Mod 2pi

    def getNeighbors(self, agentList):
        # Return a list of neighbor agents, where neighbors are within visionDistance
        # and are within field of view
        withinFovList = [agent for agent in agentList if self.canSee(agent)]
        visibleList = []

        for agent in withinFovList:
            if agent.name != 'falcon': # Exclude falcon; only consider fellow sparrows neighbors
                dist = math.sqrt((self.posX - agent.posX)**2 + (self.posY - agent.posY)**2)
                if dist < visionDistance:
                    visibleList.append([agent, dist])
                visibleList = sorted(visibleList, key=lambda neighbor: neighbor[1]) # Sort by distance

        # Only return top n closest neighbors, where n is a set number of interaction partners
        return [neighbor for neighbor, dist in visibleList][:numInteractionPartners]

    def amTooClose(self, agent):
        minimumDistance = minNeighborDistance
        dist = math.sqrt((self.posX - agent.posX)**2 + (self.posY - agent.posY)**2)
        return (dist < minimumDistance)

    # Check if another agent is in this agent's FOV
    def canSee(self, agent):
        # First, find the vector to the agent
        vecX = agent.posX - self.posX
        vecY = agent.posY - self.posY

        # Get the corresponding heading
        agentHeading = math.atan2(vecY, vecX)
        agentHeading = agentHeading % (2.0 * math.pi)

        # Now, find the angle from our heading to that heading
        angle = (agentHeading - self.heading) % 2 * math.pi
        # If angle is within our FOV, then we can see the agent;
        # otherwise, we cannot
        if (angle <= fov) or (2.0 * math.pi - angle <= fov):
            return True
        else:
            return False

    def avoidFalcon(self, otherAgents):
        for agent in otherAgents:
            if agent.name == 'falcon':
                dist = math.sqrt((self.posX - agent.posX)**2 + (self.posY - agent.posY)**2)          
                if dist < minFalconDistance:
                    self.turnInOppositeDirection(sepForce, agent.posX, agent.posY)

    def turnInOppositeDirection(self, mag, agentPosX, agentPosY):
        # Apply steering in opposite direction of agent
        # (Hacky math)
        Ax = self.posX
        Ay = self.posY
        Bx = self.posX + self.velX
        By = self.posY + self.velY
        determinantDiff = (Bx - Ax) * (agentPosY - Ay) - (By - Ay) * (agentPosX - Ax)
        
        if determinantDiff < 0: # If agent is on our left side, apply right turn
            self.turnRight(mag)

        else: # Otherwise it'll be either straight ahead or to the left, so turn left
            self.turnLeft(mag)

    def turnInSameDirection(self, mag, agentPosX, agentPosY):
        # Apply steering in same direction as agent
        # (Hacky math)
        Ax = self.posX
        Ay = self.posY
        Bx = self.posX + self.velX
        By = self.posY + self.velY
        determinantDiff = (Bx - Ax) * (agentPosY - Ay) - (By - Ay) * (agentPosX - Ax)

        if determinantDiff < 0: # If average is on our left side, apply left turn
            self.turnLeft(mag)

        elif determinantDiff > 0: # Otherwise if it's to the right, turn right
            self.turnRight(mag)
        else: # Otherwise it's straight ahead, so do nothing
            pass

    def avoidWalls(self):
        # Avoid walls
        if self.posY < minWallDistance:
            # Steer away from top wall
            self.turnInOppositeDirection(wallSepForce, self.posX, 0)
        elif self.posY > maxY - minWallDistance:
            # Steer away from bottom wall
            self.turnInOppositeDirection(wallSepForce, self.posX, maxY) 

        if self.posX < minWallDistance:
            # Steer away from left wall
            self.turnInOppositeDirection(wallSepForce, 0, self.posY)
        elif self.posX > maxX - minWallDistance:
            # Steer away from right wall
            self.turnInOppositeDirection(wallSepForce, maxX, self.posY)

    def maintainSeparation(self, neighbors):
        # Avoid crowding neighbors
        for neighbor in neighbors:
            if self.amTooClose(neighbor):
                self.turnInOppositeDirection(sepForce, neighbor.posX, neighbor.posY)

    def alignToAverageHeading(self, neighbors):
        # Steer towards average heading of neighbors
        avgHeading = getAverageHeading(neighbors)

        # Determine which is shorter: the angle it would take to turn left
        # and get to the average heading, or the angle it would take to do
        # the same thing turning right
        if avgHeading < self.heading:
            angleRight = avgHeading + math.pi * 2 - self.heading
        else:
            angleRight = avgHeading - self.heading

        if avgHeading > self.heading:
            angleLeft = self.heading + math.pi * 2 - avgHeading
        else:
            angleLeft = self.heading - avgHeading

        if angleLeft < angleRight:
            self.turnLeft(alignForce)
        elif angleLeft > angleRight:
            self.turnRight(alignForce)
        else:
            pass

    def cohereToAveragePosition(self, neighbors):
        # Steer towards average position of neighbors
        avgPosX, avgPosY = getAveragePosition(neighbors)
        self.turnInSameDirection(cohesiveForce, avgPosX, avgPosY)


    def flockingLogic(self, otherAgents):

        self.avoidWalls()

        self.avoidFalcon(otherAgents)

        neighbors = self.getNeighbors(otherAgents)
        if len(neighbors) == 0:
            # If there are no neighbors, we're done with flocking logic
            return

        self.maintainSeparation(neighbors)
        self.alignToAverageHeading(neighbors)
        self.cohereToAveragePosition(neighbors)

        # Minor center attraction for effect
        self.turnInSameDirection(centerAttraction, maxX / 2, maxY / 2)


def getAveragePosition(agents):
    posXSum = 0
    posYSum = 0
    for agent in agents:
        posXSum += agent.posX
        posYSum += agent.posY

    avgPosX = posXSum / len(agents)
    avgPosY = posYSum / len(agents)

    return avgPosX, avgPosY

def getAverageHeading(agents):
    xCompSum = 0
    yCompSum = 0
    for agent in agents:
        xCompSum += math.cos(agent.heading)
        yCompSum += math.sin(agent.heading)

    avgXCompSum = xCompSum / len(agents)
    avgYCompSum = yCompSum / len(agents)

    avgHeading = math.atan2(avgYCompSum, avgXCompSum)

    avgHeading = avgHeading % (2.0 * math.pi)

    return avgHeading

def main():
    RESOURCES = sdl2.ext.Resources(__file__, "resources")

    sdl2.ext.init()

    window = sdl2.ext.Window("Flocking Demo", size=(maxX, maxY))
    window.show()
    winsurf = window.get_surface()
    
    falcon = Agent(maxX - 100, maxY - 100, falconSpeed, math.pi / 4.0, GREEN, 30, 30, name='falcon')

    sparrows = []

    for i in range(numSparrows):
        sparrow = Agent(random.randint(200,maxX - 200), random.randint(200,maxY - 200), sparrowSpeed, random.uniform(0,2*math.pi), PURPLE, 10, 10)
        sparrows.append(sparrow)

    allAgents = sparrows + [falcon]

    running = True
    while running:
        events = sdl2.ext.get_events()
        for event in events:
            if event.type == sdl2.SDL_QUIT:
                running = False
                break
            if event.type == sdl2.SDL_KEYDOWN:
                if event.key.keysym.sym == sdl2.SDLK_LEFT:
                    falcon.turnLeft(2)
                elif event.key.keysym.sym == sdl2.SDLK_RIGHT:
                    falcon.turnRight(2)

        for i, sparrow in enumerate(sparrows):
            otherAgents = allAgents[:i] + allAgents[i+1:]
            sparrow.flockingLogic(otherAgents)

        for sparrow in sparrows:
            sparrow.updatePosition()
        falcon.updatePosition()

        sdl2.ext.fill(winsurf, sdl2.ext.Color(0, 0, 0))
        drawAgents(allAgents, winsurf)

        window.refresh()

    sdl2.ext.quit()

if __name__ == '__main__':
    main()