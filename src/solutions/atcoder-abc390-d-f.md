---
title: "atcoder abc390, D-F"
date: 2025-01-26T00:50:00+08:00
tags: ["题解", "AtCoder"]
description: "D–F 题解。"
---

## abc390

### D

- 直接暴搜时枚举一堆加到另一堆显然不可行
- 实际上是要把 n 堆石子划分为任意个非空集合 (即贝尔数)
- 那么暴搜时应该枚举这一堆分到哪个集合
  - 要么分到已有的集合
  - 要么新开一个集合

  ```cpp
  for (int t = 1; t <= col; t++) {
      sum[t] += a[i];
      self(self, i + 1, col);
      sum[t] -= a[i];
  }

  sum[col + 1] += a[i];
  self(self, i + 1, col + 1);
  sum[col + 1] -= a[i];
  ```

- 不过用 set 存答案竟然会 TLE, 用 unordered_set 或者用 vector 并最后去重才能 AC
- 此外还有遍历二进制状态, 再遍历每个状态的所有子集 (这个过程时间复杂度 $3^n$) 以 DP 的做法

  ```cpp
  for (int i = 1; i < (1 << n); i++) {
      int t = __builtin_ctz(i); // 获取二进制最低位的 1

      for (int j = i; j; j = (j - 1) & i) {
          if (j >> t & 1) {
              for (auto w : dp[i ^ j]) {
                  dp[i].push_back(w ^ sum[j]);
              }
          }
      }

      sort(dp[i].begin(), dp[i].end());
      dp[i].erase(unique(dp[i].begin(), dp[i].end()), dp[i].end());
  }
  ```

- 完整代码

```cpp
#include <bits/stdc++.h>
using namespace std;

int n;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);

    cin >> n;

    vector<long long> a(n + 1);

    for (int i = 1; i <= n; i++) {
        cin >> a[i];
    }

    unordered_set<long long> s;
    vector<long long> sum(n + 1);

    auto dfs = [&] (auto self, int i, int col) -> void {
        if (i > n) {
            long long ans = 0;

            for (int t = 1; t <= n; t++) {
                ans ^= sum[t];
            }

            s.insert(ans);
            return;
        }

        for (int t = 1; t <= col; t++) {
            sum[t] += a[i];
            self(self, i + 1, col);
            sum[t] -= a[i];
        }

        sum[col + 1] += a[i];
        self(self, i + 1, col + 1);
        sum[col + 1] -= a[i];
    };

    sum[1] += a[1];
    dfs(dfs, 2, 1);

    cout<< s.size() << "\n";
    return 0;
}
```

```cpp
#include <bits/stdc++.h>
using namespace std;

int n;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);

    cin >> n;

    vector<long long> a(n + 1);

    for (int i = 1; i <= n; i++) {
        cin >> a[i];
    }

    vector<long long> sum(1 << n);

    for (int i = 1; i < (1 << n); i++) {
        int t = __builtin_ctz(i); // 获取二进制最低位的 1
        sum[i] = sum[i ^ (1 << t)] + a[t + 1];
    }

    vector<vector<long long> > dp(1 << n);
    dp[0].push_back(0);

    for (int i = 1; i < (1 << n); i++) {
        int t = __builtin_ctz(i); // 获取二进制最低位的 1

        for (int j = i; j; j = (j - 1) & i) {
            if (j >> t & 1) {
                for (auto w : dp[i ^ j]) {
                    dp[i].push_back(w ^ sum[j]);
                }
            }
        }

        sort(dp[i].begin(), dp[i].end());
        dp[i].erase(unique(dp[i].begin(), dp[i].end()), dp[i].end());
    }

    cout << dp[(1 << n) - 1].size() << "\n";
    return 0;
}
```

### E

- 先跑三个背包, 再二分答案就完事了
- 完整代码

```cpp
#include <bits/stdc++.h>
using namespace std;

int n, m;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);

    cin >> n >> m;

    vector<int> v(n + 1), a(n + 1), c(n + 1);

    for (int i = 1; i <= n; i++) {
        cin >> v[i] >> a[i] >> c[i];
    }

    vector<vector<int> > dp(4, vector<int>(m + 1));

    for (int i = 1; i <= n; i++) {
        for (int t = m; t >= c[i]; t--) {
            dp[v[i]][t] = max(dp[v[i]][t], dp[v[i]][t - c[i]] + a[i]);
        }
    }

    auto check = [&] (int x) -> bool {
        long long sum = 0;

        for (int t = 1; t <= 3; t++) {
            int cost = -1;
            for (int i = 1; i <= m; i++) {
                if (dp[t][i] >= x) {
                    cost = i;
                    break;
                }
            }
            if (cost == -1) {
                return false;
            }
            sum += cost;
        }

        return sum <= m;
    };

    int l = 0, r = 1e9;

    while (l < r) {
        int mid = l + r + 1 >> 1;
        if (check(mid)) l = mid;
        else r = mid - 1;
    }

    cout << l << "\n";
    return 0;
}
```

### F

- 每一个区间的值 = 区间内连续段的数目
- 区间内连续段的数目 = 区间内"数字 x 存在, 但 x+1 不存在"的数目
- 考虑每个 a[i] 的贡献, 即区间范围包含 i 且区间中不存在 a[i] + 1 的区间的数量
- 不过注意要避免同种数字的贡献重复计算

  ```cpp
  for (int i = 1; i <= n; i++) {
      auto it = lower_bound(pos[a[i] + 1].begin(), pos[a[i] + 1].end(), i);

      int l = *prev(it) + 1, r = *it - 1;
      l = max(l, lst[a[i]] + 1); // 避免同种数字的贡献重复计算

      if (l <= r) {
          ans += 1ll * (i - l + 1) * (r - i + 1);
      }

      lst[a[i]] = i;
  }
  ```

- 完整代码

```cpp
#include <bits/stdc++.h>
using namespace std;

int n;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);

    cin >> n;

    vector<int> a(n + 1);

    for (int i = 1; i <= n; i++) {
        cin >> a[i];
    }

    vector<vector<int> > pos(n + 2);

    for (int i = 1; i <= n + 1; i++) {
        pos[i].push_back(0);
    }

    for (int i = 1; i <= n; i++) {
        pos[a[i]].push_back(i);
    }

    for (int i = 1; i <= n + 1; i++) {
        pos[i].push_back(n + 1);
    }

    long long ans = 0;
    vector<int> lst(n + 1);

    for (int i = 1; i <= n; i++) {
        auto it = lower_bound(pos[a[i] + 1].begin(), pos[a[i] + 1].end(), i);

        int l = *prev(it) + 1, r = *it - 1;
        l = max(l, lst[a[i]] + 1); // 避免同种数字的贡献重复计算

        if (l <= r) {
            ans += 1ll * (i - l + 1) * (r - i + 1);
        }

        lst[a[i]] = i;
    }

    cout << ans << "\n";
    return 0;
}
```
