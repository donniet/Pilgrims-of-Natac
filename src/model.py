'''
Created on Apr 10, 2011

@author: donniet
'''

import logging
from google.appengine.ext import db
import datetime
from django.utils import simplejson as json
from google.appengine.api import users
import urllib
import hashlib
import util


def pagedBoards(offset, count):
    return db.Query(Board).fetch(count, offset)

def findBoard(gamekey):
    logging.info("looking for board %s" % (gamekey,))
    return db.Query(Board).filter('gameKey =', gamekey).get()

def queryBoards(offset, limit, filters, sorting):
    q = db.Query(Board)
    
    if filters is None: 
        filters = []
    
    if sorting is None:
        sorting = []
    
    for f in filters:
        field = ''
        value = None
        op = '='
        if(len(f) == 2):
            field = f[0]
            value = f[1]
        elif(len(f) == 3):
            field = f[0]
            op = f[1]
            value = f[2]
        else:
            # raise exception
            return []
        
        props = Board.properties()
        
        # handle users as a special case
        if field == 'user' and op == '=':
            pq = db.Query(Player, keys_only=True).filter('user = ', value)
            keys = [x.parent() for x in pq]
            q.filter('__key__ IN ', keys)
            break;
        elif field=='user':
            # raise exception, no operations other than = are supported on users
            return []
        elif field=='gameKey' and op != '=':
            # raise exception
            return []
        
        if not props.get(field, None) is None:
            #TODO: more error checking here
            q.filter('%s %s' % (field, op), value)
    
    #TODO: error check the sort fields
    for s in sorting:
        q.order(s)
        
            
    return q.fetch(limit, offset)

GamePhases = util.enum('GamePhases', 'join', 'buildFirst', 'buildSecond', 'main')
TurnPhases = util.enum('TurnPhases', 'buildInitialSettlement', 'buildInitialRoad', 'playKnightCard', 'mainTurn')

class Board(db.Model):
    dateTimeCreated = db.DateTimeProperty()
    dateTimeStarted = db.DateTimeProperty()
    dateTimeEnded = db.DateTimeProperty()
    gameKey = db.StringProperty()
    resources = db.StringListProperty()
    playerColors = db.StringListProperty()
    owner = db.UserProperty()
    gamePhase = db.IntegerProperty()
    currentPlayer = db.IntegerProperty()
    turnPhase = db.IntegerProperty()
    playOrder = db.ListProperty(int)
    winner = db.UserProperty()
    
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
    score = db.IntegerProperty(default=0)
    
    # send a dict of resources, integer mappings to add to players resources
    # negative integers subtract resources
    # if a resource isn't listed under a player it is assumed they have zero
    def resetResources(self):
        resource_dict = dict()
        for r in self.parent().resources:
            resource_dict[r] = 0
        
        #TODO: add exception handling
        db.run_in_transaction(self.__setResourcesTran, resource_dict)
    
    def __setResourcesTran(self, resource_dict):
        rd = resource_dict.copy()
        #HACK: shouldn't be more than 25 resource types, but still...
        playerResources = db.Query(PlayerResources).ancestor(self).fetch(25)
        #TODO: add transactions around this logic
        
        # first add to the resources we know about
        for pr in playerResources:
            if not rd.get(pr.resource, None) is None: 
                pr.amount = rd[pr.resource]
                pr.put()
                del rd[pr.resource]
                
        # then loop through remaining resources and add them as player resources
        for r, a in rd.items():
            pr = PlayerResources(parent=self, resource=r, amount=a)
            pr.put()
                
        return True        
        
    
    def adjustResources(self, resource_dict, validate_only=False):
        ret = db.run_in_transaction(self.__adjustResourcesTrans, resource_dict, validate_only)
        
        return (ret is None) or ret
    
    def __adjustResourcesTrans(self, resource_dict, validate_only):
        rd = resource_dict.copy()
        #HACK: shouldn't be more than 25 resource types, but still...
        playerResources = db.Query(PlayerResources).ancestor(self).fetch(25)
        #TODO: add transactions around this logic
        
        # first add to the resources we know about
        for pr in playerResources:
            if not rd.get(pr.resource, None) is None: 
                if pr.amount + rd[pr.resource] < 0:
                    raise db.Rollback()
                elif not validate_only:
                    pr.amount += rd[pr.resource]
                    pr.put()
                    del rd[pr.resource]
                
        # then loop through remaining resources and add them as player resources
        for r, a in rd.items():
            if a < 0:
                raise db.Rollback()
            elif not validate_only:
                pr = PlayerResources(parent=self, resource=r, amount=a)
                pr.put()
                
        return True
    #TODO: Development Cards

def userPicture(email):
    ret = "http://www.gravatar.com/avatar/" + hashlib.md5(email.lower()).hexdigest() + "?"
    ret += urllib.urlencode({'d':'identicon', 's':'128'})
    return ret

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
    
    def addDevelopment(self, color, type):
        d = Development(parent=self, color=color, type=type)
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
    
    def addDevelopment(self, color, type):
        d = Development(parent=self, color=color, type=type)
        d.put()
        return d
    
    def getAdjecentEdges(self):
        edges  = db.GqlQuery("SELECT * FROM Edge WHERE x1 = :x AND y1 = :y AND __key__ != :key AND ANCESTOR IS :parent", x=self.x1, y=self.y1, parent=self.parent(), key=self.key()).fetch(25)
        edges2 = db.GqlQuery("SELECT * FROM Edge WHERE x2 = :x AND y2 = :y AND __key__ != :key AND ANCESTOR IS :parent", x=self.x1, y=self.y1, parent=self.parent(), key=self.key()).fetch(25)
        edges3 = db.GqlQuery("SELECT * FROM Edge WHERE x1 = :x AND y1 = :y AND __key__ != :key AND ANCESTOR IS :parent", x=self.x2, y=self.y2, parent=self.parent(), key=self.key()).fetch(25)
        edges4 = db.GqlQuery("SELECT * FROM Edge WHERE x2 = :x AND y2 = :y AND __key__ != :key AND ANCESTOR IS :parent", x=self.x2, y=self.y2, parent=self.parent(), key=self.key()).fetch(25)
        edges.extend(edges2)
        edges.extend(edges3)
        edges.extend(edges4)
        
        return edges
    
class Vertex(db.Model):
    x = db.IntegerProperty()
    y = db.IntegerProperty()
    
    def getDevelopments(self):
        return db.Query(Development).ancestor(self).fetch(1000)
    
    def addDevelopment(self, color, type):
        d = Development(parent=self, color=color, type=type)
        d.put()
        return d
    
    def getAdjecentEdges(self):
        edges   = db.Query(Edge).ancestor(self.parent()).filter('x1 = ', self.x).filter('y1 = ', self.y).fetch(25)
        edges_r = db.Query(Edge).ancestor(self.parent()).filter('x2 = ', self.x).filter('y2 = ', self.y).fetch(25)
        
        edges.extend(edges_r)
        logging.info("adjecent edges to (%d,%d): %d", self.x, self.y, len(edges))
        
        return edges
    
    def getAdjecentVertexes(self):
        edges = self.getAdjecentEdges()
        xs = []
        ys = []
        for e in edges:
            if e.x1 != self.x or e.y1 != self.y:
                xs.append(e.x1)
                ys.append(e.y1)
            if e.x2 != self.x or e.y2 != self.y:
                xs.append(e.x2)
                ys.append(e.y2)
        
        # for a hexagonal board the following query actually returns exactly 
        # the adjecent verts-- but we should filter through these to make sure...
        #TODO: filter through adjecent verts to handle non-hexagonal boards
        adj = db.GqlQuery("SELECT * FROM Vertex WHERE x IN :xlist AND y IN :ylist AND ANCESTOR IS :parent", xlist=xs, ylist=ys, parent=self.parent()).fetch(100)
               
        
        return adj

class Development(db.Model):
    color = db.StringProperty()
    type = db.StringProperty()

class CurrentPlayerEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Player):
            playerResources = db.Query(PlayerResources).ancestor(obj).fetch(1000)
            
            return dict(
                color = obj.color,
                user = dict(nickname=obj.user.nickname(), email=obj.user.email()),
                playerResources = playerResources,
                totalResources = len(playerResources),
                userpicture = userPicture(obj.user.email()),
                score = obj.score
            )
        elif isinstance(obj, PlayerResources):
            return dict(
                resource = obj.resource,
                amount = obj.amount
            )
        else:
            return json.JSONEncoder.default(self, obj)

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
            playerResources = db.Query(PlayerResources).ancestor(obj).fetch(1000)
            
            return dict(
                color = obj.color,
                user = dict(nickname=obj.user.nickname(), email=obj.user.email()),
                # don't return all the resources with the board
                #playerResources = db.Query(PlayerResources).ancestor(obj),
                totalResources = len(playerResources),
                userpicture = userPicture(obj.user.email()),
                score = obj.score
                #TODO: Serialize resources and development cards here
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

