#include "navic/graph.hpp"
#include <iostream>
#include <random>

using namespace navic;
int checks = 0;
void require(bool condition, const char* description) {
    ++checks;
    if (!condition) throw std::runtime_error(description);
}
Graph fixture() {
    Graph g; g.names = {"Test Road", "Footpath"};
    for (int i = 0; i < 5; ++i) g.nodes.push_back({i, {28.6, 77.0 + i * .001}, {}, 0, 0});
    g.add_edge({0, 1, 100, {10, 60, 25}, 0, 7});
    g.add_edge({1, 2, 100, {10, 60, 25}, 0, 7});
    g.add_edge({0, 2, 500, {50, 300, 125}, 0, 7});
    g.add_edge({2, 3, 100, {0, 60, 25}, 1, 6});
    g.metadata = {{"bbox", {28.5, 76.9, 28.7, 77.2}}};
    return g;
}
int main() {
    try {
        auto g = fixture();
        require(haversine({0, 0}, {0, 0}) == 0, "zero distance");
        require(std::abs(haversine({0, 0}, {0, 1}) - 111195.08) < .1, "known equatorial distance");
        require(std::isfinite(haversine({0, 0}, {0, 180})), "antipodal stability");
        auto d = g.shortest_path(0, 2, Mode::driving, false);
        auto a = g.shortest_path(0, 2, Mode::driving, true);
        require(d.found && d.edges.size() == 2 && d.distance == 200, "Dijkstra must improve the direct expensive path");
        require(a.distance == d.distance, "A* equals Dijkstra");
        require(d.duration == 20, "ETA sums chosen edge times");
        require(!g.shortest_path(2, 0, Mode::driving, true).found, "one-way edges");
        require(!g.shortest_path(0, 3, Mode::driving, true).found, "driving excludes footpath");
        require(g.shortest_path(0, 3, Mode::walking, true).found, "walking uses footpath");
        require(!g.shortest_path(0, 4, Mode::walking, false).found, "disconnected node");
        auto same = g.shortest_path(1, 1, Mode::walking, true);
        require(same.found && same.distance == 0 && same.edges.empty(), "same node route");
        require(g.describe(same, 1, Mode::walking)["geometry"]["coordinates"].size() == 2, "valid zero-length GeoJSON");
        auto snap = g.nearest({28.6, 77.003}, Mode::driving, false);
        require(snap.node == 2, "mode-aware destination snapping");
        bool rejected = false;
        try { g.add_edge({0, 1, -1, {1, 1, 1}, 0, 7}); } catch (...) { rejected = true; }
        require(rejected, "reject negative costs");
        g.add_edge({0, 1, 120, {1, 1, 1}, 0, 7});
        require(g.shortest_path(0, 2, Mode::driving, false).distance == 200, "parallel edge reconstruction");
        Graph parking; parking.names = {"Road"};
        for (const auto p : {Point{28.6, 77.0}, Point{28.6, 77.0001}, Point{28.6, 77.001}, Point{28.6, 77.002}})
            parking.nodes.push_back({0, p, {}, 0, 0});
        parking.add_edge({0, 1, 15, {1, 1, 1}, 0, 7});
        parking.add_edge({1, 0, 15, {1, 1, 1}, 0, 7});
        parking.add_edge({2, 3, 110, {1, 1, 1}, 0, 7});
        parking.add_edge({3, 2, 110, {1, 1, 1}, 0, 7});
        parking.index_components();
        auto snaps = parking.snap_pair({28.6, 77.0}, {28.6, 77.002}, Mode::driving, 120);
        require(parking.shortest_path(snaps.first.node, snaps.second.node, Mode::driving, true).found,
            "component-aware snapping avoids disconnected nearest-node pair");
        require(snaps.first.distance <= 120 && snaps.second.distance <= 120, "snapping respects per-endpoint bound");

        // Independent Floyd–Warshall oracle on seeded random directed graphs.
        // This catches errors that a Dijkstra-versus-A* comparison alone can miss.
        std::mt19937 rng(2026);
        for (int trial = 0; trial < 30; ++trial) {
            Graph random; random.names = {"Random road"};
            constexpr int count = 12;
            std::vector<std::vector<double>> oracle(count, std::vector<double>(count, 1e30));
            for (int i = 0; i < count; ++i) {
                random.nodes.push_back({i, {28.6 + (i / 4) * .001, 77.0 + (i % 4) * .001}, {}, 0, 0});
                oracle[i][i] = 0;
            }
            for (int i = 0; i < count; ++i) for (int j = 0; j < count; ++j) {
                if (i == j || rng() % 4 != 0) continue;
                const double cost = haversine(random.nodes[i].point, random.nodes[j].point) + 1 + rng() % 200;
                random.add_edge({static_cast<std::size_t>(i), static_cast<std::size_t>(j), cost, {cost, cost, cost}, 0, 7});
                oracle[i][j] = cost;
            }
            for (int k = 0; k < count; ++k) for (int i = 0; i < count; ++i) for (int j = 0; j < count; ++j)
                oracle[i][j] = std::min(oracle[i][j], oracle[i][k] + oracle[k][j]);
            for (int i = 0; i < count; ++i) for (int j = 0; j < count; ++j) for (bool astar : {false, true}) {
                auto path = random.shortest_path(i, j, Mode::driving, astar);
                require(path.found == (oracle[i][j] < 1e29), "oracle reachability");
                if (path.found) require(std::abs(path.distance - oracle[i][j]) < 1e-7, "oracle optimal distance");
            }
        }
        std::cout << "PASS: " << checks << " routing checks including independent Floyd–Warshall oracle\n";
    } catch (const std::exception& ex) { std::cerr << "FAIL: " << ex.what() << '\n'; return 1; }
}
