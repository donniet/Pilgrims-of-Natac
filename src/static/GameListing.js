var console;

if(!console) console = {log:function(){}};

function Evalable() {}
Evalable.prototype.eval = function(str) {
	return eval(str);
}

Date.prototype.addDays = function(days) {
	return new Date(this.getTime() + days*24*60*60*1000);
}

Date.parseISO = function(str) {
	var re = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})\.(\d{6})$/;

	var m = re.exec(str);
	
	if(m) {
		return new Date(Number(m[1]), Number(m[2])-1, Number(m[3]), 
			Number(m[4]), Number(m[5]), Number(m[6]), Number(m[7])/100);
	}
	return null;
}
Date.prototype.toISOString = function() {
	return this.getFullYear()+"-"+(this.getMonth()+1)+"-"+this.getDate()+"T"+this.getHours()+":"+this.getMinutes()+":"+this.getSeconds()+"."+(this.getMilliseconds()*100);
}
Date.prototype.format = function(format) {
	var mon = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
	
	return mon[this.getMonth()] + " " + this.getDate()+ ", " + this.getFullYear();
	
}

Date.prototype.toJSON = function(formatter) {
	return this.toISOString();
}
/*
Object.prototype.toJSON = function(formatter) {
	return this.toString();
}
*/
/*
 * @author Donnie
 * @desc binary search through a sorted array
 * @param val value to search for
 * @param comp optional comparer func (returns -1, 0, 1)
 */
Array.prototype.binarySearch = function(val, comp) {
	if(typeof comp == "undefined") comp = function(a,b) { if(a<b) return -1; else if(b<a) return 1; else return 0; };
	
	var m = 0;
	var M = this.length - 1;
	var c = 0;
	
	while(m <= M) {
		var i = Math.floor((M+m) / 2);
		c = comp(val, this[i]);
		if(c == 0) return i;
		if(c < 0) M = i-1;
		if(c > 0) m = i+1;
	}
	if(c < 0) return M;
	else return m;
}

function evalScope(str, obj) {
	var o = new Evalable();
	for(var k in obj) {
		o[k] = obj[k];
		console.log(obj[k]);
	}
	
	return o.eval(str);
}

function Column(valueBinding) {
	this.heading_ = null;
	this.valueBinding_ = valueBinding;
	this.displayBinding_ = null; // defaults to value binding
	this.groupBinding_ = null;
	this.sortable_ = false;
	this.sortField_ = null;
	this.sortGroups_ = new Array();
	this.sortGroupNames_ = new Array();
	this.colindex_ = -1;
	this.listing_ = null;
	this.sortDescending_ = false;
}
Column.prototype.setGroups = function(groups) {
	this.sortGroups_ = groups;
	return this;
}
Column.prototype.setGroupNames = function(groupNames) {
	this.sortGroupNames_ = groupNames;
	return this;
}
Column.prototype.setSortable = function(sortable) {
	this.sortable_ = sortable;
	return this;
}
Column.prototype.setDisplayBinding = function(displayBinding) {
	this.displayBinding_ = displayBinding;
	return this;
}
Column.prototype.setGroupBinding = function(groupBinding) {
	this.groupBinding_ = groupBinding;
	return this;
}
Column.prototype.setSortField = function(sortField) {
	this.sortField_ = sortField;
	return this;
}
Column.prototype.setHeading = function(heading) {
	this.heading_ = heading;
	return this;
}
Column.prototype.getSortable = function() {
	return this.sortable_;
}
Column.prototype.getDisplayBinding = function() {
	return this.displayBinding_;
}
Column.prototype.getGroupBinding = function() {
	return this.groupBinding_;
}
Column.prototype.getSortField = function() {
	return this.sortField_;
}
Column.prototype.getHeading = function() {
	return this.heading_;
}
Column.prototype.sort = function(descending) {
	if(typeof descending == "undefined")
		this.sortDescending_ = !this.sortDescending_;
	else this.sortDescending_ = descending;
	this.listing_.sortResults(this.colindex_, this.sortDescending_);
}
Column.prototype.evalData = function(row, rowindex, binding) {
	var p = {
		data: row,
		col: this.colindex_,
		row: rowindex,
		coldata: this
	};
	
	if(typeof binding == "string") {
		return evalScope(binding, p);
	}
	else if(typeof binding == "function") {
		return binding(p);
	}
	else return null;
}
Column.prototype.value = function(row, rowindex) {
	return this.evalData(row, rowindex, this.valueBinding_);	
}
Column.prototype.display = function(row, rowindex) {
	return this.evalData(row, rowindex, this.displayBinding_ ? this.displayBinding_ : this.valueBinding_);	
}
Column.prototype.group = function(row, rowindex) {
	return this.evalData(row, rowindex, this.groupBinding_ ? this.groupBinding_ : this.valueBinding_);
}
Column.prototype.groupName = function(row, rowindex) {
	if(this.sortGroupNames_.length == 0) return;
	
	var group = this.group(row, rowindex);
	
	var index = this.sortGroups_.binarySearch(group);
	if(index < 0) index = 0;
	if(index >= this.sortGroupNames_.length) index = this.sortGroupNames_.length - 1;
	
	return this.sortGroupNames_[index];
	
}
Column.prototype.renderHeading = function(el) {
	if(this.heading_ == null) return;
	
	var self = this;
	
	var txt = document.createTextNode(this.heading_);
	if(this.sortable_) {
		var a = document.createElement("a");
		a.onclick = function() { self.sort(); };
		a.href = "javascript:void(0)";
		a.appendChild(txt);
		el.appendChild(a);
	}
	else {
		el.appendChild(txt);
	}
}
Column.prototype.renderGroup = function(el, row, rowindex) {
	var ng = this.groupName(row, rowindex);
	
	var trg = document.createElement("tr");
	var tdg = document.createElement("td");
	tdg.setAttribute("colspan", this.listing_.columns_.length); 
	tdg.setAttribute("class", "group");
	if(typeof ng == "string")
		tdg.appendChild(document.createTextNode(ng));
	else
		tdg.appendChild(ng);
	trg.appendChild(tdg);
	el.appendChild(trg);
}
Column.prototype.render = function(el, row, rowindex) {
	var disp = this.display(row, rowindex);
	if(typeof disp == "string")
		el.appendChild(document.createTextNode(disp));
	else
		//HACK: this should at least be in a try/catch
		el.appendChild(disp);
}

function ActionsColumn(playersBinding, joinBinding, viewBinding) {
	Column.apply(this, [playersBinding]);
	this.playersBinding_ = playersBinding;
	this.joinBinding_ = joinBinding;
	this.viewBinding_ = viewBinding;
}
ActionsColumn.prototype = new Column();
ActionsColumn.setSortable = function(sortable) {
	if(sortable) throw "ActionsColumns cannot be sorted.";
}
ActionsColumn.prototype.players = function(row, rowindex) {
	return this.evalData(row, rowindex, this.playersBinding_);
}
ActionsColumn.prototype.joinUrl = function(row, rowindex) {
	return this.evalData(row, rowindex, this.joinBinding_);
}
ActionsColumn.prototype.viewUrl = function(row, rowindex) {
	return this.evalData(row, rowindex, this.viewBinding_);
}
ActionsColumn.prototype.render = function(el, row, rowindex) {
	//var value = this.value(row, rowindex);
	var players = this.players(row, rowindex);
	var joinUrl = this.joinUrl(row, rowindex);
	var viewUrl = this.viewUrl(row, rowindex);
	
	var ul = document.createElement("ul");
	var li = document.createElement("li");
	
	var joined = false;
	for(var i = 0; !joined && i < players.length; i++) {
		var p = players[i];
		if(p.user.email == this.listing_.userEmail_) {
			li.appendChild(document.createTextNode("joined"));
			joined = true;
		}
	}
	
	if(!joined) {
		var a = document.createElement("a");
		a.appendChild(document.createTextNode("join"));
		//TODO: remove hyperlink structure
		a.href = joinUrl;
		li.appendChild(a);
	}
	
	ul.appendChild(li);
	
	li = document.createElement("li");
		
	var a = document.createElement("a");
	a.appendChild(document.createTextNode("view"));
	a.href = viewUrl;
	li.appendChild(a);
	
	ul.appendChild(li);
	
	el.appendChild(ul);
}

function PlayersColumn(valueBinding) {
	Column.apply(this, [valueBinding]);
}
PlayersColumn.prototype = new Column();
PlayersColumn.setSortable = function(sortable) {
	if(sortable) throw "PlayersColumns cannot be sorted.";
}
PlayersColumn.prototype.render = function(el, row, rowindex) {
	var ul = document.createElement("ul");
	var players = this.value(row, rowindex);
	
	for(var i = 0; i < players.length; i++) {
		var p = players[i];
		var li = document.createElement("li");
		li.className = "player-" + p.color;
		
		var a = document.createElement("a");
		//TODO: escape the email
		a.href = "/player?email=" + p.user.email;
		a.appendChild(document.createTextNode(p.user.nickname));
		li.appendChild(a);
		
		li.appendChild(document.createTextNode(": " + p.score));
		
		ul.appendChild(li); 
	}
	el.appendChild(ul);
}

function GameListingService(url) {
	this.url_ = url;
}

/*
 * @author Donnie
 * @desc Queries the boards while sorting and filtering.
 * @param sorts Array of {field,desc} objects where desc refers to descending
 * @param filters Array of {field,value,op} objects where op is =,!=,<,>,<=,>=
 * @param offset is an integer offset of the records
 * @param limit is the record limit
 */
GameListingService.prototype.queryBoards = function(offset, limit, sorts, filters) {
	var sort = "";
	for(var i = 0; sorts && i < sorts.length; i++) {
		console.log("sorts");
		var s = sorts[i];
		if(s.desc) sort += "-" + s.field;
		else sort += s.field;
		
		if(i < sorts.length - 1) sort += ",";
	}
	var filter = "";
	for(var i = 0; filters && i < filters.length; i++) {
		console.log("filters");
		var f = filters[i];
		//TODO: json encode value
		filter += f.field + (f.op ? f.op : "=") + f.value;
	}
	
	var responder = new Object();
	
	this._execute({
			sorts: sort,
			filter: filter,
			limit: limit,
			offset: offset
		},
		responder
	);
	
	return responder;
}
GameListingService.prototype._execute = function(params, responder) {
	var self = this;
	$.ajax({url: this.url_, data: $.param(params), dataType: "text", type: "GET",
	    success: function(data) {
	    	//TODO: read in the JSON here...
	    	Event.fire(responder, "load", [eval("(" + data + ")")]);
		}, 
		error: function(response) {
			Event.fire(responder, "error", [response]);
			console.log("ERROR:", response);
		}
	});
}


function GameListing(userEmail, url) {
	this.userEmail_ = userEmail;

	this.url_ = url;
	this.service_ = new GameListingService(this.url_);
	this.el_ = null;
	this.tbody_ = null;
	
	this.columns_ = new Array();
	
	this.sortBy_ = -1;
	this.sorts_ = [];
	this.filters_ = [];
	this.limit_ = 100;
	this.offset_ = 0;
}
GameListing.prototype.addColumn = function(column) {
	var index = this.columns_.length;
	column.colindex_ = index;
	column.listing_ = this;
	this.columns_.push(column);
	return index;
}
GameListing.prototype.nextPage = function() {
	//HACK: this should be smarter-- maybe see if the result set is empty
	this.offset_ += this.limit_;
	this.refresh();
}
GameListing.prototype.prevPage = function() {
	//HACK: see note on nextPage method
	this.offset_ -= this.limit_;
	this.refresh();
}
GameListing.prototype.setLimit = function(limit) {
	if(limit > 0) {
		this.limit_ = limit;
		//QUESTION: Should we go back to the first page?
		this.offset_ = 0;
		this.refresh();
	}
}
GameListing.prototype.handleResults = function(results) {
	for(var i = this.tbody_.childNodes.length - 1; i >= 0; i--) {
		this.tbody_.removeChild(this.tbody_.childNodes[i]);
	}
	
	var group = null;
	
	for(var i = 0; i < results.length; i++) {
		var r = results[i];
		var tr = document.createElement("tr");
		for(var j = 0; j < this.columns_.length; j++) {
			var col = this.columns_[j];
			var td = document.createElement("td");
			
			var value = col.value(r, i);
			var display = col.display(r, i);
			
			if(this.sortBy_ == j) {
				var ng = col.groupName(r, i);
				
				if(ng != null && ng != group) {
					col.renderGroup(this.tbody_, r, i);
					group = ng;
				}
			}
			
			col.render(td, r, i);
			
			tr.appendChild(td);
		}
		this.tbody_.appendChild(tr);
	}
};
GameListing.prototype.addFilter = function(field, value, op) {
	this.filters_.push({field:field, value:value, op:op});
}
GameListing.prototype.clearFilters = function() {
	for(var i = 0; i < this.filters_.length; i++) {
		delete this.filters_[i];
	}
	delete this.filters_;
	this.filters_ = new Array();
}
GameListing.prototype.render = function(el) {
	var self = this;
	this.el_ = el;
	
	var t = document.createElement("table");
	t.setAttribute("border", "0");
	t.setAttribute("cellpadding", "0");
	t.setAttribute("cellspacing", "0");
	var colgroup = document.createElement("colgroup");
	var thead = document.createElement("thead");
	var tr = document.createElement("tr");
	for(var i = 0; i < this.columns_.length; i++) {
		var col = this.columns_[i];
		
		var c = document.createElement("col");
		if(col.className) c.className = col.className;
		colgroup.appendChild(c);
				
		var th = document.createElement("th");
		
		col.renderHeading(th);
		
		tr.appendChild(th);
	}
	thead.appendChild(tr);
	t.appendChild(colgroup);
	t.appendChild(thead);
	
	this.tbody_ = document.createElement("tbody");
	t.appendChild(this.tbody_);
	
	this.el_.appendChild(t);
	
	this.refresh();
}
GameListing.prototype.sortResults = function(sortby, descending) {
	if(sortby < 0 || sortby >= this.columns_.length) {
		throw "sortResults: sortby index out of bounds";
	}
	this.sortBy_ = sortby;
		
	var col = this.columns_[this.sortBy_];
	this.sorts_ = [{field: col.getSortField(), desc: !descending}];
		
	if(this.el_) this.refresh();
}
GameListing.prototype.clearSorts = function() {
	this.sorts_ = new Array();
}
GameListing.prototype.handleSort = function(colindex) {
	this.sortResults(colindex);
};
GameListing.prototype.refresh = function() {
	var self = this;
	
	var responder = this.service_.queryBoards(this.offset_, this.limit_, this.sorts_, this.filters_);
	
	Event.addListener(responder, "load", this.handleResults, this);
	
	Event.addListener(responder, "error", function(message) {
		//TODO: handle service error
	});
    
}