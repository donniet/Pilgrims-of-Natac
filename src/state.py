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
    hexProduces = ["mountains", "hills", "pasture", "fields", "forest"]
    colors = ["red", "blue", "green", "orange", "white", "brown"]
    minimumPlayers = 2
    
    gamePhases = [
        ("joining", []), 
        ("buildFirstSettlement", ["buildSettlement", "buildRoad"]), 
        ("buildSecondSettlement", ["buildSettlement", "buildRoad"]), 
        ("main", ["rollDice", "moveRobber", "trade",  "playCard", "build"]), 
        ("complete", [])
    ]
    developments = [
        {"location":"vertex", "name":"settlement", "playerStart":5, "cost":{"brick":1, "wool":1, "wheat":1, "wood":1}},
        {"location":"vertex", "name":"city", "playerStart":4, "cost":{"ore":3, "wheat":2}},
        {"location":"edge", "name":"road", "playerStart":15, "cost":{"brick":1, "wood":1}},
    ]
    dice = [6,6]
    
    def __init__(self):
        
        random.shuffle(self.hexTypes)
        
    def instantiateModel(self, gameKey, owner):
        board = model.Board()
        board.gameKey = gameKey
        board.dateTimeCreated = datetime.datetime.now()
        board.resources = self.resources
        board.hexProduces = self.hexProduces
        board.playerColors = self.colors
        board.owner = owner
        board.gamePhase = 0
        board.minimumPlayers = self.minimumPlayers
        board.dice = self.dice
        
        board.put()
        
        for d in self.developments:
            dt = model.DevelopmentType(parent=board, location=d["location"], name=d["name"], playerStart=d["playerStart"])
            dt.put()
            for (r, a) in d["cost"].items():
                dtc = model.DevelopmentTypeCost(parent=dt, resource=r, amount=a)
                dtc.put()
        
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
    
class ActionResponse(dict):
    def __init__(self, success, message=None):
        self["success"] = success;
        if message is not None:
            self["message"] = message;

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
        # before processing any action, check if we are processing one now:
        
        if self.board.dateTimeStarted is not None:
            #cannot join after the game has started
            return None
            
       
        #all joined users must be registered
        self.registerUser(user)
        
        p = self.board.getPlayer(user)
        
        if p:
            return p.color
        
        
        p = memcache.get("%s-processing-join" % self.board.gameKey)
        if not p is None and p:
            return False #processing
        
        memcache.set("%s-processing-join" % self.board.gameKey, True, 60)
        
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
        
        color = None
        
        if len(players) + reservationCount < len(cols):
            for p in players:
                if p.user == user:
                    #HACK: this is ugly
                    color = p.color
                    break
                else:
                    cols.remove(p.color)
            
            if color is None:
                color = cols.pop()
            
            self.board.addPlayer(color, user)
            self.updateStateKey()
                
        memcache.delete("%s-processing-join" % self.board.gameKey)
        
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
    
    def startGame(self, user):
        logging.info("starting game...")
        if user != self.board.owner:
            logging.info("startGame: Not Owner")
            return ActionResponse(False, "Only the owner of the game may start it.")
        gp = self.board.getCurrentGamePhase()
        if gp is None or gp.phase != "joining":
            logging.info("startGame: Not joining Phase")
            return ActionResponse(False, "The game has already been started.")
        
        players = self.board.getPlayers()
        
        np = len(players)
        if np < self.board.minimumPlayers:
            logging.info("startGame: Not Enough Players")
            return ActionResponse(False, "This game requires %d players, but only %d have joined." % (self.board.minimumPlayers,np))
        
        bfs = self.board.getGamePhaseByName("buildFirstSettlement")
        if bfs is None:
            logging.info("startGame: no buildFirstSettlement gamephase")
            return ActionResponse(False, "Error: this game has no initial building phase.  Contact game creator.")
        
        po = range(np)
        random.shuffle(po)
        
        logging.info("bfs.order: %d" % bfs.order)
        
        for i in range(len(po)):
            players[i].order = po[i]
            players[i].put()
        
        self.board.dateTimeStarted = datetime.datetime.now()
        self.board.gamePhase = bfs.order
        if len(bfs.getTurnPhases()) > 0:
            self.board.turnPhase = 0
        else:
            self.board.turnPhase = None
            
        self.board.playOrder = po
        self.board.currentPlayerRef = 0 #current player is 
        self.board.put()
        
        for p in players:
            p.resetResources()
        
        self.sendMessageAll({"action":"chat", "data":"Game Started"})
        
        return ActionResponse(True);
      
            
    def processAction(self, action, data, user):
        # before processing any action, check if we are processing one now:
        p = memcache.get("%s-processing-action" % self.board.gameKey)
        if not p is None and p:
            return ActionResponse(False, "Another action is processing now...") #processing
        
        memcache.set("%s-processing-action" % self.board.gameKey, True, 60)
        ret = False
        message = None
        
        logging.info("processing action: %s %s %s" % (action, data, user))
        
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
        elif action == "rollDice":
            ret = self.rollDice(user)
        elif action == "endTurn":
            ret = self.endTurn(user)
        else:
            message = "Unknown action"
        
        
        if ret and ret["success"]:
            logging.info("processing action [True]: %s %s %s" % (action, data, user))
            dataitems = []
            if data is not None and data.items() is not None:
                dataitems = data.items()
        
            self.updateStateKey()
            color = self.board.getPlayer(user).color
            self.sendMessageAll({"action":action, "color":color,"data":data})        
        
        memcache.delete("%s-processing-action" % self.board.gameKey)
        
        if message is not None:
            return ActionResponse(ret, message);
        else:
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
                actions.extend(["startTrade", "playCard", "placeSettlement", "placeCity", "placeRoad","endTurn"])
        elif gamePhase == "complete":
            pass
        return actions
    
    def getUserActions(self, user):
        
        p = self.board.getPlayer(user)
        c = self.board.getCurrentPlayerColor()
                
        gp = self.board.getCurrentGamePhase()
        tp = self.board.getCurrentTurnPhase()
        
        return self.getUserActionsInner(user, p, c, gp, tp)    
    
    
    def endTurn(self, user):
        p = self.board.getPlayer(user)
        if p is None: 
            logging.info("player not found %s." % user)
            return ActionResponse(False, "You are not a player in this game.");
        
        color = p.color
        
        if self.board.getCurrentPlayerColor() != color:
            logging.info("not current player %s." % user)
            return ActionResponse(False, "It is not your turn.");
        
        self.board.moveNextPlayer()
        self.board.turnPhase = 0
        self.board.put()
        return ActionResponse(True)
    
    def rollDice(self, user):
        p = self.board.getPlayer(user)
        if p is None: 
            logging.info("player not found %s." % user)
            return ActionResponse(False, "You are not a player in this game.")
        
        color = p.color
        
        if self.board.getCurrentPlayerColor() != color:
            logging.info("not player turn %s." % user)
            return ActionResponse(False, "It is not your turn.");
        
        tp = self.board.getCurrentTurnPhase()
        
        if tp.phase != "rollDice":
            return ActionResponse(False, "You have already rolled the dice.");
        
        diceValues = []
        sum = 0
        for m in self.board.dice:
            d = random.randint(1, m)
            sum += d
            diceValues.append(d)
            logging.info("die: %d" % d)
        
        if sum == 0:
            #TODO handle error
            pass
        elif sum == 7:
            #TODO: handle roll of 7
            tp = self.board.getCurrentGamePhase().getTurnPhaseByName("build")
            
            self.board.turnPhase = tp.order
        else:
            pc = self.board.getPlayerColorMap()
                    
            # distribute resources
            hx = self.board.getHexesByValue(sum)
            for h in hx:
                resource = self.board.getResourceByHexType(h.type)
                vx = h.getAdjecentVertexes()
                for v in vx:
                    dx = v.getDevelopments()
                    for d in dx:
                        p = pc[d.color]
                        if p is None:
                            logging.info("player not found: %s" % d.color)
                            pass
                        elif d.type == "settlement":
                            p.adjustResources(dict([[resource, 1]]))
                        elif d.type == "city":
                            p.adjustResources(dict([[resource, 2]]))
            
            tp = self.board.getCurrentGamePhase().getTurnPhaseByName("build")
            
            self.board.turnPhase = tp.order
            
        self.board.diceValues = diceValues
        self.board.put()
        
        self.sendMessageAll({"action":"diceRolled", "data":diceValues})
        
        return ActionResponse(True)  
        
    
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
            return ActionResponse(False, "You are not a pleyer in this game.")
        
        color = p.color
        
        if self.board.getCurrentPlayerColor() != color:
            logging.info("not player turn %s." % user)
            return ActionResponse(False, "It is not your turn.")
        
        e = self.board.getEdge(x1, y1, x2, y2)
        if e is None:
            logging.info("edge %d,%d,%d,%d not found", (x1, y1, x2, y2))
            return ActionResponse(False, "The edge you selected is not found in this game.")
        
        devs = e.getDevelopments()
        if devs and len(devs) > 0:
            logging.info("found edge development")
            return ActionResponse(False, "There is already a road on this edge.")
        
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
            return ActionResponse(False, "You have no developments adjecent to this edge.")
        
        np = len(self.board.getPlayers())
        gp = self.board.getCurrentGamePhase()
        tp = self.board.getCurrentTurnPhase()
        if gp is None or tp is None:
            return ActionResponse(False, "Error: The game has not started, or is in the incorrect phase.")
        
        #update the game/turn phase
        if gp.phase == "buildFirstSettlement":
            if tp.phase != "buildRoad":
                logging.info("not in the correct phase (currentPhase: %s)" % tp.phase)
                return ActionResponse(False, "You cannot build a road now.")
            
            if self.board.currentPlayerRef < np - 1:
                self.board.moveNextPlayer()
                #self.board.currentPlayerRef += 1
                self.board.turnPhase = 0
            else:
                self.board.gamePhase += 1
                self.board.turnPhase = 0
                
            self.board.put()
            e.addDevelopment(color, "road")
            return True
        elif gp.phase == "buildSecondSettlement":
            if tp.phase != "buildRoad":
                logging.info("not in the correct phase (currentPhase: %s)" % tp.phase)
                return ActionResponse(False, "You cannot build a road now.")
            
            logging.info("currentPlayerRef: %d" % self.board.currentPlayerRef)
            
            if self.board.currentPlayerRef > 0:
                self.board.movePrevPlayer()
                #self.board.currentPlayerRef -= 1
                self.board.turnPhase = 0
            else:
                self.board.gamePhase += 1
                self.board.turnPhase = 0
                self.board.moveNextPlayer()
                #self.board.currentPlayerRef += 1
                
            self.board.put()
            e.addDevelopment(color, "road")
            return ActionResponse(True)
        elif gp.phase == "main":
            if tp.phase != "build":
                logging.info("not in the correct phase (currentPhase: %s)" % tp.phase)
                return ActionResponse(False, "You cannot build a road now.")
            else:
                cost = self.board.getDevelopmentTypeCost("road")
                for r in cost:
                    cost[r] = -cost[r]
                    
                if not p.adjustResources(cost):
                    logging.info("not enough resources to build road.")
                    return ActionResponse(False, "You do not have enough resources to build a road.")
                
                
                e.addDevelopment(color, "road")
                return ActionResponse(True)
                
                #TODO: does the player have any roads left?    
        else:
            logging.info("not in the correct phase (currentPhase: %s)" % gp.phase)
            return ActionResponse(False, "You cannot build a road now.")
        
        return False
    
    def createSendMessageAllCallback(self, message):
        def x():
            self.sendMessageAll(message)
        return x
    
    def placeSettlement(self, x, y, user):
        #logging.info("placeSettlement: " + data)

        
        p = self.board.getPlayer(user)
        if p is None: 
            logging.info("player not found %s." % (user,))
            return ActionResponse(False, "You are not a player in this game")
           
        color = p.color
        
        v = self.board.getVertex(x, y)
        if v is None: 
            logging.info("vertex %d,%d not found." % (x,y) )
            return ActionResponse(False, "Error: The vertex you selected is not found on this board.")
        
        # are there any developments on this vertex?
        devs = v.getDevelopments()
        if devs and len(devs) > 0: 
            return ActionResponse(False, "There is already a development on this vertex")
        
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
            return ActionResponse(False, "This vertex is too close to other cities or settlements")
        
        gp = self.board.getCurrentGamePhase()
        tp = self.board.getCurrentTurnPhase()
        if gp is None or tp is None:
            return ActionResponse(False, "Error: The game has not started or is in the incorrect phase.")
        
        #update the game/turn phase
        if gp.phase == "buildFirstSettlement" or gp.phase == "buildSecondSettlement":
            if tp.phase == "buildSettlement":
                rtp = gp.getTurnPhaseByName("buildRoad")
                
                self.board.turnPhase += 1
                self.board.put()
                v.addDevelopment(color, "settlement")
                
                if gp.phase == "buildSecondSettlement":
                    res = dict()
                    adj_hexes = v.getAdjecentHexes()
                    logging.info("adjecent hexes: %d" % len(adj_hexes))
                    for ah in adj_hexes:
                        r = self.board.getResourceByHexType(ah.type)
                        if r is None:
                            pass
                        elif res.get(r, None) is None:
                            res[r] = 1
                        else:
                            res[r] += 1
                            
                        logging.info("resource type: %s, %s = %d" % (ah.type, r, res[r]))
                    p.adjustResources(res)
                #self.sendMessageAll({'action': 'placeSettlement', 'x':x, 'y':y, 'color':color})
                
                return ActionResponse(True)
            else:
                logging.info("not in the correct phase (currentPhase: %s)" % tp.phase)
                return ActionResponse(False, "You cannot build a settlement now")
        elif gp.phase == "main":
            if tp.phase != "build":
                logging.info("not in the correct phase (currentPhase: %s)" % tp.phase)
                return ActionResponse(False, "You cannot build a settlement now")
            else:
                adj_edge = v.getAdjecentEdges()
                has_adj_road = False
                for e in adj_edge:
                    devs = e.getDevelopments()
                    for d in devs:
                        if d.type == "road" and d.color == p.color:
                            has_adj_road = True
                            break
                    if has_adj_road:
                        break
                
                if not has_adj_road:
                    logging.info("No adjecent roads to place settlement")
                    return ActionResponse(False, "You have no roads adjecent to this vertex")
                                
                cost = self.board.getDevelopmentTypeCost("settlement")
                for r in cost:
                    cost[r] = -cost[r]
                    
                if not p.adjustResources(cost):
                    logging.info("Not enough resources to place settlement")
                    return ActionResponse(False, "You do not have enough resources to build a settlement")
                #TODO: does the player have any settlements left?
                
                v.addDevelopment(color, "settlement")
                return ActionResponse(True) 
        else:
            return ActionResponse(False, "You cannot build a settlement now") 
                
        #self.sendMessageAll({'action': 'placeSettlement', 'x':x, 'y':y, 'color':color})
        return ActionResponse(False, "You cannot build a settlement now")
    def placeCity(self, x, y, user):
        #logging.info("placeSettlement: " + data)
        #TODO: does the player have enough resources to buy a city?
        #TODO: does the player have any cities left?
        #TODO: are we in the placement phase of the game?
        
        
        p = self.board.getPlayer(user)
        if p == None: 
            return ActionResponse(False, "You are not a player in this game")
           
        color = p.color
        
        v = self.board.getVertex(x, y)
        if v == None:
            return ActionResponse(False, "Error: The vertex you selected is not found on this board.")
        
        devs = v.getDevelopments()
        if not devs or len(devs) == 0: 
            return ActionResponse(False, "You have no settlement on this vertex")
        
        for d in devs:
            if d.type == "settlement" and d.color == color:
                cost = self.board.getDevelopmentTypeCost("city")
                for r in cost:
                    cost[r] = -cost[r]
                    
                if not p.adjustResources(cost):
                    return ActionResponse(False, "You do not have enough resources to build a city.")
                
                d.type = "city"
                d.put()
                return ActionResponse(True) 
            
        return ActionResponse(False, "You have no settlement on this vertex")
    
    

