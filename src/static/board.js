

function HexStyle(modelEl, style) {
    this.modelEl_ = modelEl;
    this.style_ = style;
}

function HexDevelopment(modelEl) {
    this.modelEl_ = modelEl;
    this.style_ = style;
}
function EdgeDevelopment(modelEl) {
    this.modelEl_ = modelEl;
    this.style_ = style;
}
function VertexDevelopment(modelEl) {
    this.modelEl_ = modelEl;
    this.style_ = style;
}

/*
if the width of one hex is w imagine a grid with 
vertical lines every 0.5w and horizontal lines every 
sqrt(3)/2 w.  Each intersection of those lines is an 
x,y coordinate
*/

function Board(options) {
    this.svgns_ = "http://www.w3.org/2000/svg";
    this.edgeLength_ = !options || typeof options.edgeLength == "undefined" ? 85 : options.edegeLength;
    this.sqrt3over2_ = Math.sqrt(3)/2;
    this.modelElements_ = new Object();
    this.players_ = new Array();
    this.marginLeft_ = 20;
    this.marginTop_ = 20;

    this.hex_ = new Array();
    this.edge_ = new Array();
    this.vertex_ = new Array();
    this.listeners_ = new Object();
}
Board.prototype.loadJSON = function(obj) {
    this.hex_ = new Array();
    this.edge_ = new Array();
    this.vertex_ = new Array();

    var hexes = obj["hexes"];
    var hexdict = new Object();

    for(var i = 0; hexes && i < hexes.length; i++) {
	var h = new Hex(hexes[i]["x"], hexes[i]["y"], hexes[i]["type"], hexes[i]["value"]);
        this.addHex(h);
	hexdict[hexes[i]["id"]] = h;
        console.log("added hex: " + hexes[i]["id"] + ":" + hexes[i]["type"]);
    }
    var edges = obj["edges"];
    for(var i = 0; edges && i < edges.length; i++) {
        var e = new Edge(edges[i]["x1"], edges[i]["y1"], edges[i]["x2"], edges[i]["y2"]);
	console.log(edges[i]["hex"]);
	for(var j = 0; j < edges[i]["hex"].length; j++) {
    	    var h = hexdict[edges[i]["hex"][j]];
	    h.edge_.push(e);
	    e.hex_.push(h);
	}
	this.addEdge(e);
    }
    var vertex = obj["vertex"];
    for(var i = 0; vertex && i < vertex.length; i++) {
	var v = new Vertex(vertex[i]["x"], vertex[i]["y"]);
	for(var j = 0; j < vertex[i]["hex"].length; j++) {
	    var h = hexdict[vertex[i]["hex"][j]];
	    h.vertex_.push(v);
	    v.hex_.push(h);
        }

	for(var j = 0; j < vertex[i]["dev"].length; j++) {
	    d = vertex[i]["dev"][j];
	    console.log("development(" + vertex[i]["x"]+","+vertex[i]["y"]+")={"+d["type"]+","+d["color"]+"}");
	    v.addDevelopment({
		model: d["type"],
		player: "player-" + d["color"]
	    });
	}
	this.addVertex(v);
    }
    
    //TODO: pull verts and edges too
    //this.createVertexAndEdgesFromHex();
}
Board.prototype.setModelElement = function (modelName, svgEl, centerPosition) {
    this.modelElements_[modelName] = {
        "svgElement": svgEl,
        "centerPosition": centerPosition
    };
}
Board.prototype.placeSettlement = function(x, y, color) {
    for(var i = 0; i < this.vertex_.length; i++) {
        v = this.vertex_[i];
        if(v.position_.x == x && v.position_.y == y) {
            v.vertexDevelopments_ = [];
            v.addDevelopment({
		model: "settlement",
		player: "player-" + color
	    });
	    break;
        }
    }
}
Board.prototype.placeCity = function(x, y, color) {
    for(var i = 0; i < this.vertex_.length; i++) {
        v = this.vertex_[i];
        if(v.position_.x == x && v.position_.y == y) {
            v.vertexDevelopments_ = [];
            v.addDevelopment({
		model: "city",
		player: "player-" + color
	    });
	    break;
        }
    }
}
Board.prototype.addListener = function (event, listener) {
    if (typeof this.listeners_[event] == "undefined") {
        this.listeners_[event] = new Array();
    }

    this.listeners_[event].push(listener);
}
Board.prototype.removeListener = function (event, listener) {
    if (this.listeners_[event]) {
        for (var i = 0; i < this.listeners_[event].length; i++) {
            if (listener === this.listeners_[event][i]) {
                this.listeners_[event][i] = null;
                delete this.listeners_[event][i];
            }
        }
    }
}
Board.prototype.fire = function (event, args) {
    if (this.listeners_[event]) {
        for (var i = 0; i < this.listeners_[event].length; i++) {
            var listener = this.listeners_[event][i];
            if (typeof listener == "function") {
                listener.apply(listener, args);
            }
        }
    }
}

/* transform grid coords to pixel coords */
Board.prototype.c = function (/* int */nx, /* int */ny) {
    /* returns x = nx * cos PI/3
    y = ny * sin PI/3 */
    
    var fx = 0.5 * nx * this.edgeLength_;
    var fy = this.sqrt3over2_ * ny * this.edgeLength_;


    /* perspective experiment */
    /*
    var centerOfView = {x:360, y:100};

    var theta = Math.PI / 3.0;
    //var theta = 0;
    var distance = 1000.0;

    var z = distance - fy * Math.sin(theta);
    fx = centerOfView.x + (fx - centerOfView.x) * distance / z;
    fy = centerOfView.y + (fy - centerOfView.y) * distance / z;
    */

    return {
        "x": fx + this.marginLeft_,
        "y": fy + this.marginTop_
    };
}
/*
Coords of a hex are (nx, ny) + {
   (1, 0), (3, 0), (4, 1), (3, 2), (1, 2), (0, 1)
}
*/

Board.prototype.hexCoords = function (nx, ny) {
    return [
      this.c(nx + 1, ny),
      this.c(nx + 3, ny),
      this.c(nx + 4, ny + 1),
      this.c(nx + 3, ny + 2),
      this.c(nx + 1, ny + 2),
      this.c(nx + 0, ny + 1)
   ];
}
Board.prototype.renderBoard = function (svgEl) {
    this.renderHexes(svgEl);
    this.renderEdges(svgEl);
    this.renderVertexes(svgEl);
}
Board.prototype.renderVertexes = function (svgEl) {
    for (var i = 0; i < this.vertex_.length; i++) {
        this.renderVertex(this.vertex_[i], svgEl);
    }
}
Board.prototype.renderVertex = function (vertex, svgEl) {
    var g = vertex.svgEl_;
    if (g == null) {
        g = document.createElementNS(this.svgns_, "g");
        svgEl.appendChild(g);
        vertex.svgEl_ = g;
    }

    for (var i = 0; i < vertex.vertexDevelopments_.length; i++) {
        this.renderVertexDevelopment(vertex, vertex.vertexDevelopments_[i], g);
    }

    this.renderVertexHitArea(vertex, g);
}
Board.prototype.renderVertexDevelopment = function (vertex, vertexDevelopment, svgEl) {
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
Board.prototype.renderVertexHitArea = function (vertex, svgEl) {
    var pp = this.c(vertex.position_.x, vertex.position_.y);

    var c = svgEl.ownerDocument.createElementNS(this.svgns_, "circle");
    c.setAttribute("cx", pp.x);
    c.setAttribute("cy", pp.y);
    c.setAttribute("r", this.edgeLength_ * 0.2);
    c.setAttribute("class", "vertex");

    var self = this;
    c.onclick = function () { self.fire("vertexclick", [vertex]); };
    c.onmouseover = function () { self.fire("vertexover", [vertex]); };
    c.onmouseout = function () { self.fire("vertexout", [vertex]); };

    svgEl.appendChild(c);
}

Board.prototype.renderHexes = function (svgEl) {
    for (var i = 0; i < this.hex_.length; i++) {
        this.renderHex(this.hex_[i], svgEl);
    }
}
Board.prototype.renderEdges = function (svgEl) {
    for (var i = 0; i < this.edge_.length; i++) {
        this.renderEdge(this.edge_[i], svgEl);
    }
}
Board.prototype.calculateEdgePoly = function (edgeWidth, p1, p2) {
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
Board.prototype.renderEdge = function (edge, svgEl) {
    var g = edge.svgEl_;
    if (g == null) {
        g = document.createElementNS(this.svgns_, "g");
        svgEl.appendChild(g);
        edge.svgEl_ = g;
    }

    for (var i = 0; i < edge.edgeDevelopments_.length; i++) {
        this.renderEdgeDevelopment(edge, edge.edgeDevelopments_[i], g);
    }

    this.renderEdgeHitArea(edge, g);
}
Board.prototype.renderEdgeDevelopment = function (edge, edgeDevelopment, svgEl) {
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
Board.prototype.renderEdgeHitArea = function (edge, svgEl) {
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
    p.onclick = function () { self.fire("edgeclick", [edge]); };
    p.onmouseover = function () { self.fire("edgeover", [edge]); };
    p.onmouseout = function () { self.fire("edgeout", [edge]); };
}
Board.prototype.renderHex = function (hex, svgEl) {
    var g = hex.svgEl_;
    if (g == null) {
        g = document.createElementNS(this.svgns_, "g");
        svgEl.appendChild(g);
        hex.svgEl_ = g;
    }

    var pp = this.hexCoords(hex.position_.x, hex.position_.y);
    var points = "";
    for (var i = 0; i < pp.length; i++) {
        points += pp[i].x + " " + pp[i].y + " ";
    }
    var p = svgEl.ownerDocument.createElementNS(this.svgns_, "polygon");

    p.setAttribute("points", points);
    //p.setAttribute("style", "fill:#cccccc;stroke:#000000;stroke-width:1");
    //HACK: replace with better way to style
    p.setAttribute("class", "hex " + hex.hexType_);
    g.appendChild(p);

    var self = this;
    p.onclick = function () { self.fire("hexclick", [hex]); };
    p.onmouseover = function () { self.fire("hexover", [hex]); };
    p.onmouseout = function () { self.fire("hexout", [hex]); };


    var txt = svgEl.ownerDocument.createElementNS(this.svgns_, "text");
    txt.appendChild(svgEl.ownerDocument.createTextNode(hex.value_));
    var color = (hex.value_ == 6 || hex.value_ == 8) ? "#FF0000" : "#000000";

    txt.setAttribute("style", "font-family:Verdana;font-size:24px;stroke:" + color + ";fill:" + color + ";");
    txt.setAttribute("x", (pp[0].x + pp[1].x) / 2 - 10);
    txt.setAttribute("y", (pp[0].y + pp[4].y) / 2 + 10);
    txt.onclick = function () { self.fire("hexclick", [hex]); };
    txt.onmouseover = function () { self.fire("hexover", [hex]); };
    txt.onmouseout = function () { self.fire("hexout", [hex]); };

    g.appendChild(txt);
}
Board.prototype.addHex = function(hex) {
    this.hex_.push(hex);
    hex.board_ = this;
    return hex;
}
Board.prototype.addVertex = function(vertex) {
    this.vertex_.push(vertex);
    vertex.board_ = this;
    return vertex;
}
Board.prototype.addEdge = function(edge) {
    this.edge_.push(edge);
    edge.board_ = this;
    return edge;
}

function Hex(x, y, hexType, value) {
    /* Hex vertexes will be: */
    this.position_ = { "x": typeof x == "undefined" ? 0 : x, "y": typeof y == "undefined" ? 0 : y };
    this.hexType_ = typeof hexType == "undefined" ? "unknown" : hexType;
    this.value_ = typeof value == "undefined" ? 0 : value;
    this.edge_ = new Array(); /* always 6 */
    this.vertex_ = new Array(); /* always 6 */
    this.adjecentHex_ = new Array(); /* between 1 and 6 */
    this.hexDevelopments_ = new Array(); /* robber or merchant */
    this.svgEl_ = null;
    this.board_ = null;
}

function Edge(x1, y1, x2, y2) {
    /* ASSERT(first.x < second.x) */
    this.first_ = { "x": typeof x1 == "undefined" ? 0 : x1, "y": typeof y1 == "undefined" ? 0 : y1 };
    this.second_ = { "x": typeof x2 == "undefined" ? 0 : x2, "y": typeof y2 == "undefined" ? 0 : y2 };
    this.hex_ = new Array(); /* between 1 and 2 */
    this.vertex = new Array(); /* always 2 */
    this.edgeDevelopments_ = new Array(); /* road */
    this.svgEl_ = null;
    this.board_ = null;
}
Edge.prototype.addDevelopment = function (development) {
    this.edgeDevelopments_.push(development);
    if (this.svgEl_ && this.board_) {
        this.board_.renderEdgeDevelopment(this, development, this.svgEl_);
    }
}
Edge.prototype.removeDevelopment = function (index) {
    var arr = new Array();
    for (var i = 0; i < this.edgeDevelopments_.length; i++) {
        var vd = this.edgeDevelopments_[i];
        if (i != index) {
            arr.push(vd);
        }
        else {
            vd.svgEl_.parentNode.removeChild(vd.svgEl_);
            vd.svgEl_ = null;
        }
    }
    delete this.edgeDevelopments_;
    this.edgeDevelopments_ = arr;
}

function Vertex(x, y) {
    this.position_ = { "x": typeof x == "undefined" ? 0 : x, "y": typeof y == "undefined" ? 0 : y };
    this.hex_ = new Array(); /* between 1 and 3 */
    this.edge_ = new Array(); /* between 2 and 3 */
    this.vertexDevelopments_ = new Array(); /* city, settlement, city wall, knight, etc. */
    this.svgEl_ = null;
    this.board_ = null;
}
Vertex.prototype.addDevelopment = function (vertexDevelopment) {
    this.vertexDevelopments_.push(vertexDevelopment);
    if (this.svgEl_ && this.board_) {
        this.board_.renderVertexDevelopment(this, vertexDevelopment, this.svgEl_);
    }
}
Vertex.prototype.removeDevelopment = function (index) {
    var arr = new Array();
    for (var i = 0; i < this.vertexDevelopments_.length; i++) {
        var vd = this.vertexDevelopments_[i];
        if (i != index) {
            arr.push(vd);
        }
        else {
            vd.svgEl_.parentNode.removeChild(vd.svgEl_);
            vd.svgEl_ = null;
        }
    }
    delete this.vertexDevelopments_;
    this.vertexDevelopments_ = arr;
}


Board.prototype.createVertexAndEdgesFromHex = function () {
    var edges = new Array();
    var vertex = new Array();
    for (var i = 0; i < this.hex_.length; i++) {
        var h = this.hex_[i];

        var hc = [
            { x: h.position_.x + 1, y: h.position_.y + 0 },
            { x: h.position_.x + 3, y: h.position_.y + 0 },
            { x: h.position_.x + 4, y: h.position_.y + 1 },
            { x: h.position_.x + 3, y: h.position_.y + 2 },
            { x: h.position_.x + 1, y: h.position_.y + 2 },
            { x: h.position_.x + 0, y: h.position_.y + 1 }
        ];

        // push the first edge
        edges.push({ points: [{ x: hc[0].x, y: hc[0].y }, { x: hc[5].x, y: hc[5].y}], hex: h });

        for (var j = 0; j < hc.length; j++) {
            var p1 = hc[j];
            if (j > 0) {
                var p2 = hc[j - 1];
                edges.push({ points: [{ x: p1.x, y: p1.y }, { x: p2.x, y: p2.y}], hex: h });
            }
            vertex.push({ x: p1.x, y: p1.y, hex: h });
        }
    }
    vertex.sort(function (a, b) {
        return a.x == b.x ? a.y < b.y : a.x < b.x;
    });

    var n = null;
    for (var i = 0; i < vertex.length; i++) {
        var v = vertex[i];
        if (n == null || n.position_.x != v.x || n.position_.y != v.y) {
            n = new Vertex(v.x, v.y);
            n.hex_.push(v.hex);
            this.addVertex(n);
        }
        else {
            n.hex_.push(v.hex);
        }
    }

    for (var i = 0; i < edges.length; i++) {
        var e = edges[i];
        if (e.points[0].x > e.points[1].x || e.points[0].x == e.points[1].x && e.points[0].y > e.points[0].y) {
            var p0 = e.points[0];
            var p1 = e.points[1];
            e.points[0] = p1;
            e.points[1] = p0;
        }
    }

    edges.sort(function (a, b) {
        if (a.points[0].x == b.points[0].x) {
            if (a.points[0].y == b.points[0].y) {
                if (a.points[1].x == b.points[1].x) {
                    return a.points[1].y < b.points[1].y;
                }
                else {
                    return a.points[1].x < b.points[1].x;
                }
            }
            else {
                return a.points[0].y < b.points[0].y;
            }
        }
        else {
            return a.points[0].x < b.points[0].x;
        }
    });

    var n = null;
    for (var i = 0; i < edges.length; i++) {
        var e = edges[i];
        if (n == null || n.first_.x != e.points[0].x || n.first_.y != e.points[0].y ||
            n.second_.x != e.points[1].x || n.second_.y != e.points[1].y) {
            n = new Edge(e.points[0].x, e.points[0].y, e.points[1].x, e.points[1].y);
            n.hex_.push(e.hex);
            this.addEdge(n);
        }
        else {
            n.hex_.push(e.hex);
        }
    }
}
