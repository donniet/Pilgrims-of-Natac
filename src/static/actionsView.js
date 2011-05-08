

function ActionsView(actionsElement) {
	this.actionsElement_ = actionsElement;
	this.board_ = null;
	
	this.currentAction_ = null;
	this.eventName_ = null;
	this.eventHandlerId = null;
	
	this.boardView_ = null;
	this.actionsChangedHandlerId_ = null;
	this.loadListenerId_ = null;
	
	
}
ActionsView.prototype.setBoardView = function(boardView) {
	this.boardView_ = boardView;
}
ActionsView.prototype.setBoard = function(board) {
	var self = this;
	if(this.board_) {
		Event.removeListenerById(this.board_, "actionschanged", this.actionsChangedHandlerId_);
		//Event.removeListenerById(this.board_, "load", this.loadListenerId_);
		this.actionsChangedHandlerId_ = null;
		this.board_ = null;
	}
	this.board_ = board;
	this.actionsChangedHandlerId_ = Event.addListener(this.board_, "actionschanged", function() { self.cancelAction() });
	//this.loadListenerId_ = Event.addListener(this.board_, "load", function() {self.cancelAction();})
}
ActionsView.prototype.render = function() {
	this.actionsElement_.empty();
	var ul = $("<ul/>");
	
	// if there is a current action, just populate with a cancel button
	if(this.currentAction_) {
		var li = $("<li/>");
		var a = $("<a href='javascript:void(0)'/>");
		li.append(a);
		a.append("Cancel");
		a.click(this.createCancelClickHandler());
		ul.append(li);
	}
	// otherwise populate with all the available actions
	else {
		var actions = this.board_.getAvailableActions();
			
		for(var i = 0; i < actions.length; i++) {
			var action = actions[i];
			var li = $("<li/>");
			var a = $("<a href='javascript:void(0)'/>");
			li.append(a);
			a.append(action.displayText);
			a.click(this.createClickHandler(action));
			ul.append(li);
		}
	}
	this.actionsElement_.append(ul);
}
ActionsView.prototype.createCancelClickHandler = function() {
	var self = this;
	return function() { self.cancelAction(); };
}
ActionsView.prototype.cancelAction = function(doRender /* = true */) {
	doRender = typeof doRender == "undefined" ? true : doRender;
	if(this.currentAction_) {
		Event.removeListenerById(this.boardView_, this.eventName_, this.eventHandlerId_);
		this.currentAction_ = null;
		this.eventName_ = null;
		this.eventHandlerId_ = null;
	}
	if(doRender) this.render();
}
ActionsView.prototype.handleBeginAction = function(eventName, action) {
	this.cancelAction(false);
	
	this.currentAction_ = action;
	this.eventName_ = eventName;
	
	var self = this;
	
	this.eventHandlerId_ = Event.addListener(this.boardView_, this.eventName_, function(arg) {
		var args = [action];
		args.push(arg);
		
		console.log("action args length: " + args.length);
		
		self.handleCompleteAction.apply(self, args);
	});
	this.render();
}
ActionsView.prototype.handleCompleteAction = function() {
	Event.fire(this, "action", arguments);
	
	this.cancelAction();
}

ActionsView.prototype.createClickHandler = function(action) {
	var self = this;
	var eventName = null;
	
	// if no extra data is required, just fire an event for the action
	if(!action.requiredData) {
		return function() { self.handleCompleteAction(action); };
	}
	// otherwise use the boardView_ to collect the required data from the user
	//TODO: Tell the user that we are expecting a click on the board.
	else {
		switch(action.requiredData) {
		case Action.RequiredData.HEX:
			eventName = "hexclick";
			break;
		case Action.RequiredData.EDGE:
			eventName = "edgeclick";
			break;
		case Action.RequiredData.VERTEX:
			eventName = "vertexclick";
			break;
		default:
			return function() { self.handleCompleteAction(action); };
		}
		
		return function() {
			self.handleBeginAction(eventName, action);
		};
	}
}