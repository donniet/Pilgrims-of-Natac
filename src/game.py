from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext.webapp import template
from google.appengine.api import users
from google.appengine.api import channel
from google.appengine.ext import db
from google.appengine.ext.webapp.util import login_required
from google.appengine.api import memcache
from google.appengine.api import mail
import email
from xml.sax.saxutils import escape


from django.utils import simplejson as json

import re
import os.path
import logging
import model
import datetime

from state import GameState
import state

application = None

class ModelTestHandler(webapp.RequestHandler):
    def get(self):
        s = GameState()
        
        
        s.get_board().dump(self.response.out)
        

class MainHandler(webapp.RequestHandler):
    def get(self):
        user = users.get_current_user()
        
        template_params = {
            'user' : user,
            'gameListingUrl': '/gameList',
            'imageUrl' : "" if user is None else model.userPicture(user.email()),
            'loginUrl' : users.create_login_url(self.request.uri),
            'logoutUrl' : users.create_logout_url(self.request.uri),
            'loggedin' : (not user is None),
            'creategameUrl' : '/creategame',
        }
                
        path = os.path.join(os.path.dirname(__file__), 'templates/main.xhtml')
        self.response.out.write(template.render(path, template_params))
        
class CurrentBoardByGameHandler(webapp.RequestHandler):
    # this is called by JS so we shouldn't use the @login_required which would redirect
    # instead just return an error
    def get(self, gamekey):
        user = users.get_current_user()
        if not user:
            #self.response.headers.add_header("Content-Type", "application/json")
            self.response.set_status(401)
            json.dump(dict(error="not signed in"), self.response.out)
            return
        
        s = get_live_game(gamekey)
        
        s.sendMessageUser(user, {"chat": "Welcome!"})
        
        #self.response.headers.add_header("Content-Type", "application/json") 
        #json.dump(ret, self.response.out, cls=model.BoardEncoder);
        
        #
        s.get_board().dump(self.response.out)


class CurrentTradeByGameHandler(webapp.RequestHandler):
    def get(self, gamekey):
        user = users.get_current_user()
        if not user:
            self.response.headers.add_header("Content-Type", "application/json")
            self.response.set_status(401)
            json.dump(dict(error="not signed in"), self.response.out)
            return
        
        s = get_live_game(gamekey)
        
        if s is None:
            json.dump(dict(error="game is not live or does not exist"), self.response.out)
            return
        
        trade = s.getCurrentTrade()
        #self.response.headers.add_header("Content-Type", "application/json")
        json.dump(trade, self.response.out, cls=model.BoardEncoder)
        
        
class CurrentPlayerByGameHandler(webapp.RequestHandler):
    def get(self, gamekey):
        user = users.get_current_user()
        if not user:
            self.response.headers.add_header("Content-Type", "application/json")
            self.response.set_status(401)
            json.dump(dict(error="not signed in"), self.response.out)
            return
        
        s = get_live_game(gamekey)
        
        if s is None:
            json.dump(dict(error="game is not live or does not exist"), self.response.out)
            return
        
        player = s.get_player_by_user(user)
        if player is None:
            json.dump(dict(error="player is not part of game"), self.response.out)
            return
        
        #self.response.headers.add_header("Content-Type", "application/json")
        json.dump(player, self.response.out, cls=model.CurrentPlayerEncoder)
        
        
        
class ActionHandler(webapp.RequestHandler):
    def post(self, gamekey):
        user = users.get_current_user()
        #TODO: handle error better-- should this be a get maybe?
        if not user:
            self.response.headers.add_header("Content-Type", "application/json")
            self.response.set_status(401)
            json.dump(dict(error="not signed in"), self.response.out)
            return
                
        action = self.request.get("action")
        data = self.request.get("data")
        logging.info("data: " + self.request.get("data"))
        try: 
            data = json.loads(self.request.get("data"))
        except:
            pass
        
        s = get_live_game(gamekey)        
        
        ret = s.processAction(action, data, user)

        self.response.headers.add_header("Content-Type", "application/json")
        json.dump(ret, self.response.out)

class NewGameHandler(webapp.RequestHandler):
    @login_required
    def get(self):
        user = users.get_current_user()
        
        gamekey = state.create_game(user)
                
        self.redirect("/game/%s/" % (gamekey,))

class JoinHandler(webapp.RequestHandler):
    @login_required
    def get(self, gamekey):
        user = users.get_current_user()
        
        s = get_live_game(gamekey)
        
        if s is None:
            self.error(404)
            return
        
        reservationKey = self.request.get("key")
        color = None
        
        logging.info("reservation key '%s'" % (reservationKey,))
        
        if reservationKey is None or len(reservationKey) == 0:
            color = s.joinUser(user)
            
        else:
            #having the key overrides the reservedFor setting in the database
            color = s.joinByReservation(user, reservationKey)
            
        if color is not None:
            self.redirect("/game/%s/" % (gamekey,))
        else:
            self.error(401)
        
class ReserveHandler(webapp.RequestHandler):
    def post(self, gamekey):
        user = users.get_current_user()
        
        self.response.headers.add_header("Content-Type", "application/json")
        
        s = get_live_game(gamekey)
        
        if s is None:
            self.error(404)
            return
        
        # you can only reserve a spot if you are the owner
        if s.get_board().owner != user:
            self.error(401)
            return
        
        reservedForEmail = self.request.get("reservedFor")
        logging.info("ReservedForEmail: %s" % reservedForEmail)
        #TODO: make sure it's a valid email address
        
        
        reservedFor = users.User(reservedForEmail)
        
        #TODO: put reservation time limit in configuration file
        reservationKey = s.reserve(reservedFor, 20)
        
        logging.info("Reservation Processing: %s" % reservationKey)
        
        if reservationKey is None:
            json.dump({"reserved":False}, self.response.out)
        else:            
            # send an email to them with the game key and reservation key
            self.send_invitation(user, gamekey, reservedForEmail, reservationKey)
            
            json.dump({"reserved":True}, self.response.out)
        

    def send_invitation(self, user, gamekey, reservedForEmail, key):        
        bodyPath = os.path.join(os.path.dirname(__file__), 'templates/reserve.txt')
        htmlPath = os.path.join(os.path.dirname(__file__), 'templates/reserve.html')
        
        params = {
            "domain":"pilgrimsofnatac.appspot.com",
            "path":"/game/%s/join?key=%s" % (gamekey,key),
        }
        
        mail.send_mail(sender=email.utils.formataddr((user.nickname(), user.email())),
                       to=reservedForEmail,
                       subject="Pilgrims of Natac Game Invitation",
                       body=template.render(bodyPath, params),
                       html=template.render(htmlPath, params))

     


class GameHandler(webapp.RequestHandler):
    @login_required
    def get(self, gamekey):
        user = users.get_current_user()
        
        logging.info("gamekey %s" % (gamekey,))
        
        s = get_live_game(gamekey)
        
        if s is None:
            #TODO: something more interesting here
            self.error(404)
            return
        
        tok = s.registerUser(user)
        color = s.get_user_color(user)
        nick = user.nickname()
        
        template_params = {
            'color' : color,
            'token' : tok,
            'gamekey' : gamekey,
            'nick': nick,
            'imageUrl' : escape(model.userPicture(user.email())),
            'isOwner': (s.get_board().owner == user),
            'reservationUrl':"reserve",
            'boardUrl':"currentBoard",
            'actionUrl':"action",
            'playerUrl':"currentPlayer",
            'tradeUrl':"currentTrade",
            'joinUrl':"join",
            'isStarted': (s.get_board().dateTimeStarted is not None),
        }
        
        self.response.headers.add_header("Content-Type", "application/xhtml+xml")
        
        path = os.path.join(os.path.dirname(__file__), 'templates/game.xhtml')
        self.response.out.write(template.render(path, template_params))

class TestResourcesHandler(webapp.RequestHandler):
    @login_required
    def get(self, gamekey):
        user = users.get_current_user()
        
        s = get_live_game(gamekey)
        
        if s is None:
            self.response.headers.add_header("Content-Type", "application/json")
            self.response.set_status(404)
            json.dump({"error": "game key not found."}, self.response.out)
            return
        
        tok = s.registerUser(user)
        color = s.joinUser(user)
        
        player = s.board.getPlayer(user)
        
        player.resetResources()
        player.adjustResources({"ore": 2, "wheat": 5})
        player.adjustResources({"ore": -1, "wheat": -2})
        if player.adjustResources({"brick": -1, "wheat": -2}, True):
            logging.error("error, we removed brick even though there isn't any")
        else:
            logging.info("successful")
        
        self.response.headers.add_header("Content-Type", "application/json");
        json.dump(player, self.response.out, cls=model.BoardEncoder)

class GameListHandler(webapp.RequestHandler):
    
    def get(self):
        filter_re = re.compile(r"(\w+)\s*(<|>|=|<=|>=|\!=|[Ii][Nn])\s*(.+)")
        email_re = re.compile(r"[A-Za-z][A-Za-z0-9_\-\.]*@[A-Za-z0-9\-\.]+")
        date_re = re.compile(r"(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})")
        #filter_re = re.compile(r"(P?<filt>\w+)(P?<op>\<|\>|\=|\<\=|\>\=|\!\=)(P?<arg>.+)")
        user = users.get_current_user()
        if not user:
            #self.response.headers.add_header("Content-Type", "application/json")
            self.response.set_status(401);
            json.dump({"error": "user not logged in."}, self.response.out)
            return
        
        offset = 0
        limit = 100
        
        try:
            offset = int(self.request.get("offset"))
        except:
            pass
    
        try:
            limit = int(self.request.get("limit"))
        except:
            pass
        
        filters = []
        sorts = []
        
        sortf = self.request.get("sorts")
        filterf = self.request.get("filter")
        
        if sortf:
            sorts = sortf.split(",")
        
        if filterf:
            filterarr = filterf.split(",")
            for f in filterarr:
                # ([A-Za-z0-9]+)((\<)|(\>)|(\=)|(\<\=)|(\>\=))([A-Za-z0-9]+)
                m = filter_re.match(f)
                if not m is None:
                    filt = m.group(1)
                    op = m.group(2)
                    arg_str = m.group(3)
                    
                    logging.info("filter: %s %s %s" % (filt,op,arg_str))
                    
                    dm = date_re.match(arg_str)
                    
                    if arg_str.find("@") >= 0:
                        arg = users.User(arg_str)
                        logging.info("user: %s" % (arg,))
                    elif not dm is None:
                        arg = datetime.date(int(dm.group("year")), int(dm.group("month")), int(dm.group("day")))
                    else:
                        try:
                            arg = json.loads("%s", (arg_str,))
                        except:
                            arg = arg_str
                         
                    filters.append((filt, op, arg))
                else:
                    logging.info("unmatched argument: %s" % (f,))
                        
        (count, games) = model.queryBoards(offset, limit, filters, sorts)
        
        #self.response.headers.add_header("Content-Type", "application/json");
        json.dump({"resultCount":count, "results":games}, self.response.out, cls=model.GameListEncoder)

def get_live_game(gamekey):
    #disable caching...
    return state.get_game(gamekey)
    '''
    s = memcache.get(gamekey)
    if s is None:
        logging.info("game '%s' not cached." % gamekey)
        s = state.get_game(gamekey)
        if s is not None:
            memcache.add(gamekey, s, 120)
    else:
        logging.info("game '%s' cached." % gamekey)
    return s
    '''

class Application(webapp.WSGIApplication):
    def __init__(self):
        handlers = [
            (r"/", MainHandler),
            (r"/game/(.*)/", GameHandler),
            (r"/game/(.*)/currentBoard", CurrentBoardByGameHandler),
            (r"/game/(.*)/action", ActionHandler),
            (r"/game/(.*)/join", JoinHandler),
            (r"/game/(.*)/currentPlayer", CurrentPlayerByGameHandler),
            (r"/game/(.*)/currentTrade", CurrentTradeByGameHandler),
            (r"/game/(.*)/reserve", ReserveHandler),
            (r"/gameList", GameListHandler),
            (r"/creategame", NewGameHandler),
            (r"/testModel", ModelTestHandler),
            (r"/testResources/(.*)/", TestResourcesHandler), 
        ]
        settings = dict(debug=True)
        webapp.WSGIApplication.__init__(self, handlers, **settings)

def main():
    run_wsgi_app(Application())

if __name__ == "__main__":
    main()
