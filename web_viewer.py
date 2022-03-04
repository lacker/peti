#!/usr/bin/env python
"""
A server for a web viewer that lets you look through peti events.
"""

import cherrypy
import html
import json
import os
import random

from config import IMAGE_ROOT
from event import Event

EVENT_DIR = os.path.expanduser("~/petievents")

CACHE_VERSION = random.random()

def make_pre(lines):
    html_lines = ["<pre>"] + [html.escape(line) for line in lines] + ["</pre>", ""]
    return "\n".join(html_lines)
    

def session_sort_key(session):
    """
    We just want to sort so that 22A comes before 22B but 100 comes after 99
    """
    parts = session.split("_")
    converted = []
    for part in parts:
        try:
            converted.append(int(part))
        except:
            converted.append(part)
    return tuple(converted)


def img_src(filename):
    assert filename.startswith(IMAGE_ROOT)
    png = filename[len(IMAGE_ROOT):].strip("/")
    return f"../../../images/{png}?cacheversion={CACHE_VERSION}"

    
def load_events(session, machine):
    filename = f"{EVENT_DIR}/{session}/{machine}.events"
    events = [e for e in Event.load_list(filename)]
    events.sort(key=lambda e: -e.score())
    return events


class WebViewer(object):
    @cherrypy.expose()
    def index(self):
        """
        List the sessions we have data for
        """
        sessions = list(sorted(os.listdir(EVENT_DIR), key=session_sort_key))
        parts = ["<h1>PETI at Green Bank: Overview</h1>", f"<pre>we have data for {len(sessions)} sessions:</pre>"]
        for session in sessions:
            parts.append(f"<pre><a href='session/{session}'>{session}</a></pre>")
        return "\n".join(parts)

    
    @cherrypy.expose()
    def session(self, session):
        session_dir = EVENT_DIR + "/" + session
        machines = [filename.split(".")[0] for filename in sorted(os.listdir(session_dir))]
        parts = [f"<h1>PETI at Green Bank: Session {session}</h1>", f"<pre>we have event data from {len(machines)} machines:</pre>"]
        for machine in machines:
            parts.append(f"<pre><a href='../events/{session}/{machine}/1'>{machine}</a></pre>")
        return "\n".join(parts)

    
    @cherrypy.expose()
    def images(self, *args, **kwargs):
        """
        We just ignore kwargs, to let them be used for cache-busting.
        """
        for arg in args:
            assert not arg.startswith(".")
        path = "/".join([IMAGE_ROOT] + list(args))
        return cherrypy.lib.static.serve_file(path)

    
    @cherrypy.expose()
    def events(self, session, machine, page):
        page = int(page)
        events = load_events(session, machine)
        events_per_page = 100
        first_index = (page - 1) * events_per_page
        last_index = min(first_index + events_per_page - 1, len(events) - 1)

        parts = [f"<h1>PETI at Green Bank: Events</h1>",
                 f"<h2>session {session}, machine {machine}</h2>",
                 f"<pre>showing events {first_index}-{last_index} of {len(events)}</pre>"]

        if page != 1:
            prev_link = f"<a href='{page - 1}'>prev</a>"
        else:
            prev_link = "prev"

        if last_index != len(events) - 1:
            next_link = f"<a href='{page + 1}'>next</a>"
        else:
            next_link = "next"

        nav_bar = f"<pre>{prev_link} | {next_link}</pre>"
        parts.append(nav_bar)

        for i, event in enumerate(events[first_index:last_index + 1]):
            index = i + first_index
            img_tag = f"<img src='{img_src(event.plot_filename())})' height='640' style='margin:30'/>"
            parts.append(f"<a href='../../../detail/{session}/{machine}/{index}'>{img_tag}</a>")
        
        parts.append(nav_bar)
        return "\n".join(parts)


    @cherrypy.expose()
    def detail(self, session, machine, event_id):
        event_id = int(event_id)
        events = load_events(session, machine)
        event = events[event_id]
        parts = [f"<h1>PETI at Green Bank: Event Detail</h1>",
                 f"<h2>session {session}, {event.readable_day_range()}, machine {machine}, candidate event {event_id}</h2>"]
        parts.append(f"<img src='{img_src(event.plot_filename())}' height='960'/>")
        lines = json.dumps(event.to_plain(), indent=2).strip().split("\n")
        lines = [f"score: {event.score()}"] + lines
        parts.append(make_pre(lines))
        return "\n".join(parts)

    
if __name__ == "__main__":
    cherrypy.config.update({
        "server.socket_host": "0.0.0.0",
        "server.socket_port": 9000,
    })

    web_viewer = WebViewer()
    
    cherrypy.quickstart(web_viewer)
