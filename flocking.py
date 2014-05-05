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
visionDistance = 150
minNeighborDistance = 20
minAntagonistDistance = 150
minWallDistance = 40
leaderWeight = 10
fov = math.pi / 2
sepForce = 2.0
wallSepForce = 4
alignForce = 0.5
cohesiveForce = 0.5
numInteractionPartners = 14 # neighbors to actually consider
centerAttraction = 0.5

# Draws all of the agents, with their headings, onto the given surface
def drawAgents(agents, surface):
    pixelview = sdl2.ext.PixelView(surface)
    for agent in agents:
        # print "Agent at %s, %s" % (agent.posX, agent.posY)
        # Draw triangle
        #pixelview[int(agent.posY)][int(agent.posX)] = WHITE
        normedVelX = agent.velX / agent.speed;
        normedVelY = agent.velY / agent.speed;
        line(int(agent.posX), int(agent.posY), int(agent.posX + normedVelX * agent.width), int(agent.posY + normedVelY * agent.width), agent.color, pixelview)
    del pixelview


# Borrowed from https://gist.github.com/arti95/6264890
def line(x0, y0, x1, y1, color, pixelview):
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
        # self.sprite = spriteFactory.from_color(self.color, size=(self.width, self.height))
        # self.spriteRenderer = spriteRenderer
        # self.sprite.position = int(self.posX - self.width/2), int(self.posY - self.height/2)
        self.name = name
        self.invisible = False

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

        # self.sprite.position = int(self.posX - self.width/2), int(self.posY - self.height/2)

    def draw(self):
        if not self.invisible:
            self.spriteRenderer.render(self.sprite)

    def becomeInvisible(self):
        print "becoming invisible!"
        self.invisible = True

    def isTouching(self, agent):
        dist = math.sqrt((self.posX - agent.posX)**2 + (self.posY - agent.posY)**2)
        # print dist
        if dist < self.width / 2 + agent.width / 2:
            return True
        else:
            return False

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
        # Return a list of neighbor agents, where neighbors are within visionDistance
        visibleList = []
        for agent in agentList:
            dist = math.sqrt((self.posX - agent.posX)**2 + (self.posY - agent.posY)**2)
            # if dist < neighborDist and self.canSee(agent):
            if dist < visionDistance:
                visibleList.append([agent, dist])
            visibleList = sorted(visibleList, key=lambda neighbor: neighbor[1]) # Sort by distance

        # Only return top n closest neighbors, where n is a set number of interaction partners
        return [neighbor for neighbor, dist in visibleList][:numInteractionPartners]

    def amTooClose(self, agent):
        if agent.name == 'antagonist':
            minimumDistance = minAntagonistDistance
        else:
            minimumDistance = minNeighborDistance
        dist = math.sqrt((self.posX - agent.posX)**2 + (self.posY - agent.posY)**2)
        return (dist < minimumDistance)

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
        if self.posY < minWallDistance:
            # Steer away from top wall
            # print "%s steering away from top wall" % self.name
            self.turnInOppositeDirection(wallSepForce, self.posX, 0)
        elif self.posY > maxY - minWallDistance:
            # Steer away from bottom wall
            # print "%s steering away from bottom wall" % self.name
            self.turnInOppositeDirection(wallSepForce, self.posX, maxY) 

        if self.posX < minWallDistance:
            # Steer away from left wall
            # print "%s steering away from left wall" % self.name
            self.turnInOppositeDirection(wallSepForce, 0, self.posY)
        elif self.posX > maxX - minWallDistance:
            # Steer away from right wall
            # print "%s steering away from right wall" % self.name
            self.turnInOppositeDirection(wallSepForce, maxX, self.posY)


        neighbors = self.getNeighbors(agents)
        if len(neighbors) == 0:
            # If there are no neighbors, we're done with flocking logic
            return

        # Isolate neighbors of same color for special flocking dynamics
        teamNeighbors = [neighbor for neighbor in neighbors if neighbor.color == self.color]

        # Avoid crowding neighbors
        for neighbor in neighbors:
            if self.amTooClose(neighbor):
                # print '%s is too close to %s!' % (self.name, neighbor.name)
                self.turnInOppositeDirection(sepForce, neighbor.posX, neighbor.posY)

        # Steer towards average heading of team neighbors
        avgHeading = getAverageHeading(teamNeighbors)

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
            # print "%s: steering left to match heading" % self.name
        elif angleLeft > angleRight:
            # print "%s: steering right to match heading" % self.name
            # print "avgHeading", avgHeading
            # print "self.heading", self.heading
            # print "angleLeft", angleLeft
            # print "angleRight", angleRight
            # print "========="
            self.turnRight(alignForce)
        else:
            pass

        # Steer towards average position of team neighbors
        avgPosX, avgPosY = getAveragePosition(teamNeighbors)

        self.turnInSameDirection(cohesiveForce, avgPosX, avgPosY)

        # Minor center attraction for effect
        self.turnInSameDirection(centerAttraction, maxX / 2, maxY / 2)

        # Occasionally, go a little off course (random disturbance)
        # if random.uniform(0, 100) < 1.0:
        #     self.heading = (self.heading + math.pi) % (2.0 * math.pi)



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
    winsurf = window.get_surface()

    # spriteFactory = sdl2.ext.SpriteFactory(sdl2.ext.SOFTWARE)
    # spriteRenderer = spriteFactory.create_sprite_render_system(window)
    
    antagonist = Agent(500, 500, 3, 0, GREEN, 30, 30, name='antagonist')

    numFollowers = 40
    followers = []

    for i in range(numFollowers):
        follower = Agent(random.randint(200,maxX - 200), random.randint(200,maxY - 200), 2.1, random.uniform(0,2*math.pi), PURPLE, 10, 10)
        followers.append(follower)

    # for i in range(numFollowers):
    #     follower = Agent(random.randint(200,maxX - 200), random.randint(200,maxY - 200), 2.1, random.uniform(0,2*math.pi), BLUE, 10, 10)
    #     followers.append(follower)

    # for i in range(numFollowers):
    #     follower = Agent(random.randint(200,maxX - 200), random.randint(200,maxY - 200), 2.1, random.uniform(0,2*math.pi), RED, 10, 10)
    #     followers.append(follower)

    # for i in range(numFollowers):
    #     follower = Agent(random.randint(200,maxX - 200), random.randint(200,maxY - 200), 2.1, random.uniform(0,2*math.pi), WHITE, 10, 10)
    #     followers.append(follower)

    # followerB = Agent(random.randint(200,800), random.randint(200,800), 2, random.uniform(0,2*math.pi), BLUE, 10, 10, spriteFactory, spriteRenderer, name='Blue')
    # followerW = Agent(random.randint(200,800), random.randint(200,800), 2, random.uniform(0,2*math.pi), WHITE, 10, 10, spriteFactory, spriteRenderer, name='White')
    # followerP = Agent(random.randint(200,800), random.randint(200,800), 2, random.uniform(0,2*math.pi), PURPLE, 10, 10, spriteFactory, spriteRenderer, name='Purple')

    # followers += [followerB, followerW, followerP]
    # followers += [followerB]

    # drawList = []
    # drawList += followers
    # drawList.append(antagonist)

    allAgents = followers + [antagonist]

    running = True
    while running:
        events = sdl2.ext.get_events()
        for event in events:
            if event.type == sdl2.SDL_QUIT:
                running = False
                break
            if event.type == sdl2.SDL_KEYDOWN:
                if event.key.keysym.sym == sdl2.SDLK_LEFT:
                    antagonist.turnLeft(2)
                elif event.key.keysym.sym == sdl2.SDLK_RIGHT:
                    antagonist.turnRight(2)
            # elif event.type == sdl2.SDL_KEYUP:
            #     if event.key.keysym.sym in (sdl2.SDLK_UP, sdl2.SDLK_RIGHT):
            #         leader.velocity.vy = 0

        sdl2.SDL_Delay(10)

        for i, follower in enumerate(followers):
            otherAgents = allAgents[:i] + allAgents[i+1:]
            follower.flockingLogic(otherAgents)

        for follower in followers:
            follower.updatePosition()
            # if follower.isTouching(antagonist) and not follower.invisible:
            #     follower.becomeInvisible()
                # drawList.remove(follower.sprite)
            # followerW.turnLeft(0.1)
        antagonist.updatePosition()

        sdl2.ext.fill(winsurf, sdl2.ext.Color(0, 0, 0))
        drawAgents(followers + [antagonist], winsurf)

        window.refresh()


        # spriteRenderer.render(drawList)


    sdl2.ext.quit()

if __name__ == '__main__':
    main()