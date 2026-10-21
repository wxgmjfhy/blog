---
title: "RL 异步 rollout"
date: 2026-10-20T17:00:00+08:00
tags: ["RL", "强化学习", "异步训练", "LLM"]
categories: ["技术笔记"]
description: "从 RL 基础、IMPALA/V-trace、Partial Rollout、AReaL，到 DeepSeek V4.1 / GLM-5.3 / MiMo V2.6 / Kimi K3 的异步 rollout 方案调研与总结。"
---

## RL 基础

一个 MDP 写作 $(\mathcal{S}, \mathcal{A}, P, R, \gamma)$，每一步形如：

$$s_t \xrightarrow{\pi} a_t \xrightarrow{P,\,R} (r_t,\ s_{t+1})$$

$$\text{objective:} \max_\pi \mathbb{E}_\pi\left[\sum_{t=0}^{T-1} \gamma^t r_t\right]$$

对应到 LLM（token-level MDP）：
- 状态 $s_t$：当前 context，即 prompt + 已生成 token $(x, y_{<t})$，还可能包含环境反馈
- 动作 $a_t$：生成下一个 token $y_t$
- 策略 $\pi_\theta(a_t \mid s_t)$：模型输出的 next-token 分布
- 转移概率 $P$：LLM 中是确定性转移 $s_{t+1} = s_t \oplus y_t$
- 奖励 $r$：来自 reward model / verifier / environment
- 折扣因子 $\gamma$：LLM RL 常取 $\gamma = 1$

在当前 LLM RL 中，奖励信号通常是稀疏的：仅在整条轨迹的终点给出一次整体评分，中间每一个 token 的生成步骤没有即时奖励反馈。稀疏奖励带来两个问题：一是策略梯度估计的方差高，训练过程波动大；二是信用分配困难，难以将最终的成败结果准确归因到每一步 token 生成的决策上。Actor-Critic 架构用价值网络 $V_\theta(s)$ 估计每步的期望回报，把终点信号分摊回每个 token。

> 注意：
>
> - $V^\pi(s)=\mathbb{E}_\pi[G_t \mid s_t=s]$ 是理论真值，其中 $G_t=\sum_{k=0}^{T-t-1}\gamma^k r_{t+k}$ 为从时刻 $t$ 起的折扣累计回报
>
> - $V_\theta(s)$ 是价值网络给出的评估值，$V_\theta$ 需要与策略联合训练
>
> - $V^\pi \ne V_\theta$

---

RL 的一次 rollout 是用策略在环境 / 任务中采样出一条轨迹 trajectory：

$$\tau = (s_0,\ a_0,\ r_0,\ \dots,\ s_{T-1},\ a_{T-1},\ r_{T-1},\ s_T)$$

在 LLM 中，rollout 即根据 prompt 生成一段 response；而在 agent 场景中，rollout 扩展为包含了 LLM action 和环境反馈的多轮任务轨迹。

rollout 可以分为同步 rollout 和异步 rollout。同步 rollout 即 training 阶段和 rollout 阶段交替执行：

$$\mathrm{training} \to \mathrm{rollout} \to \mathrm{training} \to \mathrm{rollout} \to \dots$$

不过，rollout 阶段往往不是只采样一条轨迹，而是采样一个 batch、多条轨迹；一个 batch 内的生成长度是长尾分布，必须等最长的结束了才能进入训练，这导致大量的资源空闲；当前 LLM 的长上下文推理、以及 agent 长任务，又进一步加剧了这个问题。**针对这个问题，于是产生了异步 rollout，即 training 和 rollout 可以并发执行，意图提升整个系统的效率。但是异步 rollout 又引入了 off-policy 问题：用于训练当前策略 $\pi_\theta$ 的样本，是由旧策略 $\pi_{\mathrm{old}}$ 生成的。直接复用旧策略采样的样本更新当前策略，会造成轨迹分布与目标策略分布不匹配，导致策略梯度估计存在偏差，破坏策略更新的稳定性，甚至引发策略退化。**

## 异步 rollout 技术

### Off-policy：修正与容忍

DeepMind 于 2018 年提出了 [Importance Weighted Actor-Learner Architecture (IMPALA)](https://arxiv.org/html/1802.01561v3)，IMPALA 架构将环境交互（Actor，生成轨迹）和模型参数更新（Learner，学习）解耦，Actor 只把状态、动作、奖励组成的轨迹发送给 Learner，而非传递梯度，以此实现大规模分布式部署，可扩展至数千台机器。但 Actor 生成轨迹使用的策略会滞后于 Learner 端最新策略，产生 off-policy 偏差，为此论文提出 V-trace 算法来修正 off-policy。

IMPALA 的系统结构很简洁：Actor 负责拿一份策略跑环境、产出 trajectory，扔进 queue；Learner 从 queue 拿出 trajectory 计算 loss、更新参数，再把新参数发回给 Actor。

针对 off-policy 问题「用策略 $\mu$ 生成的轨迹，来学习另一个策略 $\pi$ 的价值函数 $V^\pi$」，首先采用的手段是**重要性采样**：加一个重要性权重 $\rho_t = \frac{\pi(a_t \mid x_t)}{\mu(a_t \mid x_t)}$ 去修正轨迹数据的重要性：
- $\rho > 1$ 说明新策略认为这个动作比旧策略更可能，提升重要性；
- $\rho < 1$ 说明新策略认为这个动作不太可能，降低重要性。

但是，一个多步的轨迹中，不止一个 $\rho$，而是 $\prod_{t=0}^{T}\rho_t$；而 $\rho$ 之间方差可能很大，直接乘可能爆炸或接近于 0，因此我们需要对权重进行**裁剪**。V-trace 引入了：

$$\rho_t = \min\left(\bar{\rho},\ \frac{\pi}{\mu}\right), \qquad c_t = \min\left(\bar{c},\ \frac{\pi}{\mu}\right)$$

并用 $v_s$ 来作为 $V_\theta(s)$ 学习的目标：

$$v_s = V(x_s) + \sum_{t=s}^{s+n-1}\gamma^{t-s}\left(\prod_{i=s}^{t-1}c_i\right)\delta_t^V$$

其中 $\delta_t^V = \rho_t\left(r_t + \gamma V(x_{t+1}) - V(x_t)\right)$，即 $\rho$ 乘上标准 TD error。另外，论文假设 $\bar{\rho} \ge \bar{c}$。当 $\pi = \mu$ 时，假设 $\bar{\rho} \ge \bar{c} \ge 1$，则所有的 $\rho_t = 1$ 且 $c_t = 1$，此时 V-trace 自动退化成普通 n-step 回报。

**$\rho_t$ 很好理解，就是修正当前这一步 TD error 本身；$c_t$ 则是控制多步回溯时，误差能不能向后（逆时间）传播，$c_t$ 越小，远期未来的信息衰减越厉害，这样就控制了方差。**

> $v_s$ 可以递归求解：
> 
> $$v_s = V(x_s) + \delta_s^V + \gamma c_s (v_{s+1} - V(x_{s+1}))$$
> 
> 令 $D_s = v_s - V(x_s)$，递归式即：
> 
> $$D_s = \delta_s^V + \gamma c_s D_{s+1}$$
> 
> 也就是“当前修正 = 当前 TD 修正 + 折扣后、被 $c$ 衰减的未来修正”。

---

迁移到 LLM RL，[Asynchronous RLHF: Faster and More Efficient Off-Policy RL for Language Models](https://arxiv.org/html/2410.18252) 借鉴经典深度强化学习中 Actor 与 Learner 解耦的异步思想，提出了面向 LLM 的异步 RLHF 方案，并探索了异步训练对 off-policy 的容忍度：
- PPO、RLOO、Online DPO 等算法中，Online DPO 对 off-policy 的容忍度最高，并且策略模型规模越大，这种对 off-policy 的抗干扰能力越强。
- 论文真正部署的方案是 Cleanba 式的 one-step off-policy：第 $t$ 步用 $\theta_t$ 生成 $y_t$，同时用上一步的 $y_{t-1}$ 训练。此时 $T_{\mathrm{async}} \approx \max(T_{\mathrm{gen}},\ T_{\mathrm{train}})$，可以根据哪个部分是瓶颈来决定空闲算力的使用，比如：
    - generation-bound：训练 GPU 空闲，则同一批数据多训几遍（PPO epoch），提高样本效率。
    - training-bound：生成 GPU 空闲，则可以每个 prompt 采样更多候选回复，选取奖励最高和最低样本构造 DPO 损失，得到梯度信号更强的偏好对。

### Partial Rollout：另一种路线

长 CoT 强化学习中，不同样本输出 token 长度差异极大（长尾分布）：大部分样本很快生成完毕，少数样本需要生成数万 token。传统同步方式必须等整个 batch 全部轨迹生成完成，才能进入训练，长尾长轨迹会卡住整个批次，GPU 大量空闲；同时 128k 超长 CoT 一次性完整生成开销巨大，容易 OOM。[Kimi K1.5: Scaling Reinforcement Learning with LLMs](https://arxiv.org/html/2501.12599) 中提出 Partial Rollout 来解决长序列 RL 的长尾算力浪费、显存压力等问题。

**Kimi K1.5 更像是采用了一个同步 rollout 的系统方案，training 和 rollout 交替进行；不过，Partial Rollout 为 rollout 设置固定单轮 token 预算，当一条轨迹生成到 token 预算时还没有得到最终答案，不丢弃这条未完成轨迹而是暂存轨迹及相关状态，下一轮 rollout 迭代，从 buffer 取出这些未完成的前缀，直接从断点继续解码，不需要从头重新生成整段思考链。一条超长 CoT 轨迹被拆成多个片段，跨多轮迭代逐步生成完成。**

训练时，我们可以区分片段策略来源：
- 当前迭代新生成片段：属于当前策略，用于策略梯度损失计算（on-policy 部分）。
- 从 buffer 复用的旧片段：来自旧策略，属于 off-policy 数据；论文里可以选择把旧片段排除在梯度损失计算之外，只拿当前迭代新生成的 token 做损失，规避 off-policy 偏差污染训练信号。

> 这里其实存在一个问题：旧策略生成的 token 前缀，其实应当重新 prefill 计算 KV，那么为什么 Partial Rollout 还能够提高效率？我暂时猜测是因为 prefill 可以并行计算，往往快于 decode（涉及系统上的 trade-off）。

一条轨迹最终由多个策略生成，Partial Rollout 还是引入了一点 policy staleness；但是，训练计算 loss 时排除旧片段，同时 OMD 算法采用 KL 限制每次 policy update 的幅度，使这种 staleness 不至于太严重。

---

[APRIL: Active Partial Rollouts in Reinforcement Learning to tame long-tail generation](https://arxiv.org/html/2509.18521v3) 提出了另一种 Partial Rollout 方案，将每次 rollout 的 token 预算，改为了一轮 rollout 完成的轨迹预算：**在每一轮 rollout 时超额发起更多生成请求（2x），一旦收集到目标数量的完整样本就提前终止剩余任务，没有完成的部分轨迹存入缓冲区，放到后续迭代继续续写**。这套方案从根源上消除长尾样本带来的 GPU 空闲气泡，提升 rollout 阶段的 token 吞吐，并且不需要修改底层 RL 损失公式，能够直接兼容 GRPO、DAPO、GSPO、PPO 等主流 LLM 强化学习算法。

> 需要注意的是：虽然一轮 rollout 收集到足够的样本就结束，但是对于 GRPO/DAPO 这类 group-based 算法，必须等同一个 prompt 的 N 条 response 全部生成完毕，这个 group 才算有效，才能拿去算奖励、算优势、做梯度更新。
> 
> 不过，论文将同一个 prompt 的 N 条样本放在一个 batch，并且假设同一个 prompt 多次采样出来的多条回复 token 长度标准差很小，组内不会出现极端长尾，所以一个 group 内的所有样本几乎会在相近时间一起完成。

这样仍然引入了 off-policy，实验统计每步里约 40% token 来自旧策略生成的前缀；但大量数学任务实验表明，这种轻度 off-policy 并不会破坏训练稳定性，反而增加了轨迹多样性，带来约 2.1% 的平均精度提升。

### AReaL：fully-async 系统

最后来到 [AReaL: A Large-Scale Asynchronous Reinforcement Learning System for Language Reasoning](https://arxiv.org/html/2505.24298v5)，完全异步、持续流式的 RL 系统。AReaL 将样本生成 rollout 和模型训练完全解耦，rollout worker 持续流式生成轨迹，不需要互相等待；训练 worker 只要收集到足够数据就立刻执行模型更新，更新后的权重会同步给各个 rollout worker。

**具体而言，trainer 更新一次权重以后，会立即通知 rollout worker，此时 worker 会中断当前生成、丢弃 KV Cache，更新权重，然后重新 prefill 并继续 decode 生成。因此，一段轨迹可能是由多个策略生成的。**

对于 off-policy 数据，AReaL 主要采用两个手段，首先是 **Decoupled PPO**。在标准 PPO 中，涉及两个策略：
- 当前策略 $\pi_\theta$：正在优化的策略
- 行为策略 $\pi_{\mathrm{old}}$：实际生成数据的策略

PPO 通过重要性采样比率 $\frac{\pi_\theta}{\pi_{\mathrm{old}}}$ 进行校正，并用 Clip 操作将比率限制在 $[1-\epsilon,\ 1+\epsilon]$ 内防止更新步长过大。标准 PPO 假设所有轨迹是由单一 $\pi_{\mathrm{old}}$ 生成的，但 AReaL 中实际一段轨迹可能是由多个策略生成的。另外，事实上这里 old policy 同时承担两个角色：
- behavior policy：数据是谁生成的。
- proximal policy：新 policy 应该围绕谁不要走太远。

而在 AReaL 中，异步 RL 导致 $\pi_{\mathrm{old}}$ 可能已经很老，实际上是在限制模型不要离一个可能已经很差的旧 policy 太远，AReaL 认为这会拖慢学习。因此，AReaL 拆解为两个角色：行为策略 $\pi_{\mathrm{behav}}$（生成数据的策略）和近端策略 $\pi_{\mathrm{prox}}$（围绕该策略来更新）。目标变成：

$$
J(\theta)
=
\mathbb{E}_{a_t\sim\pi_{\mathrm{behav}}}
\left[
\min
\left(
\frac{\pi_\theta}{\pi_{\mathrm{behav}}}\,\hat A_t,\,
\frac{\pi_{\mathrm{prox}}}{\pi_{\mathrm{behav}}}
\operatorname{clip}
\left(
\frac{\pi_\theta}{\pi_{\mathrm{prox}}},
1-\epsilon,1+\epsilon
\right)
\hat A_t
\right)
\right]
$$

其中，$\frac{\pi_\theta}{\pi_{\mathrm{prox}}}$ 其实在限制 PPO 更新范围，$\frac{\pi_{\mathrm{prox}}}{\pi_{\mathrm{behav}}}$ 则是在校正 off-policy。

> 训练时精确计算 $\pi_{\mathrm{prox}}$ 很难，AReaL 选择取这次模型更新前的那一版策略。

AReaL 采取的第二个手段，是**引入一个参数 $\eta$ 来控制 staleness**。定义：
- $i$：当前最新的 policy version
- $N_r$：到目前为止，已经生成完成的 trajectory 总数
- $B$：每个 training step 需要的 global batch size
- $\eta$：允许 rollout 相对于 training 最多超前多少个 training step

则需要满足：

$$
\left\lfloor\frac{N_r-1}{B}\right\rfloor \le i+\eta
$$

rollout 相较于 training 执行得越快，staleness / off-policy 就越严重。左式可以理解为“rollout 目前相当于走了多少个 training step”，右式则是“当前是第 $i$ 个 step，允许 rollout 最多超前 $\eta$ 个 step”。这样，就限制了 $N_r$ 的增长速度，从而限制了 off-policy 的程度。

## DeepSeek V4.1 / GLM-5.3 / MiMo V2.6 / Kimi K3 异步 rollout 技术调研

### DeepSeek V4.1

[DeepSeek-V4.1-Flash: Pushing the Limits of KV Cache Compression](https://arxiv.org/html/2609.19969) 中，DeepSeek 将 training 和 rollout 部署在了同一批物理设备上（co-located RL），执行上进行 time-share（实际上更像是同步 RL，training 和 rollout 交替执行，而不是并发执行），这样做无需在两个阶段之间进行资源分配、调度，应该也减少了设备之间的通信（相较于 training 和 rollout 解耦的 RL 系统）。

如何设置 rollout 的并发量？DeepSeek 采用 sample-level。在 GRPO 中，一个 prompt 需要采样多个 sample，多个 sample 组成一个 group，而多个 prompt 的许多 sample 组成一个 GPU 计算的 batch。batch-level 即一个 batch 生成结束后派发下一个 batch，这样粒度过大，会导致训练指标出现严重波动；prompt-level 即一个 prompt 的 group 完成后派发下一个 prompt，这样则容易阻塞在 group 内的长尾样本。于是 DeepSeek 采用 sample-level，当 sample 积累到一定数量后（可能来自不同的 prompt），就派发一个新的 prompt（开始生成一个 group 的 sample），这样可以更稳定地维持目标 rollout concurrency。

积累足够的样本后，就会中断 rollout，进入 training。中断采取 token-level interruption，rollout 生成过程中会持久化每个 token 的 KV、expert routing 等数据；中断恢复后，不会重算旧策略生成的 KV，即不会重新 prefill，而是直接继续 decode，复用旧策略生成的 KV。这一点与先前的“恢复后重新 prefill”的方案有所不同。

> 为什么需要保存 expert routing？由于模型参数更新，router 对同一个 token 可能选择不同的 expert。如果训练时使用新 checkpoint 重新计算 routing，就会改变原 rollout 对应的专家选择路径。因此，需要保存每个 rollout 片段产生的 routing，并在训练时按 token 顺序拼接和复用，使训练前向计算沿用对应的 expert 路径，这些被激活的 expert 随后参与梯度更新。

异步生成在有效提升部署效率的同时，也带来两个会降低训练质量的副作用。首先，它会造成长度分布偏差，尤其是在训练初期，因为较短的序列往往会先生成完成，从而在初始训练批次中占据主导地位。其次，它不可避免地会产生 off-policy 样本，即部分或全部由早期 checkpoint 生成的样本。这两个问题需要采用不同的处理策略：
- 针对长度偏差问题，采用了两种机制：
    1. 调度器可以按数据集限制并发量，这有助于调节稳态训练批次中各数据集的占比，通过控制传入样本的来源间接缓解长度偏斜。
    2. 支持丢弃提前返回的短样本，以平滑向稳态长度分布的过渡，并防止模型对过短序列产生过拟合。
- 针对 off-policy 问题，采用了两种经典的机制：
    1. 通过调整控制样本分发和训练样本等待条件的逻辑，来限制最大 off-policy 比率，确保训练数据不会过度偏离当前模型。
    2. 在训练过程中加入损失掩码机制，剔除 staleness 过高的 token 的贡献，从而减轻过期样本对梯度更新的不利影响。

[DeepSeek Elastic Compute (DSec): A Sandbox Infrastructure for Effective Agentic Training at Scale](https://arxiv.org/html/2609.22978v1) 提供了 RL 系统的基建，主要有：
1. **Agent 的 sandbox / 执行状态与 GPU Training 解耦**：GPU 可在 rollout 过程中被抢占用于 Training，而 rollout 的环境状态被独立保存，待 GPU 可用后继续模型生成。

2. **海量 sandbox 的弹性调度**：统一管理 FnCall / Container / MicroVM / VM，并通过镜像按需加载、内存回收、CPU overcommit，把大量长期但低 CPU 利用率的 sandbox 高密度跑起来。

3. **sandbox 和 RL 高度协同**：结合 RL 整个 lifecycle“创建 → rollout → pause/resume → reward → 回收”，同时提供隔离和防 reward hacking 能力。

### GLM-5.3

GLM 使用 slime 框架，这是一个 training 和 rollout 解耦、fully-async 的系统。training 和 rollout 持续并行，中间通过 Data Buffer 来传递数据。

异步系统带来了两个挑战：
1. 首先，每条轨迹都可能由多个版本的旧模型生成，这会导致 off-policy 行为更不可预测、更严重，进而损害训练稳定性。
2. 其次，GRPO 等组级方法与异步训练不匹配。GRPO 为每个 prompt 采样一组响应，并利用组级平均值进行优势估计。每一组，必须等待响应较慢的样本完成后，才能将其送入训练流程，因此组级采样会引发延迟驱动的 off-policy 行为。此外，组级采样与在线或复杂的智能体场景不兼容，在真实 Agentic / online 环境中，轨迹生成往往是非“幂等”的，状态变化、副作用等使得 trajectory 环境难以重建。

[Single-Rollout Asynchronous Optimization for Agentic Reinforcement Learning](https://arxiv.org/html/2607.07508v1) 中提出了单样本异步优化算法 SAO，从一个 prompt 生成一个 group 的多个 sample，改为一个 prompt 生成一个 sample。论文明确 SAO 已用于 GLM-5.2 训练。

SAO 的一个创新点是**直接双边重要性采样（DIS）**：
- 在解耦的 RL 系统中，还存在**训推不一致**的问题：rollout 使用推理引擎（vLLM / SGLang），training 使用训练引擎（Megatron），两者实现存在差异，可能会因为数值精度不同、kernel 编写不同等问题，导致两者基于同一份参数计算得到的 logprob 不相等。
- 因此在解耦的 PPO 中，研究人员采用重要性采样来缓解 off-policy 偏差，具体做法是保留三个不同的模型：当前策略 $\pi_\theta$、旧策略 $\pi_{\theta_{\mathrm{old}}}$ 和部署策略 $\pi_{\mathrm{rollout}}$。其中，$\frac{\pi_\theta}{\pi_{\theta_{\mathrm{old}}}}$ 用于对过时的策略进行校正，$\frac{\pi_{\theta_{\mathrm{old}}}}{\pi_{\mathrm{rollout}}}$ 则用于解决训练与推理之间的不匹配问题。
- 然而，在异步 RL 的单次轨迹生成过程中，rollout 推理模型可能会经历多次更新，这使得（在训练时）精确计算行为概率 $\pi_{\theta_{\mathrm{old}}}$ 的成本变得极高。否则，就需要维护大量的模型 checkpoint 历史记录 $\{\pi_{\theta_{\mathrm{old}}}^{(1)},\dots,\pi_{\theta_{\mathrm{old}}}^{(N)}\}$，而这在实际实现中是不可行的（$\pi_{\mathrm{rollout}}$ 的 logprob 在 rollout 时就已经计算过了，记录下来就无需在 training 的时候再计算，也无需维护 $\pi_{\mathrm{rollout}}$ 的 checkpoint）。
- SAO 将 $\pi_{\theta_{\mathrm{old}}}$ 去掉了，直接将 $\pi_{\mathrm{rollout}}$ 作为行为代理，使用 $\pi_\theta$ 进行重要性采样，即 $r_{t}(\theta)=\frac{\pi_\theta}{\pi_{\mathrm{rollout}}}$。接着，他们将置信区间限制在 $[1-\epsilon_{\ell},\ 1+\epsilon_{h}]$ 范围内，范围外的 token 直接 mask，不参与 loss 计算。

既然不用 GRPO，就需要重新引入 Critic 价值模型，并且对价值模型的质量要求很高。于是 GLM 做了这几件事：
- **价值更新频率高于策略**：每 1 次策略更新做 K=2 次价值更新。这样让价值估计在被用于优势计算之前更快地适应当前策略，从而降低方差。
- **冻结注意力层、只训练 MoE 层**：GLM 发现训练时 Critic 梯度范数显著更大，问题集中在 Full Attention 层，而 MoE 层相对稳定。因此在 RL 训练时，冻结注意力层参数，只优化 MoE 投影（应该指 expert 内部的投影 / FFN 权重）。GLM 推测预训练的注意力权重已经具备足够的语义能力去关注相关 token。
- **面向 Agent 任务的 Skip-Observation Token-level GAE**：Agent 轨迹中还有大量环境反馈，从模型的视角来看，其生成的动作之间的转移是不连续的，其中引入了环境反馈的噪声，因此选择直接跳过这些环境反馈，只让模型生成的 token 进入计算。
- **scaling 价值模型的预训练**：GLM 发现价值估计中存在“冷启动”问题，通过 scaling 价值模型预训练语料库的规模，可以提供一个稳健的初始点，以支持上述机制。

### MiMo V2.6

系统方面，[MiMo V2.6](https://arxiv.org/html/2610.11959v1) 声称 RL 是 fully-async 系统，但似乎开源代码和文档中为 co-located。MiMo 建立了统一 trajectory 表示，把模型生成、环境反馈、tool call、reward 等组织起来；同时把控制面和数据面解耦：控制面负责任务调度、worker 管理，数据面负责海量 trajectory 的传输、缓存与迁移。

算法方面，异步仍然引入 staleness。MiMo V2.6 在 GRPO 上做异步 partial rollout，允许样本最多落后约 4 个 policy update，并使用 token-level importance sampling ratio 来修正，同时设置正、负 advantage 分开控制的 clip bounds。相比简单 PPO clipping，使用了更宽的置信区间，更适合存在 policy lag 的异步场景。

此外，MiMo V2.6 还采取了：
1. prompt-mean aggregation。先在每个 prompt 内计算 loss，再对 prompt 求平均，而不是把整个 batch 的 token 混在一起平均。这样长 trajectory 不会因为 token 多就自动获得更大的梯度权重，避免模型学习到过长输出的错误习惯。
2. 引入 groupwise agentic grading 以提供超出二元评价之外、更精细的奖励信号。具体而言，在高通过率任务的子集上使用 GRS，即使全部通过二元的测试评价，也能通过额外的两个 rubric 分数产生差异；对于剩下的任务，则使用 GAR。
3. 为确保所有样本都能通过有效梯度参与训练，也采用了动态采样器来过滤全通过或全失败的样本组（结合上一个 groupwise agentic grading，“全通过或全失败”应该更多指组内优势为 0，而不是指“对于二元测试全通过或全失败”）。
4. 对于 rollout 非常漫长、难验证的任务（这些任务存在严重的 staleness），MiMo 没有将它们纳入主 RL 训练，而是单独训练成专家教师，然后用 MOPD 蒸馏回主模型。

### Kimi K3

[Kimi K3](https://arxiv.org/html/2607.24653v1) 大致还是延续 partial rollout + 同步 RL（或者说 co-located RL，training 和 rollout 共用 GPU 资源，与 DeepSeek 相似）的思路。相较于 K1.5，K3 更像是 APRIL 的思路（收集到目标数量的完整样本就提前终止剩余任务，没有完成的部分轨迹存入缓冲区，放到后续迭代继续续写）：每轮为 $N$ 个 prompt 各采样 $K$ 条，维持 $N \times K$ 条活跃轨迹，完成比例到 $\lambda$（即 $\lambda NK$ 条）就暂停生成阶段；被暂停的轨迹入队，下一轮迭代开始时优先恢复，由沙箱基础设施承载。某个 prompt 的 $K$ 条回复全部完成即立刻派发做策略优化，组内需要是同步的。

当然，这样一条轨迹会由多个策略生成。算法层面，K3 的 policy optimization 沿用 Kimi K2.5，目标可以大致理解为：

$$
\mathcal{L}
\approx
\sum_i
\underbrace{
\text{ClippedRatio}_i
\cdot
A(y)
}_{\text{RL 更新}}
-
\underbrace{
\tau
\left(
\log
\frac{\pi_\theta(y_i \mid x, y_{<i})}
{\pi_{\mathrm{old}}(y_i \mid x, y_{<i})}
\right)^2
}_{\text{局部约束}}
$$

$$
A(y)=r(x,y)-\bar{r}(x)
$$

主要就是两点：
1. **ClippedRatio** 做有裁剪的重要性修正（这里的 Clip 区别于标准 PPO，而是 token-level log-ratio masking）。
2. **per-token 的正则**把策略更新约束在局部邻域内（区别于整个分布层面的 KL 约束）。

系统上，K3 有两点值得注意：
1. **External KV-cache pool**：1M context 下，unfinished trajectory 的 KV cache 不能都永远放 GPU，因此引入 CPU DRAM KV pool。
2. **Rollout auto-throttling**：rollout 的并发度不是固定的，而是根据 active request、queue length、KV pressure 等信息动态调度的。

最后，K3 也是先训练 3 个领域 $\times$ 3 个 reasoning effort 共 9 个专家模型，然后 MOPD 蒸馏回一个主模型。

### 总结

从 RLHF 优化单轮对话 + 标量偏好奖励，到 RLVR 把奖励换成了数学题、代码单测这类可自动判定的信号，再到 Agentic RL 将训练对象变成了在真实或仿真环境里多轮调用工具、读写文件、执行代码、检索网页、完成长程任务的智能体轨迹，带来更长的轨迹、更复杂的环境、更稀疏的奖励、强长尾效应等挑战。为了提升训练效率，我们引入了 RL 异步 rollout，实现宏观上 training 和 rollout 异步、并发的执行。

| 基模 | DeepSeek V4.1 | GLM-5.3 | MiMo V2.6 | Kimi K3 |
| ---  | --- | --- | --- | --- |
| 系统 | co-located | fully-async | 不确定 | co-located |
| 算法 | GRPO | SAO | GRPO | 沿用 K2.5 的组相对策略优化算法 | 
| rollout 调度 | sample-level：积累足够 sample 就派发新的 prompt，维持目标并发度 | 不确定 | 按数据源的目标贡献、动态并发预算和剩余 batch 缺口派发 | 按迭代启动 $N\times K$ 条轨迹，并通过自动限流控制请求并发 |
| partial rollout 恢复 | 保存并复用 KV、expert routing，不用重新 prefill | 不确定（slime 默认是清空 KV 后重建） | 重建 KV | 尽量保留 MLA KV 与 KDA 状态，可外置到 CPU DRAM |
| off-policy 处理 | 限制最大 off-policy 比率；staleness 太高的 token 不计入 loss | 采用 DIS，双边置信区间外的 token 被 mask | staleness=4；正负 advantage 使用四个独立边界，越界 token 被 mask | 越界 token 被 mask；使用 per-token 正则约束更新 | 

系统上，目前主流的路线可以分为两条：
1. **co-located**（如 DeepSeek、Kimi）：training 和 rollout 分时复用 time-share 同一批物理设备。这样可能节省设备资源、减少通信，但是也存在显存压力和算力竞争等问题。
2. **fully-async**（如 GLM）：training 和 rollout 解耦，部署在不同的物理设备上，中间设置数据面 / buffer。解耦使得两类负载能够独立去优化，结合异步的架构可能带来更高的吞吐上限，但也可能需要更多设备、引入通信开销、系统复杂度等挑战。

对于两种方案，轨迹都可能分为多段、由多个策略生成，引入 off-policy 问题：对于 co-located，一般是收集到足够的样本后，就停止 rollout、进入 training 阶段，未完成的轨迹在下次 rollout 阶段继续完成；对于 fully-async，则是 rollout 持续生成、training 持续消费，training 收集到足够的样本就训练更新，然后通知 rollout 更新参数（可能是立即同步 / 每 K 步同步 / 每隔一定时间同步 / 自适应同步），更新后会用新参数在未完成轨迹上继续生成。

算法上，处理 off-policy 的手段大致可以分类为：
1. **修正**：即重要性采样
2. **裁剪**：对重要性权重裁剪，或者是超出置信区间的 mask 掉不参与 loss 计算；控制 staleness 上限，丢弃过于滞后的策略生成的样本，感觉也能算作裁剪
3. **约束**：通过正则、KL 等手段，限制一次模型更新的范围

**算法能够处理多大的 off-policy，影响着 training 和 rollout 之间的调度比例和资源分配，反之亦然。核心的 trade-off 是用系统异步性换取硬件利用率，用算法鲁棒性吸收由此产生的数据分布偏移。总结下来，异步 RL 的目标即：如何在尽可能充分利用 GPU 资源的同时，避免 policy lag 过于严重而导致训练信号失真、降低训练质量，最终在吞吐和 off-policy 之间取一个平衡。显然，这是一个需要系统和算法 co-design 的问题。**

off-policy 是异步 RL 的核心矛盾，此外还存在“长度分布偏差”、“组内采样与异步、与 agentic 环境在机制上不兼容”等问题，需要结合不同的调度器 / 采样器、策略优化算法（GRPO / SAO / GSPO / ...）来解决。而在异步之外，Agentic RL 还存在训推不一致、稀疏奖励与信用分配、Reward Hacking、环境基建等挑战。

