from __future__ import division

import sys
import sdl2
import sdl2.ext
import random
import math

WHITE = sdl2.ext.Color(255, 255, 255)
GREEN = sdl2.ext.Color(0, 255, 0)
RED = sdl2.ext.Color(255, 0, 0)
BLUE = sdl2.ext.Color(0, 0, 255)
PURPLE = sdl2.ext.Color(255, 0, 255)


maxX = 1024
maxY = 800
neighborDist = 150
minDist = 20
leaderWeight = 5
fov = math.pi / 2

class Agent:
    def __init__(self, posX, posY, speed, heading, color, width, height, spriteFactory, spriteRenderer, name = ''):
        self.posX = posX
        self.posY = posY
        self.speed = speed
        self.heading = heading
        self.velX = self.speed * math.cos(self.heading)
        self.velY = self.speed * math.sin(self.heading)
        self.color = color
        self.width = width
        self.height = height
        self.sprite = spriteFactory.from_color(self.color, size=(self.width, self.height))
        self.spriteRenderer = spriteRenderer
        self.sprite.position = int(self.posX), int(self.posY)
        self.name = name

    def turnLeft(self, mag):
        # Change heading and velocity direction accordingly
        self.heading -= mag * math.pi / 16.0
        self.velX = self.speed * math.cos(self.heading)
        self.velY = self.speed * math.sin(self.heading)

    def turnRight(self, mag):
        # Change heading and velocity direction accordingly
        self.heading += mag * math.pi / 16.0
        self.velX = self.speed * math.cos(self.heading)
        self.velY = self.speed * math.sin(self.heading)

    def updatePosition(self):
        self.posX += self.velX
        self.posY += self.velY
        # Clamp
        self.posX = min(maxX - 10, max(self.posX, 10))
        self.posY = min(maxY - 10, max(self.posY, 10))

        self.heading = self.heading % (math.pi*2) # Mod 2pi

        self.sprite.position = int(self.posX), int(self.posY)

    def draw(self):
        self.spriteRenderer.render(self.sprite)

    # Check if an agent is in this agent's FOV
    def canSee(self, agent):
        # First, find the vector to the agent
        vecX = agent.posX - self.posX
        vecY = agent.posY - self.posY

        # Get the corresponding heading
        agentHeading = math.atan2(vecY, vecX)
        agentHeading = agentHeading % (2.0 * math.pi)

        # Now, find the angle from our heading to that heading
        angle = (self.heading - agentHeading) % 2 * math.pi
        # If angle is within our FOV, then we can see the agent;
        # otherwise, we cannot
        if (angle < fov) or (2.0 * math.pi - angle < fov):
            return True
        else:
            return False


    def getNeighbors(self, agentList):
        # Return a list of neighbor agents, where neighbors are within neighborDist and
        # are within the agent's field of view
        neighbors = []
        for agent in agentList:
            dist = math.sqrt((self.posX - agent.posX)**2 + (self.posY - agent.posY)**2)
            # if dist < neighborDist and self.canSee(agent):
            if dist < neighborDist:
                neighbors.append(agent)
        return neighbors

    def amTooClose(self, agent):
        dist = math.sqrt((self.posX - agent.posX)**2 + (self.posY - agent.posY)**2)
        return (dist < minDist)

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
            # print "%s: steering left to match position" % self.name
            self.turnLeft(mag)

        elif determinantDiff > 0: # Otherwise if it's to the right, turn right
            # print "%s: steering right to match position" % self.name
            self.turnRight(mag)
        else: # Otherwise it's straight ahead, so do nothing
            pass


    def flockingLogic(self, agents):
        # Avoid walls
        if self.posY < minDist:
            # Steer away from top wall
            # print "%s steering away from top wall" % self.name
            self.turnInOppositeDirection(0.2, self.posX, 0)
        elif self.posY > maxY - minDist:
            # Steer away from bottom wall
            # print "%s steering away from bottom wall" % self.name
            self.turnInOppositeDirection(0.2, self.posX, maxY) 

        if self.posX < minDist:
            # Steer away from left wall
            # print "%s steering away from left wall" % self.name
            self.turnInOppositeDirection(0.2, 0, self.posY)
        elif self.posX > maxX - minDist:
            # Steer away from right wall
            # print "%s steering away from right wall" % self.name
            self.turnInOppositeDirection(0.2, maxX, self.posY)


        neighbors = self.getNeighbors(agents)
        if len(neighbors) == 0:
            # If there are no neighbors, we're done with flocking logic
            return

        # Avoid crowding neighbors
        for neighbor in neighbors:
            if self.amTooClose(neighbor):
                # print '%s is too close to %s!' % (self.name, neighbor.name)
                self.turnInOppositeDirection(0.4, neighbor.posX, neighbor.posY)

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
            self.turnLeft(0.1)
            # print "%s: steering left to match heading" % self.name
        elif angleLeft > angleRight:
            # print "%s: steering right to match heading" % self.name
            # print "avgHeading", avgHeading
            # print "self.heading", self.heading
            # print "angleLeft", angleLeft
            # print "angleRight", angleRight
            # print "========="
            self.turnRight(0.1)
        else:
            pass

        # Steer towards average position of neighbors
        avgPosX, avgPosY = getAveragePosition(neighbors)

        self.turnInSameDirection(0.1, avgPosX, avgPosY)


def getAveragePosition(agents):
    posXSum = 0
    posYSum = 0
    for agent in agents:
        if agent.name == 'leader':
            # print "is getting leader's position!"
            # print "(it's %s, %s)" % (agent.posX, agent.posY)
            posXSum += agent.posX * leaderWeight
            posYSum += agent.posY * leaderWeight
        else:
            posXSum += agent.posX
            posYSum += agent.posY

    avgPosX = posXSum / (len(agents) + leaderWeight - 1)
    avgPosY = posYSum / (len(agents) + leaderWeight - 1)

    # print "calculated average position of %s, %s" % (avgPosX, avgPosY)

    return avgPosX, avgPosY

def getAverageHeading(agents):

    xCompSum = 0
    yCompSum = 0
    for agent in agents:
        if agent.name == 'leader':
            # print "getting leader's heading!"
            # print "(it's %s)" % (agent.heading)
            xCompSum += math.cos(agent.heading) * leaderWeight
            yCompSum += math.sin(agent.heading) * leaderWeight
        else:
            xCompSum += math.cos(agent.heading)
            yCompSum += math.sin(agent.heading)

    avgXCompSum = xCompSum / (len(agents) + leaderWeight - 1)
    avgYCompSum = yCompSum / (len(agents) + leaderWeight - 1)

    avgHeading = math.atan2(avgYCompSum, avgXCompSum)

    avgHeading = avgHeading % (2.0 * math.pi)
    # print "calculated average heading of %s" % (avgHeading)

    return avgHeading

def main():
    RESOURCES = sdl2.ext.Resources(__file__, "resources")

    sdl2.ext.init()

    window = sdl2.ext.Window("Flocking Demo", size=(maxX, maxY))
    window.show()

    spriteFactory = sdl2.ext.SpriteFactory(sdl2.ext.SOFTWARE)
    spriteRenderer = spriteFactory.create_sprite_render_system(window)
    
    leader = Agent(500, 500, 0, 0, GREEN, 20, 20, spriteFactory, spriteRenderer, name='leader')

    numFollowers = 30
    followers = []
    for i in range(numFollowers):
        follower = Agent(random.randint(200,800), random.randint(200,800), 3, random.uniform(0,2*math.pi), RED, 10, 10, spriteFactory, spriteRenderer)
        followers.append(follower)

    # followerB = Agent(random.randint(200,800), random.randint(200,800), 2, random.uniform(0,2*math.pi), BLUE, 10, 10, spriteFactory, spriteRenderer, name='Blue')
    # followerW = Agent(random.randint(200,800), random.randint(200,800), 2, random.uniform(0,2*math.pi), WHITE, 10, 10, spriteFactory, spriteRenderer, name='White')
    # followerP = Agent(random.randint(200,800), random.randint(200,800), 2, random.uniform(0,2*math.pi), PURPLE, 10, 10, spriteFactory, spriteRenderer, name='Purple')

    # followers += [followerB, followerW, followerP]
    # followers += [followerB]

    drawList = []
    drawList += [follower.sprite for follower in followers]
    drawList.append(leader.sprite)

    allAgents = followers + [leader]

    running = True
    while running:
        events = sdl2.ext.get_events()
        for event in events:
            if event.type == sdl2.SDL_QUIT:
                running = False
                break
            if event.type == sdl2.SDL_KEYDOWN:
                if event.key.keysym.sym == sdl2.SDLK_LEFT:
                    leader.turnLeft(2)
                elif event.key.keysym.sym == sdl2.SDLK_RIGHT:
                    leader.turnRight(2)
            # elif event.type == sdl2.SDL_KEYUP:
            #     if event.key.keysym.sym in (sdl2.SDLK_UP, sdl2.SDLK_RIGHT):
            #         leader.velocity.vy = 0

        sdl2.SDL_Delay(10)

        for i, follower in enumerate(followers):
            otherAgents = allAgents[:i] + allAgents[i+1:]
            follower.flockingLogic(otherAgents)

        for follower in followers:
            follower.updatePosition()
            # followerW.turnLeft(0.1)
        leader.updatePosition()

        sdl2.ext.fill(spriteRenderer.surface, sdl2.ext.Color(0, 0, 0))
        spriteRenderer.render(drawList)

    sdl2.ext.quit()

if __name__ == '__main__':
    main()