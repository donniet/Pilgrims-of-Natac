
function TradeView(element) {
	this.el_ = element;
	this.board_ = null;
	this.myOffer_ = new Array();
	
	this.resourcesDiv_ = null;
	this.potDiv_ = null;
	this.bankDiv_ = null;
}
TradeView.prototype.setBoard = function(board) {
	this.board_ = board;
	var trade = this.board_.getTrade();
	
	var self = this;
	
	//Event.addListener(this.board_.getCurrentPlayer(), "load", this.renderPlayerResources, this);
	Event.addListener(trade, "load", this.renderPot, this);
	
	this.render();
}
TradeView.prototype.render = function() {
	this.el_.empty();

	this.resourcesDiv_ = $("<div class='trade-view-resources'/>");
	this.el_.append(this.resourcesDiv_);
	

	this.potDiv_ =  $("<div class='trade-view-players'/>");
	this.el_.append(this.potDiv_);
	
	this.bankDiv_ = $("<div class='trade-view-bank-resources'/>");
	this.el_.append(this.bankDiv_);
}
TradeView.prototype.renderPlayerResources = function() {
	var currentPlayer = this.board_.getCurrentPlayer();
	var adjustedResources = new Array();
	var playerResources = currentPlayer.getResources();
	
	for(var i = 0; i < playerResources.length; i++) {
		var pr = playerResources[i];
		adjustedResources.push({"resource":pr.resource, "amount":pr.amount});
	}
	
	for(var i = 0; i < this.myOffer_.length; i++) {
		var my = this.myOffer_[i];
		for(j = 0; j < adjustedResources.length; j++) {
			var ar = adjustedResources[j];
			if(ar.resource == my.resource) {
				ar.amount -= my.amount;
				break;
			}
		}
	}
	
	var resourcesView = new ResourcesView(this.resourcesDiv_);
	resourcesView.setResourceArray(adjustedResources);
	Event.addListener(resourcesView, "resourceclick", this.handleResourceClick, this);
}
TradeView.prototype.renderBank = function() {
	var resources = this.board_.getResources();
	var ras = new Array();
	for(var i = 0; i < resources.length; i++) {
		ras.push({"resource":resources[i], "amount":1});
	}
	
	var resourcesView = new ResourcesView(this.bankDiv_);
	resourcesView.setResourceArray(ras);
	Event.addListener(resourcesView, "resourceclick", this.handleBankResourceClick, this);
}

TradeView.prototype.renderPot = function() {
	this.renderPlayerResources();
	
	var players = this.board_.getPlayers();
	var trade = this.board_.getTrade();
	var currentPlayer = this.board_.getCurrentPlayer();
	var currentColor = currentPlayer.getColorName();
	
	this.potDiv_.empty();
	
	var ul = $("<ul/>");
	
	var offers = null;
	if(trade) offers = trade.getOffers();
	
	if(!trade.isTrading_) {
		this.myOffer_ = new Array();
	}
	
	for(var i = 0; players && i < players.length; i++) {
		var p = players[i];
		var li = $("<li/>");
		var span = $("<span class='list-player-image'></span>");
		var img = $("<img/>");
		img.attr("width", 44);
		img.attr("height", 44);
		
		img.attr("src", p.image_);
		span.append(img);
		li.append(span);
		
		span = $("<span/>");
		
		var o = offers ? offers[p.getColorName()] : null;
		if(o) {
			var rv = new ResourcesView(span);
			rv.setResourceArray(o);
			
			// if this is the current player
			if(currentColor == p.getColorName()) {
				this.myOffer_ = o;
				Event.addListener(rv, "resourceclick", this.handleResourceRemove, this);
			}
			
			// if no offer has been accepted (or confirmed) put accept markers next to other players offers
			if(trade.getState() == "initial" && trade.getColorFrom() == currentColor && trade.getColorFrom() != p.getColorName()) {
				var accept = $("<a href='javascript:void(0)' class='trade-accept-offer'><span>Accept</span></a>");
				
				var self = this;
				accept.click(function(color) { 
					return function() { self.handleOfferAccept(color); } 
				}(p.getColorName()));
				
				li.append(accept);
			}
			
			if(trade.getState() == "accepted" && trade.getColorTo() == currentColor && trade.getColorFrom() == p.getColorName()) {
				var confirm = $("<a href='javascript:void(0)' class='trade-confirm-offer'><span>Confirm</span></a>");
				
				var self = this;
				confirm.click(function() { self.handleOfferConfirm(); });
				
				li.append(confirm);
			}
			
		}
		li.append(span)
		ul.append(li);
	}
	
	var li = $("<li/>");
	var span = $("<span class='bank-offer-image'/>");
	var img = $("<img/>");
	img.attr("width",44);
	img.attr("height",44);
	img.attr("src", "/static/i/dollar.jpg");
	span.append(img);
	li.append(span);
	
	span = $("<span/>");
	var bankOffer = trade.getBankOffer();
	
	var rv = new ResourcesView(span);
	rv.setResourceArray(bankOffer);
		
	if(trade.getColorFrom() == currentColor) {
		Event.addListener(rv, "resourceclick", this.handleBankResourceRemove, this);
		
		var confirm = $("<a href='javascript:void(0)' class='trade-confirm-offer'><span>Confirm</span></a>");
		
		var self = this;
		confirm.click(function() { self.handleBankOfferConfirm(); });
		
		li.append(confirm);
	}
	li.append(span);
	ul.append(li);
		
	this.potDiv_.append(ul);
	
	this.renderBank();
}
TradeView.prototype.handleOfferAccept = function(colorTo) {
	Event.fire(this, "acceptoffer", [colorTo]);
}
TradeView.prototype.handleOfferConfirm = function() {
	Event.fire(this, "confirmoffer", []);
}
TradeView.prototype.handleBankOfferConfirm = function() {
	Event.fire(this, "confirmbankoffer", []);
}
TradeView.prototype.handleResourceRemove = function(resource) {
	var i = 0;
	for(; i < this.myOffer_.length; i++){
		var ra = this.myOffer_[i];
		if(ra.resource == resource && ra.amount > 0) {
			ra.amount--;
			break;
		}
	}
	
	if(i < this.myOffer_.length)
		Event.fire(this, "changeoffer", [this.myOffer_]);
}
TradeView.prototype.handleBankResourceRemove = function(resource) {
	var trade = this.board_.getTrade();
	
	if(!trade) return;
	var bankOffer = trade.getBankOffer();
	
	if(!bankOffer) return;
	var i = 0;
	for(; i < bankOffer.length; i++) {
		var ra = bankOffer[i];
		if(ra.resource == resource && ra.amount > 0) {
			ra.amount--;
			break;
		}
	}
	
	if(i < bankOffer.length)
		Event.fire(this, "changebankoffer", [bankOffer]);
		
}
	

TradeView.prototype.handleResourceClick = function(resource) {
	console.log("resource clicked: " + resource);
	if(!this.myOffer_) this.myOffer_ = new Array();
	var i = 0;
	for(; i < this.myOffer_.length; i++){
		var ra = this.myOffer_[i];
		if(ra.resource == resource) {
			ra.amount++;
			break;
		}
	}
	if(i >= this.myOffer_.length)
		this.myOffer_.push({"resource":resource, "amount":1});
	
	Event.fire(this, "changeoffer", [this.myOffer_]);
	
}
TradeView.prototype.handleBankResourceClick = function(resource) {
	console.log("bank resource clicked: " + resource);

	var trade = this.board_.getTrade();
	var bankOffer = trade.getBankOffer();
	
	var i = 0; 
	for(; i < bankOffer.length; i++) {
		var ra = bankOffer[i];
		if(ra.resource == resource) {
			ra.amount++;
			break;
		}
	}
	if(i >= bankOffer.length) {
		bankOffer.push({"resource":resource, "amount":1});
	}
	
	Event.fire(this, "changebankoffer", [bankOffer]);	
}