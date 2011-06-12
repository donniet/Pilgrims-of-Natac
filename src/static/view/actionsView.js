

function ActionsView(actionsElement) {
	this.actionsElement_ = actionsElement;
	this.board_ = null;
	
	this.currentAction_ = null;
	this.eventName_ = null;
	this.eventHandlerId = null;
	
	this.boardView_ = null;
	this.resourceView_ = null;
	this.actionsChangedHandlerId_ = null;
	this.loadListenerId_ = null;
	
	this.contextActionsBox_ = null;
	
	
}
ActionsView.prototype.setBoardView = function(boardView) {
	var self = this;
	this.boardView_ = boardView;
	Event.addListener(this.boardView_, "vertexclick", function(vertex, evt) { self.handleBoardClick(Action.RequiredData.VERTEX, vertex, evt); });
	Event.addListener(this.boardView_, "edgeclick", function(edge, evt) { self.handleBoardClick(Action.RequiredData.EDGE, edge, evt); });
	Event.addListener(this.boardView_, "hexclick", function(hex, evt) { self.handleBoardClick(Action.RequiredData.HEX, hex, evt); });
}
ActionsView.prototype.setResourceView = function(resourceView) {
	var self = this;
	this.resourceView_ = resourceView;
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
	this.hideContextActions();
	
	this.actionsElement_.empty();
	var ul = $("<ul/>");
	
	// if there is a current action, just populate with a cancel button
	if(this.currentAction_) {
		var li = $("<li/>");
		li.addClass("action-cancel");
		var a = $("<a href='javascript:void(0)'/>");
		var span = $("<span/>");
		span.text("Cancel");
		a.click(this.createCancelClickHandler());
		a.append(span);
		li.append(a);
		ul.append(li);
	}
	// otherwise populate with all the available actions
	else {
		var actions = this.board_.getAvailableActions();
			
		for(var i = 0; i < actions.length; i++) {
			var action = actions[i];
			var li = $("<li/>");
			li.addClass("action-" + action.actionName);
			var a = $("<a href='javascript:void(0)'/>");
			var span = $("<span/>");
			span.text(action.displayText);
			a.click(this.createClickHandler(action));
			a.append(span);
			li.append(a);
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
		//Event.removeListenerById(this.boardView_, this.eventName_, this.eventHandlerId_);
		this.currentAction_ = null;
		this.eventName_ = null;
		this.eventHandlerId_ = null;
	}
	if(doRender) this.render();
}

ActionsView.prototype.handleBoardClick = function(requiredData, obj, evt) {
	if(this.currentAction_) {
		this.handleCompleteAction(this.currentAction_, obj);
	}
	else {
		// here we guess what action they wanted to take
		var actions = this.board_.getAvailableActions();
		var context = new Array();
		
		var context = actions.filter(function(a) { return a.requiredData == requiredData; });
		
		if(context.length == 0) {
			// do nothing-- ignore the click
		}
		else if(context.length == 1) {
			// only one action available, we can safely assume this is what the user meant
			this.handleCompleteAction(context[0], obj);
		}
		else {
			//TODO: show context menu with all actions available to this click
			this.renderContextActions(context, obj, evt);
		}
	}
}

ActionsView.prototype.renderContextActions = function(contextActions, obj, evt) {
	this.hideContextActions();
	
	var ca = $("<div id='context-actions'/>");
	var ul = $("<ul/>");
	ca.append(ul);
	
	var self = this;
	
	for(var i = 0; i < contextActions.length; i++) {
		var action = contextActions[i];
		var li = $("<li/>");
		li.addClass("action-" + action.actionName);
		var a = $("<a href='javascript:void(0);'/>");
		var span = $("<span/>");
		a.click(function(action) { return function() {
			self.handleCompleteAction(action, obj);
			self.hideContextActions();
		} }(action));
		span.text(action.displayText);
		a.append(span);
		li.append(a);
		ul.append(li);
	}
	var li = $("<li/>");
	li.addClass("action-cancel");
	var a = $("<a href='javascript:void(0);'/>");
	var span = $("<span/>");
	a.click(function() { self.hideContextActions();	});
	span.text("Cancel");
	a.append(span)
	li.append(a);
	ul.append(li);
	
	var scrollTop = document.body.scrollTop ? document.body.scrollTop : document.documentElement.scrollTop; 
	var scrollLeft = document.body.scrollLeft ? document.body.scrollLeft : document.documentElement.scrollLeft;
	ca.css("position", "absolute");
	ca.css("left", evt.clientX + scrollLeft + "px");
	ca.css("top", evt.clientY + scrollTop + "px");
		
	$(document.body).append(ca);
	
	this.contextActionsBox_ = ca;
}
ActionsView.prototype.calculateContextPosition = function(obj, evt) {
	if(obj.svgEl_) {
		var rect = obj.svgEl_.getBBox();
		return {left:rect.x + rect.width/2.0, top:rect.y + rect.height/2.0};
	}
}

ActionsView.prototype.hideContextActions = function() {
	if(this.contextActionsBox_ != null) {
		this.contextActionsBox_.hide();
		this.contextActionsBox_.remove();
		this.contextActionsBox_ = null;
	}
}

ActionsView.prototype.handleBeginAction = function(eventName, action) {
	this.cancelAction(false);
	
	this.currentAction_ = action;
	this.eventName_ = eventName;
	
	var self = this;
	/*
	this.eventHandlerId_ = Event.addListener(this.boardView_, this.eventName_, function(arg) {
		var args = [action];
		args.push(arg);
		
		console.log("action args length: " + args.length);
		
		self.handleCompleteAction.apply(self, args);
	});
	*/
	this.render();
}
ActionsView.prototype.handleCompleteAction = function(action, data) {
	Event.fire(this, "completeaction", [action, data]);
		
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
		case Action.RequiredData.RESOURCESET:
			return function() {
				self.handleCompleteAction(action, self.resourceView_.getSelectedResources());
			}
			break;
		default:
			return function() { self.handleCompleteAction(action); };
		}
		
		return function() {
			self.handleBeginAction(eventName, action);
		};
	}
}