

function ChatView(element) {
	this.el_ = element;
	this.board_ = null;
}
ChatView.prototype.setBoard = function(board) {
	this.board_ = board;
	var self = this;
	
	Event.addListener(this.board_, "log", function(msg) { self.handler(msg, "log"); });
	Event.addListener(this.board_, "chat", function(msg) { self.handler(msg, "chat"); });
	
	Event.addListener(this.board_, "load", function() { self.handleLoad(); });
}
ChatView.prototype.handleLoad = function() {	
	var log = this.board_.getLog();
	console.log("log length: " + log.length)
	for(var i = log.length - 1; i >= 0; i--) {
		l = log[i];
		this.handler(l, l.type);
	}
}
ChatView.prototype.handler = function(message, type) {
	m = $("<p/>");
	m.addClass("player-" + message["color"]);
	m.addClass("message-type-" + type);
	m.text(message["message"]);
	
	this.el_.append(m);
	this.el_.scrollTop(this.el_[0].scrollHeight);
}

