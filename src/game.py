from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext.webapp import template
from google.appengine.api import users
from google.appengine.api import channel
from google.appengine.ext import db
from google.appengine.ext.webapp.util import login_required


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
        
        '''
        if not user:
            self.redirect(users.create_login_url(self.request.uri))
            return
        '''   
                 
        template_params = {
            'games': model.pagedBoards(0, 1000),
            #'games': model.queryBoards(0, 100, query_filters, sort_options),
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
            json.dump(dict(error="not signed in"), self.response.out)
            return
        
        s = application.get_live_game(gamekey)
                
        s.get_board().dump(self.response.out)
        
class CurrentPlayerByGameHandler(webapp.RequestHandler):
    def get(self, gamekey):
        user = users.get_current_user()
        if not user:
            json.dump(dict(error="not signed in"), self.response.out)
            return
        
        s = application.get_live_game(gamekey)
        
        if s is None:
            json.dump(dict(error="game is not live or does not exist"), self.response.out)
            return
        
        player = s.get_player_by_user(user)
        if player is None:
            json.dump(dict(error="player is not part of game"), self.response.out)
            return
        
        json.dump(player, self.response.out, cls=model.CurrentPlayerEncoder)
        
        
        
class ActionHandler(webapp.RequestHandler):
    def post(self, gamekey):
        user = users.get_current_user()
        #TODO: handle error better-- should this be a get maybe?
        if not user:
            json.dump(dict(error="not signed in"), self.response.out)
            return
                
        action = self.request.get("action")
        data = self.request.get("data")
        logging.info("data: " + self.request.get("data"))
        try: 
            data = json.loads(self.request.get("data"))
        except:
            pass
        
        s = application.get_live_game(gamekey)        
        
        ret = s.processAction(action, data, user)

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
        
        s = application.get_live_game(gamekey)
        
        if s is None:
            self.error(404)
            return
        
        color = s.joinUser(user)
        self.redirect("/game/%s/" % (gamekey,))
        
        
class GameHandler(webapp.RequestHandler):
    @login_required
    def get(self, gamekey):
        user = users.get_current_user()
        
        logging.info("gamekey %s" % (gamekey,))
        
        s = application.get_live_game(gamekey)
        
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
            'imageUrl' : model.userPicture(user.email())
        }

        path = os.path.join(os.path.dirname(__file__), 'templates/game.xhtml')
        self.response.out.write(template.render(path, template_params))

class TestResourcesHandler(webapp.RequestHandler):
    @login_required
    def get(self, gamekey):
        user = users.get_current_user()
        
        s = application.get_live_game(gamekey)
        
        if s is None:
            self.error(404)
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
        
        json.dump(player, self.response.out, cls=model.BoardEncoder)

class GameListHandler(webapp.RequestHandler):
    
    def get(self):
        filter_re = re.compile(r"(\w+)\s*(<|>|=|<=|>=|\!=|[Ii][Nn])\s*(.+)")
        email_re = re.compile(r"[A-Za-z][A-Za-z0-9_\-\.]*@[A-Za-z0-9\-\.]+")
        date_re = re.compile(r"(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})")
        #filter_re = re.compile(r"(P?<filt>\w+)(P?<op>\<|\>|\=|\<\=|\>\=|\!\=)(P?<arg>.+)")
        user = users.get_current_user()
        if not user:
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
                        
        games = model.queryBoards(offset, limit, filters, sorts)
        
        json.dump(games, self.response.out, cls=model.GameListEncoder)

class Application(webapp.WSGIApplication):
    live_games = dict()
    def get_live_game(self, gamekey):
        s = self.live_games.get(gamekey, None)
        if s is None:
            s = state.get_game(gamekey)
            if not s is None:
                self.live_games[s.get_game_key()] = s
                return s
        else:
            return s
        
        return None
    def __init__(self):
        handlers = [
            (r"/", MainHandler),
            (r"/game/(.*)/", GameHandler),
            (r"/game/(.*)/currentBoard", CurrentBoardByGameHandler),
            (r"/game/(.*)/action", ActionHandler),
            (r"/game/(.*)/join", JoinHandler),
            (r"/game/(.*)/currentPlayer", CurrentPlayerByGameHandler),
            (r"/gameList", GameListHandler),
            (r"/creategame", NewGameHandler),
            (r"/testModel", ModelTestHandler),
            (r"/testResources/(.*)/", TestResourcesHandler)
        ]
        settings = dict(debug=True)
        webapp.WSGIApplication.__init__(self, handlers, **settings)

application = Application()

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
