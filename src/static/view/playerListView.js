
function PlayerListItemView(playerElement) {
	this.playerElement_ = $(playerElement);
	
	this.player_ = null;
}
PlayerListItemView.prototype.setPlayer = function(player) {
	this.player_ = player;
	
	this.render();
}
	
PlayerListItemView.prototype.render = function() {	
	var span = $("<span></span>");
	span.append(this.player_.getName());
	
	this.playerElement_.append(span);	
}

function PlayerListView(playersElement) {
	this.playersElement_ = $(playersElement);
	this.board_ = null;
	this.playerListItemViews_ = null;
	this.loadListenerId_ = null;
}
PlayerListView.prototype.setBoard = function(board) {
	if(this.board_) {
		Event.removeListenerById(this.board_, "load", this.loadListenerId_);
		this.board_ = null;
		this.loadListenerId_ = null;
	}
	
	var self = this;
	this.board_ = board;
	this.loadListenerId_ = Event.addListener(this.board_, "load", function() {
		self.render();
	});
	
	this.render();
}
PlayerListView.prototype.render = function() {
	this.playersElement_.empty();
	
	var ul = $("<ul></ul>");
	this.playersElement_.append(ul);
	
	this.playerListItemViews_ = new Array();
	
	var players = this.board_.getPlayers();
	console.log("player count: " + players.length);
	
	for(var i = 0; i < players.length; i++) {
		var li = $("<li></li>");
		
		var p = players[i];
		
		var pv = new PlayerListItemView(li);
		pv.setPlayer(p);
		
		ul.append(li);
		this.playerListItemViews_.push(pv);
	}
}