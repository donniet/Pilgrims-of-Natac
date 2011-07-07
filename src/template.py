import random
import model
import datetime



       
class BoardTemplate(object):
    
    boardTemplate = dict(
        hexes = [
            {"x":0, "y":2},
            {"x":3, "y":1},
            {"x":6, "y":0},
            {"x":9, "y":1},
            {"x":12, "y":2},
            {"x":12, "y":4},
            {"x":12, "y":6},
            {"x":9, "y":7},
            {"x":6, "y":8},
            {"x":3, "y":7},
            {"x":0, "y":6},
            {"x":0, "y":4},
            
            
            {"x":3, "y":3},
            {"x":6, "y":2},
            {"x":9, "y":3},
            {"x":9, "y":5},
            {"x":6, "y":6},
            {"x":3, "y":5},
            
            {"x":6, "y":4},
        ]
    )
    hexValues = [5, 2, 6, 3, 8, 10, 9, 12, 11, 4, 8, 10, 9, 4, 5, 6, 3, 11]
    hexTypes = ["mountains", "mountains", "mountains", 
                "hills", "hills", "hills", 
                "pasture", "pasture", "pasture", "pasture", 
                "fields", "fields", "fields", "fields",
                "forest", "forest", "forest", "forest",
                "desert"]
    ports = [(2,1,"ore"), (2,1,"brick"), (2,1,"wool"), (2,1,"wheat"), (2,1,"wood"), (3,1), (3,1), (3,1), (3,1)]
    portLocations = [(10,1),(12,1),
                     (15,2),(16,3),
                     (16,5),(15,6),
                     (13,8),(12,9),
                     (9,10),(7,10),
                     (4,9), (3,8),
                     (1,6), (0,5),
                     (0,3), (1,2),
                     (4,1), (6,1)]
    resources = ["ore", "brick", "wool", "wheat", "wood"]
    hexProduces = ["mountains", "hills", "pasture", "fields", "forest"]
    colors = ["red", "blue", "green", "orange", "white", "brown"]
    minimumPlayers = 2
    #set to 5 for testing
    pointsNeededToWin = 10
    
    gamePhases = [
        ("joining", []), 
        ("buildFirstSettlement", ["buildSettlement", "buildRoad"]), 
        ("buildSecondSettlement", ["buildSettlement", "buildRoad"]), 
        ("main", ["rollDice", "discard", "moveRobber", "stealRandomResource", "trade",  "playCard", "build"]), 
        ("complete", [])
    ]
    developments = [
        {"location":"vertex", "name":"settlement", "playerStart":5, "points":1, "cost":{"brick":1, "wool":1, "wheat":1, "wood":1}},
        {"location":"vertex", "name":"city", "playerStart":4, "points":2, "cost":{"ore":3, "wheat":2}},
        {"location":"edge", "name":"road", "playerStart":15, "points":0, "cost":{"brick":1, "wood":1}},
        {"location":"hex", "name":"robber", "playerStart":0, "points":0, "cost":dict()},
    ]
    dice = [6,6]
    
    def __init__(self):
        
        random.shuffle(self.hexTypes)
        random.shuffle(self.ports)
        
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
        board.pointsNeededToWin = self.pointsNeededToWin
        
        board.put()
        
        
        for i in xrange(len(self.ports)):
            pd = self.ports[i]
            for j in [2*i, 2*i+1]:
                p = model.Port(parent=board, x=self.portLocations[j][0], y=self.portLocations[j][1], order=j)
                p.put()
                
                if len(pd) > 2:
                    rule = model.TradingRule(parent=p, name="%s port" % pd[2])
                    rule.put()
                    
                    fromMatch = model.TradeMatch(parent=rule, any=False, resource=pd[2], count=pd[0], to=False)
                    fromMatch.put()
                    toMatch = model.TradeMatch(parent=rule, any=True, count=pd[1], to=True)
                    toMatch.put()
                else:
                    rule = model.TradingRule(parent=p, name="general port")
                    rule.put()
                    
                    fromMatch = model.TradeMatch(parent=rule, any=True, count=pd[0], to=False)
                    fromMatch.put()
                    toMatch = model.TradeMatch(parent=rule, any=True, count=pd[1], to=True)
                    toMatch.put()
        
        fourForOneRule = model.TradingRule(parent=board, name="4 for 1", default=True)
        fourForOneRule.put();
        
        fourMatch = model.TradeMatch(parent=fourForOneRule, any=True, count=4, to=False)
        fourMatch.put()
        
        oneMatch = model.TradeMatch(parent=fourForOneRule, any=True, count=1, to=True)
        oneMatch.put()
        
        for d in self.developments:
            dt = model.DevelopmentType(parent=board, location=d["location"], name=d["name"], points=d["points"], playerStart=d["playerStart"])
            dt.put()
            for (r, a) in d["cost"].items():
                dtc = model.Cost(parent=dt, resource=r, amount=a)
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
                {"x":h.x+1, "y":h.y+0},
                {"x":h.x+3, "y":h.y+0},
                {"x":h.x+4, "y":h.y+1},
                {"x":h.x+3, "y":h.y+2},
                {"x":h.x+1, "y":h.y+2},
                {"x":h.x+0, "y":h.y+1},
            ]
            # push the first edge
            edges.append({
                "hex":h, 
                "x1":hc[0]["x"], 
                "y1":hc[0]["y"], 
                "x2":hc[5]["x"], 
                "y2":hc[5]["y"]
            })
            
            for i in range(len(hc)):
                if(i > 0):
                    edges.append({
                        "hex":h, 
                        "x1":hc[i]["x"], 
                        "y1":hc[i]["y"], 
                        "x2":hc[i-1]["x"], 
                        "y2":hc[i-1]["y"]
                    })
                vertex.append({
                    "hex":h, 
                    "x":hc[i]["x"], 
                    "y":hc[i]["y"]
                })
            
        for v in vertex:
            if found.get("%(x)d-%(y)d" % v, None) == None:
                vert = model.Vertex(parent=board, x=v["x"], y=v["y"])
                vert.put()
                found["%(x)d-%(y)d" % v] = True
        
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