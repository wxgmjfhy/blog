---
title: "codeforces 1002, div2, B-E1"
date: 2025-02-04T23:12:00+08:00
tags: ["题解", "Codeforces"]
description: "B–E1 题解。"
---

## cf2059

### B

- 特判 n == k 的情况
- 先看能否让第一个数不是 1 :
  - 第一个数一定是第一组, 因此从第二个数开始遍历
  - 遍历到一个不等于 1 的数, 检查如果把这个数作为第二组, 剩下的数够不够分组

  ```cpp
  for (int i = 2; i <= n; i++) {
      if (a[i] != 1) {
          if (n - i >= k - 2) {
              cout << "1\n";
              return;
          }
      }
  }
  ```

- 否则, 一定有很长的前缀使得前缀中每个数都是 1, 那么一定可以选择两个 1 作为第二组, 此时答案为 2

### C

- 操作就是取后缀, 且每一种长度的后缀只能取一次
- 因为每个数字最小为 1, 又每一种长度的后缀只能取一次, 所以我们只能取全为 1 的后缀去构造 mex
- 记录每一行最长的全为 1 的后缀长度, 再统计每种长度的数量
- 如果较小的长度没有, 可以用较大的长度去补

  ```cpp
  for (int i = 0, t = 0; i <= n; i++) {
      if (cnt[i] == 0) {
          t = max(t, i);
          while (t <= n) {
              if (cnt[t]) {
                  cnt[t]--, cnt[i]++;
                  break;
              }
              t++;
          }

          if (cnt[i] == 0) {
              cout << i << "\n";
              return;
          }
      }
  }
  ```

- 完整代码

```cpp
inline void solve() {
    cin >> n;

    vector<vector<int> > a(n + 1, vector<int>(n + 1));

    for (int i = 1; i <= n; i++) {
        for (int t = 1; t <= n; t++) cin >> a[i][t];
    }

    vector<int> mx(n + 1);

    for (int i = 1; i <= n; i++) {
        for (int t = n; t >= 1; t--) {
            if (a[i][t] != 1) break;
            mx[i]++;
        }
    }

    vector<int> cnt(n + 1);

    for (int i = 1; i <= n; i++) cnt[mx[i]]++;

    for (int i = 0, t = 0; i <= n; i++) {
        if (cnt[i] == 0) {
            t = max(t, i);
            while (t <= n) {
                if (cnt[t]) {
                    cnt[t]--, cnt[i]++;
                    break;
                }
                t++;
            }

            if (cnt[i] == 0) {
                cout << i << "\n";
                return;
            }
        }
    }
}
```

### D

- 如果两个图中有一条相同的边, 且两个标记能同时达到这条边的同一个端点, 答案才有限
- 把一对点看作一个点, 建图跑最短路

  ```cpp
  for (int i = 1; i <= n; i++) {
      for (int t = 1; t <= n; t++) {
          for (auto u : g1[i]) {
              for (auto v : g2[t]) {
                  if (u == v && i == t) { // 两个图中有一条相同的边
                      flag = 1;
                      f[id[i][t]] = f[id[u][v]] = 1; // 标记这样的点对, 如果能到达这样的点对, 答案有限
                  }

                  g[id[i][t]].push_back({id[u][v], abs(u - v)});
              }
          }
      }
  }
  ```

- 完整代码

```cpp
inline void solve() {
    cin >> n >> s1 >> s2;

    cin >> m1;

    vector<vector<int> > g1(n + 1);

    for (int i = 1; i <= m1; i++) {
        int a, b;
        cin >> a >> b;
        g1[a].push_back(b);
        g1[b].push_back(a);
    }

    cin >> m2;

    vector<vector<int> > g2(n + 1);

    for (int i = 1; i <= m2; i++) {
        int a, b;
        cin >> a >> b;
        g2[a].push_back(b);
        g2[b].push_back(a);
    }

    int P = 0;
    vector<vector<int> > id(n + 1, vector<int>(n + 1));

    for (int i = 1; i <= n; i++) {
        for (int t = 1; t <= n; t++) {
            id[i][t] = ++P;
        }
    }

    vector<int> f(P + 1);
    vector<vector<pair<int, int> > > g(P + 1);

    bool flag = 0;

    for (int i = 1; i <= n; i++) {
        for (int t = 1; t <= n; t++) {
            for (auto u : g1[i]) {
                for (auto v : g2[t]) {
                    if (u == v && i == t) {
                        flag = 1;
                        f[id[i][t]] = f[id[u][v]] = 1;
                    }

                    g[id[i][t]].push_back({id[u][v], abs(u - v)});
                }
            }
        }
    }

    if (!flag) {
        cout << "-1\n";
        return;
    }

    vector<int> d(P + 1, inf), vis(P + 1);

    priority_queue<pair<int, int>, vector<pair<int, int> >, greater<pair<int, int> > > q;
    q.push({d[id[s1][s2]] = 0, id[s1][s2]});

    while (q.size()) {
        auto [dis, u] = q.top();
        q.pop();

        if (f[u]) {
            cout << dis << "\n";
            return;
        }

        for (auto [t, w] : g[u]) {
            if (d[t] > d[u] + w) {
                d[t] = d[u] + w;

                if (!vis[t]) {
                    vis[t] = 1;
                    q.push({d[t], t});
                }
            }
        }
    }

    cout << "-1\n";
}
```

### E1

- 操作数尽量少就是让原本在 a 中数字留下来的尽量多
- 由操作可知, 如果保留了后面的数字, 则前面的数字也必须保留, 因此这些留下来的数字一定对应 a 中的一个前缀
- 注意数字都是两两不同的, 即一个数字只对应一个位置, 那么 a 中数字在 b 中可以匹配的位置是固定的
- 依次检查前缀:
  - 如果 a 中相邻两个数字 a[i-1] 和 a[i] 在 b 中匹配的位置不相邻, 说明在 a[i-1] 后面需要添加数字

  ```cpp
  for (int i = 0, t = 0; i < n * m && t < n * m; i++, t++) {
      int st = t;

      while (t < n * m && b[t] != a[i]) t++;

      if (i != 0 && t > st && check(i)) break; // t > st 说明 a[i-1] 和 a[i] 在 b 中匹配的位置不相邻
      if (t == n * m) break;

      cnt[i] = (i == 0 ? 0 : cnt[i - 1]) + t - st, ans--;
  }
  ```

  - 进而说明: 某一时刻, a[i-1] 需要排在某一行的最后一列
  - 进而说明: a[i-1] 前面添加的数字数量, 需要不小于 a[i-1] 原本所在列到最后一列的距离
  - 如果条件不满足, 说明前缀到此为止, a[i] 不能保留
  - 还没完: 不保留 a[i], a[i-1] 后面还是需要添加数字, 但不符合条件, 因此 a[i-1] 也不能保留
  - 而 a[i-1] 不保留, 就要继续看 a[i-2]...于是我写了一个"回溯"函数

  ```cpp
  auto check = [&] (int i) -> bool {
      bool flag = 0;
      while (ans < n * m) {
          int j = m - 1 - (i - 1) % m;
          if (cnt[i - 1] >= j) { // cnt[i] 记录了 a[i] 前面添加的数字的数量
              break;
          }
          flag = 1; // 说明前缀到此为止
          ans++, i--;
      }
      return flag;
  };
  ```

- 完整代码

```cpp
inline void solve() {
    cin >> n >> m;

    vector<int> a(n * m);
    for (int &x : a) cin >> x;

    vector<int> b(n * m);
    for (int &x : b) cin >> x;

    int ans = n * m;

    vector<int> cnt(n * m);

    auto check = [&] (int i) -> bool {
        bool flag = 0;
        while (ans < n * m) {
            int j = m - 1 - (i - 1) % m;
            if (cnt[i - 1] >= j) {
                break;
            }
            flag = 1;
            ans++, i--;
        }
        return flag;
    };

    for (int i = 0, t = 0; i < n * m && t < n * m; i++, t++) {
        int st = t;

        while (t < n * m && b[t] != a[i]) t++;

        if (i != 0 && t > st && check(i)) break;
        if (t == n * m) break;

        cnt[i] = (i == 0 ? 0 : cnt[i - 1]) + t - st, ans--;
    }

    cout << ans << "\n";
}
```
