

function Trade(services) {
	this.tradeUrl_ = typeof services == "undefined" ? null : services["trade-json-url"];
	
	this.tradeKey_ = null;
	this.dateTimeStarted_ = null;
	this.dateTimeCompleted_ = null;
	this.state_ = null;
	this.colorFrom_ = null;
	this.colorTo_ = null;
	
	this.isTrading_ = false;
	
	this.offers_ = new Object();
}
Trade.prototype.isTrading = function() { return this.isTrading_; }
Trade.prototype.getOffers = function() { return this.offers_; }
Trade.prototype.getState = function() { return this.state_; }
Trade.prototype.getColorTo = function() { return this.colorTo_; }
Trade.prototype.getColorFrom = function() { return this.colorFrom_; }
Trade.prototype.load = function() {
	var responder = new Object();
	
	var self = this;
	
	jQuery.getJSON(this.tradeUrl_, function(data) {
		if(data && data["error"]) {
			self.isTrading_ = false;
			Event.fire(responder, "error", []);
		}
		else {
			self.loadJSON(data);
		}
	});
}
Trade.prototype.loadJSON = function(json) {
	
	if(!json) {
		this.tradeKey_ = null;
		this.dateTimeStarted_ = null;
		this.dateTimeCompleted_ = null;
		this.state_ = null;
		this.colorFrom_ = null;
		this.colorTo_ = null;
		
		this.isTrading_ = false;
		
		this.offers_ = new Object();
	}
	else {
		console.log("loading from a valid json object.  offers: " + json.offers);
		this.tradeKey_ = json.tradeKey;
		this.dateTimeStarted_ = json.dateTimeStarted;
		this.dateTimeCompleted_ = json.dateTimeCompleted;
		this.state_ = json.state;
		this.colorFrom_ = json.colorFrom;
		this.colorTo_ = json.colorTo;
		this.isTrading_ = (json.dateTimeCompleted == null);
		
		this.offers_ = new Object();
		for(var i = 0; json.offers && i < json.offers.length; i++) {
			var o = json.offers[i];
			this.offers_[o.color] = o.offer;
		}
	}
	Event.fire(this, "load", []);
}