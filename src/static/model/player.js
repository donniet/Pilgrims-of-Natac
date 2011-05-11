


function Player(services) {
    this.score_ = 0;
    this.name_ = "";
    this.email_ = "";
    this.image_ = null;
    this.resourceCount_ = 0;
    this.bonusCount_ = 0;
    this.color_ = "#000000";
    this.colorName_ = "black";
    this.active_ = false;
    this.isLocal_ = false;
    this.playerUrl_ = typeof services == "undefined" ? null : services["player-json-url"];

    /* only populated for the local player */
    this.resources_ = new Array();
    this.bonuses_ = new Array();
    this.playerHash_ = "";
}


Player.nameToColorMap = {
	"blue": "rgb(0,0,255)",
	"red": "rgb(255,0,0)",
	"green": "rgb(0,255,0)",
	"orange": "#FF9900",
	"white": "#CCC",
	"brown": "#CC6600",
};


Player.prototype.load = function() {
	var responder = new Object();
	
	var self = this;
	
	jQuery.getJSON(this.playerUrl_, function(data) {
		if(! data || data["error"]) {
			Event.fire(responder, "error", []);
		}
		else {
        	self.isLocal_ = (this.playerUrl_ != null);
        	self.loadJSON(data);
		}
    });
	
	return responder;
}


Player.prototype.loadJSON = function (json) {
    // TODO: Update loading
    
	this.colorName_ = json["color"];
	this.playerColor_ = "player-" + json["color"];
	this.color_ = typeof Player.nameToColorMap[this.colorName_] != "undefined" ? Player.nameToColorMap[this.colorName_] : this.colorName_;
	this.name_ = json["user"]["nickname"];
	this.email_ = json["user"]["email"];
	this.image_ = json["userpicture"];
	this.score_ = json["score"];
	this.resourceCount_ = json["totalResources"];
	this.resources_ = new Array();
	this.active_ = json["active"];
	for(var i = 0; json["playerResources"] && i < json["playerResources"].length; i++) {
		var r = json["playerResources"][i];
		this.resources_.push({
			resource: r["resource"],
			amount: r["amount"]
		});
	}
	
    Event.fire(this, "load", [this]);
}

Player.prototype.getName = function() { return this.name_; }


