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
from copy import copy
from template import BoardTemplate


from events import EventHook

def random_string(length):
    return ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(length))
 
def create_game(user, template = BoardTemplate):
    #TODO: check for the unlikely case of this board key being a duplicate
    # generate board key
    
    gameKey = random_string(8)
    #gameKey = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(8))
    bt = template()
    
    logging.info("creating game %s" % (gameKey,))
    
    bt.instantiateModel(gameKey, user)
    
    return gameKey
    
def get_game(gamekey):
    #logging.info("finding game %s" % (gamekey,))
    
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
        self.board.stateKey = random_string(16)
        #self.board.stateKey = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(16))
        self.board.put()
        
    def getStateKey(self):
        return self.board.stateKey
    
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
    def isUserRegistered(self, user):
        for u in self.users:
            if u == user:
                return True
            
        return False
    def unregisterUser(self, user):
        try:
            self.users.remove(user)
        except ValueError:
            pass
            
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
            reservationKey = random_string(8)                
            #reservationKey = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(8))
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
            self.sendPlayerUpdate()
                
        memcache.delete("%s-processing-join" % self.board.gameKey)
        
        return color
    def sendPlayerUpdate(self):
        players = self.board.getPlayers()
        for p in players:
            p.connected = self.isUserRegistered(p.user)
            
        self.sendMessageAll({"action":"updatePlayers", "players":players})
    
    def sendMessageAll(self, message):
        logging.info("sending message to all '%s'" % message["action"])
        
        c = self.board.getCurrentPlayerColor()
                
        gp = self.board.getCurrentGamePhase()
        tp = self.board.getCurrentTurnPhase()
        
        users = copy(self.users)
        
        for user in users:
            p = self.board.getPlayer(user)
            
            mu = message.copy()
            mu["availableActions"] = self.getUserActionsInner(user, p, c, None if gp is None else gp.phase, None if tp is None else tp.phase)
            mu["stateKey"] = self.getStateKey()

            try:
                channel.send_message(self.gamekey + user.user_id(), json.dumps(mu, cls=model.MessageEncoder))
            except channel.InvalidChannelClientIdError:
                # we should remove this user from the user list
                self.unregisterUser(user)
            except KeyError:
                self.unregisterUser(user)
                
            
    def sendMessageUser(self, user, message):
        c = self.board.getCurrentPlayerColor()
                
        gp = self.board.getCurrentGamePhase()
        tp = self.board.getCurrentTurnPhase()
        p = self.board.getPlayer(user)
        
        mu = message.copy()
        mu["availableActions"] = self.getUserActionsInner(user, p, c, None if gp is None else gp.phase, None if tp is None else tp.phase)
        mu["stateKey"] = self.getStateKey()
        
        channel.send_message(self.gamekey + user.user_id(), json.dumps(mu, cls=model.MessageEncoder))
    
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
        logmessage = ""
        
        logging.info("processing action: %s %s %s" % (action, data, user))
        
        if action == "placeSettlement":
            ret = self.placeSettlement(data["x"], data["y"], user)
            logmessage = "placed settlement (%d,%d)" % (data["x"], data["y"])
        elif action == "placeCity":
            ret = self.placeCity(data["x"], data["y"], user)
            logmessage = "placed city (%d,%d)" % (data["x"], data["y"])
        elif action == "placeRoad":
            ret = self.placeRoad(user, data["x1"], data["y1"], data["x2"], data["y2"])
            logmessage = "placed road from (%d,%d) to (%d,%d)" % (data["x1"], data["y1"], data["x2"], data["y2"])
        elif action == "startGame":
            ret = self.startGame(user)
            logmessage = "started game"
        elif action == "rollDice":
            ret = self.rollDice(user)
            logmessage = "rolled dice"
        elif action == "endTurn":
            ret = self.endTurn(user)
            logmessage = "ended turn"
        elif action == "discard":
            ret = self.discard(user, data)
            logmessage = "discarded"
        elif action == "placeRobber":
            ret = self.placeRobber(user, data["x"], data["y"])
            logmessage = "placed robber"
        elif action == "stealRandomResource":
            ret = self.stealRandomResource(user, data["x"], data["y"])
            logmessage = "stole resource from player at vertex %d, %d" % (data["x"], data["y"])
        elif action == "startTrade":
            ret = self.startTrade(user)
            logmessage = "started trading"
        elif action == "cancelTrade":
            ret = self.cancelTrade(user)
            logmessage = "cancelled trade"
        elif action == "changeTradeOffer":
            ret = self.changeTradeOffer(user, data)
            logmessage = "changed trade offer"
        elif action == "changeBankOffer":
            ret = self.changeBankOffer(user, data)
            logmessage = "changed bank offer"
        elif action == "acceptTradeOffer":
            ret = self.acceptTradeOffer(user, data)
            logmessage = "acceptTradeOffer"
        elif action == "confirmTradeOffer":
            ret = self.confirmTradeOffer(user)
            logmessage = "confirm trade offer"  
        elif action == "confirmBankOffer":
            ret = self.confirmBankOffer(user)
            logmessage = "confirm bank offer"       
        elif action == "chat":
            self.board.log("chat", data, user)
            color = self.board.getPlayer(user).color
            self.sendMessageAll({"action":"chat", "color":color,"message":data});
            ret = ActionResponse(True)
        else:
            message = "Unknown action"
            logmessage = "unknown action '%s'" % action
        
        if ret and ret["success"] and action != "chat":
            logging.info("processing action [True]: %s %s %s" % (action, data, user))
            #dataitems = []
            #if data is not None and data.items() is not None:
            #    dataitems = data.items()
        
            self.updateStateKey()
            self.updateScore() 
            color = self.board.getPlayer(user).color
            self.sendMessageAll({"action":action, "color":color,"data":data})
            self.board.log("action", logmessage, user)
            self.sendMessageAll({"action":"log", "color":color,"message":logmessage});       
        
        memcache.delete("%s-processing-action" % self.board.gameKey)
        
        if message is not None:
            return ActionResponse(ret, message);
        else:
            return ret
    
    def updateScore(self):
        ad = self.board.getAllDevelopments()
        dts = self.board.getDevelopmentTypeMap()
        
        scores = dict()
        players = self.board.getPlayers()
        
        for p in players:
            scores[p.color] = 0
        
        for d in ad:
            dt = dts[d.type]
            if dt.points == 0 or d.color is None:
                continue
            elif dt is None:
                logging.info("ERROR: development type not found '%s'" % d.type)
            elif scores.get(d.color, None) is None:
                logging.info("ERROR: player color not found '%s'" % d.color)
            elif d.color is not None:
                scores[d.color] += dt.points
                
        #TODO: other ways you can get points, aka Longest Road, Largest Army
        
        updated = False
        
        for p in players:
            if scores[p.color] != p.score:
                p.setScore(scores[p.color])
                updated = True 
            if scores[p.color] >= self.board.pointsNeededToWin:
                #somebody just won the game
                self.board.setWinner(p.user)
        
        #update players all the time
        #if updated:
        self.sendPlayerUpdate()
                
            
    
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
        elif gamePhase == "main" and player is not None:
            if turnPhase == "rollDice" and player.color == currentColor:
                actions.append("rollDice")
            elif turnPhase == "moveRobber" and player.color == currentColor:
                actions.append("placeRobber")
            elif turnPhase == "stealRandomResource" and player.color == currentColor:
                actions.append("stealRandomResource")
            elif turnPhase == "playCard" or turnPhase == "build" and player.color == currentColor:
                actions.extend(["cancelTrade", "startTrade", "playCard", "placeSettlement", "placeCity", "placeRoad","endTurn"])
            elif turnPhase == "trade" and player.color == currentColor:
                actions.extend(["cancelTrade"])
            elif turnPhase == "discard":
                d = self.board.getCurrentDiscard()
                pd = d.getPlayerDiscardsByColor(player.color)
                if pd.requiredDiscards > 0 and not pd.discardComplete:
                    actions.extend(["discard"])
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
    
    def discard(self, user, resources):
        p = self.board.getPlayer(user)
        if p is None: 
            logging.info("player not found %s." % user)
            return ActionResponse(False, "You are not a player in this game.")
        
        tp = self.board.getCurrentTurnPhase()
        
        if tp.phase != "discard":
            logging.info("incorrect phase to discard")
            return ActionResponse(False, "You cannot discard right now.")
        
        d = self.board.getCurrentDiscard()
        if d is None:
            logging.info("no discard in progress")
            return ActionResponse(False, "You cannot discard right now.")
        
        pd = d.getPlayerDiscardsByColor(p.color)
        if pd is None or pd.requiredDiscards == 0:
            logging.info("player does not have to discard")
            return ActionResponse(False, "You do not have to discard any cards.")
        
        if pd.discardComplete:
            logging.info("player already discarded")
            return ActionResponse(False, "You have already discarded")
        
        
        
        sum = 0
        resourceDict = dict()
        logging.info("resources: %s" % resources)
        for r in resources:
            logging.info("resource: %s, amount: %i" % (r["resource"], r["amount"]))
            sum += r["amount"]
            resourceDict[r["resource"]] = -r["amount"]
        
        logging.info("sum: %i" % sum)
        if pd.requiredDiscards != sum:
            logging.info("player discarded incorrect amount")
            return ActionResponse(False, "You must discard %i cards." % pd.requiredDiscards)
        
        ret = p.adjustResources(resourceDict)
        if not ret:
            logging.info("player cannot discard specified resources")
            return ActionResponse(False, "You do not have the resources you tried to discard.")
        
        pd.discardComplete = True
        pd.put()
        
        discards = d.getPlayerDiscards()
        discardsComplete = True
        for d in discards:
            if not d.discardComplete:
                discardsComplete = False
                break
            
        if discardsComplete:
            tp = self.board.getCurrentGamePhase().getTurnPhaseByName("moveRobber")
            self.board.turnPhase = tp.order
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
        
        self.sendMessageAll({"action":"diceRolled", "data":diceValues})
        
        if sum == 0 or sum == 1:
            #TODO handle error
            pass
        elif sum == 7:
            #TODO: handle roll of 7
            
            mustDiscard = False
            playerDiscardMap = dict()
            players = self.board.getPlayers()
            for p in players:
                tr = p.getTotalResources()
                #TODO: make this configurable
                discardCount = 0
                    
                if tr > 7:
                    if tr % 2 == 0:
                        discardCount = tr / 2
                    else:
                        discardCount = (tr-1) / 2
                         
                    playerDiscardMap[p.color] = discardCount
                    mustDiscard = True
                else:
                    playerDiscardMap[p.color] = 0
            
            
            if mustDiscard: 
                tp = self.board.getCurrentGamePhase().getTurnPhaseByName("discard")
                self.board.turnPhase = tp.order
                discardKey = random_string(16)
                #discardKey = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(16))
                self.board.createDiscard(discardKey, playerDiscardMap)
            else:
                tp = self.board.getCurrentGamePhase().getTurnPhaseByName("moveRobber")
                self.board.turnPhase = tp.order
            
        else:
            pc = self.board.getPlayerColorMap()
                    
            # distribute resources
            hx = self.board.getHexesByValue(sum)
            for h in hx:
                hd = h.getDevelopments()
                robber = False
                for d in hd:
                    if d.type == "robber":
                        robber = True
                        break;
                    
                if robber:
                    continue
                
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
            return ActionResponse(True)
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
                
                logging.info("a road costs: %s" % json.dumps(cost))
                
                negCost = dict(map(lambda (r,a): (r,-a), cost.items()))
                    
                if not p.adjustResources(negCost):
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
    
    def placeRobber(self, user, x, y):
        p = self.board.getPlayer(user)
        if p is None: 
            logging.info("player not found %s." % (user,))
            return ActionResponse(False, "You are not a player in this game")
           
        color = p.color
        if self.board.getCurrentPlayerColor() != color:
            logging.info("not player turn %s." % user)
            return ActionResponse(False, "It is not your turn.")
        
        gp = self.board.getCurrentGamePhase()
        tp = self.board.getCurrentTurnPhase()
        if gp is None or tp is None:
            return ActionResponse(False, "Error: The game has not started or is in the incorrect phase.")
        
        if tp.phase != "moveRobber":
            logging.info("incorrect turn phase, should be 'moveRobber'")
            return ActionResponse(False, "You cannot move the robber right now.")
        
        h = self.board.getHex(x, y)
        if h is None:
            logging.info("hex %d,%d not found." % (x,y))
            return ActionResponse(False, "Error: The hex you selected is not found on this board.")
        
        devs = h.getDevelopments()
        if devs and len(devs) > 0:
            return ActionResponse(False, "There is already a development on this hex.")
        
        hexes = self.board.getHexes()
        for hex in hexes:
            devs = hex.getDevelopments()
            for d in devs:
                if d.type == "robber":
                    d.delete()
        
        h.addDevelopment(None, "robber")
        
        canSteal = False
        singlePlayer = None
        singlePlayerX = None
        singlePlayerY = None
        verts = h.getAdjecentVertexes()
        for v in verts:
            devs = v.getDevelopments()
            for d in devs:
                if d.color != color:
                    canSteal = True
                    if singlePlayer is None:
                        singlePlayer = d.color
                        singlePlayerX = v.x
                        singlePlayerY = v.y
                    elif singlePlayer != d.color:
                        singlePlayer = None
                        singlePlayerX = None
                        singlePlayerY = None
                    break
            if canSteal:
                break
        
        tp = None
        
        if canSteal and singlePlayer is None:
            tp = gp.getTurnPhaseByName("stealRandomResource")
        elif singlePlayer is not None:
            stealPlayer = self.board.getPlayerByColor(singlePlayer)
            if stealPlayer is None:
                logging.info("no player found of color %s" % singlePlayer)
                return ActionResponse(False, "No player found of color %s" % singlePlayer)
            
            ret = self.innerStealRandomResource(p, stealPlayer)
            
            if ret:
                tp = gp.getTurnPhaseByName("build")
            else:
                logging.info("error stealing from lone player adjecent to hex")
                return ActionResponse(False, "Error: Could not steal from adjecent player.")
        else:
            tp = gp.getTurnPhaseByName("build")
        
        self.board.turnPhase = tp.order
        self.board.put()
        
        return ActionResponse(True)   

    def innerStealRandomResource(self, player, stealPlayer):
        res = stealPlayer.getPlayerResourcesDict()
        tot = 0
        for _,amount in res.items():
            tot += amount
            
        if tot == 0:
            logging.info("no resources available to steal!")
            
            return True
        
        rand = random.randint(0, tot-1)
        stolen = None
        for resource,amount in res.items():
            if amount >= rand:
                stolen = resource
                break
            else:
                rand -= amount
                
        if stolen is None:
            logging.info("something went wrong-- random resource selection failed")
            return False
        
        player.adjustResources(dict([[stolen, 1]]))
        stealPlayer.adjustResources(dict([[stolen, -1]]))
        
        return True

    def stealRandomResource(self, user, x, y):
        p = self.board.getPlayer(user)
        if p is None: 
            logging.info("player not found %s." % (user,))
            return ActionResponse(False, "You are not a player in this game")
           
        color = p.color
        if self.board.getCurrentPlayerColor() != color:
            logging.info("not player turn %s." % user)
            return ActionResponse(False, "It is not your turn.")
        
        gp = self.board.getCurrentGamePhase()
        tp = self.board.getCurrentTurnPhase()
        if gp is None or tp is None:
            return ActionResponse(False, "Error: The game has not started or is in the incorrect phase.")
        
        if tp.phase != "stealRandomResource":
            logging.info("incorrect turn phase, should be 'stealRandomResource'")
            return ActionResponse(False, "You cannot steal resources right now.")
        
        v = self.board.getVertex(x, y)
        if v is None:
            logging.info("vertex %d,%d not found." % (x,y))
            return ActionResponse(False, "Error: The vertex you selected is not found on this board.")
        
        hexes = v.getAdjecentHexes()
        if hexes is None or len(hexes) == 0:
            logging.info("no hexes adjecent to %d, %d." %(x,y))
            return ActionResponse(False, "Error: The vertex you selected has no adjecent hexes.")
        
        robberFound = False
        for h in hexes:
            devs = h.getDevelopments()
            for d in devs:
                if d.type == "robber":
                    robberFound = True
                    break
            if robberFound:
                break
        
        if not robberFound:
            logging.info("robber not found adjecent to hex %d,%d" % (x,y))
            return ActionResponse(False, "The vertex you selected is not adjecent to the robber.")
        
        stealColor = None
        
        devs = v.getDevelopments()
        for d in devs:
            if d.color is not None:
                stealColor = d.color
                break
        
        if stealColor is None:
            logging.info("no player with developments on vertex %d,%d" %(x,y))
            return ActionResponse(False, "The vertex you selected has no player developments.")

        stealPlayer = self.board.getPlayerByColor(stealColor)
        if stealPlayer is None:
            logging.info("no player found of color %s" % stealColor)
            return ActionResponse(False, "No player found of color %s" % stealColor)
        
        ret = self.innerStealRandomResource(p, stealPlayer)
        
        if ret:
            tp = gp.getTurnPhaseByName("build")
            self.board.turnPhase = tp.order
            self.board.put()
            
            return ActionResponse(True, "Stole from the player on vertex %d,%d" % (x, y))
        else:
            return ActionResponse(False, "Error: Could not steal resources.")

    
    def placeSettlement(self, x, y, user):
        #logging.info("placeSettlement: " + data)

        
        p = self.board.getPlayer(user)
        if p is None: 
            logging.info("player not found %s." % (user,))
            return ActionResponse(False, "You are not a player in this game")
           
        color = p.color
        if self.board.getCurrentPlayerColor() != color:
            logging.info("not player turn %s." % user)
            return ActionResponse(False, "It is not your turn.")
        
        
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
        #TODO: does the player have any cities left?
        
        
        p = self.board.getPlayer(user)
        if p == None: 
            return ActionResponse(False, "You are not a player in this game")
           
        color = p.color
        if self.board.getCurrentPlayerColor() != color:
            logging.info("not player turn %s." % user)
            return ActionResponse(False, "It is not your turn.")
        
        gp = self.board.getCurrentGamePhase()
        tp = self.board.getCurrentTurnPhase()
        if gp is None or tp is None:
            return ActionResponse(False, "Error: The game has not started or is in the incorrect phase.")
        
        if gp.phase != "main" or tp.phase != "build":
            logging.info("not in the correct phase (currentPhase: %s)" % tp.phase)
            return ActionResponse(False, "You cannot build a city now")
        
        
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
    
    def startTrade(self, user):
        p = self.board.getPlayer(user)
        if p == None: 
            return ActionResponse(False, "You are not a player in this game")
           
        color = p.color
        if self.board.getCurrentPlayerColor() != color:
            logging.info("not player turn %s." % user)
            return ActionResponse(False, "It is not your turn.")
        
        gp = self.board.getCurrentGamePhase()
        tp = self.board.getCurrentTurnPhase()
        if gp is None or tp is None:
            return ActionResponse(False, "Error: The game has not started or is in the incorrect phase.")
        
        if gp.phase != "main" or tp.phase != "build":
            logging.info("not in the correct phase (currentPhase: %s)" % tp.phase)
            return ActionResponse(False, "You cannot trade right now")
        
        tp = gp.getTurnPhaseByName("trade")
        if tp is None:
            logging.info("no trading phase found")
            return ActionResponse(False, "You cannot trade right now")
        
        t = self.board.getCurrentTrade()
        if t is not None:
            logging.info("there is already a trade going on")
            return ActionResponse(False, "There is already a trade in progress.")
        
        self.board.turnPhase = tp.order
        self.board.put()
        
        tradeKey = random_string(16)
        #tradeKey = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(16))
        self.board.createTrade(tradeKey)
        return ActionResponse(True)
    
    def cancelTrade(self, user):
        p = self.board.getPlayer(user)
        if p == None: 
            return ActionResponse(False, "You are not a player in this game")
           
        color = p.color
        if self.board.getCurrentPlayerColor() != color:
            logging.info("not player turn %s." % user)
            return ActionResponse(False, "It is not your turn.")
        
        gp = self.board.getCurrentGamePhase()
        tp = self.board.getCurrentTurnPhase()
        if gp is None or tp is None:
            return ActionResponse(False, "Error: The game has not started or is in the incorrect phase.")
        
        #if gp.phase != "main" or tp.phase != "trade":
        #    logging.info("not in the correct phase (currentPhase: %s)" % tp.phase)
        #    return ActionResponse(False, "There is no trade in progress.")
        
        tp = gp.getTurnPhaseByName("build")
        if tp is None:
            logging.info("no building phase found")
            return ActionResponse(False, "You cannot cancel trading now")
        
        t = self.board.getCurrentTrade()
        if t is not None:
            t.cancel()
            
        self.board.turnPhase = tp.order
        self.board.currentTradeKey = None
        self.board.put()
        return ActionResponse(True)
        
    def changeTradeOffer(self, user, resourceDict):
        p = self.board.getPlayer(user)
        if p == None: 
            return ActionResponse(False, "You are not a player in this game")
        
        gp = self.board.getCurrentGamePhase()
        tp = self.board.getCurrentTurnPhase()
        if gp is None or tp is None:
            return ActionResponse(False, "Error: The game has not started or is in the incorrect phase.")
        
        if gp.phase != "main" or tp.phase != "trade":
            logging.info("not in the correct phase (currentPhase: %s)" % tp.phase)
            return ActionResponse(False, "There is no trade in progress.")
        
        t = self.board.getCurrentTrade()
        if t is None:
            logging.info("no current trade in progress")
            return ActionResponse(False, "There is no current trade in progress.")
        
        ret = t.changeOffer(p.color, resourceDict)
        if not ret:
            logging.info("could not change the trade.")
            return ActionResponse(False, "There was a problem changing your trade offer.")
        
        return ActionResponse(True)
    
    def changeBankOffer(self, user, resourceDict):
        p = self.board.getPlayer(user)
        if p == None: 
            return ActionResponse(False, "You are not a player in this game")
        
        gp = self.board.getCurrentGamePhase()
        tp = self.board.getCurrentTurnPhase()
        if gp is None or tp is None:
            return ActionResponse(False, "Error: The game has not started or is in the incorrect phase.")
        
        if gp.phase != "main" or tp.phase != "trade":
            logging.info("not in the correct phase (currentPhase: %s)" % tp.phase)
            return ActionResponse(False, "There is no trade in progress.")
        
        t = self.board.getCurrentTrade()
        if t is None:
            logging.info("no current trade in progress")
            return ActionResponse(False, "There is no current trade in progress.")
        
        if p.color != t.colorFrom:
            logging.info("not the current player")
            return ActionResponse(False, "You are not the trading player.")
        
        ret = t.changeBankOffer(resourceDict)
        if not ret:
            logging.info("could not change the bank's offer.")
            return ActionResponse(False, "There was a problem changing the bank's offer")
        
        return ActionResponse(True)

    def acceptTradeOffer(self, user, colorTo):
        p = self.board.getPlayer(user)
        if p == None: 
            return ActionResponse(False, "You are not a player in this game")
        
        color = p.color
        if self.board.getCurrentPlayerColor() != color:
            logging.info("not player turn %s." % user)
            return ActionResponse(False, "The current player must accept the trade.")
        
        pTo = self.board.getPlayerByColor(colorTo)
        if pTo is None:
            logging.info("to player does not exist: %s" % colorTo)
            return ActionResponse(False, "The player %s does not exist." % colorTo)
        
        gp = self.board.getCurrentGamePhase()
        tp = self.board.getCurrentTurnPhase()
        if gp is None or tp is None:
            return ActionResponse(False, "Error: The game has not started or is in the incorrect phase.")
        
        if gp.phase != "main" or tp.phase != "trade":
            logging.info("not in the correct phase (currentPhase: %s)" % tp.phase)
            return ActionResponse(False, "There is no trade in progress.")
        
        t = self.board.getCurrentTrade()
        if t is None:
            logging.info("no current trade in progress")
            return ActionResponse(False, "There is no current trade in progress.")
        
        if t.state != "initial":
            logging.info("trade is not in correct state (current state: %s)" % t.state)
            return ActionResponse(False, "Cannot accept the trade right now")
        
        ret = t.acceptOffer(colorTo)
        if not ret:
            logging.info("accept of trade failed")
            return ActionResponse(False, "Trade could not be accepted.")
        
        return ActionResponse(True)
    
    def confirmTradeOffer(self, user):
        p = self.board.getPlayer(user)
        if p == None: 
            return ActionResponse(False, "You are not a player in this game")
        
        gp = self.board.getCurrentGamePhase()
        tp = self.board.getCurrentTurnPhase()
        if gp is None or tp is None:
            return ActionResponse(False, "Error: The game has not started or is in the incorrect phase.")
        
        if gp.phase != "main" or tp.phase != "trade":
            logging.info("not in the correct phase (currentPhase: %s)" % tp.phase)
            return ActionResponse(False, "There is no trade in progress.")
        
        tp = gp.getTurnPhaseByName("build")
        if tp is None:
            logging.info("no building phase found")
            return ActionResponse(False, "You cannot cancel trading now")
        
        t = self.board.getCurrentTrade()
        if t is None:
            logging.info("no current trade in progress")
            return ActionResponse(False, "There is no current trade in progress.")
        
        if t.colorTo != p.color:
            logging.info("this player has not had his trade accepted")
            return ActionResponse(False, "You have not had your trade accepted.")
        
        if t.state != "accepted":
            logging.info("trade is not in correct state (current state: %s)" % t.state)
            return ActionResponse(False, "This trade has not been accepted yet")
        
        if not t.confirmOffer():
            logging.info("offer validation failed")
            return ActionResponse(False, "Could not complete this trade.")
            
        self.board.turnPhase = tp.order
        self.board.currentTradeKey = None
        self.board.put()
        return ActionResponse(True)
    
    def confirmBankOffer(self, user):
        p = self.board.getPlayer(user)
        if p == None: 
            return ActionResponse(False, "You are not a player in this game")
        
        gp = self.board.getCurrentGamePhase()
        tp = self.board.getCurrentTurnPhase()
        if gp is None or tp is None:
            return ActionResponse(False, "Error: The game has not started or is in the incorrect phase.")
        
        if gp.phase != "main" or tp.phase != "trade":
            logging.info("not in the correct phase (currentPhase: %s)" % tp.phase)
            return ActionResponse(False, "There is no trade in progress.")
        
        tp = gp.getTurnPhaseByName("build")
        if tp is None:
            logging.info("no building phase found")
            return ActionResponse(False, "You cannot cancel trading now")
        
        t = self.board.getCurrentTrade()
        if t is None:
            logging.info("no current trade in progress")
            return ActionResponse(False, "There is no current trade in progress.")
        
        if p.color != t.colorFrom:
            logging.info("not the trading player.")
            return ActionResponse(False, "You are not the trading player.")
        
        tradingRules = self.getTradingRules(self.board, p)
        
        #logging.info("processing trading rule combinations...")
        
        found = False
        for (df, dt) in self.recurseThroughTradingRuleCombinations(tradingRules, t.getOfferDictByColor(p.color), t.getBankOfferDict()):
            validFrom = True
            for (r,a) in df.items():
                #logging.info("remaining From %s: %d" % (r,a))
                if a != 0:
                    validFrom = False
                    break
            
            if not validFrom:
                continue
            
            validTo = True
            for (r,a) in dt.items():
                #logging.info("remaining To %s: %d" % (r,a))
                if a != 0:
                    validTo = False
                    break
            
            if validFrom and validTo:
                found = True
                break
            
        #logging.info("done processing trading rule combos.")
        
        if not found:
            logging.info("no trading rule combination allowed the trade")
            return ActionResponse(False, "The trade is not allowed.")                
        
        #TODO: rules for bank trades: 4:1 always
        #TODO: port rules
        
        if not t.confirmBankOffer():
            logging.info("offer validation failed")
            return ActionResponse(False, "Could not complete this trade.")
            
        self.board.turnPhase = tp.order
        self.board.currentTradeKey = None
        self.board.put()
        return ActionResponse(True)
     
    def recurseThroughTradingRuleCombinations(self, rules, resource_dict_from, resource_dict_to):
        for rule in rules:
            for (df,dt) in rule.matches(resource_dict_from, resource_dict_to):
                # maybe applying the rule once will work?
                yield (df,dt)
                
                # if not, keep going through all other combinations
                for (df2, dt2) in self.recurseThroughTradingRuleCombinations(rules, df, dt):
                    yield (df2, dt2)
                

    def getTradingRules(self, board, player):
        rules = self.board.getDefaultTradingRules()
        
        devs = self.board.getDevelopmentsByColorAndLocation(player.color, "vertex")
        for d in devs:
            v = d.parent()
            ports = v.getPorts()
            for p in ports:
                rules.extend(p.getTradingRules())
        
        return rules
        
        

    def getCurrentTrade(self):
        return self.board.getCurrentTrade()