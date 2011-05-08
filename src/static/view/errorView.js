
function ErrorView(errorElement) {
	this.board_ = null;
	this.errorEl_ = errorElement;
	this.errorInterval_ = null;
	this.errorClearTime_ = 5000; // 5 seconds
	var self = this;
	
	this.errorListenerId_ = null;
}
ErrorView.prototype.setBoard = function(board) {
	if(this.board_) {
		Event.removeListenerById(this.board_, "error", this.errorListenerId_);
		this.board_ = null;
		this.errorListenerId_ = null;
	}
	this.board_ = board;
	var self = this;
	this.errorListenerId_ = Event.addListener(this.board_, "error", function(error) {
		self.renderError(error);
	});
}
ErrorView.prototype.renderError = function(error) {
	this.clearError();
	// for now just display the message
	this.errorEl_.append(error);
	
	var self = this;
	this.errorInterval_ = setTimeout(function() {
		self.clearError();
	}, this.errorClearTime_);
}
ErrorView.prototype.clearError = function() {
	if(this.errorInterval_) {
		clearInterval(this.errorInterval_);
		this.errorInterval_ = null;
	}
	this.errorEl_.empty();
}