#include "navic/graph.hpp"
#include "httplib.h"
#include <cctype>
#include <cstdlib>
#include <deque>
#include <functional>
#include <iostream>
#include <mutex>
#include <sstream>
#include <unordered_map>
#include <unordered_set>

using navic::Json;
using navic::Point;
using navic::Mode;
namespace {
struct ApiError : std::runtime_error {
    int status; std::string code;
    ApiError(int s, std::string c, const std::string& message) : std::runtime_error(message), status(s), code(std::move(c)) {}
};
std::string env(const char* key, const std::string& fallback) {
    const char* value = std::getenv(key); return value && *value ? value : fallback;
}
void send(httplib::Response& response, const Json& body, int status = 200) {
    response.status = status;
    response.set_content(body.dump(), "application/json; charset=utf-8");
}
void error(httplib::Response& response, int status, const std::string& code, const std::string& message) {
    send(response, {{"error", {{"code", code}, {"message", message}}}}, status);
}
std::string lower(std::string text) {
    for (auto& ch : text) ch = static_cast<char>(std::tolower(static_cast<unsigned char>(ch)));
    return text;
}
double number(const Json& value) {
    if (!value.is_number()) throw ApiError(422, "INVALID_COORDINATE", "Coordinates must be JSON numbers");
    const double result = value.get<double>();
    if (!std::isfinite(result)) throw ApiError(422, "INVALID_COORDINATE", "Coordinates must be finite");
    return result;
}
Point point(const Json& value) {
    if (!value.is_object() || !value.contains("lat") || !value.contains("lon"))
        throw ApiError(422, "INVALID_COORDINATE", "Each endpoint needs numeric lat and lon fields");
    Point p{number(value.at("lat")), number(value.at("lon"))};
    if (std::abs(p.lat) > 90 || std::abs(p.lon) > 180)
        throw ApiError(422, "INVALID_COORDINATE", "Latitude must be -90..90 and longitude -180..180");
    return p;
}
double query_number(const httplib::Request& request, const std::string& key) {
    if (!request.has_param(key)) throw ApiError(400, "MISSING_QUERY", "Missing query parameter: " + key);
    const auto value = request.get_param_value(key);
    try {
        std::size_t consumed = 0;
        double result = std::stod(value, &consumed);
        if (consumed != value.size() || !std::isfinite(result)) throw std::invalid_argument("number");
        return result;
    } catch (const std::exception&) { throw ApiError(400, "INVALID_QUERY", key + " must be a finite number"); }
}
Mode parse_mode(const std::string& mode) {
    if (mode == "driving") return Mode::driving;
    if (mode == "walking") return Mode::walking;
    if (mode == "cycling") return Mode::cycling;
    throw ApiError(422, "INVALID_MODE", "mode must be driving, walking or cycling");
}
std::string string_field(const Json& body, const char* field, const char* fallback) {
    if (!body.contains(field)) return fallback;
    if (!body.at(field).is_string()) throw ApiError(422, "INVALID_FIELD", std::string(field) + " must be a string");
    return body.at(field).get<std::string>();
}
std::string read_file(const std::string& path) {
    std::ifstream stream(path);
    if (!stream) throw std::runtime_error("Missing file: " + path);
    return std::string(std::istreambuf_iterator<char>(stream), {});
}
// Fixed-size FIFO cache. Search results are immutable JSON copied under the lock.
class RouteCache {
    std::mutex mutex;
    std::unordered_map<std::string, Json> values;
    std::deque<std::string> order;
public:
    bool get(const std::string& key, Json& value) {
        std::lock_guard<std::mutex> guard(mutex);
        auto found = values.find(key);
        if (found == values.end()) return false;
        value = found->second; return true;
    }
    void put(const std::string& key, const Json& value) {
        // A count limit alone can still retain huge routes. Keep large responses
        // uncached so 64 serialized entries cannot exceed 4 MiB in total.
        // The JSON object representation has additional allocation overhead.
        if (value.dump().size() > 64 * 1024) return;
        std::lock_guard<std::mutex> guard(mutex);
        if (values.count(key)) return;
        if (order.size() >= 64) { values.erase(order.front()); order.pop_front(); }
        values.emplace(key, value); order.push_back(key);
    }
};
class RateLimiter {
    struct Bucket { double tokens; std::chrono::steady_clock::time_point updated; };
    std::mutex mutex;
    std::unordered_map<std::string, Bucket> buckets;
    double capacity;
public:
    explicit RateLimiter(int per_minute) : capacity(per_minute) {}
    bool allow(const std::string& peer) {
        std::lock_guard<std::mutex> guard(mutex);
        const auto now = std::chrono::steady_clock::now();
        // Expire idle identities and cap cardinality to prevent unbounded memory use.
        if (buckets.size() >= 1024) {
            for (auto it = buckets.begin(); it != buckets.end();)
                if (now - it->second.updated > std::chrono::minutes(5)) it = buckets.erase(it); else ++it;
            if (buckets.size() >= 1024 && !buckets.count(peer)) return false;
        }
        auto [it, inserted] = buckets.emplace(peer, Bucket{capacity, now});
        auto& bucket = it->second;
        bucket.tokens = std::min(capacity, bucket.tokens +
            std::chrono::duration<double>(now - bucket.updated).count() * capacity / 60.0);
        bucket.updated = now;
        if (bucket.tokens < 1) return false;
        bucket.tokens -= 1; return true;
    }
};
} // namespace

int main(int argc, char** argv) {
    try {
        const auto started = std::chrono::steady_clock::now();
        const auto graph = navic::Graph::load(env("GRAPH_PATH", "data/graph.ndjson"));
        const auto network = read_file(env("NETWORK_PATH", "data/network.geojson"));
        const auto openapi = read_file(env("OPENAPI_PATH", "docs/openapi.json"));
        const auto swagger = read_file(env("SWAGGER_PATH", "docs/swagger.html"));
        if (argc == 2 && std::string(argv[1]) == "--check-data") {
            std::cout << "Verified " << graph.nodes.size() << " nodes, " << graph.edges.size()
                      << " edges, " << graph.places.size() << " places\n";
            return 0;
        }
        const int port = std::stoi(env("PORT", "8080"));
        const int per_minute = std::stoi(env("RATE_LIMIT_PER_MINUTE", "180"));
        if (port < 1 || port > 65535 || per_minute < 1 || per_minute > 10000)
            throw std::runtime_error("Invalid PORT or RATE_LIMIT_PER_MINUTE");
        const auto origins_text = env("ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8080,http://127.0.0.1:8080");
        std::unordered_set<std::string> origins;
        std::istringstream origin_stream(origins_text);
        for (std::string origin; std::getline(origin_stream, origin, ',');) origins.insert(origin);
        // Render supplies the canonical HTTPS origin after it assigns the service URL.
        const auto public_origin = env("RENDER_EXTERNAL_URL", "");
        if (!public_origin.empty()) origins.insert(public_origin);
        RouteCache cache;
        RateLimiter limiter(per_minute);
        httplib::Server server;
        server.new_task_queue = [] { return new httplib::ThreadPool(4, 4, 64); };
        server.set_payload_max_length(16 * 1024);
        server.set_read_timeout(10);
        server.set_write_timeout(15);
        server.set_keep_alive_max_count(50);
        server.set_pre_routing_handler([&](const httplib::Request& request, httplib::Response& response) {
            const auto origin = request.get_header_value("Origin");
            if (!origin.empty() && !origins.count(origin)) {
                error(response, 403, "ORIGIN_DENIED", "This browser origin is not in ALLOWED_ORIGINS");
                return httplib::Server::HandlerResponse::Handled;
            }
            if (request.method == "OPTIONS") {
                response.status = 204;
                return httplib::Server::HandlerResponse::Handled;
            }
            if ((request.path == "/route" || request.path == "/geocode" || request.path == "/reverse-geocode") &&
                !limiter.allow(request.remote_addr)) {
                response.set_header("Retry-After", std::to_string(static_cast<int>(std::ceil(60.0 / per_minute))));
                error(response, 429, "RATE_LIMITED", "Too many requests; wait briefly and try again");
                return httplib::Server::HandlerResponse::Handled;
            }
            return httplib::Server::HandlerResponse::Unhandled;
        });
        server.set_post_routing_handler([&](const httplib::Request& request, httplib::Response& response) {
            const auto origin = request.get_header_value("Origin");
            response.set_header("Vary", "Origin");
            response.set_header("X-Content-Type-Options", "nosniff");
            response.set_header("X-Frame-Options", "DENY");
            response.set_header("Referrer-Policy", "strict-origin-when-cross-origin");
            if (!origin.empty() && origins.count(origin)) {
                response.set_header("Access-Control-Allow-Origin", origin);
                response.set_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
                response.set_header("Access-Control-Allow-Headers", "Content-Type");
                response.set_header("Access-Control-Max-Age", "600");
            }
            if (request.path == "/route") response.set_header("Cache-Control", "no-store");
        });
        std::mutex log_mutex;
        server.set_logger([&](const httplib::Request& request, const httplib::Response& response) {
            std::lock_guard<std::mutex> guard(log_mutex);
            // Deliberately omit query strings, bodies and IP addresses from logs.
            std::clog << Json({{"method", request.method}, {"path", request.path}, {"status", response.status}}).dump() << '\n';
        });
        server.set_error_handler([](const httplib::Request&, httplib::Response& response) {
            if (response.body.empty()) error(response, response.status, "HTTP_ERROR", "Request could not be served");
        });
        server.set_exception_handler([](const httplib::Request&, httplib::Response& response, std::exception_ptr exception) {
            try { if (exception) std::rethrow_exception(exception); }
            catch (const ApiError& ex) { error(response, ex.status, ex.code, ex.what()); return; }
            catch (const Json::parse_error&) { error(response, 400, "INVALID_JSON", "Request body must be valid JSON"); return; }
            catch (const Json::exception&) { error(response, 422, "INVALID_FIELD", "Request contains invalid or missing fields"); return; }
            catch (const std::exception& ex) { std::cerr << "Request failed: " << ex.what() << '\n'; }
            error(response, 500, "INTERNAL_ERROR", "An unexpected error occurred");
        });
        auto checked = [&](Point p) {
            if (!graph.contains(p)) throw ApiError(422, "OUTSIDE_COVERAGE", "Point is outside the Delhi pilot coverage boundary");
        };
        server.Get("/health", [&](const auto&, auto& response) {
            send(response, {{"status", "ok"}, {"service", "navic-cpp"}, {"version", "1.0.0"},
                {"nodes", graph.nodes.size()}, {"edges", graph.edges.size()}, {"places", graph.places.size()},
                {"data_version", graph.metadata.at("data_version")}, {"uptime_s",
                std::chrono::duration<double>(std::chrono::steady_clock::now() - started).count()}});
        });
        server.Get("/coverage", [&](const auto&, auto& response) {
            auto result = graph.metadata;
            result["modes"] = {"driving", "walking", "cycling"};
            result["algorithms"] = {"dijkstra", "astar"}; result["max_snap_m"] = 800;
            result["snap_strategy"] = "nearest nodes on a shared weakly connected component when available";
            send(response, result);
        });
        server.Get("/geocode", [&](const httplib::Request& request, auto& response) {
            const auto query = lower(request.get_param_value("q"));
            if (query.size() < 2 || query.size() > 120)
                throw ApiError(400, "INVALID_QUERY", "q must contain 2–120 UTF-8 bytes");
            int limit = 6;
            if (request.has_param("limit")) {
                const auto value = query_number(request, "limit");
                if (value < 1 || value > 10 || std::floor(value) != value)
                    throw ApiError(400, "INVALID_QUERY", "limit must be an integer from 1 to 10");
                limit = static_cast<int>(value);
            }
            std::vector<std::pair<int, std::size_t>> matches;
            for (std::size_t i = 0; i < graph.places.size(); ++i) {
                const auto& place = graph.places[i];
                const auto name = lower(place.at("name").get<std::string>());
                const auto aliases = lower(place.at("aliases").get<std::string>());
                int score = name == query ? 0 : name.rfind(query, 0) == 0 ? 1 :
                    name.find(query) != std::string::npos ? 2 : aliases.find(query) != std::string::npos ? 3 : 99;
                if (score < 99) matches.push_back({score + (place.at("kind") == "road" ? 4 : 0), i});
            }
            std::stable_sort(matches.begin(), matches.end());
            Json results = Json::array();
            std::unordered_set<std::string> seen;
            for (const auto& match : matches) {
                auto place = graph.places[match.second];
                const auto name = place.at("name").get<std::string>();
                if (!seen.insert(lower(name)).second) continue;
                place.erase("aliases"); results.push_back(place);
                if (results.size() == static_cast<std::size_t>(limit)) break;
            }
            send(response, {{"results", results}, {"provider", "local_osm_gazetteer"}});
        });
        server.Get("/reverse-geocode", [&](const httplib::Request& request, auto& response) {
            Point p = point({{"lat", query_number(request, "lat")}, {"lon", query_number(request, "lon")}});
            checked(p);
            double best = std::numeric_limits<double>::infinity();
            Json nearest = nullptr;
            for (const auto& place : graph.places) {
                const auto distance = navic::haversine(p, {place.at("lat"), place.at("lon")});
                if (distance < best) { best = distance; nearest = place; }
            }
            if (!nearest.is_null()) { nearest.erase("aliases"); nearest["distance_m"] = best; }
            send(response, {{"result", nearest}, {"approximate", true}, {"provider", "local_osm_gazetteer"}});
        });
        server.Post("/route", [&](const httplib::Request& request, auto& response) {
            auto content_type = lower(request.get_header_value("Content-Type"));
            const auto delimiter = content_type.find(';');
            if (delimiter != std::string::npos) content_type.resize(delimiter);
            if (content_type != "application/json") throw ApiError(415, "CONTENT_TYPE", "Use Content-Type: application/json");
            const auto body = Json::parse(request.body);
            if (!body.is_object() || !body.contains("source") || !body.contains("destination"))
                throw ApiError(422, "MISSING_ENDPOINT", "Provide source and destination objects");
            const Point source = point(body.at("source")), destination = point(body.at("destination"));
            checked(source); checked(destination);
            const auto mode_name = string_field(body, "mode", "driving");
            const auto algorithm = string_field(body, "algorithm", "astar");
            const auto mode = parse_mode(mode_name);
            if (algorithm != "astar" && algorithm != "dijkstra")
                throw ApiError(422, "INVALID_ALGORITHM", "algorithm must be astar or dijkstra");
            auto [a, b] = graph.snap_pair(source, destination, mode, 800);
            if (navic::haversine(source, destination) < 0.001) b = a;
            if (a.distance > 800 || b.distance > 800)
                throw ApiError(422, "SNAP_TOO_FAR", "No usable road node within 800 m; choose a point closer to a road");
            const auto key = std::to_string(a.node) + ":" + std::to_string(b.node) + ":" + mode_name + ":" + algorithm;
            Json result;
            const bool cached = cache.get(key, result);
            if (!cached) {
                const auto path = graph.shortest_path(a.node, b.node, mode, algorithm == "astar");
                if (!path.found) throw ApiError(404, "NO_ROUTE", "No route connects these road nodes for the selected mode within coverage");
                result = graph.describe(path, a.node, mode); cache.put(key, result);
            } else { result["search_ms"] = 0; result["visited_nodes"] = 0; }
            auto snap_json = [&](const navic::Snap& snap) {
                const auto& node = graph.nodes[snap.node];
                return Json{{"lat", node.point.lat}, {"lon", node.point.lon}, {"osm_id", node.osm_id}, {"distance_m", snap.distance}};
            };
            result["snapped"] = {{"source", snap_json(a)}, {"destination", snap_json(b)}};
            result["algorithm"] = algorithm; result["mode"] = mode_name; result["cached"] = cached;
            result["data_version"] = graph.metadata.at("data_version");
            result["warnings"] = {"Distance and ETA exclude the gaps between selected points and snapped road nodes.",
                "Snapping prefers nearby nodes on a shared road component; selected points may be inside isolated campus or parking areas.",
                "ETA uses fixed speeds, without traffic or waiting time.",
                "Basic guidance: turn restrictions, barriers and conditional access are not modeled."};
            if (a.node == b.node) result["warnings"].push_back("Both points snap to the same road node; road distance is zero.");
            send(response, result);
        });
        server.Get("/network", [&](const auto&, auto& response) {
            response.set_header("Cache-Control", "public, max-age=86400");
            response.set_content(network, "application/geo+json");
        });
        server.Get("/openapi.json", [&](const auto&, auto& response) { response.set_content(openapi, "application/json"); });
        server.Get("/docs", [&](const auto&, auto& response) { response.set_content(swagger, "text/html; charset=utf-8"); });
        server.set_mount_point("/", env("STATIC_DIR", "frontend/dist"));
        std::cout << "Navic ready: " << graph.nodes.size() << " nodes, " << graph.edges.size()
                  << " directed edges; http://localhost:" << port << std::endl;
        if (!server.listen(env("HOST", "0.0.0.0"), port)) throw std::runtime_error("Cannot bind HTTP listener");
    } catch (const std::exception& exception) {
        std::cerr << "Startup failed: " << exception.what() << '\n'; return 1;
    }
    return 0;
}
