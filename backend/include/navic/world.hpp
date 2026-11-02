// Worldwide service adapters. Endpoint roots come only from server configuration.
#pragma once
#include "navic/graph.hpp"
#include <curl/curl.h>
#include <chrono>
#include <memory>
#include <mutex>
#include <stdexcept>

namespace world {
using navic::Json;
using navic::Point;

struct Failure : std::runtime_error {
    int status;
    std::string code;
    Failure(int status_, std::string code_, std::string message)
        : std::runtime_error(std::move(message)), status(status_), code(std::move(code_)) {}
};

inline size_t append_body(char* chunk, size_t size, size_t count, void* destination) {
    auto& body = *static_cast<std::string*>(destination);
    const size_t bytes = size * count;
    if (bytes > 8 * 1024 * 1024 - body.size()) return 0;
    try { body.append(chunk, bytes); } catch (...) { return 0; }
    return bytes;
}

inline Json get(const std::string& url) {
    std::unique_ptr<CURL, decltype(&curl_easy_cleanup)> client(curl_easy_init(), curl_easy_cleanup);
    if (!client) throw Failure(503, "PROVIDER_UNAVAILABLE", "Map service unavailable. Try again.");
    std::string body;
    curl_easy_setopt(client.get(), CURLOPT_URL, url.c_str());
    curl_easy_setopt(client.get(), CURLOPT_USERAGENT, "Navic/2.0 (https://github.com/sourcestik/navic)");
    curl_easy_setopt(client.get(), CURLOPT_CONNECTTIMEOUT, 4L);
    curl_easy_setopt(client.get(), CURLOPT_TIMEOUT, 18L);
    curl_easy_setopt(client.get(), CURLOPT_NOSIGNAL, 1L);
    curl_easy_setopt(client.get(), CURLOPT_ACCEPT_ENCODING, "");
    curl_easy_setopt(client.get(), CURLOPT_WRITEFUNCTION, append_body);
    curl_easy_setopt(client.get(), CURLOPT_WRITEDATA, &body);
    auto rc = curl_easy_perform(client.get());
    long status = 0;
    curl_easy_getinfo(client.get(), CURLINFO_RESPONSE_CODE, &status);
    if (rc != CURLE_OK || status == 429 || status >= 500)
        throw Failure(503, "PROVIDER_UNAVAILABLE", "Worldwide map service is busy or unreachable. Try again shortly.");
    auto result = Json::parse(body, nullptr, false);
    if (result.is_discarded() || (status != 200 && result.value("code", "") != "NoRoute" && result.value("code", "") != "NoSegment"))
        throw Failure(502, "PROVIDER_ERROR", "The worldwide service could not complete this request.");
    return result;
}

inline std::string encode(const std::string& value) {
    char* escaped = curl_easy_escape(nullptr, value.c_str(), static_cast<int>(value.size()));
    if (!escaped) throw std::bad_alloc();
    std::string result(escaped); curl_free(escaped); return result;
}

inline Json places(const std::string& url) {
    Json results = Json::array();
    const auto payload = get(url);
    if (!payload.contains("features") || !payload["features"].is_array())
        throw Failure(502,"PROVIDER_ERROR","Place search returned an unreadable response.");
    for (const auto& feature : payload["features"]) {
        const auto& props = feature.at("properties");
        const auto& xy = feature.at("geometry").at("coordinates");
        auto name = props.value("name", props.value("street", std::string{}));
        if (name.empty() || !xy.is_array() || xy.size()!=2) continue;
        std::string area;
        for (const auto* key : {"city","state","country"}) {
            auto part = props.value(key,std::string{});
            if (!part.empty() && part!=name && area.find(part)==std::string::npos)
                area += (area.empty() ? "" : ", ") + part;
        }
        results.push_back({{"name",name},{"source","photon"},{"id",props.value("osm_type",std::string("osm"))+props.at("osm_id").dump()},
            {"kind",props.value("osm_value",std::string("place"))},{"context",area},{"lat",xy[1]},{"lon",xy[0]}});
    }
    return results;
}

inline Json route(const std::string& root, Point a, Point b, const std::string& mode) {
    // Protect the shared FOSSGIS service across all profiles, including concurrent visitors.
    static std::mutex gate;
    static std::chrono::steady_clock::time_point next;
    {
        std::lock_guard<std::mutex> lock(gate);
        auto now = std::chrono::steady_clock::now();
        if (now < next) throw Failure(429,"ROUTER_BUSY","Please wait a second and try the route again.");
        next = now + std::chrono::seconds(1);
    }
    const std::string profile = mode=="driving" ? "car" : mode=="cycling" ? "bike" : "foot";
    auto coords = [](Point p){return std::to_string(p.lon)+","+std::to_string(p.lat);};
    const auto payload = get(root+"/routed-"+profile+"/route/v1/driving/"+coords(a)+";"+coords(b)
        +"?overview=simplified&steps=true&geometries=geojson&radiuses=1000;1000&generate_hints=false");
    if (payload.value("code","")=="NoRoute" || payload.value("code","")=="NoSegment")
        throw Failure(404,"NO_ROUTE","No "+mode+" route found between these locations. Choose points near connected roads.");
    if (payload.value("code","")!="Ok" || payload.at("routes").empty())
        throw Failure(502,"PROVIDER_ERROR","The routing service returned an unexpected result.");
    const auto& path = payload.at("routes").at(0);
    Json steps = Json::array();
    for (const auto& leg : path.at("legs")) for (const auto& step : leg.at("steps")) {
        const auto& m = step.at("maneuver");
        const auto type = m.value("type",std::string("continue"));
        const auto modifier = m.value("modifier",std::string{});
        const auto road = step.value("name",std::string{});
        std::string instruction;
        if (type=="depart") instruction="Depart";
        else if (type=="arrive") instruction="Arrive at your destination";
        else if (type.find("roundabout")!=std::string::npos || type=="rotary")
            instruction = m.contains("exit") ? "Take exit "+m.at("exit").dump()+" at the roundabout" : "Enter the roundabout";
        else instruction = type + (modifier.empty() ? "" : " "+modifier);
        if (!road.empty() && type!="arrive") instruction += " on "+road;
        instruction[0]=static_cast<char>(std::toupper(static_cast<unsigned char>(instruction[0])));
        steps.push_back({{"maneuver",type=="depart" || type=="arrive" ? type : modifier.find("left")!=std::string::npos ? "left" : modifier.find("right")!=std::string::npos ? "right" : "continue"},
            {"instruction",instruction},{"road",road},{"coordinate",m.at("location")},{"distance_m",step.at("distance")},{"duration_s",step.at("duration")}});
    }
    auto snap=[&](size_t i){const auto& w=payload.at("waypoints").at(i);
        return Json{{"lon",w.at("location").at(0)},{"lat",w.at("location").at(1)},{"distance_m",w.at("distance")}};};
    return {{"provider","osrm"},{"algorithm","osrm"},{"mode",mode},{"cached",false},{"geometry",path.at("geometry")},
        {"distance_m",path.at("distance")},{"duration_s",path.at("duration")},{"steps",steps},
        {"snapped",{{"source",snap(0)},{"destination",snap(1)}}},{"warnings",{"Estimated times exclude live traffic. Road availability depends on OpenStreetMap data and the selected mode."}}};
}
} // namespace world
