
function BoardView(boardElement, modelElements, options) {
	this.svgns_ = "http://www.w3.org/2000/svg";
	this.edgeLength_ = !options || typeof options.edgeLength == "undefined" ? 85 : options.edegeLength;
	this.sqrt3over2_ = Math.sqrt(3)/2;
    this.marginLeft_ = 20;
    this.marginTop_ = 20;
	this.boardElement_ = boardElement;
	this.vertexDevListener_ = null;
	this.edgeDevListener_ = null;
	this.loadListener_ = null;
	
	this.modelElements_ = new Object();
	for(var i = 0; modelElements && i < modelElements.length; i++) {
		var m = modelElements[i];
		this.setModelElement(m.type, m.element, m.center);
	}
	
	this.board_ = null;
	
	var self = this;
}

BoardView.prototype.hexCoords = function (nx, ny) {
    return [
      this.c(nx + 1, ny),
      this.c(nx + 3, ny),
      this.c(nx + 4, ny + 1),
      this.c(nx + 3, ny + 2),
      this.c(nx + 1, ny + 2),
      this.c(nx + 0, ny + 1)
   ];
}
BoardView.prototype.setBoard = function(board) {
	if(this.board_) {
		Event.removeListenerById(this.board_, "placeVertexDevelopment", this.vertexDevListener_);
		Event.removeListenerById(this.board_, "placeEdgeDevelopment", this.edgeDevListener_);
		Event.removeListenerById(this.board_, "load", this.loadListener_);
	}
	
	this.board_ = board;
	
	var self = this;

	this.vertexDevListener_ = Event.addListener(board, "placeVertexDevelopment", function() {
		self.handlePlaceVertexDevelopment.apply(self, arguments);
	});

	this.edgeDevListener_ = Event.addListener(board, "placeEdgeDevelopment", function() {
		self.handlePlaceEdgeDevelopment.apply(self, arguments);
	});
	
	this.loadListener_ = Event.addListener(board, "load", function() {
		self.render();
	});
	
}

BoardView.prototype.handlePlaceVertexDevelopment = function(vertex, development) {
	if (vertex.svgEl_) {
		this.renderVertexDevelopment(vertex, development, vertex.svgEl_);
	}
}
BoardView.prototype.handlePlaceEdgeDevelopment = function(edge, development) {
	if (edge.svgEl_ ) {
	    this.renderEdgeDevelopment(edge, development, edge.svgEl_);
	}
}

BoardView.prototype.render = function() {
	while(this.boardElement_.firstChild)
		this.boardElement_.removeChild(this.boardElement_.firstChild);
	this.renderBoard(this.boardElement_);
}
BoardView.prototype.setModelElement = function (modelName, svgEl, centerPosition) {
    this.modelElements_[modelName] = {
        "svgElement": svgEl,
        "centerPosition": centerPosition
    };
}

/* transform grid coords to pixel coords */
BoardView.prototype.c = function (/* int */nx, /* int */ny) {
    var fx = 0.5 * nx * this.edgeLength_;
    var fy = this.sqrt3over2_ * ny * this.edgeLength_;

    return {
        "x": fx + this.marginLeft_,
        "y": fy + this.marginTop_
    };
}
BoardView.prototype.renderBoard = function (svgEl) {
    this.renderHexes(svgEl);
    this.renderEdges(svgEl);
    this.renderVertexes(svgEl);
}
BoardView.prototype.renderVertexes = function (svgEl) {
    for (var i = 0; i < this.board_.vertex_.length; i++) {
        this.renderVertex(this.board_.vertex_[i], svgEl);
    }
}
BoardView.prototype.renderVertex = function (vertex, svgEl) {
    var g = vertex.svgEl_;
    if (!g) {
        g = document.createElementNS(this.svgns_, "g");
        svgEl.appendChild(g);
        vertex.svgEl_ = g;
    }

    for (var i = 0; i < vertex.vertexDevelopments_.length; i++) {
        this.renderVertexDevelopment(vertex, vertex.vertexDevelopments_[i], g);
    }

    this.renderVertexHitArea(vertex, g);
}
BoardView.prototype.renderVertexDevelopment = function (vertex, vertexDevelopment, svgEl) {
    var n = svgEl.firstChild
    for (; n && n.getAttribute("class") != "development-container"; n = n.nextSibling) { }

    if (!n) {
        n = document.createElementNS(this.svgns_, "g");
        n.setAttribute("class", "development-container");
        if (svgEl.firstChild) svgEl.insertBefore(n, svgEl.firstChild);
        else svgEl.appendChild(n);
    }

    var model = null;
    if (model = this.modelElements_[vertexDevelopment.model]) {
        var newNode = model.svgElement.cloneNode(true);
        var newPos = this.c(vertex.position_.x, vertex.position_.y);
        newNode.setAttribute("x", newPos.x - model.centerPosition.x);
        newNode.setAttribute("y", newPos.y - model.centerPosition.y);
        newNode.setAttribute("class", "vertex-development " + vertexDevelopment.player);
        n.appendChild(newNode);
        vertexDevelopment.svgEl_ = newNode;
    }
}
BoardView.prototype.renderVertexHitArea = function (vertex, svgEl) {
    var pp = this.c(vertex.position_.x, vertex.position_.y);

    var c = svgEl.ownerDocument.createElementNS(this.svgns_, "circle");
    c.setAttribute("cx", pp.x);
    c.setAttribute("cy", pp.y);
    c.setAttribute("r", this.edgeLength_ * 0.2);
    c.setAttribute("class", "vertex");

    var self = this;
    c.onclick = function (evt) { Event.fire(self, "vertexclick", [vertex, evt]); };
    c.onmouseover = function (evt) { Event.fire(self, "vertexover", [vertex, evt]); };
    c.onmouseout = function (evt) { Event.fire(self, "vertexout", [vertex, evt]); };

    svgEl.appendChild(c);
}

BoardView.prototype.renderHexes = function (svgEl) {
    for (var i = 0; i < this.board_.hex_.length; i++) {
        this.renderHex(this.board_.hex_[i], svgEl);
    }
}
BoardView.prototype.renderEdges = function (svgEl) {
    for (var i = 0; i < this.board_.edge_.length; i++) {
        this.renderEdge(this.board_.edge_[i], svgEl);
    }
}
BoardView.prototype.calculateEdgePoly = function (edgeWidth, p1, p2) {
    var l = edgeWidth;
    var xm = (p2.x - p1.x) / (p2.y - p1.y);
    var ym = 1.0 / xm;
    var dx = l / Math.sqrt(xm * xm + 1);
    var dy = l / Math.sqrt(ym * ym + 1);
    if (p2.x > p1.x) { dx = -dx; }
    if (p2.y > p1.y) { dy = -dy; }

    return [
        { x: p1.x - dx, y: p1.y + dy },
        { x: p2.x - dx, y: p2.y + dy },
        { x: p2.x + dx, y: p2.y - dy },
        { x: p1.x + dx, y: p1.y - dy }
    ];
}
BoardView.prototype.renderEdge = function (edge, svgEl) {
    var g = edge.svgEl_;
    if (!g) {
        g = document.createElementNS(this.svgns_, "g");
        svgEl.appendChild(g);
        edge.svgEl_ = g;
    }

    for (var i = 0; i < edge.edgeDevelopments_.length; i++) {
        this.renderEdgeDevelopment(edge, edge.edgeDevelopments_[i], g);
    }

    this.renderEdgeHitArea(edge, g);
}
BoardView.prototype.renderEdgeDevelopment = function (edge, edgeDevelopment, svgEl) {
    //TODO: how to represent models of roads? for now we just draw a poly...
    var n = svgEl.firstChild
    for (; n && n.getAttribute("class") != "development-container"; n = n.nextSibling) { }

    if (!n) {
        n = document.createElementNS(this.svgns_, "g");
        n.setAttribute("class", "development-container");
        if (svgEl.firstChild) svgEl.insertBefore(n, svgEl.firstChild);
        else svgEl.appendChild(n);
    }

    var p1 = this.c(edge.first_.x, edge.first_.y);
    var p2 = this.c(edge.second_.x, edge.second_.y);

    var pps = this.calculateEdgePoly(this.edgeLength_ * 0.075, p1, p2);

    var p = svgEl.ownerDocument.createElementNS(this.svgns_, "polygon");
    var points = "";
    for (var i = 0; i < pps.length; i++) {
        points += pps[i].x + "," + pps[i].y + " ";
    }

    p.setAttribute("points", points);
    p.setAttribute("class", "edge-development " + edgeDevelopment.player);
    n.appendChild(p);
    edgeDevelopment.svgEl_ = p;
}
BoardView.prototype.renderEdgeHitArea = function (edge, svgEl) {
    var p1 = this.c(edge.first_.x, edge.first_.y);
    var p2 = this.c(edge.second_.x, edge.second_.y);

    var pps = this.calculateEdgePoly(this.edgeLength_ * 0.1, p1, p2);

    var p = svgEl.ownerDocument.createElementNS(this.svgns_, "polygon");
    var points = "";
    for (var i = 0; i < pps.length; i++) {
        points += pps[i].x + "," + pps[i].y + " ";
    }

    p.setAttribute("points", points)
    p.setAttribute("class", "edge");
    svgEl.appendChild(p);

    var self = this;
    p.onclick = function (evt) { Event.fire(self, "edgeclick", [edge, evt]); };
    p.onmouseover = function (evt) { Event.fire(self, "edgeover", [edge, evt]); };
    p.onmouseout = function (evt) { Event.fire(self, "edgeout", [edge, evt]); };
}
BoardView.prototype.renderHex = function (hex, svgEl) {
    var g = hex.svgEl_;
    if (!g) {
        g = document.createElementNS(this.svgns_, "g");
        svgEl.appendChild(g);
        hex.svgEl_ = g;
    }

    var pp = this.hexCoords(hex.position_.x, hex.position_.y);
    var points = "";
    var pointsi = "";
    var cx = (pp[0].x + pp[1].x) / 2;
    var cy = (pp[0].y + pp[4].y) / 2;
    var alpha = 0.9;
    
    for (var i = 0; i < pp.length; i++) {
        points += pp[i].x + " " + pp[i].y + " ";
        pointsi += ((pp[i].x - cx)*alpha + cx) + " " + ((pp[i].y - cy)*alpha + cy) + " ";
    }
    var p = svgEl.ownerDocument.createElementNS(this.svgns_, "polygon");
    var pi = svgEl.ownerDocument.createElementNS(this.svgns_, "polygon");
    var hit = svgEl.ownerDocument.createElementNS(this.svgns_, "polygon");

    p.setAttribute("points", points);
    hit.setAttribute("points", pointsi);
    pi.setAttribute("points", pointsi);
    //HACK: replace with better way to style
    p.setAttribute("class", "hex");
    hit.setAttribute("class", "hex-hitarea");
    pi.setAttribute("class", "hex-inner " + hex.hexType_);
    g.appendChild(p);
    g.appendChild(pi);

    var self = this;
    hit.onclick = function (evt) { Event.fire(self, "hexclick", [hex, evt]); };
    hit.onmouseover = function (evt) { Event.fire(self, "hexover", [hex, evt]); };
    hit.onmouseout = function (evt) { Event.fire(self, "hexout", [hex, evt]); };

    var circ = svgEl.ownerDocument.createElementNS(this.svgns_, "circle");
    circ.setAttribute("cx", cx);
    circ.setAttribute("cy", cy);
    circ.setAttribute("r", Math.abs((pp[0].x - pp[1].x) / 3.75));
    circ.setAttribute("class", "hexlabel-back");
    g.appendChild(circ);

    var txt = svgEl.ownerDocument.createElementNS(this.svgns_, "text");
    txt.appendChild(svgEl.ownerDocument.createTextNode(hex.value_));
    var className = "hexlabel";
    if(hex.value_ == 6 || hex.value_ == 8) className += " labelemph";
    
    txt.setAttribute("class", className);
    txt.setAttribute("x", (pp[0].x + pp[1].x) / 2 );
    txt.setAttribute("y", (pp[0].y + pp[4].y) / 2 );

    g.appendChild(txt);
    
    g.appendChild(hit);
}

BoardView.prototype.highlightBuildableVertex = function(player) {
	//alert("blah");
	for(var i = 0; i < this.board_.vetex_.length; i++) {
		v = this.board_.vetex_[i];
		var buildable = true;
		if(v.vertexDevelopments_.length == 0) {
			// more than one vertex away from another city/settlement
			for(var j = 0; buildable && j < v.adjecentVertex_.length; j++) {
				va = v.adjecentVertex_[j];
				if(va.vertexDevelopments_.length > 0)
					buildable = false;
			}
			// connected by a road

			if(buildable) {
				var incomingroad = false;
				for(var j = 0; !incomingroad && j < v.edge_.length; j++) {
					ea = v.edge_[j];
					
					for(var k = 0; k < !incomingroad && ea.edgeDevelopments_.length; k++) {
						ed = ea.edgeDevelopments_[k];
						
						//console.log("edge development: " + ed.type + ", " + ed.player);
						if(ed.model == "road" && ed.player == player)
							incomingroad = true;
					}
				}
				buildable = incomingroad;
			}
		}
		else
			buildable = false;

		if(buildable) {
			console.log("buildabl!" + v.svgEl_.firstChild.getAttribute("class"));
			var el = null;
			for(el = v.svgEl_.firstChild; el && !/\bvertex\b/.test(el.getAttribute("class")); el = el.nextSibling) {};

			if(el) {
				this._highlight(el);
				console.log("found one!");
			}
		}
	}
}
BoardView.prototype.highlightBuildableEdge = function(player) {
	for(var i = 0; i < this.board_.edge_.length; i++) {
		var e = this.board_.edge_[i];
		var buildable = false;
		if(e.edgeDevelopments_.length == 0) {
			// is this road adjecent to any of the users cities/settlements?
			var adjecentVertexDev = false;
			for(var j = 0; !adjecentVertexDev && j < e.vertex_.length; j++) {
				va = e.vertex_[j];
				for(var k = 0; k < !adjecentVertexDev && va.vertexDevelopments_.length; k++) {
					vd = va.vertexDevelopments_[k];
					if(vd.player == player) 
						adjecentVertexDev = true;
				}
			}

			// or else look through the adjecent edges for roads...
			if(!adjecentVertexDev) {
				var adjecentRoad = false;
				for(var j = 0; !adjecentRoad && j < e.adjecentEdge_.length; j++) {
					ea = e.adjecentEdge_[j];
					for(var k = 0; !adjecentRoad && k < ea.edgeDevelopments_.length; k++) {
						ed = ea.edgeDevelopments_[k];
						if(ed.player == player)
							adjecentRoad = true;
					}
				}
			}
			
			buildable = (adjecentVertexDev || adjecentRoad);
		}

		if(buildable) {
			var el = null;
			for(el = e.svgEl_.firstChild; el && !/\bedge\b/.test(el.getAttribute("class")); el = el.nextSibling) {};

			if(el) {
				this._highlight(el);
				console.log("found a road!");
			}
		}
		
	}
}
BoardView.prototype.clearHighlights = function() {
	for(var i = 0; i < this.board_.vetex_.length; i++) {
		for(var el = this.board_.vetex_[i].svgEl_.firstChild; el; el = el.nextSibling) {
			this._clearHighlight(el);
		}
	}
	for(var i = 0; i < this.board_.edge_.length; i++) {
		for(var el = this.board_.edge_[i].svgEl_.firstChild; el; el = el.nextSibling) {
			this._clearHighlight(el);
		}
	}
}



BoardView.prototype._highlight = function(svgEl) {
	svgEl.setAttribute("class", svgEl.getAttribute("class") + " highlighted");
//	svgEl.style.fill = "rgba(100,255,100,0.3)";
}
BoardView.prototype._clearHighlight = function(svgEl) {
	var cname = svgEl.getAttribute("class");
	cname = cname.replace("highlighted", "");
	svgEl.setAttribute("class", cname);
//	svgEl.style.fill = "inherit";
}

