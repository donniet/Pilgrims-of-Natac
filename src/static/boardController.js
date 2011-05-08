/*
 * @author Donnie
 * @requires board.js
 */


function BoardController(userToken, boardView, actionsView, errorView, playerListView, diceView, playerView, services) {
	this.channel_ = null;
	this.socket_ = null;
	this.connected_ = false;
	
	this.userToken_ = userToken;
	//this.boardUrl_ = services["board-json-url"];
	this.playerUrl_ = services["player-json-url"];
	//this.actionUrl_ = services["action-json-url"];
	this.reservationUrl_ = services["reservation-json-url"];
	
	this.board_ = new Board(userToken, services);
	this.player_ = new Player(services);
	
	this.boardView_ = boardView;
	this.actionsView_ = actionsView;
	this.errorView_ = errorView;
	this.playerListView_ = playerListView;
	this.diceView_ = diceView;
	this.playerView_ = playerView;
}
BoardController.prototype.load = function() {
    this.actionsView_.setBoardView(this.boardView_);
    this.actionsView_.setBoard(this.board_);
    this.boardView_.setBoard(this.board_);
    this.errorView_.setBoard(this.board_);
    this.playerListView_.setBoard(this.board_);
    this.diceView_.setBoard(this.board_);
    this.playerView_.setBoard(this.board_);
    
    var self = this;
    Event.addListener(this.actionsView_, "action", function() {
    	self.handleAction.apply(self, arguments);
    });

	this.board_.load();
}

BoardController.prototype.handleAction = function(action, data) {
	var responder = this.board_.sendAction(action, data);
};

BoardController.prototype.getPlayer = function() {
	return this.player_;
}
BoardController.prototype.getBoard = function() {
	return this.board_;
}


