from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext.webapp import template
from google.appengine.api import users
from google.appengine.api import channel


from django.utils import simplejson as json

import os.path
import logging

from state import GameState

application = None

class MainHandler(webapp.RequestHandler):
    def get(self):
        user = users.get_current_user()
        if not user:
            self.redirect(users.create_login_url(self.request.uri))
            return
            
        color = application.gameState.registerUser(user) 
        
        tok = channel.create_channel(user.user_id())
        
        template_params = dict(
            color=color,
            token=tok
        )
        path = os.path.join(os.path.dirname(__file__), 'templates/game.xhtml')
        #self.response.headers['Content-Type'] = "application/xml"
        self.response.out.write(template.render(path, template_params))
        

class CurrentBoardHandler(webapp.RequestHandler):
    def get(self):
        user = users.get_current_user()
        if not user:
            json.dump(dict(error="not signed in"), self.response.out)
            return
        
        json.dump(application.gameState.get_board(), self.response.out)
        
class ActionHandler(webapp.RequestHandler):
    def post(self):
        user = users.get_current_user()
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
                
        #print data
        
        ret = application.gameState.processAction(action, data, user)

        json.dump(ret, self.response.out)

class ResetHandler(webapp.RequestHandler):
    def get(self):
        user = users.get_current_user()
        if not user:
            json.dump(dict(error="not signed in"), self.response.out)
            return
        application.sendMessageAll({'action':'reset'})
        
        application.gameState = GameState()
        application.setupHandlers(application.gameState)
        

class Application(webapp.WSGIApplication):
    gameState = None
    def __init__(self):
        self.gameState = GameState()
        self.setupHandlers(self.gameState)
        
        handlers = [
            (r"/", MainHandler),
            (r"/currentBoard", CurrentBoardHandler),
            (r"/action", ActionHandler),
            (r"/reset", ResetHandler)
        ]
        settings = dict(
            debug=True
        )
        webapp.WSGIApplication.__init__(self, handlers, **settings)
    def setupHandlers(self, gameState):
        gameState.onReset += self.handleReset
        gameState.onPlaceSettlement += self.handlePlaceSettlement
        gameState.onPlaceCity += self.handlePlaceCity
        
    def sendMessageAll(self, message):
        for user in self.gameState.players:
            channel.send_message(user.user_id(), json.dumps(message))
    def handleReset(self):
        message = {'action': 'reset'}
        self.sendMessageAll(message)
    def handlePlaceSettlement(self, x, y, color):
        message = {'action': 'placeSettlement', 'x':x, 'y':y, 'color':color}
        self.sendMessageAll(message)
    def handlePlaceCity(self, x, y, color):
        message = {'action': 'placeCity', 'x':x, 'y':y, 'color':color}
        self.sendMessageAll(message)

application = Application()

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
