

function ChatView(element) {
	this.el_ = element;
	this.chatEl_ = null;
	this.input_ = null;
	this.submit_ = null;
	this.board_ = null;
	
	this.render();
}
ChatView.prototype.render = function() {
	this.chatEl_ = $("<div class='chat-window'/>");
	this.el_.append(this.chatEl_);
	var self = this;
	
	this.input_ = $("<input type='text'/>");
	this.input_.bind('keypress', function(e){ self.handleKeypress(e); })
	this.el_.append(this.input_);

}
ChatView.prototype.handleKeypress = function(e) {
	var code = (e.keyCode ? e.keyCode : e.which);
	if(code == 13) {
		var msg = this.input_.val();
		this.board_.sendAction("chat", msg);
		this.input_.val('');
	}
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
	//console.log("log length: " + log.length)
	for(var i = log.length - 1; i >= 0; i--) {
		l = log[i];
		this.handler(l, l.type);
	}
}
ChatView.prototype.handler = function(message, type) {
	//console.log("chat handler: " + message);
	m = $("<p/>");
	m.addClass("player-" + message["color"]);
	m.addClass("message-type-" + type);
	if(message["data"])
		m.text(message["data"]);
	else
		m.text(message["message"]);
	
	this.chatEl_.append(m);
	this.chatEl_.scrollTop(this.el_[0].scrollHeight);
}

