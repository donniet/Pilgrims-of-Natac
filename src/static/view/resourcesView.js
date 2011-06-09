
function ResourcesView(element) {
	this.el_ = element;
	this.resources_ = null;
	this.player_ = null;
	this.selectMode_ = ResourcesView.SelectMode.One;
	this.selectedResources_ = new Array();
}
ResourcesView.SelectMode = {
	"One": 1,
	"Many": 2
}
ResourcesView.prototype.setPlayer = function(player) {
	this.player_ = player;
	
	var self = this;
	Event.addListener(this.player_, "load", function() { self.renderPlayer(); });
}
ResourcesView.prototype.setResourceArray = function(resourceArray) {
	this.resources_ = resourceArray;
	this.render();
}
ResourcesView.prototype.renderPlayer = function() {	
	this.resources_ = this.player_.getResources();
	this.render();
}
ResourcesView.prototype.clearSelectedResources = function() {
	for(var i = 0; i < this.selectedResources_.length; i++) {
		var s = this.selectedResources_[i];
		s.span.removeClass("resource-view-resource-selected");
		s.span.__selected = false;
		//delete this.selectedResources_[i];
	}
	this.selectedResources_ = new Array();
	Event.fire(this, "clearselected", []);
}
ResourcesView.prototype.getSelectedResources = function() {
	var obj = new Object();
	var ret = new Array();
	for(var i = 0; i < this.selectedResources_.length; i++) {
		var s = this.selectedResources_[i];
		if(obj[s.resource]) {
			obj[s.resource].amount++;
		}
		else {
			var r = {"resource":s.resource, "amount":1};
			ret.push(r);
			obj[s.resource] = r;
		}
	}
	return ret;
}
ResourcesView.prototype.setSelectMode = function(mode) {
	this.selectMode_ = mode;
	this.clearSelectedResources();
	Event.fire(this, "setselectmode", [mode]);
}
ResourcesView.prototype.handleResourceClick = function(resource, span) {
	switch(this.selectMode_) {
	case ResourcesView.SelectMode.One:
		Event.fire(self, "resourceclick", [resource]);
		break;
	case ResourcesView.SelectMode.Many:
		if(!span.__selected) {
			var obj = {"resource":resource, "span":span};
			this.selectedResources_.push(obj);
			span.addClass("resource-view-resource-selected");
			span.__selected = obj;
		}
		else {
			//TODO: add unselect code
			var sr = new Array();
			
			var i = 0;
			for(; i < this.selectedResources_.length; i++) {
				var s = this.selectedResources_[i];
				if(s.span !== span) {
					sr.push(s);
				} 
				delete this.selectedResources_[i];
			}
			delete this.selectedResources_;
			this.selectedResources_ = sr;
			span.__selected = null;
			span.removeClass("resource-view-resource-selected");
		}
		break;
	default:
		break;
	}
}
ResourcesView.prototype.render = function(resources) {	
	this.el_.empty();
	var self = this;
	
	var ul = $("<ul/>");
	ul.addClass("resource-view");
	for(var i = 0; i < this.resources_.length; i++) {
		var r = this.resources_[i];
		for(var j = 0; j < r.amount; j++) {
			var li = $("<li/>");
			var resource = $("<span/>");
			li.click(function(r) { 
				return function() {  
				}	
			}(r.resource));
			resource.addClass("resource-view-" + r.resource);
			var textSpan = $("<span/>");
			textSpan.text(r.resource);
			resource.append(textSpan);
			li.append(resource);
			ul.append(li);
		}
	}
	this.el_.append(ul);
}