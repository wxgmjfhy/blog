---
title: "codeforces edu 175, div2, A-E"
date: 2025-02-28T00:57:00+08:00
tags: ["题解", "Codeforces"]
description: "Codeforces Educational Round 175 Div.2 的 A–E 题解。"
---

## cf2070

### A

- 猜想答案即 15k, 15k + 1, 15k + 2 的数量, k = 0, 1, 2 ...

### B

- 模拟

### C

- 二分答案, 贪心 check

  ```cpp
  auto check = [&] (int x) -> bool {
      int cnt = 0;
      for (int i = 1; i <= n; i++) {
          if (s[i] == 'B' && a[i] > x) {
              int t = i + 1;
              while (t <= n) {
                  if (s[t] == 'R' && a[t] > x) break;
                  t++;
              }
              cnt++, i = t;
          }
      }
      return cnt <= k;
  };
  ```

### D

- 按照深度的顺序一层一层 dp, dp[u] 表示以 u 结尾的合法序列的数量
- dp[u] = sum - dp[p[u]], sum 为上一层的 dp 和, p[u] 为 u 的父节点

  ```cpp
  for (int i = 2; i <= n; i++) {
      if (v[i].empty()) {
          break;
      }

      for (auto w : v[i]) {
          dp[w] = sum - dp[p[w]];
          dp[w] = (dp[w] % mod + mod) % mod;
      }

      sum = 0;
      for (auto w : v[i]) {
          sum = (sum + dp[w]) % mod;
      }
  }
  ```

### E

- 猜想只有两种情况满足:
  - cnt0 > cnt1 * 3 + 1
  - cnt0 = cnt1 * 3 - 1
- 在是 1 的下标处 +3, 是 0 的下标处 -1
- 转换为计算:
  - 贡献和小于 -1 的区间数量
  - 贡献和恰好等于 1 的区间数量
- 计算前缀和 p[i], 然后从左往右扫一遍, 将 p[i] 加到树状数组中即可
- 因为 p[i] 可能有负数, 所以在树状数组中的下标整体位移

  ```cpp
  const int N = -mn + 10;

  BIT tr(mx - mn + 50);

  long long ans = 0;

  for (int i = 1; i <= n; i++) {
      ans += tr.suf(p[i] + 2 + N);
      ans += tr.query(p[i] - 1 + N, p[i] - 1 + N);

      tr.add(p[i - 1] + N, 1);
  }
  ```
