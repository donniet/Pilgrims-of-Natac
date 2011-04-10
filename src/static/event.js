var Event = {
    addListener: function (obj, event, listener, scope) {
        if (obj) {
            if (typeof obj.__listeners == "undefined") {
                obj.__listeners = new Object();
            }

            if (typeof obj.__listeners[event] == "undefined") {
                obj.__listeners[event] = new Array();
            }

            if (typeof scope == "undefined")
                obj.__listeners[event].push(listener);
            else
                obj.__listeners[event].push({ "listener": listener, "scope": scope });

            obj["on" + event] = function () {
                Event.fire(obj, event, arguments);
            };

            return obj.__listeners[event].length - 1;
        }
    },
    removeListener: function (obj, event, listener, scope) {
        if (obj && obj.__listeners && obj.__listeners[event]) {
            for (var i = 0; i < obj.__listeners[event].length; i++) {
                if (obj.__listeners[event][i] === listener) {
                    obj.__listeners[event][i] = null;
                    delete obj.__listeners[event][i];
                }
                else {
                    var l = obj.__listeners[event][i];
                    if (l && l.listener === listener && l.scope === scope) {
                        obj.__listeners[event][i] = null;
                        delete obj.__listeners[event][i];
                    }
                }
            }
        }
    },
    removeListenerById: function (obj, event, listenerId) {
        if (obj && obj.__listeners && obj.__listeners[event] && obj.__listeners[event][listenerId]) {
            obj.__listeners[event][listenerId] = null;
            delete obj.__listeners[event][listenerId];
        }
    },
    fire: function (obj, event, args) {
        if (obj && obj.__listeners && obj.__listeners[event]) {
            for (var i = 0; i < obj.__listeners[event].length; i++) {
                var f = obj.__listeners[event][i];
                if (typeof f == "function") {
                    // TODO: should the scope be the obj, the listener, or should it be passed in?
                    f.apply(obj, args);
                }
                else if (f && typeof f.listener == "function") {
                    f.listener.apply(f.scope, args);
                }
            }
        }
    }
};
