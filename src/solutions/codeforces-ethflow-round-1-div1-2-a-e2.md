---
title: "codeforces Ethflow Round 1, div1+2, A-E2"
date: 2025-01-29T18:32:00+08:00
tags: ["题解", "Codeforces"]
description: "Codeforces Ethflow Round 1（Div.1+2）的 A–E2 题解。"
---

## cf2062

### A

- 显然一个一个把 1 转成 0 最优

### B

- 猜想每个点都要满足: 向左/向右走到尽头再返回这个点时, 时钟还没结束

  ```cpp
  for (int i = 1; i <= n; i++) {
      int x = a[i] - 1 >> 1;

      if (i - x > 1 || i + x < n) {
          cout << "NO\n";
          return;
      }
  }
  ```

### C

- 猜想直接模拟一直差分, 每次数组的和取绝对值
- 需要开 long long

### D

- 假设点 u 的每一个儿子 t 对应的子树都已经平衡了
  - 对于权值 <=r[u] 的子树, 显然 u 这个点可以取权值的最大值, 然后每棵子树都整体增加到这一权值即可
  - 但有的儿子 t 对应的子树权值 >r[u], 我们就想让 t 对应的子树权值整体减少到 r[u], 才能符合上一条
  - 这等效于让 t 对应的子树以外的点权值整体增加, 根据题目所需要的操作为: 选择 t 为根, 对 u 这棵子树操作
  - 而这样操作等效于对整棵树最后的答案增加了, 我们额外记录这一部分即可, 而在代码中, 我们呈现为把子树权值减小到 r[u] 了

  ```cpp
  int cnt = 0;

  auto dfs = [&] (auto self, int u, int fa) -> int {
      int mx = l[u];

      for (auto t : g[u]) {
          if (t == fa) {
              continue;
          }

          int temp = self(self, t, u);

          if (temp > r[u]) {
              cnt += temp - r[u];
              temp = r[u];
          }

          mx = max(temp, mx);
      }

      return mx;
  };

  cout <<  dfs(dfs, 1, -1) + cnt << "\n";
  ```

- 需要开 long long

### E1

- 如果一个点, 比这个点权值大的点全在这个点的子树内, 显然不能选这个点
- 按权值从大到小, 找到第一个不符合上述条件的点即为答案
- 检查"比这个点权值大的点全在这个点的子树内"是否满足, 可以用线段树 + dfs 序

  ```cpp
  int cnt = 0; // 记录比当前权值大的点的总数

  for (int i = n; i >= 1; i--) { // 遍历权值
      for (auto w : v[i]) {
          // 查询子树中比当前权值大的点的数量
          int x = query(1, n, dfn[w], bot[w], 1);

          if (x != cnt) {
              cout << w << "\n";
              return;
          }
      }

      for (auto w : v[i]) {
          update(1, n, dfn[w], 1);
      }

      cnt += v[i].size();
  }
  ```

- 完整代码

```cpp
const int N = 4e5 + 5;

struct segt {
    int sum;
}tr[N << 2];

#define ls i<<1
#define rs i<<1|1

inline void pushup(int i) {
    tr[i].sum = tr[ls].sum + tr[rs].sum;
}

inline void build(int l, int r, int i) {
    tr[i].sum = 0;
    if (l == r) {
        return;
    }
    int mid = l + r >> 1;
    build(l, mid, ls), build(mid + 1, r, rs);
}

inline void update(int l, int r, int x, int i) {
    if (l == r) {
        tr[i].sum++;
        return;
    }
    int mid = l + r >> 1;
    if (x <= mid) update(l, mid, x, ls);
    else update(mid + 1, r, x, rs);
    pushup(i);
}

inline int query(int l, int r, int s, int t, int i) {
    if (s <= l && r <= t) return tr[i].sum;
    int mid = l + r >> 1;
    if (t <= mid) return query(l, mid, s, t, ls);
    if (s > mid) return query(mid + 1, r, s, t, rs);
    return query(l, mid, s, t, ls) + query(mid + 1, r, s, t, rs);
}

int n;

inline void solve() {
    cin >> n;

    vector<int> a(n + 1);

    for (int i = 1; i <= n; i++) {
        cin >> a[i];
    }

    vector<vector<int> > g(n + 1);

    for (int i = 1; i < n; i++) {
        int a, b;
        cin >> a >> b;
        g[a].push_back(b);
        g[b].push_back(a);
    }

    int tim = 0;
    vector<int> dfn(n + 1), bot(n + 1);

    auto dfs = [&] (auto self, int u, int fa) -> void {
        dfn[u] = ++tim;
        for (auto t : g[u]) {
            if (t == fa) {
                continue;
            }
            self(self, t, u);
        }
        bot[u] = tim;
    };
    dfs(dfs, 1, -1);

    vector<vector<int> > v(n + 1);

    for (int i = 1; i <= n; i++) {
        v[a[i]].push_back(i);
    }

    build(1, n, 1);

    int cnt = 0;

    for (int i = n; i >= 1; i--) {
        for (auto w : v[i]) {
            int x = query(1, n, dfn[w], bot[w], 1);

            if (x != cnt) {
                cout << w << "\n";
                return;
            }
        }

        for (auto w : v[i]) {
            update(1, n, dfn[w], 1);
        }

        cnt += v[i].size();
    }

    cout << "0\n";
}
```

### E2

- 记点 u 的 dfs 序为 dfn[u], 点 u 子树中最大的 dfs 序为 bot[u], [dfn[u],bot[u]] 这个 dfs 序区间就表示 u 这棵子树
- 仍然是同样于 E1 的思路, Cirno 的策略是: 第一轮操作后, 第二轮 Daiyousei 可以操作, 而第三轮 Cirno 就无法操作而胜利了
- 那么有两点要满足:
  - 第一轮 Cirno 选的点 u 要满足 u 的子树外有比 u 大的点 v
  - 而对于上述所有 v, 要满足 v 的子树外比 v 大的点 t, 要么不存在, 要么在 u 的子树内
- 我们使用两个线段树来维护 dfs 序区间的 lca(因为 lca 具有结合律), 根据值从大到小遍历节点, 并更新线段树, 这样遍历到某个点 u 时线段树中只有比 u 大的点的贡献
  -
    第一个线段树中, 在 dfn[u] 处的值就是 **u 自身**
    - 查询 [1,dfn[u]-1] 的 lca 和 [bot[u]+1,n] 的 lca, 这两者的 lca 记为 x
    - x 即为所有 v 的 lca
    - 如果 x 不存在, 说明 v 不存在, 这个点不可行

    ```cpp
    int x = pushup(lcaTr1.query(1, n, 1, dfn[u] - 1, 1), lcaTr1.query(1, n, bot[u] + 1, n, 1));

    if (x == -1) {
        continue;
    }
    ```

  -
    第二个线段树中, 在 dfn[u] 处的值是 **u 子树外所有比 u 大的点 v 的 lca**, 这个 lca 就是第一个线段树中得到的 x
    - 查询 [1,dfn[u]-1] 的 lca 和 [bot[u]+1,n] 的 lca, 这两者的 lca 记为 y
    - y 即为所有 t 的 lca
    - 如果 y 不存在, 或者 y 在 u 的子树内, 说明所有 t 不存在或者在 u 的子树中, 这个点可行

    ```cpp
    int y = pushup(lcaTr2.query(1, n, 1, dfn[u] - 1, 1), lcaTr2.query(1, n, bot[u] + 1, n, 1));

    if (y == -1 || (dfn[u] <= dfn[y] && dfn[y] <= bot[u])) {
        ans.push_back(u);
    }
    ```

- 完整代码

```cpp
const int N = 4e5 + 5;

int dfn[N], bot[N];
int dep[N], p[N][19];

inline int lca(int a, int b) {
    if (dep[a] > dep[b]) swap(a,b);
    int temp = dep[b] - dep[a];
    for (int i = 0; temp; i++, temp >>= 1) {
        if (temp & 1) b = p[b][i];
    }
    if (a == b) return a;
    for (int i = 18; i >= 0; i--) {
        if (p[a][i] != p[b][i]) {
            a = p[a][i];
            b = p[b][i];
        }
    }
    return p[a][0];
}

inline int pushup(int a, int b) {
    int c = -1;
    if (a == -1 && b == -1) {
        c = -1;
    } else if (a == -1) {
        c = b;
    } else if (b == -1) {
        c = a;
    } else {
        c = lca(a, b);
    }
    return c;
}

struct segt{
    int tr[N << 2];

    #define ls i << 1
    #define rs i << 1 | 1

    inline void build(int l, int r, int i) {
        tr[i] = -1;
        if (l == r) return;
        int mid = l + r >> 1;
        build(l, mid, ls), build(mid + 1, r, rs);
    }

    inline void update(int l, int r, int x, int w, int i) {
        if (l == r) {
            tr[i] = w;
            return;
        }
        int mid = l + r >> 1;
        if (x <= mid) update(l, mid, x, w, ls);
        else update(mid + 1, r, x, w, rs);
        tr[i] = pushup(tr[ls], tr[rs]);
    }

    inline int query(int l, int r, int s, int t, int i) {
        if (s > t) return -1;
        if (s <= l && r <= t) return tr[i];
        int mid = l + r >> 1;
        if (t <= mid) return query(l, mid, s, t, ls);
        if (s > mid) return query(mid + 1, r, s, t, rs);
        return pushup(query(l, mid, s, t, ls), query(mid + 1, r, s, t, rs));
    }
}lcaTr1, lcaTr2;

int n;

inline void solve() {
    cin >> n;

    vector<int> a(n + 1);

    for (int i = 1; i <= n; i++) {
        cin >> a[i];
    }

    vector<vector<int> > g(n + 1);

    for (int i = 1; i < n; i++) {
        int a, b;
        cin >> a >> b;
        g[a].push_back(b);
        g[b].push_back(a);
    }

    int tim = 0;
    auto dfs = [&] (auto self, int u, int fa) -> void {
        dfn[u] = ++tim;
        for (auto t : g[u]) {
            if (t == fa) {
                continue;
            }
            self(self, t, u);
        }
        bot[u] = tim;
    };
    dfs(dfs, 1, -1);

    for (int i = 1; i <= n; i++) {
        for (int t = 18; t >= 0; t--) p[i][t] = 0;
    }

    auto dfs2 = [&] (auto self, int u, int fa) -> void {
        dep[u] = dep[fa] + 1, p[u][0] = fa;
        for (int i = 1; (1 << i) <= dep[u]; i++) {
            p[u][i] = p[p[u][i - 1]][i - 1];
        }
        for (auto t : g[u]) {
            if (t == fa) {
                continue;
            }
            self(self, t, u);
        }
    };
    dfs2(dfs2, 1, 0);

    vector<vector<int> > v(n + 1);

    for (int i = 1; i <= n; i++) {
        v[a[i]].push_back(i);
    }

    lcaTr1.build(1, n, 1), lcaTr2.build(1, n, 1);

    vector<int> ans;

    for (int i = n; i >= 1; i--) {
        for (auto u : v[i]) {
            int x = pushup(lcaTr1.query(1, n, 1, dfn[u] - 1, 1), lcaTr1.query(1, n, bot[u] + 1, n, 1));

            if (x == -1) {
                continue;
            }

            int y = pushup(lcaTr2.query(1, n, 1, dfn[u] - 1, 1), lcaTr2.query(1, n, bot[u] + 1, n, 1));

            if (y == -1 || (dfn[u] <= dfn[y] && dfn[y] <= bot[u])) {
                ans.push_back(u);
            }
        }

        for (auto u : v[i]) {
            int x = pushup(lcaTr1.query(1, n, 1, dfn[u] - 1, 1), lcaTr1.query(1, n, bot[u] + 1, n, 1));

            if (x != -1) {
                lcaTr2.update(1, n, dfn[u], x, 1);
            }
        }

        for (auto u : v[i]) {
            lcaTr1.update(1, n, dfn[u], u, 1);
        }
    }

    sort(ans.begin(), ans.end());

    cout << ans.size() << " ";
    for (auto w : ans) cout << w << " ";
    cout << "\n";
}
```
