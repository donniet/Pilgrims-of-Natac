import random
import uuid
import logging
from django.utils import simplejson as json
import model
import datetime
from google.appengine.api import channel
import string

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
    
    def __init__(self):
        
        random.shuffle(self.hexTypes)
        
    def instantiateModel(self, gameKey, owner):
        board = model.Board()
        board.gameKey = gameKey
        board.dateTimeStarted = datetime.datetime.now()
        board.resources = self.resources
        board.playerColors = self.colors
        board.owner = owner
        board.put()
        
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
    colors = ["red", "blue", "green", "orange", "white", "brown"]
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
        
    def joinUser(self, user):
        #all joined users must be registered
        self.registerUser(user)
        
        p = self.board.getPlayer(user)
        
        if p:
            return p.color
        
        cols = set(self.board.playerColors)
        players = self.board.getPlayers()
        
        if len(players) >= len(cols):
            return None
        
        for p in players:
            if p.user == user:
                #HACK: this is ugly
                return p.color
            else:
                cols.remove(p.color)
            
        color = cols.pop()
            
        self.board.addPlayer(color, user)
        return color
    def sendMessageAll(self, message):
        for user in self.users:
            channel.send_message(self.gamekey + user.user_id(), json.dumps(message))
    def processAction(self, action, data, user):
        if action == "reset":
            return self.resetBoardAction()
        if action == "placeSettlement":
            return self.placeSettlement(data["x"], data["y"], user)
        if action == "placeCity":
            return self.placeCity(data["x"], data["y"], user)
        if action == "placeRoad":
            return self.placeRoad(user, **data)
        return False
    def get_game_key(self):
        return self.gamekey
    def resetBoardAction(self):
        del self.board
        bt = BoardTemplate()        
        self.gamekey = "A"
        self.board = bt.instantiateModel(self.gameKey)
        self.onReset.fire()
        return True
    def get_board(self):
        return self.board
    def get_players(self):
        return self.board.getPlayers()
    def placeRoad(self, user, x1, y1, x2, y2):
        #TODO: does the player have enough resources to buy a road?
        #TODO: does the player have any roads left? 
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
            return False
        
        e.addDevelopment(color, "road")
        self.sendMessageAll({'action': 'placeRoad', 'x1':x1, 'y1':y1, 'x2':x2, 'y2':y2, 'color':color})
        return True
            
    def placeSettlement(self, x, y, user):
        #logging.info("placeSettlement: " + data)
        #TODO: does this vertex have a road of the right color running into it?
        #TODO: does the player have enough resources to buy a settlement?
        #TODO: does the player have any settlements left? 
        #TODO: are we in the placement phase of the game?
        
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
            return False
                
        v.addDevelopment(color, "settlement")
        self.sendMessageAll({'action': 'placeSettlement', 'x':x, 'y':y, 'color':color})
        return True
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
                self.sendMessageAll({'action': 'placeCity', 'x':x, 'y':y, 'color':color})
                return True
            
        return False
    
    

