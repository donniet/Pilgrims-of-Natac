
function PlayerListItemView(playerElement) {
	this.playerElement_ = $(playerElement);
	
	this.player_ = null;
}
PlayerListItemView.prototype.setPlayer = function(player) {
	this.player_ = player;
	
	this.render();
}
	
PlayerListItemView.prototype.render = function() {
	span = $("<span class='list-player-image'></span>");
	var img = $("<img/>");
	img.attr("width", 44);
	img.attr("height", 44);
	
	img.attr("src", this.player_.image_);
	span.append(img);
	this.playerElement_.append(span);
	
	span = $("<span class='list-player-name'></span>");
	var a = $("<a/>")
	a.attr("href", "/player?email=" + this.player_.email_);
	a.text(this.player_.getName());
	span.append(a);
	this.playerElement_.append(span);
	
	span = $("<span/>")
	span.addClass(this.player_.playerColor_);
	this.playerElement_.append(span);
	
	span = $("<span class='list-player-resource-count'/>")
	span.text(this.player_.resourceCount_);
	this.playerElement_.append(span);

	span = $("<span class='list-player-bonus-count'/>")
	span.text(this.player_.bonusCount_);
	this.playerElement_.append(span);
	
	span = $("<span class='list-player-score'/>")
	span.text(this.player_.score_);
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
		Event.removeListenerById(this.board_, "loadPlayers", this.loadListenerId_);
		this.board_ = null;
		this.loadListenerId_ = null;
	}
	
	var self = this;
	this.board_ = board;
	this.loadListenerId_ = Event.addListener(this.board_, "loadPlayers", function() {
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
	//console.log("player count: " + players.length);
	
	for(var i = 0; i < players.length; i++) {
		var li = $("<li></li>");
		
		var p = players[i];
		li.addClass("list-" + p.playerColor_);
		if(p.active_) li.addClass("list-player-active");
		
		var pv = new PlayerListItemView(li);
		pv.setPlayer(p);
		
		ul.append(li);
		this.playerListItemViews_.push(pv);
	}
}