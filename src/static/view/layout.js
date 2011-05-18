
function Layout() {
	this.layoutItems_ = new Array();
	this.grabSize_ = 10;
	this.handle_ = null;
	
	var self = this;
	$(window).resize(function() { self.handleResize(); });
	$(document).ready(function() { self.handleResize(); });
	
	$(window).mousemove(function(evt) {self.handleSizeMouseMove(evt);});
}
Layout.prototype.addItem = function(element, attach, dimension, sizeable, overlay) {
	var self = this;
	var item = {element: element, attach: attach, dimension: dimension, sizeEl: sizeEl, overlay:overlay};
	
	var sizeEl = null;
	if(sizeable) {
		sizeEl = $("<div class='size-bar'/>");
		sizeEl.addClass("size-bar-attach-" + attach);
		sizeEl.css("position", "absolute");
		if(attach == "left") {
			sizeEl.css("width", this.grabSize_);
			sizeEl.css("top", 0);
			sizeEl.css("right", 0);
			sizeEl.css("height", "100%");
		}
		else if(attach == "right") {
			sizeEl.css("width", this.grabSize_);
			sizeEl.css("top", 0);
			sizeEl.css("left", 0);
			sizeEl.css("height", "100%");
		}
		else if(attach == "top") {
			sizeEl.css("height", this.grabSize_);
			sizeEl.css("left", 0);
			sizeEl.css("bottom", 0);
			sizeEl.css("width", "100%");
		}
		else if(attach == "bottom") {
			sizeEl.css("height", this.grabSize_);
			sizeEl.css("left", 0);
			sizeEl.css("top", 0);
			sizeEl.css("width", "100%");
		}
		
		element.append(sizeEl);
		
		sizeEl.mousedown(function(evt) {self.handleSizeMouseDown(evt, item); return false;});
		sizeEl.mouseup(function(evt) {self.handleSizeMouseUp(evt, item);});
		sizeEl.mousemove(function(evt) {self.handleSizeMouseMove(evt, item);});
	}
	this.layoutItems_.push(item);
}
Layout.prototype.handleSizeMouseDown = function(evt, item) {
	this.handle_ = {x:evt.clientX, y:evt.clientY, item:item};
	return false;
}
Layout.prototype.handleSizeMouseUp = function(evt, item) {
	this.handle_ = null;
}
Layout.prototype.handleSizeMouseMove = function(evt) {
	if(this.handle_) {
		var item = this.handle_.item;
		
		if(item.attach == "left") {
			var dx = evt.clientX - this.handle_.x;
			item.dimension += dx;
			this.handle_.x = evt.clientX;
		}
		else if(item.attach == "right") {
			var dx = evt.clientX - this.handle_.x;
			item.dimension -= dx;
			this.handle_.x = evt.clientX;
		}
		else if(item.attach == "bottom") {
			var dy = this.handle_.y - evt.clientY;
			item.dimension += dy;
			this.handle_.y = evt.clientY;
		}
		else if(item.attach == "top") {
			var dy = this.handle_.y - evt.clientY;
			item.dimension -= dy;
			this.handle_.y = evt.clientY;			
		}
		this.handleResize();
	}
}
Layout.prototype.handleResize = function() {
	var m = {
		"top":0,
		"right":0,
		"bottom":0,
		"left":0
	};
	for(var i = 0; i < this.layoutItems_.length; i++) {
		var li = this.layoutItems_[i];
		this.layout(li.element, li.attach, li.dimension, li.sizeEl, li.overlay, m);
	} 
}
Layout.prototype.layout = function(element, attach, dimension, sizeEl, overlay, margin) {
	var width = $(window).width();
	var height = $(window).height();
	
	$(element).css("position", "absolute");
	$(element).css("display", "block");
	
	switch(attach) {
	case "top":
		if(sizeEl) {
			$(sizeEl).css("bottom",0);
			$(sizeEl).css("left", 0);
			$(sizeEl).css("width", "100%");
			$(sizeEl).css("height", this.grabSize_ + "px");
		}
		$(element).css("top", margin["top"] + "px");
		$(element).css("left", margin["left"] + "px");
		$(element).css("width", (width - margin["left"] - margin["right"]) + "px");
		$(element).css("height", dimension + "px");
		if(!overlay) margin["top"] += dimension;
		break;
	case "right": 
		if(sizeEl) {
			$(sizeEl).css("top",0);
			$(sizeEl).css("right", 0);
			$(sizeEl).css("height", "100%");
			$(sizeEl).css("width", this.grabSize_ + "px");
		}
		$(element).css("top", margin["top"] + "px");
		$(element).css("right", margin["right"] + "px");
		$(element).css("width", dimension + "px");
		$(element).css("height", (height - margin["top"] - margin["bottom"]) + "px");
		if(!overlay) margin["right"] += dimension;
		break;
	case "bottom":
		if(sizeEl) {
			$(sizeEl).css("top",0);
			$(sizeEl).css("left", 0);
			$(sizeEl).css("width", "100%");
			$(sizeEl).css("height", this.grabSize_ + "px");
		} 
		$(element).css("bottom", margin["bottom"] + "px");
		$(element).css("left", margin["left"] + "px");
		$(element).css("width", (width - margin["left"] - margin["right"]) + "px");
		$(element).css("height", dimension + "px");
		if(!overlay) margin["bottom"] += dimension;
		break;
	case "left":  
		if(sizeEl) {
			$(sizeEl).css("top",0);
			$(sizeEl).css("left", 0);
			$(sizeEl).css("height", "100%");
			$(sizeEl).css("width", this.grabSize_ + "px");
		} 
		$(element).css("top", margin["top"] + "px");
		$(element).css("left", margin["left"] + "px");
		$(element).css("width", dimension + "px");
		$(element).css("height", (height - margin["top"] - margin["bottom"]) + "px");
		if(!overlay) margin["left"] += dimension;
		break;
	case "center":
		if(element.nodeName && element.nodeName == "svg") {
			element.setAttribute("width", (width - margin["left"] - margin["right"]) + "px");
			element.setAttribute("height", (height - margin["top"] - margin["bottom"]) + "px");
			$(element).css("top", margin["top"] + "px");
			$(element).css("left", margin["left"] + "px");
		}
		else {
			$(element).css("top", margin["top"] + "px");
			$(element).css("left", margin["left"] + "px");
			$(element).css("width", (width - margin["left"] - margin["right"]) + "px");
			$(element).css("height", (height - margin["top"] - margin["bottom"]) + "px");
		}
		break;
	}	
}

