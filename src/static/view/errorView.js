
function ErrorView(errorElement) {
	this.board_ = null;
	this.errorEl_ = errorElement;
	this.errorInterval_ = null;
	this.errorClearTime_ = 5000; // 5 seconds
	this.critical_ = false;
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
	this.errorListenerId_ = Event.addListener(this.board_, "error", function(error, critical) {
		self.renderError(error, critical);
	});
}
ErrorView.prototype.renderError = function(error, critical) {
	if(this.critical_ && !critical) {
		// do nothing, we're displaying a critical error
	}
	else {
		this.clearError();
		this.critical_ = !!critical;
		// for now just display the message
		this.errorEl_.text(error);
		
		if(!this.critical_) {
			var self = this;
			this.errorInterval_ = setTimeout(function() {
				self.clearError();
			}, this.errorClearTime_);
		}
	}
}
ErrorView.prototype.clearError = function() {
	if(this.errorInterval_) {
		clearInterval(this.errorInterval_);
		this.errorInterval_ = null;
	}
	this.errorEl_.empty();
}