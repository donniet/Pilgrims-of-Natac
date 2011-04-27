import random
import uuid
import logging
from django.utils import simplejson as json
import model
import datetime
from google.appengine.api import channel
import string
from google.appengine.ext import db
from google.appengine.api import memcache

from events import EventHook

   
       
class BoardTemplate(object):
    
    boardTemplate = dict(
        hexes = [
            dict(x=0, y=2),
            dict(x=3, y=1),
            dict(x=6, y=0),
            dict(x=9, y=1),
            dict(x=12, y=2),
            dict(x=12, y=4),
            dict(x=12, y=6),
            dict(x=9, y=7),
            dict(x=6, y=8), 
            dict(x=3, y=7),
            dict(x=0, y=6),
            dict(x=0, y=4),
            
            dict(x=3, y=3),
            dict(x=6, y=2),
            dict(x=9, y=3),
            dict(x=9, y=5),
            dict(x=6, y=6),
            dict(x=3, y=5),
            
            dict(x=6, y=4),
        ]
    )
    hexValues = [5, 2, 6, 3, 8, 10, 9, 12, 11, 4, 8, 10, 9, 4, 5, 6, 3, 11]
    hexTypes = ["mountains", "mountains", "mountains", 
                "hills", "hills", "hills", 
                "pasture", "pasture", "pasture", "pasture", 
                "fields", "fields", "fields", "fields",
                "forest", "forest", "forest", "forest",
                "desert"]
    resources = ["ore", "brick", "wool", "wheat", "wood"]
    colors = ["red", "blue", "green", "orange", "white", "brown"]
    minimumPlayers = 2
    
    gamePhases = [
        ("joining", []), 
        ("buildFirstSettlement", ["buildSettlement", "buildRoad"]), 
        ("buildSecondSettlement", ["buildSettlement", "buildRoad"]), 
        ("main", ["rollDice", "moveRobber", "trade",  "playCard", "build"]), 
        ("complete", [])
    ]
    
    def __init__(self):
        
        random.shuffle(self.hexTypes)
        
    def instantiateModel(self, gameKey, owner):
        board = model.Board()
        board.gameKey = gameKey
        board.dateTimeCreated = datetime.datetime.now()
        board.resources = self.resources
        board.playerColors = self.colors
        board.owner = owner
        board.gamePhase = 0
        board.minimumPlayers = self.minimumPlayers;
        
        board.put()
        
        for i in range(len(self.gamePhases)):
            gp_desc = self.gamePhases[i][0]
            gp = model.GamePhase(parent=board, phase=gp_desc, order=i)
            gp.put()
            for j in range(len(self.gamePhases[i][1])):
                tp_desc = self.gamePhases[i][1][j]
                tp = model.TurnPhase(parent=gp, phase=tp_desc, order=j)
                tp.put()
                        
        j = 0
        for i in range(len(self.boardTemplate["hexes"])):
            h = self.boardTemplate["hexes"][i]
            hex = model.Hex(parent=board, x=h["x"], y=h["y"], type=self.hexTypes[i])
            
            if self.hexTypes[i]=="desert":
                hex.value = 0
            else:
                hex.value = self.hexValues[j]
                j += 1
            
            hex.put()
            
        self.__createVertexAndEdgesFromHexesModel(board)
        return board
        
    def __createVertexAndEdgesFromHexesModel(self, board):
        edges = []
        vertex = []
        hexes = board.getHexes()
        
        found = dict()
        
        for h in hexes:
            hc = [
                dict(x=h.x+1, y=h.y+0),
                dict(x=h.x+3, y=h.y+0),
                dict(x=h.x+4, y=h.y+1),
                dict(x=h.x+3, y=h.y+2),
                dict(x=h.x+1, y=h.y+2),
                dict(x=h.x+0, y=h.y+1),
            ]
            # push the first edge
            edges.append(dict(hex=h, x1=hc[0]["x"], y1=hc[0]["y"], x2=hc[5]["x"], y2=hc[5]["y"]))
            
            for i in range(len(hc)):
                if(i > 0):
                    edges.append(dict(hex=h, x1=hc[i]["x"], y1=hc[i]["y"], x2=hc[i-1]["x"], y2=hc[i-1]["y"]))
                vertex.append(dict(hex=h, x=hc[i]["x"], y=hc[i]["y"]))
            
        for v in vertex:
            if found.get("%(x)d-%(y)d" % v, None) == None:
                vert = model.Vertex(parent=board, x=v["x"], y=v["y"])
                vert.put()
                found["%(x)d-%(y)d" % v] = True
        
        
        
        # TODO: edges
        #Ensure that y1 < y2 if x1 = x2 else x1 < x2
        for e in edges:
            if e["x1"] > e["x2"] or (e["x1"] == e["x2"] and e["y1"] > e["y2"]):
                x1 = e["x1"]
                y1 = e["y1"]
                e["x1"] = e["x2"]
                e["y1"] = e["y2"]
                e["x2"] = x1
                e["y2"] = y1
            
        found = dict()
            
        for e in edges:
            if found.get("%(x1)d-%(y1)d-%(x2)d-%(y2)d" % e, None) == None:
                edge = model.Edge(parent=board, x1=e["x1"], y1=e["y1"], x2=e["x2"], y2=e["y2"])
                edge.put()
                found["%(x1)d-%(y1)d-%(x2)d-%(y2)d" % e] = True
    
    
def create_game(user, template = BoardTemplate):
    #TODO: check for the unlikely case of this board key being a duplicate
    # generate board key
    
    gameKey = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(8))
    bt = template()
    
    logging.info("creating game %s" % (gameKey,))
    
    bt.instantiateModel(gameKey, user)
    
    return gameKey
    
def get_game(gamekey):
    logging.info("finding game %s" % (gamekey,))
    
    b = model.findBoard(gamekey)
    
    if b is None:
        logging.info("did not find it...")
    
    s = GameState(gamekey)
    if not s.isvalid():
        logging.info("is not valid %s" % (gamekey,))
        return None
    else:
        return s
    

class GameState(object):
    board = None
    #colors = ["red", "blue", "green", "orange", "white", "brown"]
    log = []
    gamekey = None
    users = []
    valid = False
    stateKey = None
    
    #events
    onPlaceSettlement = EventHook()
    onPlaceCity = EventHook()
    onReset = EventHook()
    onRegisterUser = EventHook()
    
    def __init__(self, gamekey):
        self.gamekey = gamekey
        self.board = model.findBoard(self.gamekey)
        self.valid = (not self.board is None)
        
    def updateStateKey(self):
        self.stateKey = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(16))
        
    def getStateKey(self):
        return self.stateKey
    
    def isvalid(self):
        return self.valid
    
    def addUser(self, user):        
        for u in self.users:
            if u.user_id() == user.user_id():
                return
        
        self.users.append(user)
    def registerUser(self, user):
        self.addUser(user)
        return channel.create_channel(self.gamekey + user.user_id())
    def get_user_color(self, user):
        player = self.board.getPlayer(user)
        
        if player is None:
            return None
        else:
            return player.color
        
    def get_player_by_user(self, user):
        player = self.board.getPlayer(user)
        
        return player
    
    def reserve(self, reservedFor, expirationMinutes):
        reservationKey = None
        
        # first check if the user is already playing
        p = self.board.getPlayer(reservedFor)
        if p is not None:
            return None
        
        # first check to see if we already have a reservation for this user
        r = self.board.getReservationByUser(reservedFor)
        if r is None:                
            reservationKey = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(8))
            self.board.addReservation(reservationKey, reservedFor, datetime.datetime.now() + datetime.timedelta(minutes=expirationMinutes))
        else:
            reservationKey = r.reservationKey
        
        return reservationKey
    
    def cancelReservation(self, reservationKey):
        r = self.board.getReservation(reservationKey)
        if r is None:
            return False
    
        r.delete()
        return True
    
    def joinByReservation(self, user, reservationKey):
        r = self.board.getReservation(reservationKey)
        
        if r is None:
            logging.info("No Reservation Found %s" % reservationKey)
            return None
        
        r.delete()
        return self.joinUser(user, True)
    
    
    def joinUser(self, user, byReservation=False):
        if self.board.dateTimeStarted is not None:
            #cannot join after the game has started
            return False
        
        #all joined users must be registered
        self.registerUser(user)
        
        p = self.board.getPlayer(user)
        
        if p:
            return p.color
                
        cols = set(self.board.playerColors)
        players = self.board.getPlayers()
        reservationCount = self.board.getReservationCount()
        
        # remove any reservations pending for this user
        r = self.board.getReservationByUser(user)
        if r is not None:
            r.delete()
            # since this guy was one of the spots reserved, don't check against other reservations
            reservationCount = 0
        
        if byReservation:
            reservationCount = 0
        
        if len(players) + reservationCount >= len(cols):
            return None
        
        for p in players:
            if p.user == user:
                #HACK: this is ugly
                return p.color
            else:
                cols.remove(p.color)
        
        color = cols.pop()
            
        self.board.addPlayer(color, user)
        self.updateStateKey()
        
        return color
    def sendMessageAll(self, message):
        c = self.board.getCurrentPlayerColor()
                
        gp = self.board.getCurrentGamePhase()
        tp = self.board.getCurrentTurnPhase()
        
        for user in self.users:
            p = self.board.getPlayer(user)
            
            mu = message.copy()
            mu["availableActions"] = self.getUserActionsInner(user, p, c, None if gp is None else gp.phase, None if tp is None else tp.phase)

            channel.send_message(self.gamekey + user.user_id(), json.dumps(mu))
            
    def sendMessageUser(self, user, message):
        c = self.board.getCurrentPlayerColor()
                
        gp = self.board.getCurrentGamePhase()
        tp = self.board.getCurrentTurnPhase()
        p = self.board.getPlayer(user)
        
        mu = message.copy()
        mu["availableActions"] = self.getUserActionsInner(user, p, c, None if gp is None else gp.phase, None if tp is None else tp.phase)
        mu["stateKey"] = self.getStateKey()
        
        channel.send_message(self.gamekey + user.user_id(), json.dumps(mu))
        
            
    def processAction(self, action, data, user):
        # before processing any action, check if we are processing one now:
        p = memcache.get("%s-processing-action" % self.board.gameKey)
        if not p is None and p:
            return False #processing
        
        memcache.set("%s-processing-action" % self.board.gameKey, True, 60)
        ret = False
        
        if action == "reset":
            ret = self.resetBoardAction()
        elif action == "placeSettlement":
            ret = self.placeSettlement(data["x"], data["y"], user)
        elif action == "placeCity":
            ret = self.placeCity(data["x"], data["y"], user)
        elif action == "placeRoad":
            ret = self.placeRoad(user, data["x1"], data["y1"], data["x2"], data["y2"])
        elif action == "startGame":
            ret = self.startGame(user)
        
        if ret:
            dataitems = []
            if data is not None and data.items() is not None:
                dataitems = data.items()
        
            self.updateStateKey()
            color = self.board.getPlayer(user).color
            self.sendMessageAll({"action":action, "color":color,"data":data})        
        
        memcache.delete("%s-processing-action" % self.board.gameKey)
        
        return ret
    
    def getUserActionsInner(self, user, player, currentColor, gamePhase, turnPhase):
        actions = ["quit"]
        logging.info("useractions params: %s, %s, %s, %s, %s" % (gamePhase, turnPhase, user.email(), currentColor, None if player is None else player.color))
        if gamePhase == "joining" and user == self.board.owner:
            actions.append("startGame")
        elif gamePhase == "buildFirstSettlement" and player is not None and player.color == currentColor:
            if turnPhase == "buildSettlement":
                actions.append("placeSettlement")
            elif turnPhase == "buildRoad":
                actions.append("placeRoad")
        elif gamePhase == "buildSecondSettlement" and player is not None and player.color == currentColor:
            if turnPhase == "buildSettlement":
                actions.append("placeSettlement")
            elif turnPhase == "buildRoad":
                actions.append("placeRoad")
        elif gamePhase == "main" and player is not None and player.color == currentColor:
            if turnPhase == "rollDice":
                actions.append("rollDice")
            elif turnPhase == "moveRobber":
                actions.append("placeRobber")
            elif turnPhase == "trade" or turnPhase == "playCard" or turnPhase == "build":
                actions.extend(["startTrade", "playCard", "placeSettlement", "placeCity", "placeRoad"])
        elif gamePhase == "complete":
            pass
        return actions
    
    def getUserActions(self, user):
        
        p = self.board.getPlayer(user)
        c = self.board.getCurrentPlayerColor()
                
        gp = self.board.getCurrentGamePhase()
        tp = self.board.getCurrentTurnPhase()
        
        return self.getUserActionsInner(user, p, c, gp, tp)    
    
    def startGame(self, user):
        if user != self.board.owner:
            logging.info("startGame: Not Owner")
            return False
        gp = self.board.getCurrentGamePhase()
        if gp is None or gp.phase != "joining":
            logging.info("startGame: Not joining Phase")
            return False
        
        np = len(self.board.getPlayers())
        if np < self.board.minimumPlayers:
            logging.info("startGame: Not Enough Players")
            return False
        
        bfs = self.board.getGamePhaseByName("buildFirstSettlement")
        if bfs is None:
            logging.info("startGame: no buildFirstSettlement gamephase")
            return False
        
        po = range(np)
        random.shuffle(po)
        
        logging.info("bfs.order: %d" % bfs.order)
        
        self.board.dateTimeStarted = datetime.datetime.now()
        self.board.gamePhase = bfs.order
        if len(bfs.getTurnPhases()) > 0:
            self.board.turnPhase = 0
        else:
            self.board.turnPhase = None
            
        self.board.playOrder = po
        self.board.currentPlayerRef = 0 #current player is 
        self.board.put()
        
        self.sendMessageAll({"action":"chat", "data":"Game Started"})
        
        return True
    
    def get_game_key(self):
        return self.gamekey

    def get_board(self):
        return self.board
    def get_players(self):
        return self.board.getPlayers()
    def placeRoad(self, user, x1, y1, x2, y2):
        p = self.board.getPlayer(user)
        if p is None:
            logging.info("player not found %s." % (user,))
            return False
        
        color = p.color
        
        e = self.board.getEdge(x1, y1, x2, y2)
        if e is None:
            logging.info("edge %d,%d,%d,%d not found", (x1, y1, x2, y2))
            return False
        
        devs = e.getDevelopments()
        if devs and len(devs) > 0:
            logging.info("found edge development")
            return False
        
        adjecentVertDev = False
        adjecentEdgeDev = False
        
        adj_edges = e.getAdjecentEdges()
        for a in adj_edges:
            devs = a.getDevelopments()
            for d in devs:
                if d.color == color:
                    adjecentEdgeDev = True
                    break;
            if adjecentEdgeDev:
                break;
        
        adj_verts = [
            self.board.getVertex(e.x1, e.y1),
            self.board.getVertex(e.x2, e.y2)
        ]
        for a in adj_verts:
            devs = a.getDevelopments()
            for d in devs:
                if d.color == color:
                    adjecentVertDev = True
                    break;
            if adjecentVertDev:
                break;
        
        if not adjecentVertDev and not adjecentEdgeDev:
            logging.info("no adjecent placements")
            return False
        
        np = len(self.board.getPlayers())
        gp = self.board.getCurrentGamePhase()
        tp = self.board.getCurrentTurnPhase()
        if gp is None or tp is None:
            return False
        
        #update the game/turn phase
        if gp.phase == "buildFirstSettlement":
            if tp.phase != "buildRoad":
                logging.info("not in the correct phase (currentPhase: %s)" % tp.phase)
                return False
            
            if self.board.currentPlayerRef < np - 1:
                self.board.currentPlayerRef += 1
                self.board.turnPhase = 0
            else:
                self.board.gamePhase += 1
                self.board.turnPhase = 0
                
            self.board.put()
        elif gp.phase == "buildSecondSettlement":
            if tp.phase != "buildRoad":
                logging.info("not in the correct phase (currentPhase: %s)" % tp.phase)
                return False
            
            logging.info("currentPlayerRef: %d" % self.board.currentPlayerRef)
            
            if self.board.currentPlayerRef > 0:
                self.board.currentPlayerRef -= 1
                self.board.turnPhase = 0
            else:
                self.board.gamePhase += 1
                self.board.turnPhase = 0
                self.board.currentPlayerRef += 1
                
            self.board.put()
        elif gp.phase == "main":
            if tp.phase != "build":
                logging.info("not in the correct phase (currentPhase: %s)" % tp.phase)
                return False
            else:   
                #TODO: does the player have enough resources to buy a road?
                #TODO: does the player have any roads left?    
                pass
        else:
            logging.info("not in the correct phase (currentPhase: %s)" % gp.phase)
            return False
        
        e.addDevelopment(color, "road")
        return True
    
    def createSendMessageAllCallback(self, message):
        def x():
            self.sendMessageAll(message)
        return x
    
    def placeSettlement(self, x, y, user):
        #logging.info("placeSettlement: " + data)

        
        p = self.board.getPlayer(user)
        if p is None: 
            logging.info("player not found %s." % (user,))
            return False
           
        color = p.color
        
        v = self.board.getVertex(x, y)
        if v is None: 
            logging.info("vertex %d,%d not found." % (x,y) )
            return False
        
        # are there any developments on this vertex?
        devs = v.getDevelopments()
        if devs and len(devs) > 0: 
            return False
        
        # is this vertex at least one unit away from another settlement or city?
        adjecentDev = False
        adj = v.getAdjecentVertexes()
        for a in adj:
            logging.info("adjecent (%d,%d)", a.x, a.y)
            devs = a.getDevelopments()
            for d in devs:
                if d.type == "settlement" or d.type == "city":
                    adjecentDev = True 
                    break;
            if adjecentDev: 
                break;
        
        if adjecentDev:
            logging.info("too close to other developments")
            return False
        
        gp = self.board.getCurrentGamePhase()
        tp = self.board.getCurrentTurnPhase()
        if gp is None or tp is None:
            return False
        
        #update the game/turn phase
        if gp.phase == "buildFirstSettlement" or gp.phase == "buildSecondSettlement":
            if tp.phase == "buildSettlement":
                rtp = gp.getTurnPhaseByName("buildRoad")
                
                self.board.turnPhase += 1
                self.board.put()
                v.addDevelopment(color, "settlement")
                
                #self.sendMessageAll({'action': 'placeSettlement', 'x':x, 'y':y, 'color':color})
                
                return True
            else:
                logging.info("not in the correct phase (currentPhase: %s)" % tp.phase)
                return False
        elif gp.phase == "main":
            if tp.phase != "build":
                logging.info("not in the correct phase (currentPhase: %s)" % tp.phase)
                return False
            else:
                #TODO: does this vertex have a road of the right color running into it?
                #TODO: does the player have enough resources to buy a settlement?
                #TODO: does the player have any settlements left?
                pass
        else:
            return False 
                
        #self.sendMessageAll({'action': 'placeSettlement', 'x':x, 'y':y, 'color':color})
        return False
    def placeCity(self, x, y, user):
        #logging.info("placeSettlement: " + data)
        #TODO: does the player have enough resources to buy a city?
        #TODO: does the player have any cities left?
        #TODO: are we in the placement phase of the game?
        
        
        p = self.board.getPlayer(user)
        if p == None: 
            return False
           
        color = p.color
        
        v = self.board.getVertex(x, y)
        if v == None:
            return False
        
        devs = v.getDevelopments()
        if not devs or len(devs) == 0: 
            return False
        
        for d in devs:
            if d.type == "settlement" and d.color == color:
                d.type = "city"
                d.put()
                return True
            
        return False
    
    

