---
title: "GYM102759 - XXI Open Cup, Grand Prix of Korea"
date: 2025-10-15T19:29:00+08:00
tags: ["题解", "ICPC"]
description: "A、C、D、F、H、I、J、K 八题的题解。"
---

### A

```cpp
#include <bits/stdc++.h>
using namespace std;

/**
 * c[k] = cnt(b[i] >= k)
 * sum(min(b[i], k)), 1 <= i <= n = sum(c[j]), 1 <= j <= k
 */

#define int long long

const int N = 2.5e5 + 5;

struct segt {
    int sum, lmn;
} tr[N << 2];

#define ls i << 1
#define rs i << 1 | 1

inline void pushup(int i) {
    tr[i].sum = tr[ls].sum + tr[rs].sum;
    tr[i].lmn = min(tr[ls].lmn, tr[ls].sum + tr[rs].lmn);
}

inline void update(int l, int r, int x, int w, int i) {
    if (l == r) {
        tr[i].sum = tr[i].lmn = w;
        return;
    }
    int mid = l + r >> 1;
    if (x <= mid) update(l, mid, x, w, ls);
    else update(mid + 1, r, x, w, rs);
    pushup(i);
}

int n, m, q;

signed main() {
    ios::sync_with_stdio(false);
    cin.tie(0);

    cin >> n >> m;

    vector<int> a(n + 1);
    for (int i = 1; i <= n; i++) cin >> a[i];

    vector<int> b(m + 1);
    for (int i = 1; i <= m; i++) cin >> b[i];

    vector<int> c(n + 1);
    for (int i = 1; i <= m; i++) {
        c[1]++;
        if (b[i] + 1 <= n) c[b[i] + 1]--;
    }

    for (int i = 1; i <= n; i++) {
        c[i] += c[i - 1];
    }

    auto init_a = a;

    sort(a.begin() + 1, a.end(), greater{});

    auto upd = [&] (int i) -> void {
        update(1, n, i, c[i] - a[i], 1);
    };
    for (int i = 1; i <= n; i++) {
        upd(i);
    }

    cin >> q;

    for (int op, i; q--; ) {
        cin >> op >> i;

        if (op == 1) {
            int pos = lower_bound(a.begin() + 1, a.end(), init_a[i]++, greater{}) - a.begin();

            a[pos]++;
            upd(pos);
        } else if (op == 2) {
            int pos = upper_bound(a.begin() + 1, a.end(), init_a[i]--, greater{}) - a.begin();
            pos--;

            a[pos]--;
            upd(pos);
        } else if (op == 3) {
            b[i]++;
            if (b[i] <= n) {
                c[b[i]]++;
                upd(b[i]);
            }
        } else {
            if (b[i] <= n) {
                c[b[i]]--;
                upd(b[i]);
            }
            b[i]--;
        }

        cout << (tr[1].lmn >= 0) << "\n";
    }

    return 0;
}
```

### C

```cpp
#include <bits/stdc++.h>
using namespace std;

int n;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);

    cin >> n;

    vector<vector<int> > a(n, vector<int>(n));
    for (auto &v : a) for (auto &x : v) cin >> x;

    int ans = 0;
    for (int i = 0; i < n; i++) {
        for (int t = i + 1; t < n; t++) {
            if (a[i][t] == -1) continue;

            int mn = min(a[i][t], a[t][i]);
            ans += mn;
            a[i][t] -= mn, a[t][i] -= mn;
        }
    }

    const int inf = 1e9;

    vector<int> f(1 << n, inf);
    for (int i = 0; i < n; i++) f[1 << i] = 0;

    vector dp(1 << n, vector<vector<int> >(n, vector<int>(n, inf)));

    for (int s = 0; s < (1 << n); s++) {
        for (int i = 0; i < n; i++) {
            if (s >> i & 1 ^ 1) continue;

            for (int t = 0; t < n; t++) {
                if (s >> t & 1 ^ 1) continue;

                dp[s][i][t] = min(dp[s][i][t], f[s]);
                if (dp[s][i][t] == inf) continue;

                for (int j = 0; j < n; j++) {
                    if (s >> j & 1) continue;

                    if (a[i][j] != -1) {
                        dp[s | (1 << j)][j][t] = min(dp[s | (1 << j)][j][t], dp[s][i][t] + a[i][j]);
                        if (i != t && a[j][t] != -1) {
                            f[s | (1 << j)] = min(f[s | (1 << j)], dp[s][i][t] + a[i][j] + a[j][t]);
                        }
                    }
                }
            }
        }
    }

    if (f[(1 << n) - 1] == inf) {
        ans = -1;
    } else {
        ans = ans + f[(1 << n) - 1];
    }

    cout << ans << "\n";
    return 0;
}
```

### D

```cpp
#include <bits/stdc++.h>
using namespace std;

/**
 * (1, 2): 5
 * (1, 3): 1
 * (1, 4): 3
 * (2, 3): 1
 * (2, 4): 3
 * (3, 4): 1
 */

/**
 * (1, 2): 10
 * (1, 3): 20
 * (1, 4):
 * (2, 3): 10 <-> 30
 * (2, 4): 30
 * (3, 4): 40
 */

int n, m;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);

    cin >> n >> m;

    vector<array<int, 3> > e(m);
    for (auto &[a, b, w] : e) cin >> a >> b >> w;

    sort(e.begin(), e.end(), [&] (array<int, 3> a, array<int, 3> b) {
        return a[2] > b[2];
    });

    vector<int> p(n + 1), sz(n + 1, 1);
    iota(p.begin(), p.end(), 0);

    auto find = [&] (auto self, int x) -> int {
        if (x != p[x]) p[x] = self(self, p[x]);
        return p[x];
    };

    auto merge = [&] (int a, int b) -> void {
        a = find(find, a), b = find(find, b);
        if (a == b) return;
        if (sz[a] > sz[b]) swap(a, b);
        p[a] = b, sz[b] += sz[a];
    };

    long long ans = 0;

    for (int i = 0; i < m; ) {
        int t = i;
        while (t < m && e[t][2] == e[i][2]) {
            auto [a, b, w] = e[t];
            if (find(find, a) == find(find, b)) {
                cout << "-1\n";
                return 0;
            }
            t++;
        }

        while (i < t) {
            auto [a, b, w] = e[i];
            a = find(find, a), b = find(find, b);
            if (a != b) {
                ans += 1LL * sz[a] * sz[b] * w;
                merge(a, b);
            }
            i++;
        }
    }

    for (int i = 1; i <= n; i++) {
        int x = find(find, i), y = find(find, 1);
        if (x != y) {
            ans += 1LL * sz[x] * sz[y];
            merge(x, y);
        }
    }

    cout << ans << "\n";
    return 0;
}
```

### F

```cpp
#include <bits/stdc++.h>
using namespace std;

template <class Cap, class Cost>
struct SSP {
    struct E {
        int to;
        Cap f;
        Cost w;
    };

    int n;
    vector<E> e;
    vector<vector<int> > g;

    vector<Cost> h, dis;
    vector<int> pre, vis;

    SSP(int n) : n(n), g(n), h(n), dis(n), pre(n), vis(n) {}

    inline void add(int a, int b, Cap f, Cost w) {
        g[a].push_back(e.size());
        e.push_back({b, f, w});
        g[b].push_back(e.size());
        e.push_back({a, 0, -w});
    }

    inline pair<Cap, Cost> mcf(int S, int T, Cap max_flow = numeric_limits<Cap>::max(), Cost max_cost = numeric_limits<Cost>::max()) {
        h.assign(n, max_cost);
        h[S] = 0;
        for (int u = 0; u < n; u++) {
            for (auto i : g[u]) {
                auto [t, c, w] = e[i];
                if (c > 0) h[t] = min(h[t], h[u] + w);
            }
        }

        Cost cost = 0;
        Cap flow = 0;

        while (max_flow) {
            priority_queue<pair<Cost, int> > q;

            vis.assign(n, 0);
            pre.assign(n, -1);
            dis.assign(n, max_cost);

            q.emplace(dis[S] = 0, S);

            while (q.size()) {
                auto [_, u] = q.top();
                q.pop();

                if (vis[u]) continue;
                vis[u] = 1;

                for (auto i : g[u]) {
                    auto [t, c, w] = e[i];
                    Cost off = dis[u] + w + h[u] - h[t];
                    if (c > 0 && dis[t] > off) {
                        q.emplace(-(dis[t] = off), t);
                        pre[t] = i;
                    }
                }
            }

            if (pre[T] == -1) break;

            for (int i = 0; i < n; i++) {
                if (dis[i] != max_cost) h[i] += dis[i];
            }

            Cap mn = max_flow;
            for (int i = pre[T]; ~i; i = pre[e[i ^ 1].to]) mn = min(mn, e[i].f);
            for (int i = pre[T]; ~i; i = pre[e[i ^ 1].to]) e[i].f -= mn, e[i ^ 1].f += mn;

            max_flow -= mn;

            flow += mn;
            cost += mn * h[T];
        }

        return {flow, cost};
    }
};

int n, l, r;
long long w;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);

    int S = 0, T = 500002;

    SSP<long long, long long> ssp(T + 1);

    cin >> n;

    for (int i = 1; i <= n; i++) {
        cin >> l >> r >> w;
        ssp.add(l, r + 1, 1, -w);
    }

    for (int i = 0; i < T; i++) {
        ssp.add(i, i + 1, 2, 0);
    }

    auto [flow, cost] = ssp.mcf(S, T);
    cout << -cost << "\n";
    return 0;
}
```

### H

```cpp
#include <bits/stdc++.h>
using namespace std;

/**
 * 0, 0 -> 1 -> 0, 所以 0 的数量可以减少
 * 不断将 x -> {0, 1, ..., x - 1}, 最终检查 0 的数量是否足够即可
 */

#define int long long

const int inf = 1e18;

int n;

inline void solve() {
    cin >> n;
    int m = n + 100;

    vector<int> c(m);
    for (int i = 0; i < n; i++) {
        cin >> c[i];
    }

    if (accumulate(c.begin(), c.end(), 0ll) == 1) {
        int ans = max_element(c.begin(), c.end()) - c.begin();
        cout << (ans == 0 ? ans + 1 : ans) << "\n";
        return;
    }

    auto check = [&] (int x) -> bool {
        int cnt0 = 0;
        for (int i = x; i < n; i++) {
            cnt0 += c[i];
        }

        int need = 1;
        for (int i = x - 1; i >= 1; i--) {
            if (need <= c[i]) {
                cnt0 += c[i] - need;
            } else {
                need += need - c[i];
                if (need > inf) return false;
            }
        }

        return need <= cnt0 + c[0];
    };

    int l = 0, r = m;

    while (l < r) {
        int mid = l + r + 1 >> 1;
        if (check(mid)) l = mid;
        else r = mid - 1;
    }

    cout << l << "\n";
}

#undef int

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);

    solve();
    return 0;
}
```

### I

```cpp
#include <bits/stdc++.h>
using namespace std;

const int N = 1e5 + 5;

long long tr[N << 2];
int lz[N << 2];

#define ls i << 1
#define rs i << 1 | 1

inline void pushup(int i) {
    tr[i] = tr[ls] + tr[rs];
}

inline void pushdown(int i, int l, int r) {
    int mid = l + r >> 1;
    tr[ls] += 1LL * (mid - l + 1) * lz[i], lz[ls] += lz[i];
    tr[rs] += 1LL * (r - mid) * lz[i], lz[rs] += lz[i];
    lz[i] = 0;
}

inline void update(int l, int r, int s, int t, int w, int i) {
    if (s <= l && r <= t) {
        tr[i] += 1LL * (r - l + 1) * w, lz[i] += w;
        return;
    }
    if (lz[i]) pushdown(i, l, r);
    int mid = l + r >> 1;
    if (s <= mid) update(l, mid, s, t, w, ls);
    if (t > mid) update(mid + 1, r, s, t, w, rs);
    pushup(i);
}

inline long long query(int l, int r, int s, int t, int i) {
    if (s <= l && r <= t) return tr[i];
    if (lz[i]) pushdown(i, l, r);
    int mid = l + r >> 1;
    if (t <= mid) return query(l, mid, s, t, ls);
    if (s > mid) return query(mid + 1, r, s, t, rs);
    return query(l, mid, s, t, ls) + query(mid + 1, r, s, t, rs);
}

inline int find(int l, int r, long long k, int i) {
    if (l == r) return l;
    if (lz[i]) pushdown(i, l, r);
    int mid = l + r >> 1;
    if (tr[ls] >= k) return find(l, mid, k, ls);
    return find(mid + 1, r, k - tr[ls], rs);
}

int n, q;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);

    cin >> n;

    vector<vector<int> > g(n + 1);
    for (int i = 1; i < n; i++) {
        int a, b;
        cin >> a >> b;
        g[a].push_back(b);
        g[b].push_back(a);
    }

    vector<array<int, 17> > p(n + 1);
    vector<int> dep(n + 1), sz(n + 1), son(n + 1);
    auto dfs1 = [&] (auto self, int u, int fa) -> void {
        sz[u] = 1, dep[u] = dep[fa] + 1, p[u][0] = fa;
        for (int i = 1; (1 << i) <= dep[u]; i++) {
            p[u][i] = p[p[u][i - 1]][i - 1];
        }
        for (auto t : g[u]) {
            if (t == fa) continue;
            self(self, t, u);
            sz[u] += sz[t];
            if (sz[son[u]] < sz[t]) son[u] = t;
        }
    };
    dfs1(dfs1, 1, 0);

    int tim = 0;
    vector<int> dfn(n + 1), top(n + 1), id(n + 1), bot(n + 1);
    auto dfs2 = [&] (auto self, int u, int tp) -> void {
        tim++;
        dfn[u] = tim, id[tim] = u, top[u] = tp;
        if (son[u]) self(self, son[u], tp);
        for (auto t : g[u]) {
            if (t == p[u][0] || t == son[u]) continue;
            self(self, t, t);
        }
        bot[u] = tim;
    };
    dfs2(dfs2, 1, 1);

    auto updTree = [&] (int u) -> void {
        update(1, n, dfn[u], bot[u], 1, 1);
    };

    auto qryTree = [&] (int u) -> long long {
        return query(1, n, dfn[u], bot[u], 1);
    };

    auto upd = [&] (int a, int b) -> void {
        while (top[a] != top[b]) {
            if (dep[top[a]] < dep[top[b]]) swap(a, b);
            update(1, n, dfn[top[a]], dfn[a], 1, 1);
            a = p[top[a]][0];
        }
        if (dfn[a] > dfn[b]) swap(a, b);
        update(1, n, dfn[a], dfn[b], 1, 1);
    };

    auto qry = [&] () -> int {
        int u = id[find(1, n, (tr[1] + 1) / 2, 1)];

        for (int i = 16; i >= 0; i--) {
            if (p[u][i] && qryTree(p[u][i]) <= tr[1] / 2) {
                u = p[u][i];
            }
        }

        return (qryTree(u) <= tr[1] / 2 ? p[u][0] : u);
    };

    cin >> q;

    for (int op, u, v; q--; ) {
        cin >> op;

        if (op == 1) {
            cin >> u;
            updTree(u);
        } else {
            cin >> u >> v;
            upd(u, v);
        }

        cout << qry() << "\n";
    }

    return 0;
}
```

### J

```cpp
#include <bits/stdc++.h>
using namespace std;

int n, m;
string s;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);

    cin >> n >> s;

    map<pair<int, int>, vector<int> > mp;

    cin >> m;

    for (int i = 1; i <= m; i++) {
        int x, y;
        cin >> x >> y;
        mp[{x, y}].push_back(i);
    }

    int x = 0, y = 0;
    for (auto w : s) {
        int dx = (w == 'L' ? 1 : (w == 'R' ? -1 : 0));
        int dy = (w == 'D' ? 1 : (w == 'U' ? -1 : 0));

        if (mp.find({x + dx, y + dy}) != mp.end()) {
            int ax = x + dx, ay = y + dy;
            int bx = x + dx + dx, by = y + dy + dy;

            if (mp[{ax, ay}].size() > mp[{bx, by}].size()) {
                swap(mp[{ax, ay}], mp[{bx, by}]);
            }

            for (auto w : mp[{ax, ay}]) {
                mp[{bx, by}].push_back(w);
            }

            mp[{ax, ay}].clear();
        }

        x += dx, y += dy;
    }

    vector<pair<int, int> > ans(m + 1);
    for (auto &[p, v] : mp) {
        auto [xx, yy] = p;
        for (auto w : v) {
            ans[w] = {xx - x, yy - y};
        }
    }

    for (int i = 1; i <= m; i++) {
        auto [x, y] = ans[i];
        cout << x << " " << y << "\n";
    }

    return 0;
}
```

### K

```cpp
#include <bits/stdc++.h>
using namespace std;

int n;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);

    cin >> n;

    vector<int> x(n + 1), y(n + 1);
    for (int i = 1; i <= n; i++) cin >> x[i] >> y[i];

    vector<int> ord(n);
    iota(ord.begin(), ord.end(), 1);
    sort(ord.begin(), ord.end(), [&] (int a, int b) {
        if (x[a] != x[b]) return x[a] < x[b];
        return y[a] < y[b];
    });

    cout << n + n - 1 << "\n";

    for (auto w : ord) cout << w << " ";

    ord.pop_back();
    reverse(ord.begin(), ord.end());

    for (auto w : ord) cout << w << " ";

    return 0;
}
```
