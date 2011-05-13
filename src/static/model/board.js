

/*
if the width of one hex is w imagine a grid with 
vertical lines every 0.5w and horizontal lines every 
sqrt(3)/2 w.  Each intersection of those lines is an 
x,y coordinate
*/

function DictList() {
    this.dict = new Object()
}
DictList.prototype.add = function(key, object) {
    if(typeof this.dict[key] == "undefined") this.dict[key] = new Array();

    this.dict[key].push(object);
}
DictList.prototype.get = function(key) {
    arr = this.dict[key];
    if(typeof this.dict[key] == "undefined") return new Array();

    return this.dict[key];
}



function Action(displayText, actionName, requiredData) {
	this.displayText = displayText;
	this.actionName = actionName;
	this.requiredData = typeof requiredData == "undefined" ? null : requiredData;
}
Action.RequiredData = {
	"HEX":"HEX",
	"EDGE":"EDGE",
	"VERTEX":"VERTEX"
};
//TODO: send this information from the server
Action.make = function(str) {
	switch(str) {
	case "startGame": return new Action("Start Game", str);
	case "placeSettlement": return new Action("Place Settlement", str, Action.RequiredData.VERTEX);
	case "placeRoad": return new Action("Place Road", str, Action.RequiredData.EDGE);
	case "placeCity": return new Action("Place City", str, Action.RequiredData.VERTEX);
	case "rollDice": return new Action("Roll Dice", str);
	case "endTurn": return new Action("End Turn", str);
	case "quit": return new Action("Quit", str);
	// replace default case with exception
	default: return new Action(str, str);
	}
}




function Board(token, services) {
    this.modelElements_ = new Object();
    this.players_ = new Array();
    this.userToken_ = token;
    
    this.boardUrl_ = services["board-json-url"];
	this.actionUrl_ = services["action-json-url"];
	this.reservationUrl_ = services["reservation-json-url"];

    this.hex_ = new Array();
    this.edge_ = new Array();
    this.vertex_ = new Array();
    this.dice_ = new Array();
    this.availableActions_ = new Array();
    this.log_ = new Array();
    
    this.player_ = new Player(services);
}
Board.prototype.getPlayers = function() { return this.players_; }
Board.prototype.getDice = function() { return this.dice_; }
Board.prototype.getAvailableActions = function() { return this.availableActions_; };
Board.prototype.getCurrentPlayer = function() { return this.player_; }

Board.prototype.sendAction = function(action, data) {	
	var responder = new Object();
	
	var actionName = action;
	if(typeof action != "string")
		actionName = action.actionName;
	
	var dat = null;
	var self = this;
	
	if(data && typeof data.toJSON == "function") { dat = data.toJSON(); }
	
	jQuery.postJSON(this.actionUrl_, {action:actionName, data:dat}, function(ret) {
		// action responses are always success, message pairs
		if(ret && ret.success) 
			Event.fire(responder, "load", arguments);
		
		else Event.fire(self, "error", [ret.message]);
    });
	
	return responder;
}

Board.prototype.createChannel = function() {
	this.channel_ = new goog.appengine.Channel(this.userToken_);
	this.socket_ = this.channel_.open();
	
	var self = this;
	this.socket_.onopen = function() {
		self.connected_ = true;
		
		Event.fire(self, "socketOpen", []);
	}
	this.socket_.onmessage = function(msg) {
		self.handleSocketMessage(msg);
	}
	this.socket_.onerror = function() {
		self.handleSocketError.apply(self, arguments);
	}
	this.socket_.onclose = function() {
		self.handleSocketClose.apply(self, arguments);
	}
}

Board.prototype.handleSocketError = function() {
	Event.fire(this, "error", ["There was an error connecting to the server.  Please refresh your browser window.", true]);
}
Board.prototype.handleSocketClose = function() {
	self.connected_ = false;
	
	Event.fire(self, "socketClose", []);
	Event.fire(this, "error", ["Communication with the server has been lost.  Please refresh your browser window.", true]);
}

Board.prototype.handleSocketMessage = function(msg) {
	
	message = JSON.parse(msg.data);
	
    switch(message["action"]) {
    case "placeSettlement":
        this.placeVertexDevelopment(message["data"]["x"], message["data"]["y"], "settlement", message["color"]);
        Event.fire(this, "placeVertexDevelopment", [message["data"]["x"], message["data"]["y"], "settlement", message["color"]]);
        break;
    case "placeCity":
    	this.placeVertexDevelopment(message["data"]["x"], message["data"]["y"], "city", message["color"]);
    	Event.fire(this, "placeVertexDevelopment", [message["data"]["x"], message["data"]["y"], "city", message["color"]]);
        break;
    case "placeRoad":
    	this.placeEdgeDevelopment(message["data"]["x1"], message["data"]["y1"], message["data"]["x2"], message["data"]["y2"], "road", message["color"]);
    	Event.fire(this, "placeEdgeDevelopment", [message["data"]["x1"], message["data"]["y1"], message["data"]["x2"], message["data"]["y2"], "road", message["color"]]);
        break;
    case "diceRolled":
    	//console.log("dice Rolled: " + message["data"][0] + "," + message["data"][1]);
    	this.dice_ = message["data"];
    	Event.fire(this, message["action"], [message["data"]]);
    	break;
    case "updatePlayers":
    	console.log("updatePlayers");
    	this.loadPlayersJSON(message["players"]);
    	break;    	
    case "playerJoinGame":
        throw "Message not yet implemented";
    case "playerLeaveGame":
        throw "Message not yet implemented";
    case "playerStartFirstTurn":
        throw "Message not yet implemented";
    case "playerBuildFirstSettlement":
        throw "Message not yet implemented";
    case "playerBuildFirstRoad":
        throw "Message not yet implemented";
    case "playerStartSecondTurn":
        throw "Message not yet implemented";
    case "playerBuildSecondSettlement":
        throw "Message not yet implemented";
    case "playerBuildSecondRoad":
        throw "Message not yet implemented";
    case "playerStartNormalTurn":
        throw "Message not yet implemented";
    case "log":
    	Event.fire(this, "log", [message]);
    	break;
    case "chat":
    	Event.fire(this, "chat", [message]);
    	break;
    }
    
    this.availableActions_ = new Array();
    for(var i = 0; message["availableActions"] && i < message["availableActions"].length; i++) {
    	var str =  message["availableActions"][i];
    	this.availableActions_.push(Action.make(str));
    }
    Event.fire(this, "actionschanged", [this.availableActions_]);
    
    //console.log("available actions: " + this.availableActions_.length);
    //TODO: only update player when needed or when asked
    this.player_.load();
}

Board.prototype.reserve = function(reserveEmail) {
	var ret = new Object();
	
	jQuery.postJSON(this.reservationUrl_, {reservedFor:reserveEmail}, function(data, xhr) {
		if(data && data.reserved) {
			Event.fire(ret, "reserved", []);
		}
		else {
			Event.fire(ret, "error", []);
		}
	});
	
	return ret;
}
Board.prototype.load = function() {
	var self = this;
	
	var responder = new Object();
	
    jQuery.getJSON(this.boardUrl_, function(data) {
        self.loadJSON(data);
        self.createChannel();
    	
        self.dice_ = data.diceValues;
        
        Event.fire(self, "load", [this]);
        Event.fire(self, "diceRolled", [self.dice_]);
    });
    
    return responder;
}

Board.prototype.loadPlayersJSON = function(obj) {
	this.players_ = new Array();

	for(var i = 0; obj && i < obj.length; i++) {
		var p = new Player();
		p.loadJSON(obj[i]);
		this.players_.push(p);
	}
	
    Event.fire(this, "loadPlayers", [this.getPlayers()]);
}

Board.prototype.loadJSON = function(obj) {
    this.hex_ = new Array();
    this.edge_ = new Array();
    this.vertex_ = new Array();
    this.log_ = new Array();

    var hexes = obj["hexes"];
    var hexdict = new Object();
    
    this.loadPlayersJSON(obj["players"]);

    for(var i = 0; hexes && i < hexes.length; i++) {
		var h = new Hex(hexes[i]["x"], hexes[i]["y"], hexes[i]["type"], hexes[i]["value"]);
        this.addHex(h);
		hexdict[hexes[i]["id"]] = h;
        //console.log("added hex: " + hexes[i]["id"] + ":" + hexes[i]["type"]);
    }
    var edges = obj["edges"];
    for(var i = 0; edges && i < edges.length; i++) {
        var e = new Edge(edges[i]["x1"], edges[i]["y1"], edges[i]["x2"], edges[i]["y2"]);

		for(var j = 0; j < edges[i]["developments"].length; j++) {
			d = edges[i]["developments"][j];
			//console.log("edge development: " + d["color"]);
			e.addDevelopment({
			    model: d["type"],
			    player: "player-" + d["color"]
			});
		}
		this.addEdge(e);
    }
    var vertex = obj["vertex"];
    for(var i = 0; vertex && i < vertex.length; i++) {
		var v = new Vertex(vertex[i]["x"], vertex[i]["y"]);

		for(var j = 0; j < vertex[i]["developments"].length; j++) {
			d = vertex[i]["developments"][j];
			//console.log("development(" + vertex[i]["x"]+","+vertex[i]["y"]+")={"+d["type"]+","+d["color"]+"}");
			v.addDevelopment({
			model: d["type"],
			player: "player-" + d["color"]
			});
		}
		this.addVertex(v);
    }
    var log = obj["log"];
    for(var i = 0; log && i < log.length; i++) {
    	this.log_.push(log[i]);
    }
    this.createAdjecencyMap()
}
Board.prototype.getLog = function() { return this.log_; }
Board.prototype.setModelElement = function (modelName, svgEl, centerPosition) {
    this.modelElements_[modelName] = {
        "svgElement": svgEl,
        "centerPosition": centerPosition
    };
}
Board.prototype.placeVertexDevelopment = function(x, y, model, color) {
    for(var i = 0; i < this.vertex_.length; i++) {
        v = this.vertex_[i];
        if(v.position_.x == x && v.position_.y == y) {
            v.vertexDevelopments_ = [];
            var dev = {
				"model": model,
				"player": "player-" + color
			}
            v.addDevelopment(dev);
            Event.fire(this, "placeVertexDevelopment", [v, dev]);
			return true;
        }
    }
	return false;
}
Board.prototype.placeEdgeDevelopment = function(x1, y1, x2, y2, model, color) {
    for(var i = 0; i < this.edge_.length; i++) {
        e = this.edge_[i];
		if(e.first_.x == x1 && e.first_.y == y1 && e.second_.x == x2 && e.second_.y == y2) {
			e.edgeDevelopments_ = [];
			var dev = {
				"model": model,
				"player": "player-" + color
			};
	        e.addDevelopment(dev);
            Event.fire(this, "placeEdgeDevelopment", [e, dev]);
			return true;
		}
    }
	return false;
}

Board.prototype.hexCoords = function (nx, ny) {
    return [
      {x:nx + 1, y:ny},
      {x:nx + 3, y:ny},
      {x:nx + 4, y:ny + 1},
      {x:nx + 3, y:ny + 2},
      {x:nx + 1, y:ny + 2},
      {x:nx + 0, y:ny + 1}
   ];
}

Board.prototype.addHex = function(hex) {
    this.hex_.push(hex);
    hex.board_ = this;
    return hex;
}
Board.prototype.addVertex = function(vertex) {
    this.vertex_.push(vertex);
    vertex.board_ = this;
    return vertex;
}
Board.prototype.addEdge = function(edge) {
    this.edge_.push(edge);
    edge.board_ = this;
    return edge;
}


/* TODO: this function can almost certainly be optimized... */
Board.prototype.createAdjecencyMap = function () {
    // first create dictionaries of all pieces by their x,y coords
    var hexdict = new DictList()
    var edgedict = new DictList()
    var vertdict = new DictList()

    var poskey = function(pos) { return pos.x + "," + pos.y; };

    for(var i = 0; i < this.hex_.length; i++) {
        var h = this.hex_[i];
        var hexcoords = this.hexCoords(h.position_.x, h.position_.y);
		for(var j = 0; j < hexcoords.length; j++) {
            hexdict.add(poskey(hexcoords[j]), h);
        }
    }
    for(var i = 0; i < this.edge_.length; i++) {
        var e = this.edge_[i];
		edgedict.add(poskey(e.first_), e);
		edgedict.add(poskey(e.second_), e);
    }
    for(var i = 0; i < this.vertex_.length; i++) {
		var v = this.vertex_[i];
		vertdict.add(poskey(v.position_), v);
    }

	/* HEXES */
    for(var i = 0; i < this.hex_.length; i++) {
        var h = this.hex_[i];
        var hexcoords = this.hexCoords(h.position_.x, h.position_.y);
		var hexesAdded = new Object();
		var edgesAdded = new Object();
		var vertsAdded = new Object();
		hexesAdded[poskey(h.position_)] = true;

        for(var j = 0; j < hexcoords.length; j++) {
	    	var key = poskey(hexcoords[j]);
			var hd = hexdict.get(key);
			for(k = 0; k < hd.length; k++) {
				if(typeof hexesAdded[poskey(hd[k].position_)] == "undefined") {
					h.adjecentHex_.push(hd[k]);
					hexesAdded[poskey(hd[k].position_)] = true;
				}
			}

			var ed = edgedict.get(key);			
			for(k = 0; k < ed.length; k++) {
				if(typeof edgesAdded[poskey(ed[k].first_)+","+poskey(ed[k].second_)] == "undefined") {
					h.edge_.push(ed[k]);
					ed[k].hex_.push(h);
					edgesAdded[poskey(ed[k].first_)+","+poskey(ed[k].second_)] = true;
				}
			}

			var vd = vertdict.get(key);
			for(k = 0; k < vd.length; k++) {
				if(typeof vertsAdded[poskey(vd[k].position_)] == "undefined") {
					h.vertex_.push(vd[k]);
					vd[k].hex_.push(h);
					vertsAdded[poskey(vd[k].position_)] = true;
				}
			}
        }
    }

	/* VERTS */
    for(var i = 0; i < this.vertex_.length; i++) {
        var v = this.vertex_[i];
		var edgesAdded = new Object();
		var vertsAdded = new Object();

		var key = poskey(v.position_);
		vertsAdded[poskey(v.position_)] = true;

		var ed = edgedict.get(key);			
		for(k = 0; k < ed.length; k++) {
			if(typeof edgesAdded[poskey(ed[k].first_)+","+poskey(ed[k].second_)] == "undefined") {
				v.edge_.push(ed[k]);
				ed[k].vertex_.push(v);
				edgesAdded[poskey(ed[k].first_)+","+poskey(ed[k].second_)] = true;
								
				if(typeof vertsAdded[poskey(ed[k].first_)] == "undefined") {
					vd = vertdict.get(poskey(ed[k].first_))
					if(vd.length > 0) {
						v.adjecentVertex_.push(vd[0]);
						vertsAdded[poskey(vd[0].position_)] = true;
					}
				}
				if(typeof vertsAdded[poskey(ed[k].second_)] == "undefined") {
					vd = vertdict.get(poskey(ed[k].second_))
					if(vd.length > 0) {
						v.adjecentVertex_.push(vd[0]);
						vertsAdded[poskey(vd[0].position_)] = true;
					}
				}
			}
		}
    }

	/* EDGES */
	for(var i = 0; i < this.edge_.length; i++) {
		var e = this.edge_[i];
		var edgesAdded = new Object();

		// all we have to worry about are adj edges
		var ed = edgedict.get(poskey(e.first_));

		for(var k = 0; k < ed.length; k++) {
			if(typeof edgesAdded[poskey(ed[k].first_)+","+poskey(ed[k].second_)] == "undefined") {
				e.adjecentEdge_.push(ed[k]);
				edgesAdded[poskey(ed[k].first_)+","+poskey(ed[k].second_)] = true;
			}
		}

		ed = edgedict.get(poskey(e.second_));

		for(var k = 0; k < ed.length; k++) {
			if(typeof edgesAdded[poskey(ed[k].first_)+","+poskey(ed[k].second_)] == "undefined") {
				e.adjecentEdge_.push(ed[k]);
				edgesAdded[poskey(ed[k].first_)+","+poskey(ed[k].second_)] = true;
			}
		}
	}
}


function Hex(x, y, hexType, value) {
    /* Hex vertexes will be: */
    this.position_ = { "x": typeof x == "undefined" ? 0 : x, "y": typeof y == "undefined" ? 0 : y };
    this.hexType_ = typeof hexType == "undefined" ? "unknown" : hexType;
    this.value_ = typeof value == "undefined" ? 0 : value;
    this.edge_ = new Array(); /* always 6 */
    this.vertex_ = new Array(); /* always 6 */
    this.adjecentHex_ = new Array(); /* between 1 and 6 */
    this.hexDevelopments_ = new Array(); /* robber or merchant */
}
Hex.prototype.toJSON = function() {
	return '{"x":'+this.position_.x+',"y":'+this.position_.y+'}';
}

function Edge(x1, y1, x2, y2) {
    /* ASSERT(first.x < second.x) */
    this.first_ = { "x": typeof x1 == "undefined" ? 0 : x1, "y": typeof y1 == "undefined" ? 0 : y1 };
    this.second_ = { "x": typeof x2 == "undefined" ? 0 : x2, "y": typeof y2 == "undefined" ? 0 : y2 };
    this.hex_ = new Array(); /* between 1 and 2 */
    this.vertex_ = new Array(); /* always 2 */
    this.adjecentEdge_ = new Array(); /* 2 or 3 */
    this.edgeDevelopments_ = new Array(); /* road */
}
Edge.prototype.toJSON = function() {
	return '{"x1":'+this.first_.x+',"y1":'+this.first_.y+',"x2":'+this.second_.x+',"y2":'+this.second_.y+'}';
}
function Vertex(x, y) {
    this.position_ = { "x": typeof x == "undefined" ? 0 : x, "y": typeof y == "undefined" ? 0 : y };
    this.hex_ = new Array(); /* between 1 and 3 */
    this.edge_ = new Array(); /* between 2 and 3 */
    this.adjecentVertex_ = new Array();
    this.vertexDevelopments_ = new Array(); /* city, settlement, city wall, knight, etc. */
}
Vertex.prototype.toJSON = function() {
	return '{"x":'+this.position_.x+',"y":'+this.position_.y+'}';
}


Vertex.prototype.addDevelopment = function (vertexDevelopment) {
    this.vertexDevelopments_.push(vertexDevelopment);
}
Edge.prototype.addDevelopment = function (development) {
    this.edgeDevelopments_.push(development);
}




/* Now executed in Python */
Board.prototype.createVertexAndEdgesFromHex = function () {
    var edges = new Array();
    var vertex = new Array();
    for (var i = 0; i < this.hex_.length; i++) {
        var h = this.hex_[i];

        var hc = [
            { x: h.position_.x + 1, y: h.position_.y + 0 },
            { x: h.position_.x + 3, y: h.position_.y + 0 },
            { x: h.position_.x + 4, y: h.position_.y + 1 },
            { x: h.position_.x + 3, y: h.position_.y + 2 },
            { x: h.position_.x + 1, y: h.position_.y + 2 },
            { x: h.position_.x + 0, y: h.position_.y + 1 }
        ];

        // push the first edge
        edges.push({ points: [{ x: hc[0].x, y: hc[0].y }, { x: hc[5].x, y: hc[5].y}], hex: h });

        for (var j = 0; j < hc.length; j++) {
            var p1 = hc[j];
            if (j > 0) {
                var p2 = hc[j - 1];
                edges.push({ points: [{ x: p1.x, y: p1.y }, { x: p2.x, y: p2.y}], hex: h });
            }
            vertex.push({ x: p1.x, y: p1.y, hex: h });
        }
    }
    vertex.sort(function (a, b) {
        return a.x == b.x ? a.y < b.y : a.x < b.x;
    });

    var n = null;
    for (var i = 0; i < vertex.length; i++) {
        var v = vertex[i];
        if (n == null || n.position_.x != v.x || n.position_.y != v.y) {
            n = new Vertex(v.x, v.y);
            n.hex_.push(v.hex);
            this.addVertex(n);
        }
        else {
            n.hex_.push(v.hex);
        }
    }

    for (var i = 0; i < edges.length; i++) {
        var e = edges[i];
        if (e.points[0].x > e.points[1].x || e.points[0].x == e.points[1].x && e.points[0].y > e.points[0].y) {
            var p0 = e.points[0];
            var p1 = e.points[1];
            e.points[0] = p1;
            e.points[1] = p0;
        }
    }

    edges.sort(function (a, b) {
        if (a.points[0].x == b.points[0].x) {
            if (a.points[0].y == b.points[0].y) {
                if (a.points[1].x == b.points[1].x) {
                    return a.points[1].y < b.points[1].y;
                }
                else {
                    return a.points[1].x < b.points[1].x;
                }
            }
            else {
                return a.points[0].y < b.points[0].y;
            }
        }
        else {
            return a.points[0].x < b.points[0].x;
        }
    });

    var n = null;
    for (var i = 0; i < edges.length; i++) {
        var e = edges[i];
        if (n == null || n.first_.x != e.points[0].x || n.first_.y != e.points[0].y ||
            n.second_.x != e.points[1].x || n.second_.y != e.points[1].y) {
            n = new Edge(e.points[0].x, e.points[0].y, e.points[1].x, e.points[1].y);
            n.hex_.push(e.hex);
            this.addEdge(n);
        }
        else {
            n.hex_.push(e.hex);
        }
    }
}
