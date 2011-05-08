


function Player(services) {
    this.score_ = 0;
    this.name_ = "";
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
	this.image_ = json["userpicture"];
	this.resources_ = new Array();
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


function PlayerView(el) {
    this.el_ = el;
    this.player_ = null;

    this.imageEl_ = null;
    this.scoreEl_ = null;
    this.resourceCountEl_ = null;
    this.bonusCountEl_ = null;
    this.colorEl_ = null;
    this.nameEl_ = null;

    this.resourcesEl_ = null;
    this.bonusesEl_ = null;
    
}
PlayerView.prototype.setBoard = function(board) {
	this.player_ = board.getCurrentPlayer();
	
    Event.addListener(this.player_, "load", this.handleUpdate, this);
}
PlayerView.prototype.handleUpdate = function () {
    if (this.imageEl_) this.imageEl_.src = this.player_.image_;
    if (this.scoreEl_) this.scoreEl_.nodeValue = this.player_.score_;
    if (this.resourceCountEl_) this.resourceCountEl_.nodeValue = this.player_.resourceCount_;
    if (this.bonusCountEl_) this.bonusCountEl_.nodeValue = this.player_.bonusCount_;
    if (this.colorEl_) this.colorEl_.nodeValue = this.player_.color_;
    if (this.nameEl_) this.nameEl_.nodeValue = this.player_.name_;
    if (this.resourcesEl_) this.renderResources();
    if (this.bonusesEl_) this.renderBonuses();
    if (this.el_) {
        this.el_.className = "player " + this.player_.colorName_ + " " + (this.player_.active_ ? "active" : "inactive");
    }
    this.renderResources();
}
PlayerView.prototype.render = function (el) {
    var doc = el.ownerDocument;

    this.el_ = doc.createElement("div");
    this.el_.className = "player " + this.player_.colorName_ + " " + (this.player_.active_ ? "active" : "inactive");
    el.appendChild(this.el_);

    var imageSpan = doc.createElement("span");
    imageSpan.className = "player-image";

    this.imageEl_ = doc.createElement("img");
    this.imageEl_.src = this.player_.image_;
    imageSpan.appendChild(this.imageEl_);
    this.el_.appendChild(imageSpan);

    $("#pp-name").html(this.player_.name_);
    this.nameEl_ = doc.createTextNode(this.player_.name_);
    var nameSpan = doc.createElement("span");
    nameSpan.className = "player-name";

    var nameLabel = doc.createElement("span");
    nameLabel.className = "player-name-label";
    nameLabel.appendChild(doc.createTextNode("Name"));
    nameSpan.appendChild(nameLabel);

    nameSpan.appendChild(this.nameEl_);
    this.el_.appendChild(nameSpan);

    this.scoreEl_ = doc.createTextNode(this.player_.score_);
    var scoreSpan = doc.createElement("span");
    scoreSpan.className = "player-score";

    var scoreLabel = doc.createElement("span");
    scoreLabel.className = "player-score-label";
    scoreLabel.appendChild(doc.createTextNode("Score"));
    scoreSpan.appendChild(scoreLabel);

    scoreSpan.appendChild(this.scoreEl_);
    this.el_.appendChild(scoreSpan);

    this.resourceCountEl_ = doc.createTextNode(this.player_.resourceCount_);
    var resourceCountSpan = doc.createElement("span");
    resourceCountSpan.className = "player-resource-count";

    var resourceCountLabel = doc.createElement("span");
    resourceCountLabel.className = "player-resource-count-label";
    resourceCountLabel.appendChild(doc.createTextNode("Resource Count"));
    resourceCountSpan.appendChild(resourceCountLabel);

    resourceCountSpan.appendChild(this.resourceCountEl_);
    this.el_.appendChild(resourceCountSpan);

    this.bonusCountEl_ = doc.createTextNode(this.player_.bonusCount_);
    var bonusCountSpan = doc.createElement("span");
    bonusCountSpan.className = "player-bonus-count";

    var bonusCountLabel = doc.createElement("span");
    bonusCountLabel.className = "player-bonus-count-label";
    bonusCountLabel.appendChild(doc.createTextNode("Bonus Count"));
    bonusCountSpan.appendChild(bonusCountLabel);

    bonusCountSpan.appendChild(this.bonusCountEl_);
    this.el_.appendChild(bonusCountSpan);


    if (this.player_.isLocal_) {

        var resourcesLabel = doc.createElement("span");
        resourcesLabel.className = "player-resources-label";
        resourcesLabel.appendChild(doc.createTextNode("Resources"));
        this.el_.appendChild(resourcesLabel);

        this.resourcesEl_ = doc.createElement("ul");
        this.renderResources();
        this.el_.appendChild(this.resourcesEl_);

        var bonusesLabel = doc.createElement("span");
        bonusesLabel.className = "player-bonuses-label";
        bonusesLabel.appendChild(doc.createTextNode("Bonuses"));
        this.el_.appendChild(bonusesLabel);

        this.bonusesEl_ = doc.createElement("ul");
        this.renderBonuses();
        this.el_.appendChild(this.bonusesEl_);
    }

}
PlayerView.prototype.renderResources = function () {
	//console.log("rendering resources...");
    var _p = this;

    var _find = function(resourceType) {
        return _p.findResource(resourceType);
    };

    $("#pp-res-sheep").html( _find("wool").amount );
    $("#pp-res-wheat").html( _find("wheat").amount );
    $("#pp-res-wood").html( _find("wood").amount );
    $("#pp-res-rock").html( _find("ore").amount );
    $("#pp-res-clay").html( _find("brick").amount );
    /*
    $('[id^="pp-res-card"]').click( function() {
        var ar_k = this.id.split("-");
        var k = ar_k[ar_k.length-1];
        
        var res = _find( k );
        alert("clicked " + res.resource);
        Event.fire(this, "resourceclick", [res, this.player_]);
    });
    */
}

PlayerView.prototype.findResource = function(resourceType) {
	//console.log("looking for " + resourceType);
    for (var i = 0; i < this.player_.resources_.length; i++) {
        if( this.player_.resources_[i].resource == resourceType ){
        	//console.log("found " + resourceType + " = " + this.player_.resources_[i].amount);
            return this.player_.resources_[i];
        }
    }
    // return something so we avoid null's
    return {"amount":0,"resource":resourceType};
}

PlayerView.prototype.renderBonuses = function () {
    while (this.bonusesEl_.firstChild)
        this.bonusesEl_.removeChild(this.bonusesEl_.firstChild);

    for (var i = 0; i < this.player_.bonuses_.length; i++) {
        this.renderBonus(this.player_.bonuses_[i], this.bonusesEl_);
    }
}
PlayerView.prototype.renderResource = function (resource, el) {
    var doc = el.ownerDocument;

    var li = doc.createElement("li");
    li.className = resource.resourceName_;

    var span = doc.createElement("span");
    span.appendChild(doc.createTextNode(resource.resourceName_));
    li.appendChild(span);
    
    // bubble resource click events
    Event.addListener(li, "click", function () {
        Event.fire(this, "resourceclick", [resource, this.player_]);
    }, this);

    el.appendChild(li);
}
PlayerView.prototype.renderBonus = function (bonus, el) {
    var doc = el.ownerDocument;

    var li = doc.createElement("li");
    li.className = bonus.bonusName_;
    var span = doc.createElement("span");
    span.appendChild(doc.createTextNode(bonus.bonusName_));
    li.appendChild(span);

    // bubble bonus click events
    Event.addListener(li, "click", function () {
        Event.fire(this, "bonusclick", [bonus, this.player_]);
    }, this);

    el.appendChild(li);
}

