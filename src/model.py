'''
Created on Apr 10, 2011

@author: donniet
'''

from google.appengine.ext import db
import datetime
from django.utils import simplejson as json


class Board(db.Model):
    dateTimeStarted = db.DateTimeProperty()
    gameKey = db.StringProperty()
    resources = db.StringListProperty()
    #TODO: add all deck of development cards
    def getVertexes(self):
        return db.Query(Vertex).ancestor(self).fetch(1000)
    def getEdges(self):
        return db.Query(Edge).ancestor(self).fetch(1000)
    def getHexes(self):
        return db.Query(Hex).ancestor(self).fetch(1000)
    
    def getVertex(self, x, y):
        return db.Query(Vertex).ancestor(self).filter('x=', x).filter('y=', y).get()
    def getEdge(self, x1, y1, x2, y2):
        return db.Query(Edge).ancestor(self).filter('x1=', x1).filter('y1=', y1).filter('x2=', x2).filter('y2=', y2).get()
    def getHex(self, x, y):
        return db.Query(Hex).ancestor(self).filter('x=', x).filter('y=', y).get()
        
        

class DevelopmentType(db.Model):
    name = db.StringProperty()
    location = db.StringProperty(choices=set(["hex","edge","vertex"]))
    playerStart = db.IntegerProperty()

class Player(db.Model):
    color = db.StringProperty()
    user = db.UserProperty()
    #TODO: Resource and Development Cards
    
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
    
    def addDevelopment(self, player, type):
        d = Development(parent=self, player=player, type=type)
        d.put()
        return d    

class Development(db.Model):
    player = db.ReferenceProperty(Player)
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
                user = dict(nickname=obj.user.nickname(), email=obj.user.email())
                #TODO: Serialize resources and development cards here
            )
        elif isinstance(obj, Hex):
            return dict(
                x = obj.x,
                y = obj.y,
                type = obj.type,
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
                player = obj.player.color, #TODO: what if obj.player is None?
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

