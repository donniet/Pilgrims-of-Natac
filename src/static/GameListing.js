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

Date.prototype.format = function(format) {
	var mon = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
	
	return mon[this.getMonth()] + " " + this.getDate()+ ", " + this.getFullYear();
	
}

function GameListing(userEmail, url) {
	this.userEmail_ = userEmail;

	this.url_ = url;
	this.el_ = null;
	this.tbody_ = null;
	
	//TODO: I don't like the binding mechanism.
	this.columns_ = [
		{heading:"Game Key", binding: "GameListing.anchorBinding(this.data.gameKey, '/game/'+this.data.gameKey+'/')", value:"this.data.gameKey", field:"gameKey", sortable:true, className:"gameKey"},
		{heading:"Owner", binding: "this.data.owner.nickname", value:"this.data.owner", field:"owner", sortable:true, className:"owner"},
		{heading:"Created", grouping:GameListing.dateGrouping, value:"this.data.dateTimeCreated", binding: "Date.parseISO(this.data.dateTimeCreated).format()", field:"dateTimeCreated", sortable:true, className:"created"},
		{heading:"Ended", grouping:GameListing.dateGrouping, value:"this.data.dateTimeEnded", binding:"this.data.dateTimeEnded ? Date.parseISO(this.data.dateTimeEnded).format() : 'ongoing'", field:"dateTimeEnded", sortable:true},
		{heading:"Players", binding: this.playerBinding, value:"this.data.players", field:"players", sortable:false }, 
		{heading:"", binding: this.joinBinding, sortable: false, className: "commands"}
	];
	
	this.sortBy_ = -1;
	this.sortDir_ = GameListing.SortDir.Ascending;
	this.sorts_ = [];
	this.filters_ = [];
	this.limit_ = 100;
	this.offset_ = 0;
}
GameListing.SortDir = {Ascending:"ASC", Descending:"DESC"};
GameListing.anchorBinding = function(text, href, opts) {
	var a = document.createElement("a");
	a.href = href;
	a.appendChild(document.createTextNode(text));
	return a;
}
GameListing.dateGrouping = function(valueStr, row, results) {
	var now = new Date();
	var today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
	var sunday = today.addDays(today.getDay());
	var lastsunday = sunday.addDays(-7);
	
	var value = Date.parseISO(valueStr);
	
	if(!value) {
		return "Ongoing";
	}
	else if(value > today) {
		console.log("group: Today");
		return "Today";
	}
	else if(value > today.addDays(-1)) {
		console.log("group: yesterday");
		return "Yesterday";
	}
	else if(value > sunday) {
		console.log("group: This"); 
		return "This Week";
	}
	else if(value > lastsunday) {
		console.log("group: Last");
		return "Last Week";
	}
	else if(value <= lastsunday) {
		console.log("group: More: " + value); 
		return "More than two weeks ago";
	}
	
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
GameListing.prototype.playerBinding = function(el, data, coldef, row, column, gameListing) {
	var ul = document.createElement("ul");
	for(var i = 0; i < data.players.length; i++) {
		var p = data.players[i];
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
GameListing.prototype.joinBinding = function(el, data, coldef, row, column, gameListing) {
	for(var i = 0; i < data.players.length; i++) {
		var p = data.players[i];
		if(p.user.email == gameListing.userEmail_) {
			el.appendChild(document.createTextNode("joined"));
			return;
		}
	}
	
	var a = document.createElement("a");
	a.appendChild(document.createTextNode("join"));
	a.href = "/game/" + data.gameKey + "/join";
	el.appendChild(a);
}
GameListing.prototype.createdBinding = function(el, data, coldef, row, column) {
	
	var txt = document.createTextNode(formatDate(data.dateTimeCreated));
	el.appendChild(txt);
}
GameListing.prototype.gameKeyBinding = function(el, data, coldef, row, column) {
	var a = document.createElement("a");
	a.appendChild(document.createTextNode(data.gameKey));
	a.href = "/game/" + data.gameKey + "/";
	el.appendChild(a);
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
			
			var obj = new Evalable();
			obj.data = r;
			obj.col = j;
			obj.row = i;
			obj.coldata = col;
			
			var value = null;
			
			if(typeof col.value == "string") {
				value = obj.eval(col.value);
			}
			else if(typeof col.value == "function") {
				value = col.value(r);
			}
			
			if(this.sortBy_ == j) {
				var ng = null;
				if(typeof col.grouping == "string") {
					ng = obj.eval(col.grouping);
				}
				else if(typeof col.grouping == "function") {
					ng = col.grouping(value, r, results);
				}
				
				if(ng != null && ng != group) {
					var trg = document.createElement("tr");
					var tdg = document.createElement("td");
					tdg.setAttribute("colspan", this.columns_.length); 
					tdg.setAttribute("class", "group");
					tdg.appendChild(document.createTextNode(ng));
					trg.appendChild(tdg);
					this.tbody_.appendChild(trg);
					group = ng;
				}
			}
			
			if(typeof col.binding == "function") {
				
				col.binding.apply(r, [td, r, col, i, j, this]);
			}
			else {
				
				var el = obj.eval(col.binding);
				
				if(typeof el == "string")
					td.appendChild(document.createTextNode(el));
				else 
					td.appendChild(el);
					
			}
			
			tr.appendChild(td);
		}
		this.tbody_.appendChild(tr);
	}
};
GameListing.prototype.createParams = function() {
	var sort = ""
	console.log("about to sort" + this.sorts_.length);
	for(var i = 0; i < this.sorts_.length; i++) {
		console.log("sorts");
		var s = this.sorts_[i];
		if(s.desc) sort += "-" + s.field;
		else sort += s.field;
		
		if(i < this.sorts_.length - 1) sort += ",";
	}
	return {
		sorts: sort,
		filter: "",
		limit: this.limit_,
		offset: this.offset_
	};
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
		
		var txt = document.createTextNode(col.heading);
		if(col.sortable) {
			var a = document.createElement("a");
			a.onclick = function(colindex) {
				return function() { self.handleSort(colindex); };
			}(i);
			a.href = "javascript:void(0)";
			a.appendChild(txt);
			th.appendChild(a);
		}
		else {
			th.appendChild(txt);
		}
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
GameListing.prototype.handleSort = function(colindex) {
	this.sortBy_ = colindex;
	var col = this.columns_[colindex];
	
	var i = 0;
	for(i = 0; i < this.sorts_.length; i++) {
		var s = this.sorts_[i];
		if(col.field == this.sorts_[i].field) {
			this.sorts_[i].desc = !this.sorts_[i].desc;
			this.sortDir_ = this.sorts_[i].desc ? GameListing.SortDir.Ascending : GameListing.SortDir.Descending;
			break;
		}
	}
	console.log("handleSort: " + col.field);
	if(i >= this.sorts_.length) {
		this.sorts_ = [{field: col.field, desc: false}];
		this.sortDir_ = GameListing.SortDir.Ascending;
		console.log("no sorts found, added one.");
	}
		
	this.refresh();
};
GameListing.prototype.refresh = function() {
	var self = this;
	$.ajax({url: this.url_, data: $.param(this.createParams()), dataType: "text", type: "GET",
        success: function(data) {
        	//TODO: read in the JSON here...
			self.handleResults(eval("(" + data + ")"));
		}, 
		error: function(response) {
    		console.log("ERROR:", response);
		}
    });
    
}