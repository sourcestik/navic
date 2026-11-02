#pragma once
#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <limits>
#include <queue>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>
#include "json.hpp"

namespace navic {
using Json = nlohmann::json;
constexpr double earth_radius_m = 6371008.8;
constexpr double pi = 3.14159265358979323846;
struct Point { double lat{}, lon{}; };
inline double radians(double degrees) { return degrees * pi / 180.0; }
inline double haversine(Point a, Point b) {
    const double dlat = radians(b.lat - a.lat), dlon = radians(b.lon - a.lon);
    const double h = std::pow(std::sin(dlat / 2), 2) + std::cos(radians(a.lat)) *
        std::cos(radians(b.lat)) * std::pow(std::sin(dlon / 2), 2);
    return 2 * earth_radius_m * std::asin(std::sqrt(std::clamp(h, 0.0, 1.0)));
}
inline double bearing(Point a, Point b) {
    const double dlon = radians(b.lon - a.lon);
    return std::atan2(std::sin(dlon) * std::cos(radians(b.lat)),
        std::cos(radians(a.lat)) * std::sin(radians(b.lat)) -
        std::sin(radians(a.lat)) * std::cos(radians(b.lat)) * std::cos(dlon)) * 180 / pi;
}
enum class Mode { driving = 0, walking = 1, cycling = 2 };
inline int mode_bit(Mode mode) { return 1 << static_cast<int>(mode); }
struct Node {
    std::int64_t osm_id{};
    Point point;
    std::vector<std::size_t> outgoing;
    int out_modes{}, in_modes{};
};
struct Edge {
    std::size_t from{}, to{};
    double length{};
    std::array<double, 3> seconds{};
    std::size_t name{};
    int modes{};
};
struct Path {
    bool found{false};
    double distance{}, duration{}, search_ms{};
    std::size_t visited{};
    std::vector<std::size_t> edges;
};
struct Snap { std::size_t node{}; double distance{}; };

class Graph {
public:
    std::vector<Node> nodes;
    std::vector<Edge> edges;
    std::vector<std::string> names;
    Json metadata, places;
    std::array<std::vector<std::size_t>, 3> components;

    void index_components() {
        // Weak components are a cheap necessary connectivity check. They do not
        // imply directed reachability; Dijkstra/A* still make that final decision.
        for (int mode = 0; mode < 3; ++mode) {
            auto& parent = components[mode];
            parent.resize(nodes.size());
            std::vector<unsigned> rank(nodes.size(), 0);
            for (std::size_t i = 0; i < nodes.size(); ++i) parent[i] = i;
            auto root = [&](std::size_t node) {
                while (parent[node] != node) { parent[node] = parent[parent[node]]; node = parent[node]; }
                return node;
            };
            for (const auto& edge : edges) {
                if (!(edge.modes & (1 << mode))) continue;
                auto a = root(edge.from), b = root(edge.to);
                if (a == b) continue;
                if (rank[a] < rank[b]) std::swap(a, b);
                parent[b] = a;
                if (rank[a] == rank[b]) ++rank[a];
            }
            for (std::size_t i = 0; i < nodes.size(); ++i) parent[i] = root(i);
        }
    }

    void add_edge(Edge edge) {
        if (edge.from >= nodes.size() || edge.to >= nodes.size() || edge.name >= names.size() ||
            edge.modes <= 0 || edge.modes > 7 || !std::isfinite(edge.length) || edge.length < 0)
            throw std::runtime_error("Invalid graph edge");
        for (double t : edge.seconds)
            if (!std::isfinite(t) || t < 0) throw std::runtime_error("Invalid edge time");
        // Great-circle distance must not exceed edge cost: required for A*'s proof.
        edge.length = std::max(edge.length, haversine(nodes[edge.from].point, nodes[edge.to].point));
        nodes[edge.from].outgoing.push_back(edges.size());
        nodes[edge.from].out_modes |= edge.modes;
        nodes[edge.to].in_modes |= edge.modes;
        edges.push_back(edge);
    }

    static Graph load(const std::string& filename) {
        std::ifstream stream(filename);
        if (!stream) throw std::runtime_error("Cannot open graph: " + filename);
        std::string line;
        if (!std::getline(stream, line)) throw std::runtime_error("Missing graph header");
        Json document = Json::parse(line);
        Graph g;
        g.metadata = document.at("metadata");
        if (g.metadata.at("schema_version") != 1) throw std::runtime_error("Unsupported graph schema");
        g.names = document.at("names").get<std::vector<std::string>>();
        g.places = std::move(document.at("places"));
        const auto node_count = g.metadata.at("nodes").get<std::size_t>();
        const auto edge_count = g.metadata.at("edges").get<std::size_t>();
        if (node_count > 2000000 || edge_count > 5000000) throw std::runtime_error("Graph exceeds configured safety bound");
        document = nullptr;
        g.nodes.reserve(node_count);
        for (std::size_t i = 0; i < node_count; ++i) {
            if (!std::getline(stream, line)) throw std::runtime_error("Truncated node records");
            const auto row = Json::parse(line);
            Point p{row.at(1).get<double>(), row.at(2).get<double>()};
            if (!std::isfinite(p.lat) || !std::isfinite(p.lon) || std::abs(p.lat) > 90 || std::abs(p.lon) > 180)
                throw std::runtime_error("Invalid graph coordinate");
            g.nodes.push_back({row.at(0).get<std::int64_t>(), p, {}, 0, 0});
        }
        g.edges.reserve(edge_count);
        for (std::size_t i = 0; i < edge_count; ++i) {
            if (!std::getline(stream, line)) throw std::runtime_error("Truncated edge records");
            const auto row = Json::parse(line);
            g.add_edge({row.at(0).get<std::size_t>(), row.at(1).get<std::size_t>(), row.at(2).get<double>(),
                {row.at(3).get<double>(), row.at(4).get<double>(), row.at(5).get<double>()},
                row.at(6).get<std::size_t>(), row.at(7).get<int>()});
        }
        if (g.nodes.empty() || g.edges.empty()) throw std::runtime_error("Graph is empty");
        g.index_components();
        return g;
    }

    bool contains(Point point) const {
        const auto& box = metadata.at("bbox");
        return point.lat >= box.at(0).get<double>() && point.lon >= box.at(1).get<double>() &&
               point.lat <= box.at(2).get<double>() && point.lon <= box.at(3).get<double>();
    }

    Snap nearest(Point point, Mode mode, bool source) const {
        Snap best{0, std::numeric_limits<double>::infinity()};
        for (std::size_t i = 0; i < nodes.size(); ++i) {
            const int allowed = source ? nodes[i].out_modes : nodes[i].in_modes;
            if (!(allowed & mode_bit(mode))) continue;
            const double distance = haversine(point, nodes[i].point);
            if (distance < best.distance) best = {i, distance};
        }
        return best;
    }

    std::pair<Snap, Snap> snap_pair(Point source, Point destination, Mode mode, double limit) const {
        const auto& component = components[static_cast<int>(mode)];
        if (component.empty()) return {nearest(source, mode, true), nearest(destination, mode, false)};
        std::unordered_map<std::size_t, Snap> sources, destinations;
        Snap nearest_source{0, std::numeric_limits<double>::infinity()};
        Snap nearest_destination = nearest_source;
        for (std::size_t i = 0; i < nodes.size(); ++i) {
            auto collect = [&](Point p, int modes, auto& candidates, Snap& nearest_point) {
                if (!(modes & mode_bit(mode))) return;
                const double distance = haversine(p, nodes[i].point);
                if (distance < nearest_point.distance) nearest_point = {i, distance};
                if (distance > limit) return;
                const auto key = component[i];
                auto found = candidates.find(key);
                if (found == candidates.end() || distance < found->second.distance) candidates[key] = {i, distance};
            };
            collect(source, nodes[i].out_modes, sources, nearest_source);
            collect(destination, nodes[i].in_modes, destinations, nearest_destination);
        }
        auto result = std::make_pair(nearest_source, nearest_destination);
        double best = std::numeric_limits<double>::infinity();
        // Prefer the closest pair on a shared network over isolated parking loops.
        for (const auto& candidate : sources) {
            const auto other = destinations.find(candidate.first);
            if (other == destinations.end()) continue;
            const double gap = candidate.second.distance + other->second.distance;
            if (gap < best) { best = gap; result = {candidate.second, other->second}; }
        }
        return result;
    }

    Path shortest_path(std::size_t source, std::size_t destination, Mode mode, bool astar) const {
        if (source >= nodes.size() || destination >= nodes.size()) throw std::out_of_range("Node index");
        const auto started = std::chrono::steady_clock::now();
        const double infinity = std::numeric_limits<double>::infinity();
        const std::size_t missing = std::numeric_limits<std::size_t>::max();
        std::vector<double> best(nodes.size(), infinity);
        std::vector<std::size_t> parent_edge(nodes.size(), missing);
        struct Entry { double priority, distance; std::size_t node; };
        auto compare = [](const Entry& a, const Entry& b) {
            if (a.priority != b.priority) return a.priority > b.priority;
            return a.node > b.node;
        };
        std::priority_queue<Entry, std::vector<Entry>, decltype(compare)> frontier(compare);
        auto heuristic = [&](std::size_t node) {
            return astar ? haversine(nodes[node].point, nodes[destination].point) : 0.0;
        };
        best[source] = 0;
        frontier.push({heuristic(source), 0, source});
        Path path;
        while (!frontier.empty()) {
            const auto current = frontier.top(); frontier.pop();
            if (current.distance > best[current.node]) continue; // discard stale heap entries
            ++path.visited;
            if (current.node == destination) { path.found = true; break; }
            for (const auto edge_id : nodes[current.node].outgoing) {
                const auto& edge = edges[edge_id];
                if (!(edge.modes & mode_bit(mode))) continue;
                const double candidate = current.distance + edge.length;
                if (candidate < best[edge.to]) {
                    best[edge.to] = candidate;
                    parent_edge[edge.to] = edge_id;
                    frontier.push({candidate + heuristic(edge.to), candidate, edge.to});
                }
            }
        }
        if (path.found) {
            path.distance = best[destination];
            for (auto node = destination; node != source;) {
                const auto id = parent_edge[node];
                if (id == missing) throw std::runtime_error("Broken parent chain");
                path.edges.push_back(id);
                path.duration += edges[id].seconds[static_cast<int>(mode)];
                node = edges[id].from;
            }
            std::reverse(path.edges.begin(), path.edges.end());
        }
        path.search_ms = std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - started).count();
        return path;
    }

    Json describe(const Path& path, std::size_t source, Mode mode) const {
        const auto point_json = [](Point p) { return Json::array({p.lon, p.lat}); };
        Json coordinates = Json::array({point_json(nodes[source].point)});
        Json steps = Json::array();
        double previous_bearing = 0;
        std::string previous_name;
        for (std::size_t i = 0; i < path.edges.size(); ++i) {
            const auto& edge = edges[path.edges[i]];
            const auto& name = names[edge.name];
            const double heading = bearing(nodes[edge.from].point, nodes[edge.to].point);
            const double change = std::remainder(heading - previous_bearing, 360.0);
            const bool new_step = i == 0 || name != previous_name || std::abs(change) > 35;
            if (new_step) {
                const std::string maneuver = i == 0 ? "depart" : std::abs(change) > 150 ? "uturn" :
                    change > 35 ? "right" : change < -35 ? "left" : "continue";
                const std::string text = maneuver == "depart" ? "Head onto " : maneuver == "uturn" ? "Make a U-turn onto " :
                    maneuver == "right" ? "Turn right onto " : maneuver == "left" ? "Turn left onto " : "Continue on ";
                steps.push_back({{"maneuver", maneuver}, {"instruction", text + name}, {"road", name},
                    {"distance_m", 0.0}, {"duration_s", 0.0}, {"coordinate", point_json(nodes[edge.from].point)}});
            }
            auto& step = steps.back();
            step["distance_m"] = step["distance_m"].get<double>() + edge.length;
            step["duration_s"] = step["duration_s"].get<double>() + edge.seconds[static_cast<int>(mode)];
            coordinates.push_back(point_json(nodes[edge.to].point));
            previous_bearing = heading; previous_name = name;
        }
        // A valid GeoJSON LineString requires at least two positions, even for a zero-length route.
        if (coordinates.size() == 1) coordinates.push_back(coordinates.front());
        steps.push_back({{"maneuver", "arrive"}, {"instruction", "Arrive at the snapped destination"},
            {"road", ""}, {"distance_m", 0}, {"duration_s", 0}, {"coordinate", coordinates.back()}});
        return {{"geometry", {{"type", "LineString"}, {"coordinates", coordinates}}},
            {"distance_m", path.distance}, {"duration_s", path.duration}, {"steps", steps},
            {"visited_nodes", path.visited}, {"search_ms", path.search_ms}};
    }
};
} // namespace navic
