"""Exercise real HTTP handlers against controlled upstream responses, without external calls."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from threading import Thread
import pytest
from conftest import call


@pytest.fixture
def provider():
    state = {"paths": [], "status": 200, "response": {}}
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            state["paths"].append(self.path)
            self.send_response(state["status"])
            self.end_headers()
            self.wfile.write(json.dumps(state["response"]).encode())
        def log_message(self, *args):
            pass
    server = ThreadingHTTPServer(("127.0.0.1",0),Handler)
    thread = Thread(target=server.serve_forever,daemon=True)
    thread.start()
    yield "http://127.0.0.1:"+str(server.server_port),state
    server.shutdown()
    server.server_close()
    thread.join()


@pytest.mark.parametrize("mode,profile",[("walking","foot"),("cycling","bike"),("driving","car")])
def test_cross_border_route(api_factory,provider,mode,profile):
    url,state=provider
    start,end=[2.3522,48.8566],[4.3517,50.8503]
    state["response"]={"code":"Ok","waypoints":[{"location":p,"distance":5} for p in (start,end)],
      "routes":[{"distance":312000,"duration":13000,"geometry":{"type":"LineString","coordinates":[start,end]},
      "legs":[{"steps":[{"distance":10,"duration":3,"name":"Rue Victor Hugo","maneuver":{"type":"turn","modifier":"left","location":start}}]}]}]}
    api=api_factory(provider=url)
    status,data,_=call(api,"/route",{"source":{"lat":start[1],"lon":start[0]},"destination":{"lat":end[1],"lon":end[0]},"mode":mode})
    assert status==200 and data["algorithm"]=="osrm" and data["steps"][0]["maneuver"]=="left"
    assert state["paths"][0].startswith("/routed-"+profile+"/route/v1/driving/2.352200,48.856600;4.351700,50.850300")


@pytest.mark.parametrize("code,status,expected",[("NoRoute",400,404),("NoSegment",400,404),("Busy",503,503)])
def test_disconnected_or_unavailable(api_factory,provider,code,status,expected):
    url,state=provider
    state.update(response={"code":code},status=status)
    api=api_factory(provider=url)
    got,data,_=call(api,"/route",{"source":{"lat":40.71,"lon":-74},"destination":{"lat":51.51,"lon":-.12}})
    assert got==expected
    if expected==404: assert "No driving route" in data["error"]["message"]


def test_global_search_and_reverse(api_factory,provider):
    url,state=provider
    state["response"]={"features":[{"geometry":{"coordinates":[139.69,35.68]},"properties":{"osm_id":1,"osm_type":"R","name":"Tokyo","country":"Japan"}}]}
    api=api_factory(provider=url)
    for path in ["/geocode?q=Tokyo","/reverse-geocode?lat=35.68&lon=139.69"]:
        status,data,_=call(api,path)
        assert status==200
        place=data["result"] if "result" in data else data["results"][0]
        assert place["lon"]==139.69 and place["context"]=="Japan"
    assert all("bbox" not in p and "countrycode" not in p for p in state["paths"])
