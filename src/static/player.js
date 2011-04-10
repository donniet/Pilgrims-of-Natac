


function Player() {
    this.score_ = 0;
    this.name_ = "";
    this.image_ = null;
    this.resourceCount_ = 0;
    this.bonusCount_ = 0;
    this.color_ = "#000000";
    this.colorName_ = "black";
    this.active_ = false;
    this.isLocal_ = false;

    /* only populated for the local player */
    this.resources_ = new Array();
    this.bonuses_ = new Array();
    this.playerHash_ = "";
}

Player.prototype.loadPlayer = function (source) {
    // TODO: Update loading

    Event.fire(this, "playerload", [this]);
}


function PlayerView(player) {
    this.el_ = null;
    this.player_ = player;

    this.imageEl_ = null;
    this.scoreEl_ = null;
    this.resourceCountEl_ = null;
    this.bonusCountEl_ = null;
    this.colorEl_ = null;
    this.nameEl_ = null;

    this.resourcesEl_ = null;
    this.bonusesEl_ = null;
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
    bonusCountLabel.appendChild(doc.createTextNode("Bonuse Count"));
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

    Event.addListener(this.player_, "playerload", this.handleUpdate, this);
}
PlayerView.prototype.renderResources = function () {
    while (this.resourcesEl_.firstChild)
        this.resourcesEl_.removeChild(this.resourcesEl_.firstChild);

    for (var i = 0; i < this.player_.resources_.length; i++) {
        this.renderResource(this.player_.resources_[i], this.resourcesEl_);
    }
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
