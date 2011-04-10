
import random
import uuid
import logging
from django.utils import simplejson as json

'''
class Hex(dict):
    def __init__(self, id, x, y, value, type, developments):
        self["id"] = id
        self["x"] = x
        self["y"] = y
        self["value"] = value
        self["type"] = type
        self["developments"] = developments
    def __hash__(self):
        return (str(self["x"]) + "," + str(self["y"])).__hash__()
        
class Edge(dict):
    def __init__(self, hexid, x1, y1, x2, y2, developments):
        self["hexid"] = hexid
        self["x1"] = x1
        self["y1"] = y1
        self["x2"] = x2
        self["y2"] = y2
        self["developments"] = developments
    def __hash__(self):
        if self["x1"] > self["x2"] or (self["x1"] == self["x2"] and self["y1"] > self["y2"]):
            return (str(self["x2"]) + "," + str(self["y2"]) + "," + str(self["x1"]) + "," str(self["y1"])).__hash__()
        else:
            return (str(self["x1"]) + "," + str(self["y1"]) + "," + str(self["x2"]) + "," str(self["y2"])).__hash__()
''' 

def edge_sort(a,b):
    if a["x1"] == b["x1"]:
        if a["y1"] == b["y1"]:
            if a["x2"] == b["x2"]:
                return a["y2"] < b["y2"]
            else:
                return a["x2"] < b["x2"]
        else:
            return a["y1"] < b["y1"]
    else:
        return a["x1"] < b["x1"]
    
       
class BoardTemplate(object):
    boardTemplate = None
    hexValues = None
    hexTypes = None
    
    def __init__(self):
        self.boardTemplate = dict(
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
        self.hexValues = [5, 2, 6, 3, 8, 10, 9, 12, 11, 4, 8, 10, 9, 4, 5, 6, 3, 11]
        self.hexTypes = ["mountains", "mountains", "mountains", 
                    "hills", "hills", "hills", 
                    "pasture", "pasture", "pasture", "pasture", 
                    "fields", "fields", "fields", "fields",
                    "forest", "forest", "forest", "forest",
                    "desert"]
        random.shuffle(self.hexTypes)
    def instantiate(self):
        board = dict(hexes=[], edges=[], vertex=[])
        vertexMap = dict()
        edgeMap = dict()
        hexMap = dict()
        j = 0
        for i in range(len(self.boardTemplate["hexes"])):
            h = self.boardTemplate["hexes"][i]
                                   
            if(self.hexTypes[i]=="desert"):
                board["hexes"].append(dict(id=i, x=h["x"], y=h["y"], value=0, type=self.hexTypes[i], developments=[]))
            else:
                board["hexes"].append(dict(id=i, x=h["x"], y=h["y"], value=self.hexValues[j], type=self.hexTypes[i], developments=[]))
                j = j + 1
        
        self.createVertexAndEdgesFromHex(board, vertexMap, edgeMap, hexMap)
        
        return {'board':board, 'vertexMap':vertexMap, 'edgeMap':edgeMap, 'hexMap':hexMap}
    #HACK: come back and use sets instead of this funky sorting mechanism
    #TODO: do we have all adjecencies mapped?  Do we need them all mapped?  I think we have Hexes to everything,and edges to hexes, but not edges to vertexes
    def createVertexAndEdgesFromHex(self, board, vertexMap, edgeMap, hexMap):
        edges = []
        vertex = []
        for h in board["hexes"]:
            hc = [
                dict(x=h["x"]+1, y=h["y"]+0),
                dict(x=h["x"]+3, y=h["y"]+0),
                dict(x=h["x"]+4, y=h["y"]+1),
                dict(x=h["x"]+3, y=h["y"]+2),
                dict(x=h["x"]+1, y=h["y"]+2),
                dict(x=h["x"]+0, y=h["y"]+1),
            ]
            # push the first edge
            edges.append(dict(hex=h, x1=hc[0]["x"], y1=hc[0]["y"], x2=hc[5]["x"], y2=hc[5]["y"]))
            
            for i in range(len(hc)):
                if(i > 0):
                    edges.append(dict(hex=h, x1=hc[i]["x"], y1=hc[i]["y"], x2=hc[i-1]["x"], y2=hc[i-1]["y"]))
                vertex.append(dict(hex=h, x=hc[i]["x"], y=hc[i]["y"]))
            
        for v in vertex:
            vstr = "%(x)d,%(y)d" % v
            if vertexMap.get(vstr, None) != None:
                vertexMap[vstr]["hex"].append(v["hex"]["id"])
            else:
                n = dict(hex=[v["hex"]["id"]], x=v["x"], y=v["y"], dev=[])
                board["vertex"].append(n)
                vertexMap[vstr] = n 
                
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
                
        for e in edges:
            estr = "%(x1)d,%(y1)d,%(x2)d,%(y2)d" % e
            
            if edgeMap.get(estr, None) != None:
                edgeMap[estr]["hex"].append(e["hex"]["id"])
            else:
                n = dict(hex=[e["hex"]["id"]], x1=e["x1"], y1=e["y1"], x2=e["x2"], y2=e["y2"], dev=[])
                board["edges"].append(n)
                edgeMap[estr] = n 
        

class EventHook(object):
    def __init__(self):
        self.__handlers = []

    def __iadd__(self, handler):
        self.__handlers.append(handler)
        return self

    def __isub__(self, handler):
        self.__handlers.remove(handler)
        return self

    def fire(self, *args, **keywargs):
        for handler in self.__handlers:
            handler(*args, **keywargs)
        

class GameState(object):
    board = None
    vertexMap = None
    edgeMap = None
    hexMap = None
    colors = ["red", "blue", "green", "orange", "white", "brown"]
    players = []
    log = []
    gamekey = None
    
    #events
    onPlaceSettlement = None
    onPlaceCity = None
    onReset = None
    onRegisterUser = None
    
    def __init__(self):
        bt = BoardTemplate()
        boardinfo = bt.instantiate()
        self.board = boardinfo["board"]
        self.vertexMap = boardinfo["vertexMap"]
        self.edgeMap = boardinfo["edgeMap"]
        self.hexMap = boardinfo["hexMap"]
        
        self.gamekey = "A"
        self.onPlaceSettlement = EventHook()
        self.onReset = EventHook()
        self.onRegisterUser = EventHook()
        self.onPlaceCity = EventHook()
        
    def registerUser(self, user):
        for i in range(len(self.players)):
            if user.user_id() == self.players[i].user_id():
                return self.colors[i]
            
        if len(self.players) < len(self.colors):
            self.players.append(user)
            return self.colors[len(self.players)-1]
        else:
            return None
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
        self.board = bt.instantiate()
        self.onReset.fire()
        return True
    def get_board(self):
        return self.board
    def placeSettlement(self, x, y, user):
        #logging.info("placeSettlement: " + data)
        #TODO: does this vertex have a road of the right color running into it?
        #TODO: is this vertex at least one vertex away from another city or settlement? 
        #TODO: does the player have enough resources to buy a settlement?
        #TODO: does the player have any settlements left? 
           
        color = None
        for i in range(len(self.players)):
            if user.user_id() == self.players[i].user_id():
                color = self.colors[i]
                break;
        
        if color == None:
            return False
        
        vstr = "%(x)d,%(y)d" % {'x':x, 'y':y}
        if self.vertexMap.get(vstr, None) != None:
            v = self.vertexMap[vstr]
            if len(v["dev"]) > 0:
                return False
            else:
                v["dev"].append({'color':color, 'type':'settlement'})
                self.onPlaceSettlement.fire(x=x, y=y, color=color)
                return True               
        
        return False
    def placeCity(self, x, y, user):
        #logging.info("placeSettlement: " + data)
        #TODO: does the player have enough resources to buy a city?
        #TODO: does the player have any cities left?
        
        color = None
        for i in range(len(self.players)):
            if user.user_id() == self.players[i].user_id():
                color = self.colors[i]
                break;
        
        if color == None:
            return False
        
        vstr = "%(x)d,%(y)d" % {'x':x, 'y':y}
        if self.vertexMap.get(vstr, None) != None:
            v = self.vertexMap[vstr]
            if  len(v["dev"]) == 0 or v["dev"][0]["type"] != "settlement" or v["dev"][0]["color"] != color:
                return False
            else:
                v["dev"][0]["type"] = "city"
                self.onPlaceCity.fire(x=x, y=y, color=color)
                return True
                            
        
        return False
    
