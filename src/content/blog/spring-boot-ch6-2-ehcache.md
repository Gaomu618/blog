---
title: Ehcache:JVM 进程内缓存,比 Redis 还快
description: 第 6 章学习笔记（中）。讲 Ehcache 4 大特点 + 4 种策略 + 分层架构 + 完整 Spring Boot 整合例子,以及什么时候该用 Ehcache 而不是 Redis。
pubDate: 2026-09-07
tags: [Spring Boot, Ehcache, Java]
---

> **读这章前**:ch6.1 的 5 个缓存注解要会（这章用 Ehcache 作为后端实现）。

这章解决一个**性能再优化 100 倍**的问题：**怎么让缓存查询比 Redis 还快**。

## 1. 先回顾一下：Redis 缓存"还是慢"的原因

上一章我们用 Spring Cache + Redis 做缓存：

```java
@Cacheable(cacheNames = "book", key = "#id")
public Book findById(Integer id) {
    return bookRepository.findById(id).orElse(null);
}
```

**调用链**（查一次缓存）：

```
应用 → [序列化对象] → [TCP 网络] → Redis → [反序列化] → 返回
```

**耗时**：

- 本地方法调用：~10ns
- Redis 网络往返：~1ms（**慢 10 万倍**）

> 哪怕 Redis 是"内存级"操作，**网络 IO 这 1ms 在高并发下也会卡**。在"我要每秒 10 万次查询"的场景下，1ms × 10万 = 100秒 CPU 在等网络。

**Ehcache 的解决思路**：**把缓存放到 JVM 进程里**。这样查缓存 = 一次 Java 方法调用，**没有网络 IO**：

```
应用 → [Ehcache 内存] → 返回
```

**耗时**：

- 一次 Ehcache 查询：~100ns
- **比 Redis 快 10 倍**

## 2. Ehcache 是啥

**Ehcache** 是一个**纯 Java 写的进程内缓存框架**，Hibernate 默认就用它做二级缓存。

**4 大特点**（教材原文）：

| # | 特点 | 大白话 |
|---|---|---|
| 1 | **快速轻量** | 不用特别配置，**几分钟就能启动**，**依赖只有一个 SLF4J**（其他缓存框架要一堆依赖）|
| 2 | **伸缩性** | 能扩展到数百个缓存，支持大堆（几十 G）+ 高并发 |
| 3 | **灵活性** | 4 种策略自由组合（过期/淘汰/存储/动态配置）|
| 4 | **标准支持** | 实现 **JSR107 规范**（JCache 是 Java 缓存的官方标准）|

**8 个特性**（教材扩展版）：

1. 快速轻量
2. 伸缩性
3. 灵活性
4. 标准支持（JSR107）
5. **可扩展性**（监听器、装饰器、加载器）
6. **监听器**（`CacheManagerEventListener` + `CacheEventListener`）
7. **企业级应用支持**（事务、分布式缓存）
8. **Apache License 2.0**（免费商用）

**2 大常见误解**：

| ❌ 误解 | ✅ 真相 |
|---|---|
| "Ehcache 只能存内存" | **支持堆 / 堆外 / 磁盘 / 集群 4 层** |
| "Ehcache 是过时的技术" | **Java 生态里最成熟的进程内缓存**，Hibernate/Spring 默认就推荐 |

## 3. 4 种策略（Ehcache 的核心配置）

策略可以**自由组合**——比如"过期时间 5 分钟 + 超过 1000 条就 LRU 淘汰 + 允许溢出到磁盘"。

### 3.1 过期策略：决定"什么时候删"

```xml
<cache name="book"
       eternal="false"           <!-- ← eternal=true 关闭过期，元素永不过期 -->
       timeToIdleSeconds="300"  <!-- ← 空闲多久过期（最后访问后 5 分钟）-->
       timeToLiveSeconds="600"> <!-- ← 存活多久过期（创建后 10 分钟，不管有没有访问）-->
</cache>
```

**两个时间的区别**：

- `timeToIdleSeconds`：用户**最后访问**算起
- `timeToLiveSeconds`：从**创建**算起

> 比喻：`timeToIdle` 是"会员卡多久不用就过期"，`timeToLive` 是"无论用不用，10 个月后必过期"

**踩坑**：两个值**别设一样长**！比如都设 600 = 满了 10 分钟后任何访问都触发过期；一个 300 一个 600 更合理。

### 3.2 淘汰策略：决定"满了怎么办"

```xml
<cache memoryStoreEvictionPolicy="LRU" />
```

**3 种算法**：

| 策略 | 全称 | 含义 | 适用 |
|---|---|---|---|
| **LRU** | Least Recently Used | 淘汰**最久没用**的 | **90% 场景都用这个**（最常用）|
| **LFU** | Least Frequently Used | 淘汰**用得最少**的 | 数据访问频率差异大（如热门 / 冷门）|
| **FIFO** | First In First Out | 淘汰**先进来的** | 简单场景，对公平性要求高 |

> **默认是 LRU**——大部分框架（Redis、Memcached）也都默认这个，因为符合"最近用到的更可能再用"这个直觉。

### 3.3 存储策略：决定"数据放哪"

```xml
<cache maxElementsInMemory="1000"      <!-- ← 内存最多 1000 条 -->
       overflowToDisk="true"           <!-- ← 内存满了溢出到磁盘 -->
       diskPersistent="true"           <!-- ← 磁盘数据重启不丢 -->
/>
```

**4 种存储层**（按速度从快到慢）：

| 层 | 速度 | 容量 | 序列化 | 用途 |
|---|---|---|---|---|
| **堆内存** | ⚡⚡⚡ | 受 JVM 限制 | 不需要 | **热点数据**（默认）|
| **堆外内存**（OffHeap）| ⚡⚡ | 大（不受 GC 影响）| 需要 | 大对象，避免 GC 停顿 |
| **磁盘** | ⚡ | 巨大 | 需要 | 冷数据 / 不常用的 |
| **集群**（Terracotta）| ⚡ | 巨大 | 需要 | 跨 JVM 共享 |

**分层架构（金字塔）**：

```
        ┌────────┐
        │  堆层   │  ← 最小最快（KB~GB）
        │────────│
        │  堆外层  │  ← 中等（GB）
        │────────│
        │  磁盘层  │  ← 最大（TB）
        └────────┘
```

**分层规则**：

- 堆层**必须存在**
- 磁盘层 + 集群层**不能同时存在**
- 层大小遵循**金字塔**（上窄下宽）

### 3.4 动态配置：运行时改

```java
CacheManager manager = ...;
Cache cache = manager.getCache("book");

// 运行时改最大容量
cache.getCacheConfiguration().setMaxEntriesInCache(5000);
// 运行时改 TTL
cache.getCacheConfiguration().setTimeToLiveSeconds(600);
```

**适用场景**：流量高峰期临时扩容、压力测试。

## 4. Ehcache vs Redis：什么时候用哪个？

| 维度 | Ehcache | Redis |
|---|---|---|
| **位置** | **JVM 进程内** | 独立服务（跨网络）|
| **速度** | ⚡⚡⚡ ~100ns | ⚡ ~1ms |
| **多实例共享** | ❌ 不共享（除非 Terracotta）| ✅ 天生共享 |
| **持久化** | ✅ 磁盘（重启不丢）| ✅ RDB / AOF |
| **大数据集** | 受 JVM 限制（GB 级）| 几乎无限（TB 级）|
| **集群** | Terracotta（商用）| Redis Cluster（免费）|
| **适用** | 单实例 / 读多写少 | 多实例 / 分布式 |

**决策树**：

```
你的应用是单实例还是多实例？
│
├── 单实例 → Ehcache（更快）
│   │
│   └── 数据要重启不丢？──Yes──→ Ehcache + 磁盘持久化
│
└── 多实例 → Redis（共享）
    │
    └── 性能要求极致？──Yes──→ Ehcache + 多播（每实例各自缓存）
                              （允许偶尔不一致换 10 倍性能）
```

**实战经验**：

- **单机 / 低并发**：Ehcache > Redis（少一次网络）
- **多机集群**：Redis 必选（多实例需要共享缓存）
- **多机但允许最终一致**：每实例各自跑 Ehcache，用消息队列同步失效广播

> 真实项目里，**不少架构是"两级缓存"**：本地 Ehcache（L1）+ 远程 Redis（L2），先查 Ehcache，没命中再查 Redis，再没命中才查 DB。

## 5. 完整 Spring Boot 整合例子

### 5.1 加依赖

`pom.xml`：

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-cache</artifactId>
</dependency>

<!-- Ehcache 3.x 用这个（旧版是 net.sf.ehcache） -->
<dependency>
    <groupId>org.ehcache</groupId>
    <artifactId>ehcache</artifactId>
</dependency>

<!-- JPA + MySQL 跟上章一样 -->
```

> ⚠️ **注意**：`spring-boot-starter-cache` 不包含 Ehcache 实现，**必须自己加 `ehcache` 依赖**（Redis 是 starter 自带，Ehcache 不是）

### 5.2 写 `ehcache.xml`

`src/main/resources/ehcache.xml`：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<ehcache xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:noNamespaceSchemaLocation="http://ehcache.org/ehcache.xsd"
         updateCheck="false">

    <!-- 磁盘存储路径（Ehcache 序列化到磁盘的位置） -->
    <diskStore path="D:\ehcache" />

    <!-- 默认缓存配置 -->
    <defaultCache
        maxElementsInMemory="1000"
        eternal="false"
        timeToIdleSeconds="120"
        timeToLiveSeconds="600"
        overflowToDisk="true"
        diskPersistent="true"
        memoryStoreEvictionPolicy="LRU" />

    <!-- book 缓存（专用配置） -->
    <cache name="book"
           maxElementsInMemory="1000"
           eternal="false"
           timeToIdleSeconds="300"
           timeToLiveSeconds="600"
           overflowToDisk="true"
           diskPersistent="true"
           memoryStoreEvictionPolicy="LRU" />

</ehcache>
```

**关键配置说明**：

- `name="book"` — 对应 `@Cacheable(cacheNames = "book")`
- `eternal="true"` — 永不过期（跟 `timeToIdleSeconds` / `timeToLiveSeconds` 互斥）
- `maxElementsInMemory` — 内存最多 1000 条（超过溢出到磁盘）
- `overflowToDisk="true"` — 允许溢出到磁盘
- `diskPersistent="true"` — **磁盘数据持久化**（重启后还在）

### 5.3 实体类必须实现 `Serializable`

```java
@Entity
@Table(name = "book")
public class Book implements Serializable {  // ← 必须！磁盘/网络传输都要序列化
    private static final long serialVersionUID = 1L;  // ← 强烈建议加

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Integer id;

    @Column(name = "name")
    private String name;
    // ... 其他字段
}
```

> **不实现 `Serializable`，溢出到磁盘时会报 `NotSerializableException`**

### 5.4 改 `application.yml`

```yaml
spring:
  cache:
    type: ehcache                    # ← 切换缓存实现（一行！）
    ehcache:
      config: classpath:ehcache.xml  # ← Ehcache 配置文件路径
```

**就这一行**——从 `simple` 改成 `ehcache`，业务代码完全不动。这就是 Spring Cache 抽象的威力。

### 5.5 业务代码（跟 ch6.1 完全一样）

```java
@Service
@CacheConfig(cacheNames = "book")
public class BookServiceImpl implements BookService {

    @Autowired
    private BookRepository bookRepository;

    @Cacheable(key = "#id")
    public Book findById(Integer id) {
        return bookRepository.findById(id).orElse(null);
    }

    @CachePut(key = "#id")
    public Book updateById(Integer id, String name) {
        Book book = this.findById(id);
        book.setName(name);
        return bookRepository.save(book);
    }

    @CacheEvict(key = "#id", beforeInvocation = true)
    public void delById(Integer id) {
        bookRepository.deleteById(id);
    }
}
```

**零改动**——ch6.1 的代码原样能用。这就是 Spring Cache 解耦的精髓。

### 5.6 验证磁盘持久化

```
1. 启动项目，访问 findById 几次
2. 在 D:\ehcache 看到 book.data 和 book.index 文件（自动生成）
3. 正常关闭项目（Ctrl+C，**不要 kill -9**）
4. 重新启动，缓存还在！
```

> **重要**：磁盘持久化只在**正常关闭**时生效。`kill -9` 杀进程 = 丢数据，**因为 Ehcache 写磁盘是关闭时批量 flush 的**。

## 6. 实战踩坑

1. **忘了加 `ehcache` 依赖** — `spring-boot-starter-cache` 不含实现，**必须自己加**。报错：`No CacheResolver could be found`
2. **实体类没实现 `Serializable`** — 第一次溢出到磁盘就崩。**所有要缓存的实体都加 `implements Serializable`**
3. **`diskStore` 路径** — Windows 注意 `D:\ehcache` 路径要存在；Linux 用 `/var/ehcache` 之类。**程序要有写权限**
4. **改了 `ehcache.xml` 不生效** — 文件改了但缓存行为没变？**删 `D:\ehcache` 下的旧数据文件**（框架不感知 XML 变化）
5. **`@EnableCaching` 重复加** — 启动报 Bean 冲突。一个应用加一次
6. **`timeToIdleSeconds` 和 `timeToLiveSeconds` 混淆** — 测试前先想清楚"什么时候算过期"
7. **多实例不共享** — Ehcache 是进程内的，A 实例的缓存 B 实例看不到。**多实例必须用 Redis 或 Terracotta**

## 7. 选型最终建议

| 场景 | 推荐 |
|---|---|
| 单实例 + 读多写少 + 性能敏感 | **Ehcache**（快 + 简单）|
| 单实例 + 数据要重启不丢 | **Ehcache + 磁盘持久化** |
| 多实例 + 中小规模 | **Redis** |
| 多实例 + 极致性能 + 允许最终一致 | **Ehcache（每实例）+ Redis（兜底）** |
| 大数据集（GB+）| **Redis**（内存无限） |
| 已有 Hibernate | **Ehcache**（默认集成）|

---

下篇讲 **Redis 作为缓存后端**（ch6.3-redis-as-cache.md）——从 Ehcache 切到 Redis **只改一行配置**，业务代码完全不动。