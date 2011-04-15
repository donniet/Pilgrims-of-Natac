from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext.webapp import template
from google.appengine.api import users
from google.appengine.api import channel
from google.appengine.ext import db
from google.appengine.ext.webapp.util import login_required


from django.utils import simplejson as json

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
        if not user:
            self.redirect(users.create_login_url(self.request.uri))
            return
        

        # query only games you have joined
        query_filters = [
            ('user', user),
            #('dateTimeCreated <', datetime.datetime.now().)
            #('gameKey', gameKey)
        ]
        sort_options = [
            "-dateTimeStarted",
        ]
                    
        template_params = {
            #'games': model.pagedBoards(0, 1000),
            'games': model.queryBoards(0, 100, query_filters, sort_options),
            'nick': user.nickname(),
            'imageUrl' : model.userPicture(user.email())
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
            (r"/creategame", NewGameHandler),
            (r"/testModel", ModelTestHandler),
            (r"/testResources/(.*)/", TestResourcesHandler)
        ]
        settings = dict(
            debug=True
        )
        webapp.WSGIApplication.__init__(self, handlers, **settings)

application = Application()

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
