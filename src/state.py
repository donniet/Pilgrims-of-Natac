
import random
import uuid
import logging
from django.utils import simplejson as json
import model
import datetime

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
        
    def instantiateModel(self, gameKey):
        board = model.Board()
        board.gameKey = gameKey
        board.dateTimeStarted = datetime.datetime.now()
        board.resources = self.resources
        board.playerColors = self.colors
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
    
        

class GameState(object):
    board = None
    colors = ["red", "blue", "green", "orange", "white", "brown"]
    log = []
    gamekey = None
    
    #events
    onPlaceSettlement = EventHook()
    onPlaceCity = EventHook()
    onReset = EventHook()
    onRegisterUser = EventHook()
    
    def __init__(self):
        bt = BoardTemplate()
        
        self.gamekey = "A"
        self.board = bt.instantiateModel(self.gamekey)
        
    def registerUser(self, user):
        p = self.board.getPlayer(user)
        
        if p:
            return p.color
        
        cols = set(self.board.playerColors)
        players = self.board.getPlayers()
        
        if len(players) >= len(cols):
            return False
        
        for p in players:
            cols.remove(p.color)
            
        color = cols.pop()
            
        self.board.addPlayer(color, user)
        return color
    def processAction(self, action, data, user):
        if action == "reset":
            return self.resetBoardAction()
        if action == "placeSettlement":
            return self.placeSettlement(data["x"], data["y"], user)
        if action == "placeCity":
            return self.placeCity(data["x"], data["y"], user)
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
    def placeSettlement(self, x, y, user):
        #logging.info("placeSettlement: " + data)
        #TODO: does this vertex have a road of the right color running into it?
        #TODO: is this vertex at least one vertex away from another city or settlement? 
        #TODO: does the player have enough resources to buy a settlement?
        #TODO: does the player have any settlements left? 
        
        p = self.board.getPlayer(user)
        if p == None: 
            logging.info("player not found %s." % (user,))
            return False
           
        color = p.color
        
        v = self.board.getVertex(x, y)
        if v == None: 
            logging.info("vertex %d,%d not found." % (x,y) )
            return False
        
        devs = v.getDevelopments()
        if devs and len(devs) > 0: 
            return False
        
        v.addDevelopment(color, "settlement")
        self.onPlaceSettlement.fire(x=x, y=y, color=color)
        return True
    def placeCity(self, x, y, user):
        #logging.info("placeSettlement: " + data)
        #TODO: does the player have enough resources to buy a city?
        #TODO: does the player have any cities left?
        
        
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
                self.onPlaceCity.fire(x=x, y=y, color=color)
                return True
            
        return False
    
    
