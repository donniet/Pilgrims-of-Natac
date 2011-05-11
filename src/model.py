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
    
    logging.info("filter count %d" % (len(filters),))
    
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
        elif field=='user':
            #TODO raise exception, no operations other than = are supported on users
            return []
        #elif field=='gameKey' and op != '=':
            # raise exception
        #    return []
        
        elif not props.get(field, None) is None:
            #TODO: more error checking here
            logging.info("misc field %s %s %s" % (field, op, value))
            q.filter('%s %s' % (field, op), value)
        else:
            logging.info("field not found '%s'" % (field,))
    
    #TODO: error check the sort fields
    for s in sorting:
        q.order(s)
        
    logging.info("limit: %s, offset: %s" %(limit, offset))
    resultCount = q.count(1000);
    return (resultCount, q.fetch(limit, offset));

GamePhases = util.enum('GamePhases', 'join', 'buildFirst', 'buildSecond', 'main')
TurnPhases = util.enum('TurnPhases', 'buildInitialSettlement', 'buildInitialRoad', 'playKnightCard', 'mainTurn')


class TurnPhase(db.Model):
    phase = db.StringProperty()
    order = db.IntegerProperty()

class GamePhase(db.Model):
    phase = db.StringProperty()
    order = db.IntegerProperty()
    
    def getTurnPhases(self):
        return db.Query(TurnPhase).ancestor(self).order("order").fetch(100)
    
    def getTurnPhaseByName(self, phase):
        return db.Query(TurnPhase).ancestor(self).filter("phase =", phase).get()


class Board(db.Model):
    dateTimeCreated = db.DateTimeProperty()
    dateTimeStarted = db.DateTimeProperty()
    dateTimeEnded = db.DateTimeProperty()
    gameKey = db.StringProperty()
    resources = db.StringListProperty()
    hexProduces = db.StringListProperty() # must be same dimension as resources
    playerColors = db.StringListProperty()
    dice = db.ListProperty(int)
    diceValues = db.ListProperty(int)
    owner = db.UserProperty()
    gamePhase = db.IntegerProperty()
    currentPlayerRef = db.IntegerProperty()
    turnPhase = db.IntegerProperty()
    playOrder = db.ListProperty(int)
    winner = db.UserProperty()
    minimumPlayers = db.IntegerProperty()
    pointsNeededToWin = db.IntegerProperty()
    resourceMap = None
    
    def save(self, callback):
        rpc = db.create_rpc(deadline=5, callback=callback)
        self.put(rpc)
    
    def getGamePhases(self):
        return db.Query(GamePhase).ancestor(self).order("order").fetch(100)
    
    def getGamePhase(self, order):
        return db.Query(GamePhase).ancestor(self).filter("order =", order).get()
    
    def getGamePhaseByName(self, phase):
        return db.Query(GamePhase).ancestor(self).filter("phase =", phase).get()
    
    def getCurrentGamePhase(self):
        if self.gamePhase is None:
            return None
        else:
            return self.getGamePhase(self.gamePhase)

    def setWinner(self, user):
        self.winner = user
        self.dateTimeEnded = datetime.datetime.now()
        
        #INFO: the greatest game phase must be the complete phase
        gp = self.getGamePhases()
        if len(gp) > 0:
            complete = gp[len(gp)-1]
            self.gamePhase = complete.order
        
        self.put()
    
    def getResourceByHexType(self, hexType):
        if self.resourceMap is None:
            self.resourceMap = dict()
            for i in range(len(self.hexProduces)):
                #TODO: error check this
                self.resourceMap[self.hexProduces[i]] = self.resources[i]
        return self.resourceMap.get(hexType, None)
        
    def getCurrentTurnPhase(self):
        if self.turnPhase is None:
            return None
        
        gp = self.getCurrentGamePhase()
        if gp is None:
            return None
        
        return db.Query(TurnPhase).ancestor(gp).filter("order =", self.turnPhase).get()
        
    def getCurrentPlayerColor(self):
        p = self.getCurrentPlayer()
        if p is None: 
            return None
        
        return p.color
    
    def moveNextPlayer(self):
        players = self.getPlayers()
        self.currentPlayerRef += 1
        if self.currentPlayerRef >= len(players):
            self.currentPlayerRef = self.currentPlayerRef % len(players)
        self.put()
    
    def movePrevPlayer(self):
        players = self.getPlayers()
        self.currentPlayerRef -= 1
        if self.currentPlayerRef < 0:
            self.currentPlayerRef = self.currentPlayerRef % len(players)
        self.put()
    
    def getCurrentPlayer(self):
        if self.currentPlayerRef is None:
            return None
        else:
            return db.Query(Player).ancestor(self).filter("order =", self.currentPlayerRef).get()
        
    #TODO: add all deck of development cards
    def getVertexes(self):
        return db.Query(Vertex).ancestor(self).fetch(1000)
    def getEdges(self):
        return db.Query(Edge).ancestor(self).fetch(1000)
    def getHexes(self):
        return db.Query(Hex).ancestor(self).fetch(1000)
    
    def getHexesByValue(self, value):
        return db.Query(Hex).ancestor(self).filter("value =", value).fetch(1000)
    
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
    
    def addReservation(self, reservationKey, reservedFor, expirationDateTime):
        r = Reservation(parent=self, reservationKey=reservationKey, reservedFor=reservedFor, expirationDateTime=expirationDateTime)
        r.put()
        logging.info("reserved for: %s" %(reservedFor,))
        return r
    
    def getPlayer(self, user):
        return db.Query(Player).ancestor(self).filter('user =', user).get()
    
    def getReservations(self):
        return db.Query(Reservation).ancestor(self).filter("expirationDateTime <", datetime.datetime.now()).fetch(100)
    
    def getReservationCount(self):
        return db.Query(Reservation).ancestor(self).filter("expirationDateTime <", datetime.datetime.now()).count(100)
    
    def getReservation(self, reservationKey):
        return db.Query(Reservation).ancestor(self).filter("reservationKey =", reservationKey).get()
    
    def getReservationByUser(self, user):
        return db.Query(Reservation).ancestor(self).filter("reservedFor = ", user).get()
    
    def getPlayers(self):
        return db.Query(Player).ancestor(self).order("order").fetch(1000)
    
    def getPlayerColorMap(self):
        ret = dict()
        players = self.getPlayers()
        for p in players:
            ret[p.color] = p
        return ret
    
    def getDevelopmentTypeCost(self, name):
        ret = dict()
        dt = db.Query(DevelopmentType).ancestor(self).filter("name =", name).get()
        if dt is None:
            return ret
        
        return dt.getCost()
    
    def getDevelopmentTypeMap(self):
        ret = dict()
        dts = db.Query(DevelopmentType).ancestor(self).fetch(1000)
        for dt in dts:
            ret[dt.name] = dt
        
        return ret 
    
    def getDevelopmentTypeMapByLocation(self, location):
        ret = dict()
        devTypes = db.Query(DevelopmentType).ancestor(self).filter("location =", location).fetch(100)
        for dt in devTypes:
            ret[dt.name] = dt
            cost = db.Query(DevelopmentTypeCost).ancestor(dt).fetch(100)
            ret["cost"] = dict()
            for c in cost:
                ret["cost"][c.resource] = c.amount
        
        return ret

    def getAllDevelopments(self):
        return db.Query(Development).ancestor(self).order("color").order("type").fetch(1000)

    def getDevelopmentsByColorAndType(self, color, type):
        return db.Query(Development).ancestor(self).filter("color =", color).filter("type =", type).fetch(100)
        
    
    
    def dump(self, fp):
        json.dump(self, fp, cls=BoardEncoder) 

class Reservation(db.Model):
    reservationKey = db.StringProperty()
    reservedFor = db.UserProperty()
    expirationDateTime = db.DateTimeProperty()  

class DevelopmentType(db.Model):
    name = db.StringProperty()
    location = db.StringProperty(choices=set(["hex","edge","vertex"]))
    playerStart = db.IntegerProperty()
    points = db.IntegerProperty()
    
    def getCost(self):
        ret = dict()
        
        cost = db.Query(DevelopmentTypeCost).ancestor(self).fetch(100)
        for c in cost:
            ret[c.resource] = c.amount
        
        return ret

class DevelopmentTypeCost(db.Model):
    resource = db.StringProperty()
    amount = db.IntegerProperty()

class Player(db.Model):
    color = db.StringProperty()
    user = db.UserProperty()
    score = db.IntegerProperty(default=0)
    order = db.IntegerProperty()
    
    def getActive(self):
        board = self.parent()
        return board is not None and self.order == board.currentPlayerRef
    
    def setScore(self, score):
        self.score = score
        self.put()
    
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
        
        if ret is None:
            return False
        else:
            return ret
    
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
                logging.info("adjusting %s = %d:" % (r, a))
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

def get_hex_coords(x,y):
    return [(x+1,y),(x+3,y),(x+4,y+1),(x+3,y+2),(x+1,y+2),(x,y+1)]

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
    
    def getAdjecentVertexes(self):
        ret = []
        hexCoords = get_hex_coords(self.x, self.y)
        for p in hexCoords:
            v = db.Query(Vertex).ancestor(self.parent()).filter("x =", p[0]).filter("y =",p[1]).get()
            if v: ret.append(v)
        return ret
            

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
    
    # this can work almost exactly liike Hex::getAdjecentVertexes
    def getAdjecentHexes(self):
        ret = []
        hexCoords = get_hex_coords(self.x-4, self.y-2)
        for p in hexCoords:
            logging.info("looking for hex: %d, %d" % (p[0], p[1]))
            h = db.Query(Hex).ancestor(self.parent()).filter("x =", p[0]).filter("y =",p[1]).get()
            if h: ret.append(h)
        return ret
        

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

class GameListEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Board):            
            return dict(
                dateTimeCreated = obj.dateTimeCreated,
                dateTimeStarted = obj.dateTimeStarted,
                dateTimeEnded = obj.dateTimeEnded,
                gameKey = obj.gameKey,
                players = db.Query(Player).ancestor(obj),
                owner = obj.owner,
                currentPlayer = obj.getCurrentPlayer(),
                currentPlayerColor = obj.getCurrentPlayerColor(),
                gamePhase = obj.getCurrentGamePhase(),
                turnPhase = obj.getCurrentTurnPhase(), #TODO: add turnphase enum
                winner = obj.winner

                #playOrder = db.ListProperty(int)
            )
        elif isinstance(obj, GamePhase):
            return obj.phase
        elif isinstance(obj, TurnPhase):
            return obj.phase
        elif isinstance(obj, Player):
            return dict(
                color = obj.color,
                user = dict(nickname=obj.user.nickname(), email=obj.user.email()),
                # don't return all the resources with the board
                #playerResources = db.Query(PlayerResources).ancestor(obj),
                userpicture = userPicture(obj.user.email()),
                score = obj.score,
                active = obj.getActive()
                #TODO: Serialize resources and development cards here
            )
        elif isinstance(obj, db.Query):
            ret = []
            res = obj.fetch(1000)
            for o in res:
                ret.append(self.default(o))
            return ret
        elif isinstance(obj, users.User):
            return dict(nickname=obj.nickname(), email=obj.email())
        elif isinstance(obj, datetime.datetime):
            return obj.isoformat()
        else:
            #raise TypeError("%r is not JSON serializable" % (obj,))
            return json.JSONEncoder.default(self, obj)


class MessageEncoder(json.JSONEncoder):
     def default(self, obj):
        if isinstance(obj, Player):
            playerResources = db.Query(PlayerResources).ancestor(obj).fetch(1000)
            
            return dict(
                color = obj.color,
                user = dict(nickname=obj.user.nickname(), email=obj.user.email()),
                # don't return all the resources with the board
                #playerResources = db.Query(PlayerResources).ancestor(obj),
                totalResources = len(playerResources),
                userpicture = userPicture(obj.user.email()),
                score = obj.score,
                order = obj.order,
                active = obj.getActive()
                #TODO: Serialize resources and development cards here
            )
        else:
            #raise TypeError("%r is not JSON serializable" % (obj,))
            return json.JSONEncoder.default(self, obj)

class BoardEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Board):
            return dict(
                dateTimeCreated = obj.dateTimeCreated,
                dateTimeStarted = obj.dateTimeStarted,
                gameKey = obj.gameKey,
                players = db.Query(Player).ancestor(obj),
                hexes = db.Query(Hex).ancestor(obj),
                edges = db.Query(Edge).ancestor(obj),
                vertex = db.Query(Vertex).ancestor(obj),
                resources = obj.resources,
                owner = obj.owner,
                gamePhase = obj.getCurrentGamePhase(),
                turnPhase = obj.getCurrentTurnPhase(),
                winner = obj.winner,
                currentPlayer = obj.getCurrentPlayer(),
                currentPlayerColor = obj.getCurrentPlayerColor(),
                diceValues = obj.diceValues,
                dice = obj.dice,
                developmentTypes=db.Query(DevelopmentType).ancestor(obj),
            )
        elif isinstance(obj, DevelopmentType):
            return dict(
                name = obj.name,
                location = obj.location,
                playerStart = obj.playerStart,
                cost = obj.getCost()
            )
        elif isinstance(obj, GamePhase):
            return obj.phase
        elif isinstance(obj, TurnPhase):
            return obj.phase
        elif isinstance(obj, Player):
            playerResources = db.Query(PlayerResources).ancestor(obj).fetch(1000)
            
            return dict(
                color = obj.color,
                user = dict(nickname=obj.user.nickname(), email=obj.user.email()),
                # don't return all the resources with the board
                #playerResources = db.Query(PlayerResources).ancestor(obj),
                totalResources = len(playerResources),
                userpicture = userPicture(obj.user.email()),
                score = obj.score,
                order = obj.order,
                active = obj.getActive()
                #TODO: Serialize resources and development cards here
            )
        
        elif isinstance(obj, users.User):
            return dict(nickname=obj.nickname(), email=obj.email())
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

