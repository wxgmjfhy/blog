---
title: "AI Infra 推理入门"
date: 2026-08-15
tags: ["AI Infra", "推理优化", "vLLM", "CUDA", "Triton"]
categories: ["技术笔记"]
keywords: ["AI Infra", "推理优化", "KV Cache", "PagedAttention", "FlashAttention", "CUDA"]
---
## 一、LLM 的一次推理

你给模型一句话，比如「介绍你自己」。它不会整段想好再吐出来，而是一次产出一个词（更准确说，
一个 token），把这个 token 接到原文后面，再跑一遍，直到它决定停，或达到长度上限。

这条回路叫**自回归**。后面所有系统问题都从这里长出来：下一步依赖上一步，所以单条请求的未来
token 没法提前算；不同请求之间没有这种依赖，所以可以拼在一起算。

### decoder block 之外

文本由 tokenizer 变成 token（id），token 再经过 embedding 变成向量：
- Embedding 是一张表，行数等于词表大小，列数等于 `hidden_size`。Qwen3-0.6B 的 `hidden_size` 是 1024，所以每个 token 变成一个 1024 维向量。这串向量叫 hidden_state / 残差流，后面每一层都在改它，但宽度保持 1024。
- Qwen3-0.6B 打开了 `tie_word_embeddings`：表的另一头，LM Head 用同一份权重，把向量点回词表，得到每个词的打分。

接下来是 N 层 decoder block，我们后面再讲；hidden_state 这一串向量经过 decoder block 丰富了信息，来到 LM Head，得到 logits：每个位置一个长度为词表的分数向量。生成下一个 token 时，真正用到的是序列最后一个位置的那一行。

但我们不会直接使用分数去生成下一个 token，而是经过 softmax 将一行分数变成和为 1 的非负权重，这样就得到了词表中每个词的概率；基于这个概率，可以采取多种 sample / 采样策略，最终得到下一个 token。

### decoder block 之内

> 首先是我对深度学习的粗糙理解：我们其实就是在模拟一个高维函数，只要维度足够高、函数足够复杂，它就能够模拟真实世界的规律。深度学习要做的事情，就是让机器想办法模拟这个函数。

Qwen3-0.6B 有 $N = 28$ 层 decoder block，每一层主要包括：
1. Norm
2. Attention
3. Norm
4. MLP / FFN

教科书级别的 pre-norm 可以如下表示：
$$
x = x + \mathrm{Attn}(\mathrm{Norm}(x)) \\
x = x + \mathrm{MLP}(\mathrm{Norm}(x))
$$

这里面的计算有 Norm，加法，Attn 和 MLP，而在 nano-vllm 中，为了减少 GPU 计算时搬用数据的消耗，采取了算子融合的手段：将加残差推迟到下一次的 Norm 中去做。

**Norm** 的作用是什么？鉴于我缺少数学基础，目前我仅理解为数学意义上的稳定操作，防止尺度乱跑。

这里的加法则是**残差连接**：
- 在残差连接出现之前，x 经过多层的变化后，会丢失 / 扭曲原本的信息，层数加深后误差反而增大
- 有了残差，x 经过一层可以什么都没学到，深度得以利用

接着便是 **Attention**，transformer 的核心，$x$ 经过 $W_Q$，$W_K$，$W_V$ 三个权重矩阵变成：
- Q：我在找什么
- K：我是什么
- V：我能提供什么

Q 和 K 比较相似度，“找到” V，进行加权求和。

Attention 更具体来讲，依次是：
1. $Q = xW_Q$，$K = xW_K$，$V = xW_V$
2. `reshape 成 heads`
3. `RoPE(Q, K, position)` 位置编码，获得 token 之间的位置关系信息
4. $\mathrm{score} = QK^\top / \sqrt{d}$ 计算相似度
5. $\mathrm{causal\ mask} + \mathrm{softmax}$ 遮住（mask）未来，并经过 softmax 变为权重
6. $\times V$ 加权求和

最后介绍 **MLP / FNN** —— Attention 更像是**从上下文中取信息**（在 token 之间，找出关联，丰富信息，得到融合了上下文信息的 token 表示）；而 MLP / FFN 更像是**在同一个 token 的特征之间做变换，对信息进行非线性加工和存储知识**：
- 一个 token 的特征之间做变换：MLP 通过升维操作，在输入的特征重新（线性）组合成新的特征
- 对信息进行非线性加工：MLP 通过引入激活函数，实现了非线性函数的模拟，非线性加工可以选择保留哪些组合
- 存储知识：MLP 的参数中隐藏着知识的映射关系

### 数字

数字来自 Qwen3-0.6B 的 `config.json`。这一节只算「一次前向里张量有多宽」，KV 占多少字节放到第 2 节。

参数在算什么：

| 参数 | 含义 | Qwen3-0.6B |
|---|---|---|
| `vocab_size` | 词表行数，Embedding / LM Head 的一侧 | 151936 |
| `hidden_size` | 残差流宽度，一层进出都是它 | 1024 |
| `num_hidden_layers` | Decoder 叠多少层 | 28 |
| `num_attention_heads` | Q 头数 | 16 |
| `num_key_value_heads` | KV 头数；小于 Q 头就是 GQA | 8 |
| `head_dim` | 每个头的宽度，配置里单独给 | **128** |
| `intermediate_size` | SwiGLU 升维后一半的宽度 | 3072 |
| `torch_dtype` | 权重和激活的位宽 | bf16（2 字节） |
| `tie_word_embeddings` | Embedding 和 LM Head 是否共用一张表 | true |

注意：
- $\mathrm{head\_dim} = 128$ 是配置给出的
- 不能这样计算：$\mathrm{head\_dim} = \mathrm{hidden\_size} / \mathrm{num\_attention\_heads} = 1024/16 = 64$

因此：

| 量 | 计算 | 结果 |
|---|---|---|
| Q 投影输出宽度 | $\mathrm{num\_attention\_heads} \times \mathrm{head\_dim} = 16 \times 128$ | $2048$ |
| K/V 投影输出宽度 | $\mathrm{num\_key\_value\_heads} \times \mathrm{head\_dim} = 8 \times 128$ | $1024$ |
| GQA 共用比 | $16 / 8$ | $2$（每 2 个 Q 头共用 1 组 K/V） |
| softmax 缩放 | $1 / \sqrt{\mathrm{head\_dim}} = 1 / \sqrt{128}$ | $\approx 0.0884$ |

残差流全程是 $[T, 1024]$，$T$ 是本步送进模型的 token 数。Q 投影把每个位置扩到 2048 再拆成 16 个头，算完注意力再乘输出投影，回到 1024。

一次前向里和形状有关的矩阵乘（写成 $[T, \text{in}] \;@\; [\text{in}, \text{out}]$）：

| 算子 | 形状变化 |
|---|---|
| Embedding 查表 | $\text{vocab} \times \text{hidden} = 151936 \times 1024$ |
| Q | $[T, 1024] \;@\; [1024, 2048] \to [T, 16, 128]$ |
| K / V | $[T, 1024] \;@\; [1024, 1024] \to [T, 8, 128]$ |
| O（注意力输出投影） | $[T, 2048] \;@\; [2048, 1024] \to [T, 1024]$ |
| SwiGLU 的 gate+up | $[T, 1024] \;@\; [1024, 6144]$ → 劈成两半各 3072 |
| SwiGLU 的 down | $[T, 3072] \;@\; [3072, 1024] \to [T, 1024]$ |
| LM Head（只取最后位置） | $[1024] \;@\; [1024, 151936] \to 151936$ 维 logits |

## 二、GPU

### GPU 模型

1. GPU 内存模型（金字塔模型，自顶向下）

- RMEM：寄存器堆，最快的存储，就在 compute unit 旁边；寄存器为每个 thread 私有
- L1 cache / SMEM：L1 cache 为每个 SM 私有的 SRAM 缓存；SMEM 为程序员管理的片上共享内存
- DSMEM：分布式共享内存
- L2 cache：多个 SM 共享的大型 SRAM 缓存
- VRAM：DRAM 内存，由堆叠的 HBM（高带宽内存）实现，大而慢

2. GPU 计算单元

计算的基本单元是 SM，一个 SM 中大致有：
- Tensor Core：小规模矩阵乘加
- CUDA cores and SFUs：其他计算（速度比 Tensor Core 低一个数量级）
- Warp scheduler：每个 SM 包含调度器，为 32 个 thread 组成的 warp（线程束）发射指令

3. GPU 编程模型

Kernel 是一段 GPU 程序，对应「对整块数据做同一种事」，比如一次矩阵乘、一次写 KV。CPU 发起一次 launch：用多大并行度、跑哪个 kernel。

一张卡有很多 SM，一次 kernel 的 grid（一次 launch 的全部 block）被拆成许多 block（共享内存的一组 thread），每个 block 进一个 SM，block 里的 thread（一个工作项，用自己的寄存器）再按 warp（锁步的 32 个 thread，锁步指 32 个 thread 必须同时做同一种指令）被调度。

### 高效深度学习

从三个部分来理解高效深度学习：
1. **Compute**：GPU 执行浮点数运算的时间
2. **Memory**：GPU 内部传输 / 搬运 tensor 的时间
3. **Overhead**：其他所有，比如 CPU 执行

优化前需要判断瓶颈在哪一块；人们往往认为 Compute 不足，但其实：
- 如果将计算操作的规模翻倍，但总时间几乎不变，很有可能 Overhead 占据了大头
- 如果提高算力，但是算力利用率还是很低、带宽吃满，问题则是 Memory

如果不改变你实际执行的操作，需要执行的计算量往往不会显著减少。而一般来讲，矩阵乘加占绝大多数的浮点运算，非矩阵乘加可能只占 0.2%；但这也不等于非矩阵乘加的计算没有优化的必要，因为 Compute 会导致 Memory，而比如在 FlashAttention v2 中就减少了非矩阵乘加的计算。

GPU 每次计算需要经过 HBM -> SRAM -> HBM 的数据搬运过程，如何减少搬运的次数呢？可以采用**算子融合**的方法，连续的两次算子，我可以在 SRAM 上连续算完再搬回 HBM，而不是计算一次就搬运一次，就比如上文提到的 Norm 和残差的融合。

Overhead 也是不可忽视的一部分：Python 和框架需要决定如何调用、执行调用，这些都是启动税；有可能 GPU 很快算完在等下一次 launch，而 CPU 还在一层层决定「下一个 kernel 是谁」；优化的方法比如 **CUDA graph**：
- 一次 launch：CPU 说「用这么大的 grid/block，跑这个 kernel」。launch 本身要花钱：Python、PyTorch 的类型分发、驱动把任务送进 GPU
- Decode 的一步：一个新 token，穿过 28 层几乎同一套 kernel，形状几乎不变。
- CUDA Graph 的做法是：先用固定形状空跑一遍，把这串 kernel 的依赖录成一张图（probably DAG），之后每步不再重新 launch，只 replay 这张图，并把新输入写进事先留好的缓冲区。

## 三、推理优化原理

### Prefill & Decode

自回归如果每步都把已经生成的整段再算一遍，第 $t$ 步的注意力会重复做前 $t-1$ 步已经做过的 K、V。K 和 V 只依赖已经存在的 token，不依赖未来，所以可以存下来，这份缓存就是 **KV Cache**。

于是一次请求裂成两段。
- **Prefill**：把整段 prompt 一次送进去。每个 prompt token 都算出 K、V 并写入缓存。注意力在这些 token 之间按因果掩码做完。最后只在最后一个位置采样，得到第一个新 token。prompt 足够长时，这里的矩阵乘很大，往往偏**计算**。
- **Decode**：每次只送进上一步采出的那一个 token，写出它的 K、V，读出历史 KV，采下一个。每一步为了一个 token，要把模型权重从显存里过一遍，还要读已经积累的 KV。权重比激活大得多的时候，这段偏**访存**。

回顾上一节介绍的优化手段：
- Prefill 往往是大 kernel，启动税相对便宜，所以更吃融合和 Tensor Core
- Decode 是很多小步，启动税和读权重都会露出来，所以更吃 CUDA Graph 和更大的 batch

### KV Cache 占用的内存

如何计算 KV 需要多大？每一个 token 需要：
1. 需要同时存 K 和 V，那么需要乘以 2
2. 每一层 decoder block 都有自己的 KV，因此乘以 num_hidden_layers，此处是 28 层
3. 一个 K / V 有多大？$\mathrm{num\_kv\_heads} \times \mathrm{head\_dim} = 8 \times 128 = 1024$
4. Qwen3-0.6B 使用的精度是 bf16（2 bytes），因此再乘以 dtype_bytes = 2
5. （如果考虑张量并行，如果将 KV 头分到多卡上，计算可以除以卡数）

因此，一个 token 需要存储 $2 \times 28 \times 1024 \times 2 = 114688$ byte，大约 112 KiB 每个 token。$\mathrm{max\_model\_len} = 4096$ 时，一条序列的 KV 上界大约 448 MiB。模型自己写着 $\mathrm{max\_position\_embeddings} = 40960$，若按这个长度预留，一条就大约 4.4 GiB。nano-vllm 会把 $\mathrm{max\_model\_len}$ 截到配置和模型上限的较小值，默认 4096。

注意：
- max_position_embeddings 指我们平时所说的模型上下文窗口大小，比如 Opus 支持 1M 上下文
- max_model_len 是 vllm 的服务参数，是引擎给这条请求划的长度天花板

### PagedAttention & Prefix cache

KV Cache 的存储是一个问题，因为其非常大，而且是变长的。如果给每条请求在显存里划一段连续空间，长度等于 max_model_len，短请求会留下用不上的大洞，新请求也塞不进去。这是外碎片，和操作系统里按进程预留整段物理内存是同一类问题。

**PagedAttention** 采用 OS 经典分页思想：将 KV 切成固定大小的块，所有请求共享内存块池，序列通过块表映射到物理内存块。这样只有最后一块可能放不满，存在内存缝隙。但块的粒度越小，碎片就越小，内存浪费往往更少；不过，块变小也会增加“管理”的难度，会增加块表、寻址、分配等开销；就像算法竞赛中的分块算法，需要选择合适的块大小（一般是 $\sqrt{n}$）才能平衡时间复杂度。

**前缀缓存 Prefix cache** 建立在同一套块上。把完整块里的 token 做成链式哈希：第 i 块的哈希吃进第 i-1 块的哈希和本块 token。新请求进来，从左往右找最长命中，命中的块加引用计数，不再算一遍。引用减到 0，块回到空闲池；真正不能再复用，是这块被重新分配给别人的那一刻，旧哈希被清掉。

### FlashAttention & Online Softmax

回顾这三步：
> 4. $\mathrm{score} = QK^\top / \sqrt{d}$ 计算相似度
> 5. $\mathrm{causal\ mask} + \mathrm{softmax}$ 遮住（mask）未来，并经过 softmax 变为权重
> 6. $\times V$ 加权求和

在 GPU 上，朴素 Attention 需要做三次 HBM -> SRAM -> HBM 的搬运：
1. 计算 $S = QK^\top / \sqrt{d} + \mathrm{Mask}$
2. 计算 $P = \mathrm{softmax}(S)$
3. 计算 $O = PV$

再次回顾 Attention 中的计算：
- 记 $T$ 是本步送进模型的 token 数
- 记 $d$ 是每个头的宽度（head_dim）
| 张量 | 形状 |
|---|---|
| $Q, K, V$ | $[T, d]$ |
| $S, P$ | $[T, T]$ |
| $O$ | $[T, d]$ |

**$S$ 和 $P$ 都要在 HBM 上经过一次读和一次写，当 $T \gg d$ 时，搬运的时间复杂度是 $4T^2$。**

**FlashAttention** 采取了分块的策略来减少搬运的消耗，核心思想：HBM 上不出现 S 和 P，块内采用 online / 流式 softmax 计算。

什么是 online softmax？
- $\mathrm{softmax}(x_i) = e^{x_i} / \sum_j e^{x_j}$，实现上防止 exp 溢出转为 $\mathrm{softmax}(x_i) = e^{x_i - \max} / \sum_j e^{x_j - \max}$
- 理论上要有 max，就得先得到所有的 $x_i$；但就像加法可以累加、乘法可以累乘，stdev、softmax 等一些运算可以构造有限维状态向量递推更新

> 状态 $(\mathrm{MAX}, \mathrm{SUM})$，其中 $\mathrm{MAX} = \max_i x_i$，$\mathrm{SUM} = \sum_i e^{x_i - \mathrm{MAX}}$
>
> 新来样本 $x_j$
>
> 1. $x_j > \mathrm{MAX}$：$\mathrm{MAX} = x_j$，$\mathrm{SUM} = \sum_i e^{x_i - x_j}$
> 2. 否则：$\mathrm{SUM} = \mathrm{SUM} + e^{x_j - \mathrm{MAX}}$
>
> Attention 还需要乘以 $V$，那么再维护一个 $a = \sum_i e^{x_i - \mathrm{MAX}} \cdot v_i$ 即可

分块后的复杂度计算：
$Q$ 按行切成块长 $B_r$，$K$、$V$ 按行切成块长 $B_c$：

| 张量 | 形状 |
|---|---|
| $Q_i$ | $[B_r, d]$ |
| $K_j, V_j$ | $[B_c, d]$ |
| $S_{ij} = Q_i K_j^\top$ | $[B_r, B_c]$ |

那么 SRAM 的内存 $M \ge B_r d + 2 B_c d + B_r B_c$。

$B_r$、$B_c$ 也往往由 $M$ 决定，取 $B_r = \Theta(\min(d, M/d))$，$B_c = \Theta(M/d)$。

$T/B_r$ 个 $Q_i$ 需要和全部 $K_j$、$V_j$ 都过一遍，计算搬运量：
- $Q$ 读 1 次，共 $Td$
- $O$ 写 1 次，共 $Td$
- $K$、$V$ 读 $T/B_r$ 次，共 $2 \cdot (T/B_r) \cdot T d = \frac{2T^2 d}{B_r}$

因此，复杂度为 $2Td + \frac{2T^2 d}{B_r}$，代入 $B_r = \Theta(\min(d, M/d))$ 后为 $2Td + \frac{2T^2 d^2}{M}$

通常情况下，$\Theta(T^2) \gg \Theta(Td + T^2 d^2 / M)$，FlashAttention 显著降低了搬运量。

### Continuous Batching & Chunked Prefill

要理解 Continuous Batching，我们先来看传统静态 batching：攒够一批请求，推理完这一批再接下一批。

> $[\mathrm{req}_1, \mathrm{req}_2, \mathrm{req}_3]$  
>
> step 1: 1, 2, 3 同时生成第 1 个 token  
> step 2: 1, 2, 3 同时生成第 2 个 token  
> ...  
> step 7: 可能 1 结束了，此时 2，3 继续生成第 7 个 token  
> ...  
> step N: 1, 2, 3 均结束生成  

显然存在木桶效应：推理服务中往往不同的请求之间输出长度差距大，一个 batch 的时间由最长的请求决定。

不过，我们先思考：为什么需要 batch？这就和 GPU 有关：首先，GPU 天生并行，matmul 支持在 batch 维度并行；但是，GPU 还存在 Kernel Launch Overhead 的固定开销，将 N 个请求打包为一个 batch 就只需要 1 次 overhead。

Continuous Batching 仍然有 batch，不过是这么做的：
- 维护两个序列：
    - Waiting：等待调度的请求序列
    - Running：正在 GPU 上运行的请求序列
- 单位由 batch 变为 step：每个 step 中，将 finished 的请求移出 Running，从 Waiting 中挑选请求移入 Running，将 Running 打包为一个 batch 发给 GPU
- 一个 batch 中仍然会有木桶效应，而因为 Prefill 比 Decode 耗时更长，还会采取以下策略：
    - Prefill / Decode 分离
    - Chunked Prefill：将长 prompt 的 Prefill 拆分为多个 chunk

再具体一些，nano-vllm 中 Prefill 和 Decode 的 batch 是不同的：
1. Prefill：将多个请求序列拼成一个序列，并记录前缀和（例如，一条 5 token，一条 3 token，拼成 $[t_0 \dots t_7]$，前缀和为 $[0, 5, 8]$），然后调用 varlen FlashAttention（flash_attn_varlen_func），这是一个写好的 kernel，根据前缀和区分不同请求序列
2. Decode：每个请求序列输入长度均为 1，不需要前缀和，需要序列的 block table 去加载 KV Cache，调用 flash_attn_with_kvcache 这个 kernel

## 四、PyTorch & CUDA / Triton

### PyTorch

PyTorch 由三个核心组成：
1. Tensor Library：作为计算基础构建模块的张量库，能够基于 GPU 加速计算
2. Automatic Differentiation Engine：自动微分引擎，简化了模型训练中的反向传播和模型优化过程
3. Deep Learning Library：深度学习库，提供模块化、灵活且高效的构建模块

张量库主要就是 `.tensor` 创建 Tensor、`.to` 转换精度、`.shape` 查看张量形状、`.reshape` 重构张量、`.T` 转置、`A @ B` 矩阵乘法等常见操作，了解即可。

自动微分引擎是 PyTorch 维护了计算图（有向图），因此可以方便的反向传播计算梯度：对 loss 调用 `.backward` 方法，就能得到计算图上叶子节点的梯度，存储在 `.grad` 属性中。

最后，深度学习库提供了现成的深度学习模块，例如 `torch.nn.Module`，还有 `Dataset`、`DataLoader` 等组件。

还有就是：PyTorch 支持 GPU 计算，比如 `to("cuda")` 可以将数据转移到 GPU 上；如果有多个 GPU 可用，还可以使用 DDP 分布式训练。

### CUDA

直接看代码：
- `__global__` 标记一个函数为可用跑在 GPU 上的 CUDA kernel
- `cudaMallocManaged` 和 `cudaFree` 管理 GPU 上的内存
- `<<< >>>` 启动 kernel，比如 `add<<<1, 1>>>(N, sum, x, y)`
- GPU 计算是异步的，调用 `cudaDeviceSynchronize` 阻塞 CPU

```cpp
#include <iostream>
#include <math.h>
 
// Kernel function to add the elements of two arrays
__global__
void add(int n, float *x, float *y)
{
 for (int i = 0; i < n; i++)
   y[i] = x[i] + y[i];
}
 
int main(void)
{
 int N = 1<<20;
 float *x, *y;
 
 // Allocate Unified Memory – accessible from CPU or GPU
 cudaMallocManaged(&x, N*sizeof(float));
 cudaMallocManaged(&y, N*sizeof(float));
 
 // initialize x and y arrays on the host
 for (int i = 0; i < N; i++) {
   x[i] = 1.0f;
   y[i] = 2.0f;
 }
 
 // Run kernel on 1M elements on the GPU
 add<<<1, 1>>>(N, x, y);
 
 // Wait for GPU to finish before accessing on host
 cudaDeviceSynchronize();
 
 // Check for errors (all values should be 3.0f)
 float maxError = 0.0f;
 for (int i = 0; i < N; i++) {
   maxError = fmax(maxError, fabs(y[i]-3.0f));
 }
 std::cout << "Max error: " << maxError << std::endl;
 
 // Free memory
 cudaFree(x);
 cudaFree(y);
  return 0;
}
```

以上是一个简单的语法示例，还没有用上 GPU 并行计算；我们注意到 `<<<1, 1>>>`，这两个参数分别是：
1. 一个 kernel 使用的 block 数量
2. 一个 thread block 中的 thread 数量（必须是 32 的倍数）

> 回顾前文：
>
> Kernel 是一段 GPU 程序，对应「对整块数据做同一种事」，比如一次矩阵乘、一次写 KV。CPU 发起一次 launch：用多大并行度、跑哪个 kernel。
>
> 一张卡有很多 SM，一次 kernel 的 grid（一次 launch 的全部 block）被拆成许多 block（共享内存的一组 thread），每个 block 进一个 SM，block 里的 thread（一个工作项，用自己的寄存器）再按 warp（锁步的 32 个 thread，锁步指 32 个 thread 必须同时做同一种指令）被调度。

假设我们讲 `<<<1, 1>>>` 改为 `<<<1, 256>>>`，这个 kernel 就会自动 256 个 thread 并行计算吗？不会。事实上，如果不修改 kernel 的代码，这个 kernel 会在每个 thread 中执行一次，即重复算 256 次。

CUDA C++ 提供了关键字，允许 kernel 获取正在运行的 thread 的索引：
- threadIdx.x：当前线程在其块内的索引
- blockDim.x：块中的线程数

因此如下修改 kernel：
```cpp
__global__
void add(int n, float *x, float *y)
{
  int index = threadIdx.x;
  int stride = blockDim.x;
  for (int i = index; i < n; i += stride)
      y[i] = x[i] + y[i];
}
```

接着修改第一个参数。假设我有 N 个元素需要处理，且每个块有 256 线程，我需要计算块的数量以确保至少 N 个线程：
```cpp
int blockSize = 256;
int numBlocks = (N + blockSize - 1) / blockSize;
add<<<numBlocks, blockSize>>>(N, x, y);
```

然后更新 kernel，应该不难理解：
```cpp
__global__
void add(int n, float *x, float *y)
{
  int index = blockIdx.x * blockDim.x + threadIdx.x;
  int stride = blockDim.x * gridDim.x;
  for (int i = index; i < n; i += stride)
    y[i] = x[i] + y[i];
}
```

最后介绍两个点：
1. 性能分析：使用 NSight Systems 命令行工具 `nsys`，比如 `nsys profile -t cuda --stats=true ./add_cuda`
2. 内存管理：GPU 内有 HBM -> SRAM -> HBM 的搬运流程，主机（host）和设备（device，指 GPU）之间也有内存搬运，`cudaMemPrefetchAsync()` 可以预先将数据搬到 GPU 上

### Triton

由于没有编写过复杂的 CUDA 代码，因此我暂时不能完全体会 Triton 对原生 CUDA 的简化。

Triton 主要的不同点在于：在 CUDA 中，我们仍然是编写 `y[i] = x[i] + y[i]` 这样的标量计算，一个 kernel 的视角也是在一个 thread 内；而在 Triton 中，我们则是编写向量运算（or 数据块），一个 kernel 的视角是在一个 thread block 内（不过 block 在 Triton 中抽象为了 program 的概念），block 内的内存合并、同步、寄存器分配、warp 等操作都隐藏到编译器中了。

暂时记到这里吧，后续再补充 Triton 实现 Vector Addition、Fused Softmax 和 Matrix Multiplication 的详细笔记。
