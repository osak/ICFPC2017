#include <bits/stdc++.h>

using namespace std;

const int create_node_count = 2;    // required count to create a new node
const int playout_count = 10000;        // times of playout
double C = 1.2;


struct Edge {
    int from;
    int to;
    int owner;
};

struct Game {
    int punter;
    int punter_id;
    int n;
    int mines;
    vector<int> mine;
    int m;
    vector<Edge> edge;
};

enum Command {
    HANDSHAKE,
    INIT,
    MOVE,
    END
};

map<int, int> is_mine;

istream &operator>>(istream &is, Game &g) {
    is >> g.punter >> g.punter_id >> g.n >> g.mines;
    g.mine.resize(g.mines);
    for (int i = 0; i < g.mines; ++i) {
        is >> g.mine[i];
    }
    is >> g.m;
    g.edge.resize(g.m);
    for (int i = 0; i < g.m; ++i) {
        is >> g.edge[i].from >> g.edge[i].to >> g.edge[i].owner;
        auto &e = g.edge[i];
    }
    return is;

}

ostream &operator<<(ostream &os, const Game &g) {
    os << g.punter << endl << g.punter_id << endl << g.n << endl << g.mines << endl;
    for (int i = 0; i < g.mines; ++i) {
        os << g.mine[i] << (i == g.mines - 1) ? "": " ";
    }
    os << endl << g.m << endl;
    for (int i = 0; i < g.m; ++i) {
        os << g.edge[i].from << ' ' << g.edge[i].to << ' ' << g.edge[i].owner << endl;
        auto &e = g.edge[i];
    }
    return os;
}

struct State {
    string s;
};

istream &operator>>(istream &is, State &s) {
    is >> s.s;
    return is;
}

ostream &operator<<(ostream &os, const State &s) {
    cout << s.s;
    return os;
}

struct Result {
    int edge;
    State state;
};

const int X = 10007;

long long hash_edge(const vector<Edge> &edge) {
    // TODO: too slow
    const int MOD = static_cast<const int>(1e9 + 7);
    long long hash = 0;
    for (int i = 0; i < edge.size(); ++i) {
        (hash += X * hash + edge[i].owner) %= MOD;
    }
    return hash;
}

inline double calc_ucb(double ex, int ni, int n) {
    return ex + C * sqrt(2 * log2(n) / ni);
}

struct UCBchild {
    double ex;
    int cnt;

    UCBchild() : ex(0), cnt(0) {}
};

struct UCBnode {
    map<int, UCBchild> ch;
    int cnt;

    UCBnode() : cnt(0) {}
};

map<long long, int> game_freq;
map<long long, UCBnode> game_to_node;

vector<vector<Edge>> G;
void buildGraph(const Game &game) {
    for (int i = 0; i < game.edge.size(); ++i) {
        G[game.edge[i].from].push_back(game.edge[i]);
        G[game.edge[i].to].push_back(game.edge[i]);
    }
}

int get_player_id(int punter_id, int punter, int turn) {
    return (turn + punter_id) % punter;
}

mt19937 mt = mt19937(static_cast<unsigned int>(1));
double mt_rand() {
    static auto rand = bind(uniform_real_distribution<double>(0.0, 100.0), mt);
    return rand();
}

// get candidate moves
vector<int> get_candidate(const Game &game, int turn, bool all = false) {
    vector<int> rest, cand;
    vector<int> visited(game.n);
    for (int i = 0; i < game.edge.size(); ++i) {
        if (game.edge[i].owner == get_player_id(game.punter_id, game.punter, turn)) {
            visited[game.edge[i].from] = visited[game.edge[i].to] = 1;
        }
    }
    for (int i = 0; i < game.edge.size(); ++i) {
        if (game.edge[i].owner == -1) {
            rest.push_back(i);
            if (visited[game.edge[i].from] || visited[game.edge[i].to]
                    || is_mine[game.edge[i].from] || is_mine[game.edge[i].to]) {
                cand.push_back(i);
            }
        }
    }
    if (all || cand.empty()) return rest;
    shuffle(rest.begin(), rest.end(), mt);
    for (int i = 0; i < min(game.edge.size() / 10, rest.size()); ++i) {
        cand.push_back(rest[i]);
    }
    return cand;
}

const int INF = static_cast<const int>(1e9);

vector<int> bfs(const vector<vector<int>> &G, int v) {
    int n = static_cast<int>(G.size());
    vector<int> dist(n, INF);

    queue<pair<int, int>> q;
    q.push(make_pair(v, 0));
    dist[v] = 0;
    while (!q.empty()) {
        auto &p = q.front();
        q.pop();

        for (auto nv: G[p.first]) {
            if (dist[nv] == INF) {
                dist[nv] = p.second + 1;
                q.emplace(nv, p.second + 1);
            }
        }
    }

    return dist;
}

// get the score of the game
long long calc_score(const Game &game, const vector<Edge> &edge, int turn) {
    // TODO: too slow
    long long score = 0;
    for (auto &mine : game.mine) {
        vector<vector<int>> org(game.n), res(game.n);
        for (auto &e : edge) {
            org[e.from].push_back(e.to);
            org[e.to].push_back(e.from);
            if (e.owner == get_player_id(game.punter_id, game.punter, turn)) {
                res[e.from].push_back(e.to);
                res[e.to].push_back(e.from);
            }
        }
        auto d1 = bfs(org, mine);
        auto d2 = bfs(res, mine);
        for (int i = 0; i < game.n; ++i) {
            if (d2[i] != INF) {
                score += d1[i] * d1[i];
            }
        }
    }

    return score;
}

long long calc_score(const Game &game, int turn) {
    return calc_score(game, game.edge, turn);
}

vector<long long> random_play(const Game &game, int turn) {
    auto edge = game.edge;
    auto cand = get_candidate(game, turn);
    // 隣接辺からランダム
    priority_queue<pair<double, int>> q;

    vector<int> inqueue(game.m);
    for (auto e: cand) {
        inqueue[e] = 1;
        q.emplace(mt_rand(), e);
    }

    while (!q.empty()) {
        auto p = q.top();
        q.pop();
        auto &e1 = edge[p.second];

        e1.owner = get_player_id(game.punter_id, game.punter, turn++);
        // TODO: reduce order..
        for (int i = 0; i < edge.size(); ++i) {
            auto &e2 = edge[i];
            if (e2.owner == -1 && !inqueue[i] && (e1.from == e2.from || e1.to == e2.to || e1.from == e2.to || e1.to == e2.from))  {
                inqueue[i] = 1;
                q.emplace(mt_rand(), i);
            }
        }
    }

    // score for punters
    vector<long long> result;
    for (int i = 0; i < game.punter; ++i) {
        result.push_back(calc_score(game, edge, i));
    }
    return result;
}

vector<long long> uct_search(Game &game, int turn) {
    long long hash_value = hash_edge(game.edge);
    int &cnt = game_freq[hash_value];
    if (cnt < create_node_count) {
        ++cnt;
        return random_play(game, turn);
    }

    UCBnode &v = game_to_node[hash_value];
    int idx = -1;
    double best = -1;

    // find the best move so far
    for (auto &e : get_candidate(game, turn)) {
        if (!v.ch[e].cnt) {
            idx = e;
            break;
        }
        double ucb = calc_ucb(v.ch[e].ex, v.ch[e].cnt, v.cnt);
        if (best < ucb) {
            best = ucb;
            idx = e;
        }
    }

    if (idx < 0) {
        vector<long long> result;
        for (int i = 0; i < game.punter; ++i) {
            result.push_back(calc_score(game, i));
        }
        return result;
    }
    game.edge[idx].owner = (game.punter_id + turn) % game.punter;
    // This res should be the score of the player playing the turn
    vector<long long> res = uct_search(game, (turn + 1) % game.punter);
    game.edge[idx].owner = -1;

    // propagate
    v.ch[idx].ex = ((v.ch[idx].ex * v.ch[idx].cnt) + res[turn]) / (v.ch[idx].cnt + 1);
    ++v.ch[idx].cnt;
    ++v.cnt;

    return res;
}

Result search(Game &game, int playout) {
    for (auto &m: game.mine) {
        is_mine[m] = 1;
    }

    long long hash = hash_edge(game.edge);
    UCBnode &root = game_to_node[hash];
    for (int i = 0; i < playout; ++i) uct_search(game, 0);

    int idx = -1;
    double best = -1;
    for (auto &e : get_candidate(game, 0)) {
        cerr << game.edge[e].from << ' ' << game.edge[e].to << ' ' << root.ch[e].ex << endl;
        double ucb1 = calc_ucb(root.ch[e].ex, root.ch[e].cnt, root.cnt);
        if (best >= ucb1) continue;
        best = ucb1, idx = e;
    }
    return Result{idx, {}};
}

/////////////////////////////////////////////////////////////////////////////////////////////

struct Settings {
    int n;
    vector<string> content;
};

istream &operator>>(istream &is, Settings &settings) {
    is >> settings.n;
    settings.content.resize(settings.n);
    for (int i = 0; i < settings.n; ++i) {
        is >> settings.content[i];
    }
    return is;
}

int main() {
    string command;
    cin >> command;

    map<string, Command> state_map{
            {"HANDSHAKE", HANDSHAKE},
            {"INIT",      INIT},
            {"MOVE",      MOVE},
            {"END",       END}
    };

    Game game;
    State state;
    Result result;
    Settings settings;
    switch (state_map.find(command)->second) {
        case HANDSHAKE:
            cout << "nitori-mu" << endl;
            break;
        case INIT:
            cin >> game >> settings;
            cerr << game << endl;
            cout << 0 << endl;
            cout << "tsurapoyo~" << endl;
            break;
        case MOVE:
            cin >> game >> settings >> state;
            result = search(game, playout_count / game.edge.size());
            cout << result.edge << '\n' << result.state;
            break;
        case END:
            break;
    }
}