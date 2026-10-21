---
title: "GYM105465 - 2023 ICPC Southeastern Europe Regional Contest (The 2nd Universal Cup, Stage 14: Southeastern Europe)"
date: 2025-10-15T19:33:00+08:00
tags: ["题解", "ICPC"]
description: "GYM105465（2023 ICPC Southeastern Europe Regional Contest，The 2nd Universal Cup Stage 14）B、E、F、G、J、K、M 七题的题解。"
---

### B

```cpp
#include <bits/stdc++.h>
using namespace std;

int n;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);

    cin >> n;

    vector<int> a(n + 1);
    for (int i = 1; i <= n; i++) cin >> a[i];

    vector<int> ord(n + 1);
    iota(ord.begin(), ord.end(), 0);
    sort(ord.begin() + 1, ord.end(), [&] (int x, int y) {
        return a[x] < a[y];
    });

    int lst = -1;
    vector<int> ans(n + 1);

    for (int i = 1, t = n; i <= t; i++, t--) {
        int x = a[ord[i]] + a[ord[t]];
        if (lst != -1 && x != lst) {
            cout << "-1\n";
            return 0;
        }
        ans[ord[i]] = ord[t];
        ans[ord[t]] = ord[i];
        lst = x;
    }

    for (int i = 1; i <= n; i++) {
        cout << ans[i] << " \n"[i == n];
    }

    return 0;
}
```

### E

```cpp
#include <bits/stdc++.h>
using namespace std;

int n;

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

    int ans = 0;

    auto dfs = [&] (auto self, int u, int fa) -> int {
        int need = 0;
        for (auto t : g[u]) {
            if (t == fa) continue;
            need += self(self, t, u);
        }

        if (need == 0) {
            return 1;
        }

        ans += (need - 1) * 2 + 1;
        return 0;
    };
    int lft = dfs(dfs, 1, -1);
    if (lft) {
        ans += 2;
    }

    cout << ans << "\n";
    return 0;
}
```

### F

```cpp
#include <bits/stdc++.h>
using namespace std;

int n;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);

    cin >> n;

    vector<int> a(n);
    for (int &x : a) cin >> x;

    int m = __lg(n);
    vector<array<long long, 2> > tot(m);

    auto wk = [&] (auto self, vector<int> &a, int i) -> void {
        if (i < 0) return;

        array<int, 2> cnt = {0, 0};
        array<long long, 2> num = {0, 0};
        vector<vector<int> > v(2);

        for (auto w : a) {
            int t = (w >> i & 1);
            num[t] += cnt[t ^ 1];
            cnt[t]++, v[t].push_back(w);
        }

        for (int t = 0; t < 2; t++) {
            tot[i][t] += num[t];
            self(self, v[t], i - 1);
        }
    };
    wk(wk, a, m - 1);

    int mask = 0;
    long long ans = 0;

    for (int i = 0; i < m; i++) {
        if (tot[i][0] <= tot[i][1]) {
            ans += tot[i][0];
        } else {
            ans += tot[i][1];
            mask |= (1 << i);
        }
    }

    if (mask) ans++;

    cout << ans << "\n";
    return 0;
}
```

### G

```cpp
#include <bits/stdc++.h>
using namespace std;

using i64 = long long;

const i64 inf = 1e18;

int n, m;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);

    cin >> n >> m;

    vector<int> a(n + 1), b(n + 1);
    for (int i = 1; i <= n; i++) cin >> a[i] >> b[i];

    vector<vector<int> > g(n + 1);
    for (int i = 1; i <= m; i++) {
        int a, b;
        cin >> a >> b;
        g[a].push_back(b);
        g[b].push_back(a);
    }

    queue<int> q;
    vector<int> d(n + 1, -1);

    vector<int> ord;

    q.push(1), d[1] = 0;
    while (q.size()) {
        int u = q.front();
        q.pop();

        ord.push_back(u);

        for (auto t : g[u]) {
            if (d[t] == -1) {
                d[t] = d[u] + 1;
                q.push(t);
            }
        }
    }

    vector<vector<int> > g1(n + 1), g2(n + 1);
    for (int u = 1; u <= n; u++) {
        for (auto t : g[u]) {
            if (d[t] == d[u] + 1) {
                g1[u].push_back(t);
            } else if (d[t] == d[u]) {
                g2[u].push_back(t);
            }
        }
    }

    multiset<i64> s;
    for (int i = 1; i <= n; i++) {
        s.insert(a[i] - 1LL * (d[i] + 1) * b[i]);
    }

    vector<i64> ans(n + 1);
    for (int i = 1; i <= n; i++) {
        s.extract(a[i] - 1LL * (d[i] + 1) * b[i]);
        ans[i] = *s.rbegin();
        s.insert(a[i] - 1LL * (d[i] + 1) * b[i]);
    }

    reverse(ord.begin(), ord.end());

    vector<i64> f1(n + 1, -inf), f2(n + 1, -inf);
    for (auto u : ord) {
        f1[u] = a[u] - 1LL * d[u] * b[u];
        for (auto t : g1[u]) {
            f1[u] = max(f1[u], f1[t]);
        }
    }

    for (auto u : ord) {
        for (auto t : g1[u]) {
            f2[u] = max(f2[u], f2[t]);
        }
        for (auto t : g2[u]) {
            f2[u] = max(f2[u], f1[t]);
        }

        ans[u] = max(ans[u], f2[u]);
        f2[u] = max(f2[u], a[u] - 1LL * (d[u] - 1) * b[u]);
    }

    for (int i = 1; i <= n; i++) {
        if (d[i] == 1) cout << ans[i] << "\n";
    }

    return 0;
}
```

### J

```cpp
#include <bits/stdc++.h>
using namespace std;

int n;

inline void solve() {
    cin >> n;

    vector<int> a(n + n + 1);
    for (int i = 1; i <= n + n; i++) cin >> a[i];

    vector<vector<int> > v(2, vector<int>(1));

    for (int i = 1; i <= n + n; i++) {
        v[i & 1].push_back(a[i]);
    }

    for (int i = 0; i < 2; i++) {
        sort(v[i].begin() + 1, v[i].end());
    }

    long long ans = 0;

    for (int i = 1; i <= n; i++) {
        ans += abs(v[0][i] - v[1][n - i + 1]);
    }

    cout << ans << "\n";
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);

    int t = 1;
    cin >> t;

    while (t--) solve();

    return 0;
}
```

### K

```cpp
#include <bits/stdc++.h>
using namespace std;

int n, k;

inline void solve() {
    cin >> n >> k;

    vector<int> a(n + 1);
    for (int i = 1; i <= n; i++) cin >> a[i];

    set<pair<int, int> > s;
    for (int i = 1; i <= k; i++) s.insert({0, i});

    vector<int> ans(n + 1);

    for (int i = 1; i <= n; i++) {
        if (a[i] == 1) {
            auto [x, y] = *s.begin();
            s.erase({x, y});

            x++, ans[i] = y;

            s.insert({x, y});
        } else {
            auto [x, y] = *s.rbegin();
            s.erase({x, y});

            x--, ans[i] = y;

            s.insert({x, y});
        }
    }

    for (int i = 1; i <= n; i++) {
        cout << ans[i] << " \n"[i == n];
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);

    int t = 1;
    cin >> t;

    while (t--) solve();

    return 0;
}
```

### M

```cpp
#include <bits/stdc++.h>
using namespace std;

int n;

inline void solve() {
    cin >> n;

    vector<int> a(n + 1);
    for (int i = 1; i <= n; i++) cin >> a[i];

    int mx = 0, mn = 1e9;
    for (int i = 1; i <= n; i++) {
        mx = max(mx, a[i]);
        mn = min(mn, a[i]);
    }

    if (mx == mn) {
        cout << 0 << "\n";
        return;
    }

    auto check = [&] (int x) -> bool {
        {
            int l = n + 1, r = 0;
            for (int i = 1; i <= n; i++) {
                if (a[i] - mn > x) {
                    l = min(l, i);
                    r = max(r, i);
                }
            }

            if (l == n + 1) return true;

            auto b = a;
            for (int i = l; i <= r; i++) {
                b[i] -= mx - mn - x;
            }

            if (*max_element(b.begin() + 1, b.end()) - *min_element(b.begin() + 1, b.end()) <= x) {
                return true;
            }
        }

        {
            int l = n + 1, r = 0;
            for (int i = 1; i <= n; i++) {
                if (mx - a[i] > x) {
                    l = min(l, i);
                    r = max(r, i);
                }
            }

            if (l == n + 1) return true;

            auto b = a;
            for (int i = l; i <= r; i++) {
                b[i] += mx - mn - x;
            }

            if (*max_element(b.begin() + 1, b.end()) - *min_element(b.begin() + 1, b.end()) <= x) {
                return true;
            }
        }

        return false;
    };

    int l = 0, r = 1e9;

    while (l < r) {
        int mid = l + r >> 1;
        if (check(mid)) r = mid;
        else l = mid + 1;
    }

    cout << l << "\n";
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);

    int t = 1;
    cin >> t;

    while (t--) solve();

    return 0;
}
```
