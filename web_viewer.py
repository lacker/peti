#!/usr/bin/env python
"""
A server for a web viewer that lets you look through peti events.
"""

import cherrypy

class WebViewer(object):
    @cherrypy.expose()
    def index(self):
        return "hello peti web viewer world"

if __name__ == "__main__":
    cherrypy.config.update({
        "server.socket_host": "0.0.0.0",
        "server.socket_port": 9000,
    })

    cherrypy.quickstart(WebViewer())
