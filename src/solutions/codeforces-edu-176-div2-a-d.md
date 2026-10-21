---
title: "codeforces edu 176, div2, A-D"
date: 2025-03-18T00:43:00+08:00
tags: ["题解", "Codeforces"]
description: "A–D 题解。"
---

## cf2075

### A

- n 是奇数就先减一次奇数, 之后一直减偶数

### B

- 特判 k = 1
- k != 1, 答案就是最大的 k + 1 个

### C

- 对于 a[i], 肯定与所有 >= n - a[i] 的 a[j] 匹配
- 而 a[j] 实际使用的数量要满足 [n - a[i], min(n - 1, a[j])], 区间长度也就是方案数
- 统计一下这样的 a[j] 有多少个, 总和是多少, 就可以计算了

```cpp
inline void solve() {
    cin >> n >> m;

    vector<int> a(m + 1);

    for (int i = 1; i <= m; i++) {
        cin >> a[i];
        if (a[i] == n) a[i]--;
    }

    BIT tr(n), cnt(n);

    for (int i = 1; i <= m; i++) {
        tr.add(a[i], a[i]);
        cnt.add(a[i], 1);
    }

    int ans = 0;

    for (int i = 1; i <= m; i++) {
        tr.add(a[i], -a[i]);
        cnt.add(a[i], -1);

        int sum = tr.suf(n - a[i]);
        sum -= (n - a[i] - 1) * cnt.suf(n - a[i]);
        ans += sum;

        tr.add(a[i], a[i]);
        cnt.add(a[i], 1);
    }

    cout << ans << "\n";
}
```

### D

- dp 预处理一下可以对 x 右位移 i, 并对 y 右位移 t 所需的最小花费

```cpp
inline void init() {
    for (int i = 0; i <= 60; i++) {
        for (int t = 0; t <= 60; t++) dp[i][t] = g[i][t] = LLONG_MAX;
    }
    dp[0][0] = g[0][0] = 0;
    for (int i = 1; i <= 60; i++) {
        for (int t = 0; t <= 60; t++) {
            for (int j = 0; j <= 60; j++) {
                if (dp[t][j] == LLONG_MAX) continue;
                if (t + i <= 60) g[t + i][j] = min(g[t + i][j], dp[t][j] + (1ll << i));
                if (j + i <= 60) g[t][j + i] = min(g[t][j + i], dp[t][j] + (1ll << i));
            }
        }
        for (int t = 0; t <= 60; t++) {
            for (int j = 0; j <= 60; j++) dp[t][j] = g[t][j];
        }
    }
}
```

- 然后枚举一下就行了

```cpp
for (int i = 0; i <= 60; i++) {
    for (int t = 0; t <= 60; t++) {
        int xx = x >> i, yy = y >> t;
        if (xx == yy) ans = min(ans, dp[i][t]);
    }
}
```
