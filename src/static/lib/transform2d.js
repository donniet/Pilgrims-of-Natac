
function Transform2d() {
	this.mat_ = new Array(9);
	this.inv_ = new Array(9);
	
	this.setIdentity();	
}
Transform2d.prototype.copy = function() {
	var ret = new Transform2d();
	
	for(var i = 0; i < 9; i++) {
		ret.mat_[i] = this.mat_[i];
		ret.inv_[i] = this.inv_[i];
	}
	
	return ret;
}
Transform2d.prototype.setIdentity = function() {
	var r = Transform2d.row;
	var c = Transform2d.col;
	
	for(var i = 0; i < 9; i++) {
		this.mat_[i] = (r(i) == c(i) ? 1 : 0);
		this.inv_[i] = this.mat_[i];
	}
}
Transform2d.__mult = function(mat1, mat2) {
	var ret = new Array(9);

	var r = Transform2d.row;
	var c = Transform2d.col;
	var x = Transform2d.index;
	
	for(var i = 0; i < 9; i++) {
		ret[i] = 0;
		for(var k = 0; k < 3; k++) {
			ret[i] += mat1[x(r(i),k)] * mat2[x(k,c(i))];
		}
	}
	
	return ret;
}
Transform2d.__trans = function(mat, vec) {
	var ret = new Array(2);
	
	var r = Transform2d.row;
	var c = Transform2d.col;
	var x = Transform2d.index;
	
	for(var i = 0; i < 2; i++) {
		ret[i] = 0;
		for(var j = 0; j < 3; j++) {
			ret[i] += mat[x(i,j)] * (j >= vec.length ? 1 : vec[j]);
		}
	}
	
	return ret;
}
Transform2d.prototype.translate = function(tx, ty) {
	var mat = [1,0, tx,
	           0,1, ty,
	           0,0, 1];
	var inv = [1,0,-tx,
	           0,1,-ty,
	           0,0, 1];
	
	this.__apply(mat, inv);
	
	return this;
}
Transform2d.prototype.rotate = function(theta) {
	var mat = [Math.cos(theta), -Math.sin(theta), 0, 
	           Math.sin(theta), Math.cos(theta), 0,
	           0,0,1];
	var inv = [Math.cos(theta),  Math.sin(theta), 0, 
	           -Math.sin(theta), Math.cos(theta), 0,
	           0,0,1];
	
	this.__apply(mat, inv);
	
	return this;
}
Transform2d.prototype.scale = function(sx, sy) {
	if(typeof sy == "undefined") sy = sx;
	
	var mat = [sx, 0, 0,
	           0, sy, 0,
	           0, 0,  1];
	
	var inv = [1/sx, 0, 0,
	           0, 1/sy, 0,
	           0, 0,    1];
	
	this.__apply(mat, inv);
	
	return this;
}
Transform2d.prototype.skewX = function(thetaX) {
	var mat = [1, Math.tan(thetaX), 0,
	           0, 1, 0,
	           0, 0, 1];
	var inv = [1, Math.tan(-thetaX), 0,
	           0, 1, 0,
	           0, 0, 1];
	
	this.__apply(mat, inv);
	
	return this;
}
Transform2d.prototype.skewY = function(thetaY) {
	var mat = [1, 0, 0,
	           Math.tan(thetaY), 1, 0,
	           0, 0, 1];
	var inv = [1, 0, 0,
	           Math.tan(-thetaY), 1, 0,
	           0, 0, 1];
	
	this.__apply(mat, inv);
	
	return this;
}
Transform2d.prototype.transformTo = function(vec) {
	return Transform2d.__trans(this.mat_, vec);
}
Transform2d.prototype.transformFrom = function(vec) {
	return Transform2d.__trans(this.inv_, vec);
}
Transform2d.prototype.__apply = function(mat, inv) {

	//$(".chat-window").append("<p>mat: " + Transform2d.__mat2string(mat) + "</p>");
	//$(".chat-window").append("<p>mat_: " + Transform2d.__mat2string(this.mat_) + "</p>");
	
	var temp = Transform2d.__mult(mat, this.mat_);
	var itemp = Transform2d.__mult(this.inv_, inv);
	
	delete this.mat_;
	delete this.inv_;
	
	this.mat_ = temp;
	this.inv_ = itemp;
	

	//$(".chat-window").append("<p>result: " + Transform2d.__mat2string(this.mat_) + "</p>");
}
Transform2d.prototype.mult = function(transform) {
	var ret = new Transform2d();
	for(var i = 0; i < 9; i++) {
		ret.mat_[i] = this.mat_[i];
		ret.inv_[i] = this.inv_[i];
	}
	
	ret.__apply(transform.mat_, transform_.inv_);
	
	return ret;
}
Transform2d.prototype.toSVG = function() {
	return "matrix(" + 
				this.mat_[0] + "," + this.mat_[3] + "," + 
				this.mat_[1] + "," + this.mat_[4] + "," + 
				this.mat_[2] + "," + this.mat_[5] + ")";
}
Transform2d.prototype.toInvSVG = function() {
	return "matrix(" + 
				this.inv_[0] + "," + this.inv_[3] + "," + 
				this.inv_[1] + "," + this.inv_[4] + "," + 
				this.inv_[2] + "," + this.inv_[5] + ")";
}
Transform2d.__mat2string = function(mat) {
	var ret = "matrix(";
	for(var i = 0; i < 9; i++) {
		ret += mat[i];
		if(i < 8) ret += ",";
	}
	return ret + ")";
}
Transform2d.prototype.toString = function() {
	return Transform2d.__mat2string(this.mat_);
}
Transform2d.row = function(i) {
	return Math.floor(i/3);
}
Transform2d.col = function(i) {
	return i % 3;
}
Transform2d.index = function(row, col) {
	return 3 * row + col;
}