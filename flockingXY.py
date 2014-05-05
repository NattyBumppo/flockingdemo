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
minDist = 40
leaderWeight = 10
fov = math.pi / 2
sepForce = 0.1
wallSepForce = 5
alignForce = 0.9
cohesiveForce = 0.9
numInteractionPartners = 7 # neighbors to actually consider
leaderAcc = 0.2
maxSpeed = 4

class Agent:
    def __init__(self, posX, posY, velX, velY, color, width, height, spriteFactory, spriteRenderer, name = ''):
        self.posX = posX
        self.posY = posY
        self.velX = velX
        self.velY = velY
        self.color = color
        self.width = width
        self.height = height
        self.sprite = spriteFactory.from_color(self.color, size=(self.width, self.height))
        self.spriteRenderer = spriteRenderer
        self.sprite.position = int(self.posX), int(self.posY)
        self.name = name

    def updatePosition(self):
        self.posX += self.velX
        self.posY += self.velY
        # Clamp
        self.posX = min(maxX - 10, max(self.posX, 10))
        self.posY = min(maxY - 10, max(self.posY, 10))

        self.velX = min(maxSpeed, max(self.velX, -maxSpeed))
        self.velY = min(maxSpeed, max(self.velY, -maxSpeed))

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

        myHeading = math.atan2(velY / velX)
        myHeading = myHeading % (2.0 * math.pi)

        # Now, find the angle from our heading to that heading
        angle = (myHeading - agentHeading) % 2 * math.pi

        # If angle is within our FOV, then we can see the agent;
        # otherwise, we cannot
        if (angle < fov) or (2.0 * math.pi - angle < fov):
            return True
        else:
            return False


    def getNeighbors(self, agentList):
        # Return a list of neighbor agents, where neighbors are within neighborDist and
        # are within the agent's field of view
        neighborDistList = []
        for agent in agentList:
            dist = math.sqrt((self.posX - agent.posX)**2 + (self.posY - agent.posY)**2)
            # if dist < neighborDist and self.canSee(agent):
            if dist < neighborDist:
                neighborDistList.append([agent, dist])
            neighborDistList = sorted(neighborDistList, key=lambda neighbor: neighbor[1]) # Sort by distance

        # Only return top n closest neighbors, where n is a set number of interaction partners
        return [neighbor for neighbor, dist in neighborDistList][:numInteractionPartners]


    def amTooClose(self, agent):
        dist = math.sqrt((self.posX - agent.posX)**2 + (self.posY - agent.posY)**2)
        return (dist < minDist)


    def flockingLogic(self, agents):
        # Avoid walls
        if self.posY < minDist:
            # Steer away from top wall
            print "%s steering away from top wall" % self.name
            self.velY += wallSepForce
        elif self.posY > maxY - minDist:
            # Steer away from bottom wall
            print "%s steering away from bottom wall" % self.name
            self.velY -= wallSepForce

        if self.posX < minDist:
            # Steer away from left wall
            print "%s steering away from left wall" % self.name
            self.velX += wallSepForce
        elif self.posX > maxX - minDist:
            # Steer away from right wall
            print "%s steering away from right wall" % self.name
            self.velX -= wallSepForce

        neighbors = self.getNeighbors(agents)

        if len(neighbors) == 0:
            # If there are no neighbors, we're done with flocking logic
            return

        # Avoid crowding neighbors
        for neighbor in neighbors:
            if self.amTooClose(neighbor):
                # print '%s is too close to %s!' % (self.name, neighbor.name)

                # Get unit vector components for the direction from the neighbor to the current agent
                oppositeDirX = (neighbor.posX - self.posX)
                oppositeDirY = (neighbor.posY - self.posY)
                if oppositeDirX != 0:
                    normedOppositeDirX = oppositeDirX / math.sqrt(oppositeDirX**2 + oppositeDirY**2)
                else:
                    normedOppositeDirX = 0
                if oppositeDirY != 0:
                    normedOppositeDirY = oppositeDirY / math.sqrt(oppositeDirX**2 + oppositeDirY**2)
                else:
                    normedOppositeDirY = 0

                self.velX += sepForce * normedOppositeDirX
                self.velY += sepForce * normedOppositeDirY

        # Match velocity of neighbors
        avgVelX, avgVelY = getAverageVelocity(neighbors)

        # Approach average velocity
        if self.velX > avgVelX:
            self.velX -= alignForce * avgVelX
        else:
            self.velX += alignForce * avgVelX

        if self.velY > avgVelY:
            self.velY -= alignForce * avgVelY
        else:
            self.velY += alignForce * avgVelY

        # Move towards average position of neighbors
        avgPosX, avgPosY = getAveragePosition(neighbors)

        if self.posX > avgPosX:
            self.velX -= cohesiveForce * avgVelX
        else:
            self.velX += cohesiveForce * avgVelX

        if self.posY > avgPosY:
            self.velY -= cohesiveForce * avgVelY
        else:
            self.velY += cohesiveForce * avgVelY      


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

def getAverageVelocity(agents):

    velXSum = 0
    velYSum = 0
    for agent in agents:
        if agent.name == 'leader':
            # print "is getting leader's velition!"
            # print "(it's %s, %s)" % (agent.posX, agent.posY)
            velXSum += agent.velX * leaderWeight
            velYSum += agent.velY * leaderWeight
        else:
            velXSum += agent.velX
            velYSum += agent.velY

    avgVelX = velXSum / (len(agents) + leaderWeight - 1)
    avgVelY = velYSum / (len(agents) + leaderWeight - 1)

    # print "calculated average position of %s, %s" % (avgPosX, avgPosY)

    return avgVelX, avgVelY

def main():
    RESOURCES = sdl2.ext.Resources(__file__, "resources")

    sdl2.ext.init()

    window = sdl2.ext.Window("Flocking Demo", size=(maxX, maxY))
    window.show()

    spriteFactory = sdl2.ext.SpriteFactory(sdl2.ext.SOFTWARE)
    spriteRenderer = spriteFactory.create_sprite_render_system(window)
    
    leader = Agent(500, 500, 2, 0, GREEN, 20, 20, spriteFactory, spriteRenderer, name='leader')

    numFollowers = 30
    followers = []
    # for i in range(numFollowers):
    #     follower = Agent(random.randint(200,800), random.randint(200,800), random.uniform(0,2), random.uniform(0,2), RED, 10, 10, spriteFactory, spriteRenderer)
    #     followers.append(follower)

    followerB = Agent(random.randint(200,800), random.randint(200,800), 2, random.uniform(0,2*math.pi), BLUE, 10, 10, spriteFactory, spriteRenderer, name='Blue')
    followerW = Agent(random.randint(200,800), random.randint(200,800), 2, random.uniform(0,2*math.pi), WHITE, 10, 10, spriteFactory, spriteRenderer, name='White')
    followerP = Agent(random.randint(200,800), random.randint(200,800), 2, random.uniform(0,2*math.pi), PURPLE, 10, 10, spriteFactory, spriteRenderer, name='Purple')

    followers += [followerB, followerW, followerP]
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
                    leader.velX -= leaderAcc
                elif event.key.keysym.sym == sdl2.SDLK_RIGHT:
                    leader.velX += leaderAcc
                elif event.key.keysym.sym == sdl2.SDLK_UP:
                    leader.velY -= leaderAcc
                elif event.key.keysym.sym == sdl2.SDLK_DOWN:
                    leader.velY += leaderAcc
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