---
title: "codeforeces 1004, div2, A-E"
date: 2025-02-12T01:00:00+08:00
tags: ["题解", "Codeforces"]
description: "A–E 题解。"
---

## cf2067

### A

- 显然 x + 1 - y 是 9 的非负整数倍时有解

```cpp
inline void solve() {
    cin >> x >> y;

    int a = x + 1 - y;

    if (a % 9 == 0 && a / 9 >= 0) {
        cout << "Yes\n";
    } else {
        cout << "No\n";
    }
}
```

### B

- 等效于要所有的数的数量为偶数
- 小的数只要数量 >=2, 无论奇偶, 就留下两个, 其余的都 +1 看大的数需不需要
- 如果中途有数量为 1 的出现或者最后还有奇数, 则无解

```cpp
inline void solve() {
    cin >> n;

    vector<int> a(n + 1);

    for (int i = 1; i <= n; i++) {
        cin >> a[i];
    }

    vector<int> cnt(n + 2);

    for (int i = 1; i <= n; i++) {
        cnt[a[i]]++;
    }

    for (int i = 1; i <= n; i++) {
        if (cnt[i]) {
            if (cnt[i] == 1) {
                cout << "No\n";
                return;
            }

            cnt[i + 1] += cnt[i] - 2;
            cnt[i] = 2;
        }
    }

    for (auto w : cnt) {
        if (w & 1) {
            cout << "No\n";
            return;
        }
    }

    cout << "Yes\n";
}
```

### C

- 不知道为什么这么做: 每次选择一种数一直加到合法

```cpp
int a[10] = {3, 4, 5, 6, 7, 8, 9, 0, 1, 2};

inline bool check(long long x) {
    while (x) {
        if (x % 10 == 7) return true;
        x /= 10;
    }
    return false;
}

inline void solve() {
    cin >> n;

    int ans = a[n % 10];

    for (auto w : num9) {
        if (w > n * 10) {
            break;
        }

        int cnt = 0;
        long long x = n;

        while (!check(x) && cnt < ans) {
            x += w;
            cnt++;
        }

        ans = min(ans, cnt);
    }

    cout << ans << "\n";
}
```

### D

- 先看 x 中是不是 1-n 都出现了
- 如果有数字没出现, 那么如果答案是一个有向图, 则这个数字对应的点到任何点的最短路为 0, 而曼哈顿距离根据题意不可能为 0, 所以询问一次看结果是否非零即可
- 如果 1-n 都出现了, 选择询问数字 1 出现的下标 pos1 和数字 n 出现的下标 posn
  - 如果是曼哈顿距离, 距离至少是 n-1, 因此如果询问的结果小于 n-1, 一定是有向图
  - 而 n 个点最短路不可能大于 n-1, 因此如果询问的结果大于 n-1, 一定是曼哈顿距离
  - 只剩下等于 n-1 的情况: 如果是有向图, 显然 posn 到 pos1 的最短路不可能是 n-1, 所以反过来询问一次, 结果相同则是曼哈顿距离, 否则是有向图

```cpp
inline void solve() {
    cin >> n;

    vector<int> a(n + 1);

    for (int i = 1; i <= n; i++) {
        cin >> a[i];
    }

    int cnt = 0;

    vector<int> vis(n + 1);

    for (int i = 1; i <= n; i++) {
        if (!vis[a[i]]) {
            cnt++;
        }
        vis[a[i]]++;
    }

    if (cnt != n) {
        for (int i = 1; i <= n; i++) {
            if (!vis[i]) {
                int j = 1;
                while (j == i) j++;

                int x = query(i, j);
                int y = query(j, i);

                if (x) {
                    cout << "! B" << endl;
                    return;
                } else {
                    cout << "! A" << endl;
                    return;
                }
            }
        }
    }

    int pos1 = -1, posn = -1;

    for (int i = 1; i <= n; i++) {
        if (a[i] == 1) pos1 = i;
        if (a[i] == n) posn = i;
    }

    int x = query(pos1, posn);

    if (x < n - 1) {
        cout << "! A" << endl;
        return;
    }

    if (x > n - 1) {
        cout << "! B" << endl;
        return;
    }

    int y = query(posn, pos1);

    if (x == y) {
        cout << "! B" << endl;
    } else {
        cout << "! A" << endl;
    }
}
```

### E

- 显然可以取所有正数, 记正数有 cnt 个
- 显然不能取两个 0
- 那么答案至少为 cnt, 至多为 cnt+1, 现在就看能不能放入一个 0
- 计算出正数的前缀 min, 以及**假设后缀中初始就有一个 0** 的后缀 mex

  ```cpp
  for (int i = 1; i <= n; i++) {
      pre[i] = min(pre[i - 1], (a[i] == 0 ? inf : a[i]));
  }

  for (int i = n, x = 1; i >= 1; i--) {
      if (a[i] < n) vis[a[i]] = 1;
      while (vis[x]) x++;
      suf[i] = x;
  }
  ```

- 如果放入一个 0, 那么从 0 开始到最后的部分不需要检查, 因为始终前缀 min 等于 0, 后缀 mex 也等于 0
- 所以只检查 0 前面的部分: 如果存在 i, a[i] == 0, 且对于所有 1<=t<i, pre[t]>=suf[t+1], 说明可以放入 a[i] 这个 0

  ```cpp
  for (int i = 1; i <= n; i++) {
      if (a[i] == 0) {
          cout << cnt + 1 << "\n";
          return;
      }

      if (i < n && pre[i] < suf[i + 1]) {
          break;
      }
  }
  ```

- 完整代码

```cpp
inline void solve() {
    cin >> n;

    vector<int> a(n + 1);

    for (int i = 1; i <= n; i++) {
        cin >> a[i];
    }

    int cnt = n - count(a.begin() + 1, a.end(), 0);

    const int inf = 1e9 + 1;

    vector<int> pre(n + 1, inf), suf(n + 1), vis(n + 1);

    for (int i = 1; i <= n; i++) {
        pre[i] = min(pre[i - 1], (a[i] == 0 ? inf : a[i]));
    }

    for (int i = n, x = 1; i >= 1; i--) {
        if (a[i] < n) vis[a[i]] = 1;
        while (vis[x]) x++;
        suf[i] = x;
    }

    for (int i = 1; i <= n; i++) {
        if (a[i] == 0) {
            cout << cnt + 1 << "\n";
            return;
        }

        if (i < n && pre[i] < suf[i + 1]) {
            break;
        }
    }

    cout << cnt << "\n";
}
```
