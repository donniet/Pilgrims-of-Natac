/*
 * @author Donnie
 * @requires board.js
 */


function BoardController(userToken, boardEl, actionsEl, services, models) {
	this.channel_ = null;
	this.socket_ = null;
	this.connected_ = false;
	
	this.userToken_ = userToken;
	this.boardUrl_ = services["board-json-url"];
	this.playerUrl_ = services["player-json-url"];
	this.actionUrl_ = services["action-json-url"];
	this.reservationUrl_ = services["reservation-json-url"];
	this.boardEl_ = boardEl;
	this.actionsEl_ = actionsEl;
	
	this.board_ = new Board();
	this.player_ = new Player();
	this.dice_ = new Array();
	
	this.availableActions_ = new Array();
	this.currentAction_ = null;
	
	this.setModels(models);
}
BoardController.prototype.load = function() {
	this.loadBoard();
	this.createChannel();
}
BoardController.prototype.setModels = function(models) {
	for(var i = 0; models && i < models.length; i++) {
		m = models[i];
		this.board_.setModelElement(m["type"], m["element"], m["center"]);
	}
}
BoardController.prototype.getPlayer = function() {
	return this.player_;
}

BoardController.prototype.reserve = function(reserveEmail) {
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


BoardController.prototype.loadBoard = function() {
	var self = this;
	
	var responder = new Object();
	
    jQuery.getJSON(this.boardUrl_, function(data) {
        self.board_.loadJSON(data);
        svg = self.boardEl_;
        while(svg.firstChild) svg.removeChild(svg.firstChild);
        self.board_.renderBoard(svg);
        
        self.dice_ = data.diceValues;
        
        Event.fire(responder, "loadBoard", []);
        Event.fire(self, "diceRolled", [self.dice_]);
    });
    
    return responder;
}

BoardController.prototype.createChannel = function() {
	this.channel_ = new goog.appengine.Channel(this.userToken_);
	this.socket_ = this.channel_.open();
	
	var self = this;
	this.socket_.onopen = function() {
		self.connected_ = true;
		
		Event.fire(self, "socket-open", []);
	}
	this.socket_.onmessage = function(msg) {
		self.handleSocketMessage(msg);
	}
	this.socket_.onerror = function() {
		self.handleSocketError.apply(self, arguments);
	}
	this.socket_.onclose = function() {
		self.connected_ = false;
		
		Event.fire(self, "socket-close", []);
	}
}

BoardController.prototype.handleSocketMessage = function(msg) {
	message = JSON.parse(msg.data);
    //TODO: get real json to work
    //message = eval(msg);
	
    switch(message["action"]) {
    case "placeSettlement":
        this.board_.placeSettlement(message["data"]["x"], message["data"]["y"], message["color"]);
        Event.fire(this, message["action"], [message["color"], message["data"]]);
        break;
    case "placeCity":
    	this.board_.placeCity(message["data"]["x"], message["data"]["y"], message["color"]);
    	Event.fire(this, message["action"], [message["color"], message["data"]]);
        break;
    case "placeRoad":
    	this.board_.placeRoad(message["data"]["x1"], message["data"]["y1"], message["data"]["x2"], message["data"]["y2"], message["color"]);
    	Event.fire(this, message["action"], [message["color"], message["data"]]);
        break;
    case "diceRolled":
    	console.log("dice Rolled: " + message["data"][0] + "," + message["data"][1]);
    	this.dice_ = message["data"];
    	Event.fire(this, message["action"], [message["data"]]);
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
    }
    
    this.availableActions_ = message["availableActions"];
    console.log("available actions: " + this.availableActions_.length);
    //TODO: only update player when needed or when asked
    this.updatePlayer();
    this.loadActions();
}


BoardController.prototype.updatePlayer = function() {
	var responder = new Object();
	
	var self = this;
	
	jQuery.getJSON(this.playerUrl_, function(data) {
		if(! data || data["error"]) {
			Event.fire(responder, "error", []);
		}
		else {
        	self.player_.loadJSON(data);
        	self.player_.isLocal_ = true;
        	Event.fire(responder, "load", [self.player_]);
		}
    });
	
	return responder;
}

BoardController.prototype.sendAction = function(action, data) {
	var responder = new Object();
	
	jQuery.postJSON(this.actionUrl_, {action:action, data:data}, function(ret) {
        Event.fire(responder, "load", arguments);
    });
	
	return responder;
}

BoardController.prototype.handleActionComplete = function() {
	console.log("complete handler");
	this.currentAction_ = null;
	this.loadActions();
};
BoardController.prototype.handleActionCancel = function() {
	console.log("cancel handler");
	if(this.currentAction_ != null) {
		Event.removeAllListeners(self.currentAction_);
		if(typeof this.currentAction_.cancel == "function")
			this.currentAction_.cancel();
		this.currentAction_ = null;
	}
	this.loadActions();
};


BoardController.prototype.loadActions = function() {
	console.log("loading actions...");
	this.actionsEl_.empty();
	if(!this.availableActions_) return;
	
	console.log("still loading..." + this.currentAction_);
	
	var actionsul = $("<ul></ul>");
	
	this.actionsEl_.append(actionsul);
	
	var self = this;
	
	if(this.currentAction_) {
		var cancel = $("<li></li>");
		var cancelLink = $("<a href='javascript:void(0)'><span>Cancel</span></a>");
		cancel.append(cancelLink);
		actionsul.append(cancel);
		
		cancelLink.click(function() { self.handleActionCancel(); });
		
	}
	else {		
		for(var i = 0; i < this.availableActions_.length; i++) {
			var a = this.availableActions_[i];
			console.log("loading action #" + i + ": " + a);
			
			var act = $("<a href='javascript:void(0)'/>");
			var li = $("<li/>");
			
			switch(a) {
			case "startGame":
				act.append("<span>Start Game</span>");
				act.click(function() {
					var responder = self.sendAction("startGame", null);
					Event.addListener(responder, "load", function(data){});
					self.loadActions();
				});
				break;
			case "placeSettlement":
				act.append("<span>Build Settlement</span>");
				act.click(function() {
					self.currentAction_ = self.beginBuildSettlement();
					Event.addListener(self.currentAction_, "complete", function() { self.handleActionComplete(); });
					self.loadActions();
				});
				break;
			case "placeRoad":
				act.append("<span>Build Road</span>");
				act.click(function() { 
					console.log("beginBuildRoad")
					self.currentAction_ = self.beginBuildRoad();
					Event.addListener(self.currentAction_, "complete", function() { self.handleActionComplete(); });
					self.loadActions();
				});
				break;
			case "placeCity":
				act.append("<span>Build City</span>");
				act.click(function() { 
					self.currentAction_ = self.beginBuildCity(); 
					Event.addListener(self.currentAction_, "complete", function() { self.handleActionComplete(); });
					self.loadActions();
				});
				break;
			case "rollDice":
				act.append("<span>Roll Dice</span>");
				act.click(function() { 
					self.currentAction_ = self.beginRollDice(); 
					if(self.currentAction_)
						Event.addListener(self.currentAction_, "complete", function() { self.handleActionComplete(); });
					self.loadActions();
				});
				break;
			case "endTurn":
				act.append("<span>End Turn</span>");
				act.click(function() { 
					self.currentAction_ = self.beginEndTurn(); 
					if(self.currentAction_)
						Event.addListener(self.currentAction_, "complete", function() { self.handleActionComplete(); });
					self.loadActions();
				});
				break;
			case "quit":
				act.append("<span>Quit</span>");
				break;
			default:
				act.append("<span>"+a+"</span>");
			}
			
			li.append(act)
			actionsul.append(li);
		}
	}
	console.log("done loading..." + this.currentAction_);
}



BoardController.prototype.beginBuildSettlement = function() {
	if(this.player_) 
		this.board_.highlightBuildableVertex(this.player_.playerColor_);
	
	var self = this;
	
	var ret = new Object();
	
	handleVertexClickId = Event.addListener(this.board_, "vertexclick", function(vertex) {
		console.log("vertex click:Settlement");
		var responder = self.sendAction("placeSettlement", "{\"x\":"+vertex.position_.x+",\"y\":"+vertex.position_.y+"}");
		Event.addListener(responder, "load", function(ret) {
			if(!ret) alert("You cannot place a settlement there.");
			
			Event.removeListenerById(self.board_, "vertexclick", handleVertexClickId);
			
		});
		Event.fire(ret, "complete", []);
		self.board_.clearHighlights();
	});
	
	ret["cancel"] = function() {
		Event.removeListenerById(self.board_, "vertexclick", handleVertexClickId);
		self.board_.clearHighlights();
	};
	
	return ret;
}


BoardController.prototype.beginBuildCity = function() {
	var self = this;
	
	var ret = new Object();
	
	handleVertexClickId = Event.addListener(this.board_, "vertexclick", function(vertex) {
		console.log("vertex click: City");
		var responder = self.sendAction("placeCity", "{\"x\":"+vertex.position_.x+",\"y\":"+vertex.position_.y+"}");
		Event.addListener(responder, "load", function(ret) {
			if(!ret) alert("You cannot place a city there.");
			
			Event.removeListenerById(self.board_, "vertexclick", handleVertexClickId);
		});
		Event.fire(ret, "complete", []);
	});
	
	ret["cancel"] = function() {
		Event.removeListenerById(self.board_, "vertexclick", handleVertexClickId);
	};
	return ret;
}

BoardController.prototype.beginRollDice = function() {	
	var responder = this.sendAction("rollDice", "null");
	Event.addListener(responder, "load", function(ret) {
		if(!ret) { alert("Dice roll error!  You Fail!"); }
		else { alert("Rolled Dice!"); }
		
	});
	return null;
}

BoardController.prototype.beginEndTurn = function() {	
	var responder = this.sendAction("endTurn", "null");
	Event.addListener(responder, "load", function(ret) {
		if(!ret) { alert("Error, could not end turn.");}
		else {}
		
	});
	return null;
}

BoardController.prototype.beginBuildRoad = function() {
	if(this.player_)
		this.board_.highlightBuildableEdge(this.player_.playerColor_);
	
	var self = this;
	var ret = new Object();
	
	clickId = Event.addListener(self.board_, "edgeclick", function(edge) {
		console.log("edge click");
		var responder = self.sendAction("placeRoad", '{"x1":'+edge.first_.x+',"y1":'+edge.first_.y+',"x2":'+edge.second_.x+',"y2":'+edge.second_.y+"}");
		Event.addListener(responder, "load", function(ret) {
			if(!ret) alert("You cannot place a road there.");
			
			Event.removeListenerById(self.board_, "edgeclick", clickId);
		});
		Event.fire(ret, "complete", []);
		self.board_.clearHighlights();
	});
	
	ret["cancel"] = function() {
		Event.removeListenerById(self.board_, "edgeclick", clickId);
		self.board_.clearHighlights();
	};
	
	return ret;
	
}
