
function DiceView(diceElement) {
	this.diceElement_ = diceElement;
	this.board_ = null;
	this.diceRolledListenerId_ = null;
	var self = this;
	Event.addListener(this.controller_, "diceRolled", function(diceValues) {
		//console.log("handling dice roll: " + diceValues.length);
		self.diceValues_ = diceValues;
		self.RenderDice();
	});
	Event.addListener(this.controller_, "loadBoard", function() {
		//console.log("handling board load...");
		self.diceValues_ = self.controller_.dice_;
		self.RenderDice();
	});
}
DiceView.prototype.setBoard = function(board) {
	if(this.board_) {
		Event.removeListenerById(this.board_, "diceRolled", this.diceRolledListenerId_);
		this.board_ = null;
		this.diceRolledListenerId_ = null;		
	}
	this.board_ = board;
	var self = this;
	this.diceRolledListenerId_ = Event.addListener(this.board_, "diceRolled", function() {
		self.render();
	});
}
DiceView.prototype.render = function() {
	console.log("rendering dice.");
	this.diceElement_.empty();
	
	var dice = this.board_.getDice();
	
	for(var i = 0; dice && i < dice.length; i++) {
		var d = dice[i];
		//console.log("current die: " + d);
		var dieEl = $('<img src="/static/i/Dice-' + d + '.svg" alt="' + d + '" width="50" height="50"/>');
		//console.log("die img: " + dieEl)
		this.diceElement_.append(dieEl);
	}
}