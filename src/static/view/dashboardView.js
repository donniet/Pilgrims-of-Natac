
function DashboardView(el, isPlayer) {
	this.el_ = el;
	this.board_ = null;
	this.boardView_ = null;
	this.isPlayer_ = !!isPlayer;
	
	this.actionsView_ = null;
	this.playersView_ = null;
	this.resourcesView_ = null;
	this.diceView_ = null;
}
DashboardView.prototype.setBoardView = function(boardView) {
	this.boardView_ = boardView;
	if(this.actionsView_) 
		this.actionsView_.setBoardView(boardView);
}
DashboardView.prototype.setBoard = function(board) {
	this.board_ = board;
	
	if(this.isPlayer_) {
	
		this.el_.append("<h3>Resources</h3>");
		var resourcesEl = $("<div id='pp-resources'/>");
		this.el_.append(resourcesEl);
		
		this.el_.append("<h3>Bonuses</h3>");
		var bonusesEl = $("<div id='pp=bonuses'/>");
		this.el_.append(bonusesEl);
		
		this.el_.append("<h3>Actions</h3>");
		var actionsEl = $("<div id='actions'/>");
		this.el_.append(actionsEl);
		
		var diceEl = $("<h3 id='diceView'/>");
		this.el_.append(diceEl);
	
	}
	
	this.el_.append("<h3>Players</h3>");
	var playersEl = $("<div id='players'/>");
	this.el_.append(playersEl);
	
	if(this.isPlayer_) {
		this.actionsView_ = new ActionsView(actionsEl);
		this.actionsView_.setBoard(board);
		
		Event.addListener(this.actionsView_, "completeaction", function(action, data) {
			console.log("data: " + data);
			board.sendAction(action, data);
		});
		
		this.resourcesView_ = new ResourcesView(resourcesEl);
		this.resourcesView_.setSelectMode(ResourcesView.SelectMode.Many);
		this.resourcesView_.setPlayer(board.getCurrentPlayer());
		
		this.actionsView_.setResourceView(this.resourcesView_);
		
		this.diceView_ = new DiceView(diceEl);
		this.diceView_.setBoard(board);
	}
	
	this.playersView_ = new PlayerListView(playersEl);
	this.playersView_.setBoard(board);
	
}
