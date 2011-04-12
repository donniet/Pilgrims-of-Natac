'''
Created on Apr 10, 2011

@author: donniet
'''

import logging
from google.appengine.ext import db
import datetime
from django.utils import simplejson as json

def pagedBoards(offset, count):
    return db.Query(Board).fetch(count, offset)

def findBoard(gamekey):
    logging.info("looking for board %s" % (gamekey,))
    return db.Query(Board).filter('gameKey =', gamekey).get()

class Board(db.Model):
    dateTimeStarted = db.DateTimeProperty()
    gameKey = db.StringProperty()
    resources = db.StringListProperty()
    playerColors = db.StringListProperty()
    owner = db.UserProperty()
    #TODO: add all deck of development cards
    def getVertexes(self):
        return db.Query(Vertex).ancestor(self).fetch(1000)
    def getEdges(self):
        return db.Query(Edge).ancestor(self).fetch(1000)
    def getHexes(self):
        return db.Query(Hex).ancestor(self).fetch(1000)
    
    def getVertex(self, x, y):
        return db.Query(Vertex).ancestor(self).filter('x =', x).filter('y =', y).get()
    def getEdge(self, x1, y1, x2, y2):
        return db.Query(Edge).ancestor(self).filter('x1 =', x1).filter('y1 =', y1).filter('x2 =', x2).filter('y2 =', y2).get()
    def getHex(self, x, y):
        return db.Query(Hex).ancestor(self).filter('x =', x).filter('y =', y).get()
    
    def addPlayer(self, color, user):
        p = Player(parent=self, color=color, user=user)
        p.put()
        logging.info("player added: %s" % (user,))
        return p
    
    def getPlayer(self, user):
        return db.Query(Player).ancestor(self).filter('user =', user).get()
    
    def getPlayers(self):
        return db.Query(Player).ancestor(self).fetch(1000)
    
    def dump(self, fp):
        json.dump(self, fp, cls=BoardEncoder)
        
        

class DevelopmentType(db.Model):
    name = db.StringProperty()
    location = db.StringProperty(choices=set(["hex","edge","vertex"]))
    playerStart = db.IntegerProperty()

class Player(db.Model):
    color = db.StringProperty()
    user = db.UserProperty()
    
    # send a dict of resources, integer mappings to add to players resources
    # negative integers subtract resources
    # if a resource isn't listed under a player it is assumed they have zero
    def adjustResources(self, resource_dict, validate_only=False):
        rd = resource_dict.copy()
        #HACK: shouldn't be more than 25 resource types, but still...
        playerResources = db.Query(PlayerResources).ancestor(self).fetch(25)
        #TODO: add transactions around this logic
        
        valid = True
        # first add to the resources we know about
        for pr in playerResources:
            if not rd.get(pr.resource, None) is None: 
                if pr.amount + rd[pr.resource] >= 0:
                    if not validate_only:
                        pr.amount += rd[pr.resource]
                        pr.put()
                        del rd[pr.resource]
                    else:
                        valid = False
                
        # then loop through remaining resources and add them as player resources
        for r, a in rd.items():
            if a >= 0:
                pr = PlayerResources(resource=r, amount=a)
                pr.put()
            else:
                valid = False
                
        return valid
    #TODO: Resource and Development Cards

class PlayerResources(db.Model):
    resource = db.StringProperty()
    amount = db.IntegerProperty()
    
class Hex(db.Model):
    x = db.IntegerProperty()
    y = db.IntegerProperty()
    type = db.StringProperty()
    value = db.IntegerProperty()
    
    def getDevelopments(self):
        return db.Query(Development).ancestor(self).fetch(1000)
    
    def addDevelopment(self, player, type):
        d = Development(parent=self, player=player, type=type)
        d.put()
        return d  

class Edge(db.Model):
    #ASSERT x1 < x2 or (x1 == x2 and y1 <= y2)
    x1 = db.IntegerProperty()
    y1 = db.IntegerProperty()
    x2 = db.IntegerProperty()
    y2 = db.IntegerProperty()
    
    def getDevelopments(self):
        return db.Query(Development).ancestor(self).fetch(1000)
    
    def addDevelopment(self, player, type):
        d = Development(parent=self, player=player, type=type)
        d.put()
        return d  
    
class Vertex(db.Model):
    x = db.IntegerProperty()
    y = db.IntegerProperty()
    
    def getDevelopments(self):
        return db.Query(Development).ancestor(self).fetch(1000)
    
    def addDevelopment(self, color, type):
        d = Development(parent=self, color=color, type=type)
        d.put()
        return d    

class Development(db.Model):
    color = db.StringProperty()
    type = db.StringProperty()

class BoardEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Board):
            return dict(
                dateTimeStarted = obj.dateTimeStarted,
                gameKey = obj.gameKey,
                players = db.Query(Player).ancestor(obj),
                hexes = db.Query(Hex).ancestor(obj),
                edges = db.Query(Edge).ancestor(obj),
                vertex = db.Query(Vertex).ancestor(obj)
            )
        elif isinstance(obj, Player):
            return dict(
                color = obj.color,
                user = dict(nickname=obj.user.nickname(), email=obj.user.email()),
                playerResources = db.Query(PlayerResources).ancestor(obj)
                #TODO: Serialize resources and development cards here
            )
        elif isinstance(obj, PlayerResources):
            return dict(
                resource = obj.resource,
                amount = obj.amount
            )
        elif isinstance(obj, Hex):
            return dict(
                x = obj.x,
                y = obj.y,
                type = obj.type,
                value = obj.value,
                developments = db.Query(Development).ancestor(obj)
            )
        elif isinstance(obj, Edge):
            return dict(
                x1 = obj.x1,
                y1 = obj.y1,
                x2 = obj.x2,
                y2 = obj.y2,
                developments = db.Query(Development).ancestor(obj)
            )
        elif isinstance(obj, Vertex):
            return dict(
                x = obj.x,
                y = obj.y,
                developments = db.Query(Development).ancestor(obj)
            )
        elif isinstance(obj, Development):
            return dict(
                color = obj.color, #TODO: what if obj.player is None?
                type = obj.type
            )
        elif isinstance(obj, db.Query):
            ret = []
            res = obj.fetch(1000)
            for o in res:
                ret.append(self.default(o))
            return ret
        elif isinstance(obj, datetime.datetime):
            return obj.isoformat()
        else:
            #raise TypeError("%r is not JSON serializable" % (obj,))
            return json.JSONEncoder.default(self, obj)

