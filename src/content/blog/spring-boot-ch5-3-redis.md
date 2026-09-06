---
title: Redis:把数据库塞进内存里,让接口快 100 倍
description: 第 5 章学习笔记（下）。从"为什么查数据库这么慢"的问题出发，讲 Redis 的 5 种数据类型 + Spring Data Redis 整合 + 缓存三大问题（穿透/雪崩/击穿）。
pubDate: 2026-09-06
tags: [Spring Boot, Redis, Java]
---

> **读这章前**:ch1 的 Spring Boot 项目要能跑起来，ch5.1/ch5.2 的 JPA/MyBatis-Plus 至少看过一个。

这章解决一个**性能问题**：怎么让接口从 200ms 变成 2ms。

## 1. 先看一个"慢得想哭"的场景

假设你有个"图书详情"接口，每个用户访问都要查数据库：

```java
@GetMapping("/book/{id}")
public Book getBook(@PathVariable int id) {
    // 每次请求都查一次数据库
    return bookRepository.findById(id).orElse(null);
}
```

**压测结果**（ab 1000 次并发）：

```
Requests per second:    487 [#/sec]   ← QPS 487
Time per request:       205.2 [ms]    ← 平均 205ms
```

瓶颈在哪？**MySQL 每次查询都要走磁盘**——B+ 树索引定位 + 磁盘 IO + 解析 SQL + 序列化结果。**100 万次查询，数据库累，用户也累。**

**Redis 的解决思路**：把查过的数据**缓存**在内存里。下次再查，**先看 Redis 有没有**——有就直接返回，没有才查数据库。**内存比磁盘快 1000 倍**（内存访问 100ns，磁盘访问 10ms）。

```java
@GetMapping("/book/{id}")
public Book getBook(@PathVariable int id) {
    // 1. 先查 Redis
    String key = "book:" + id;
    Book cached = (Book) redisTemplate.opsForValue().get(key);
    if (cached != null) return cached;     // 命中缓存，2ms 返回

    // 2. 没命中，查数据库
    Book book = bookRepository.findById(id).orElse(null);

    // 3. 写回 Redis，5 分钟过期
    if (book != null) {
        redisTemplate.opsForValue().set(key, book, 5, TimeUnit.MINUTES);
    }
    return book;
}
```

**压测结果**（缓存命中后）：

```
Requests per second:    28,431 [#/sec]   ← QPS 增长 58 倍
Time per request:       0.35 [ms]
```

这就是 Redis 的威力。这章讲怎么用。

## 2. Redis 是啥（不只"是缓存"）

**Redis (Remote Dictionary Server)** 是一个**基于内存的键值数据库**。但它能做的不只是缓存：

| 数据类型 | 用法举例 |
|---|---|
| String | 缓存、计数器、分布式锁 |
| Hash | 对象存储（用户资料、商品详情） |
| List | 消息队列、最新列表 |
| Set | 标签、共同好友、抽奖 |
| SortedSet | 排行榜、延迟队列 |

**Redis 的核心特性**（教材一句话总结）：

1. **基于内存** → 快
2. **支持持久化** → 重启数据不丢
3. **多种数据类型** → 一库多用
4. **支持事务** → 但**不推荐**用（Redis 事务是乐观锁语义，跟 MySQL 不一样）

**Redis 跟 Memcached 的区别**（教材没讲但很常问）：

| 维度 | Redis | Memcached |
|---|---|---|
| 数据类型 | 5 种 | 只有 String |
| 持久化 | 有（RDB / AOF） | 无 |
| 集群 | Redis Cluster / Sentinel | 客户端分片 |
| 线程模型 | 6.0 前单线程，6.0 后 IO 多线程 | 完全多线程 |
| 适用场景 | 复杂业务（缓存 + 队列 + 排行榜） | 纯缓存（最便宜的方案） |

> **选型**：90% 的项目选 Redis。Memcached 在"我就要一个超级快的缓存，别的不需要"时才考虑。

## 3. Redis 为什么快（面试常考）

**三个关键点**：

1. **纯内存操作** → 数据都在内存里，访问 100ns 级别
2. **单线程处理命令** → 不用加锁，**避免线程切换开销**（IO 线程是 6.0 后才引入的）
3. **IO 多路复用 (epoll)** → 一个线程处理多个客户端连接，**类似 NIO 的 Selector**

> 反直觉的点：**单线程反而快**。多线程不一定快，因为加锁、上下文切换有开销。Redis 把"CPU 不是瓶颈，内存和网络才是"这个观察发挥到了极致。

## 4. 5 种数据类型实战

教材列了一堆命令，我按**实际用途**整理：

### 4.1 String（最常用）

**用途**：普通缓存、计数器、分布式锁、Session 存储。

```bash
SET book:1 '{"id":1,"name":"楚辞"}' EX 300    # 写，5 分钟过期
GET book:1                                     # 读
INCR pv:book:1                                 # 自增（阅读量 +1）
DECR stock:book:1                              # 自减（库存 -1）
SETNX lock:order:123 "uuid"  EX 30             # 分布式锁：只设置不存在的
```

**实战场景**：
- 缓存 JSON 字符串（`book:1` → `{...}`)
- 计数器（`pv:article:1` → 阅读量）
- 限流（`rate:user:1:60s` → 60 秒内访问次数）

### 4.2 Hash

**用途**：存**整个对象**，比 String 存 JSON 更省内存，且**可以单独改一个字段**。

```bash
HSET user:1 name "张三" age 18 email "zs@example.com"   # 写
HGET user:1 name                                          # 读单个字段
HMGET user:1 name age                                     # 读多个字段
HGETALL user:1                                            # 读所有
HINCRBY user:1 age 1                                      # 年龄 +1
HDEL user:1 email                                         # 删字段
```

**对比 String**：

| 场景 | String（存 JSON） | Hash |
|---|---|---|
| 改一个字段 | 读全 → 改 → 写全 | 直接 `HSET user:1 age 19` |
| 序列化 | 自己处理 JSON | 框架自动处理 |
| 内存 | 大 JSON 整体存 | 紧凑存储 |
| 适用 | 整体读写 | 部分字段频繁更新 |

> **经验法则**：用户资料、商品详情用 Hash；缓存的 API 响应（只读）用 String。

### 4.3 List

**用途**：消息队列、最新列表（朋友圈时间线）。

```bash
LPUSH news:latest "新闻1"        # 左插（头插）
RPUSH news:latest "新闻2"        # 右插（尾插）
LRANGE news:latest 0 9           # 取前 10 条
LPOP news:latest                 # 弹出一条
BRPOP news:latest 0              # 阻塞弹出（消费者）

LLEN news:latest                 # 长度
```

**实战场景**：
- 最新评论（`LPUSH` + `LRANGE 0 9`）
- 简单消息队列（生产者 `LPUSH`，消费者 `BRPOP`）
- **注意**：List 长度建议 < 1 万，否则用 SortedSet 替代

### 4.4 Set

**用途**：标签、共同好友、抽奖（去重 + 随机）。

```bash
SADD user:1:tags "java" "redis" "mysql"   # 加标签
SREM user:1:tags "mysql"                  # 删标签
SMEMBERS user:1:tags                      # 所有标签
SISMEMBER user:1:tags "java"              # 是否包含
SCARD user:1:tags                         # 数量

# 集合运算
SINTER user:1:tags user:2:tags            # 交集（共同爱好）
SUNION user:1:tags user:2:tags            # 并集
SDIFF user:1:tags user:2:tags             # 差集（user:1 独有的）

SRANDMEMBER lottery 1                     # 随机抽 1 个（不删除）
SPOP lottery 1                            # 随机抽 1 个（删除）
```

**实战场景**：
- 用户标签
- 共同好友
- 抽奖（`SRANDMEMBER` 不删，`SPOP` 删了不重复）

### 4.5 SortedSet（最强大）

**用途**：排行榜、按 score 排序的集合、延迟队列。

```bash
ZADD rank:books 100 "book:1" 90 "book:2" 80 "book:3"   # 加 + score
ZREVRANGE rank:books 0 9 WITHSCORES                     # 倒序取前 10
ZRANGE rank:books 0 9 WITHSCORES                        # 正序取前 10
ZINCRBY rank:books 10 "book:1"                          # 加 10 分

ZRANGEBYSCORE rank:books 80 100                         # score 在 80~100
ZCOUNT rank:books 80 100                                # 数量

ZRANK rank:books "book:1"                               # 排名（0-based）
```

**实战场景**：
- 文章阅读量排行（`ZINCRBY` + `ZREVRANGE`）
- 延迟队列（score = 执行时间戳，`ZRANGEBYSCORE 0 now` 取出到期任务）
- 滑动窗口限流（用 score 存时间戳）

## 5. Redis 安装

教材介绍的是 Windows 安装（`redis-server.exe`）。**实际项目都用 Docker**（一行命令搞定）：

```bash
# Docker 启动 Redis（推荐）
docker run -d \
  --name redis \
  -p 6379:6379 \
  -v /data/redis:/data \
  redis:7-alpine \
  redis-server --appendonly yes
#                            ↑ 开启 AOF 持久化
```

**参数说明**：
- `-d` — 后台运行
- `--name redis` — 容器名
- `-p 6379:6379` — 端口映射（主机:容器）
- `-v /data/redis:/data` — 数据持久化目录
- `redis:7-alpine` — 用 alpine 镜像（5MB 起步）
- `--appendonly yes` — 开 AOF 持久化（数据更安全）

> **Mac/Windows 本地开发**：直接装 Redis Desktop Manager（图形化工具）就行。或者用 Redis 官方推出的 [Redis Insight](https://redis.com/redis-enterprise/redis-insight/)（免费 + 跨平台）。

## 6. Spring Data Redis 整合

教材把 Spring Data Redis 讲得比较碎，我整理成"**3 个关键选择 + 1 个完整例子**"。

### 6.1 三个关键选择

**选择 1：用 `RedisTemplate` 还是 `StringRedisTemplate`？**

| 维度 | `RedisTemplate` | `StringRedisTemplate` |
|---|---|---|
| Key/Value 类型 | Object（默认 JDK 序列化） | String |
| 序列化 | `JdkSerializationRedisSerializer`（二进制乱码） | `StringRedisSerializer`（人眼可读） |
| 适用 | 内部系统，性能优先 | 通用项目，可读性优先 |

> **实战经验**：**99% 的情况用 `StringRedisTemplate`，Value 自己用 JSON 序列化**。`RedisTemplate` 默认 JDK 序列化在 Redis Desktop Manager 里看是乱码，调试时想死。

**选择 2：Value 用 JSON 还是二进制？**

```java
// 推荐：String + JSON
StringRedisTemplate template = ...;
template.opsForValue().set("book:1", objectMapper.writeValueAsString(book));
Book book = objectMapper.readValue(template.opsForValue().get("book:1"), Book.class);

// 不推荐：Object + JDK 序列化（数据乱码、跨语言读不了）
redisTemplate.opsForValue().set("book:1", book);
Book book = (Book) redisTemplate.opsForValue().get("book:1");
```

**选择 3：自己配 RedisTemplate 还是用现成的 StringRedisTemplate？**

**自己配**（推荐，因为 StringRedisTemplate 只能存 String）：

```java
@Configuration
public class RedisConfig {

    @Bean
    public RedisTemplate<String, Object> redisTemplate(RedisConnectionFactory factory) {
        RedisTemplate<String, Object> template = new RedisTemplate<>();
        template.setConnectionFactory(factory);

        // Key 用 String 序列化
        StringRedisSerializer stringSerializer = new StringRedisSerializer();
        template.setKeySerializer(stringSerializer);
        template.setHashKeySerializer(stringSerializer);

        // Value 用 JSON 序列化（关键：GenericJackson2JsonRedisSerializer 带上类型信息）
        Jackson2JsonRedisSerializer<Object> jsonSerializer =
            new Jackson2JsonRedisSerializer<>(objectMapper, Object.class);
        //  ↑ 第二个参数要 Object.class，不能是 Book.class（不然存别的类报错）
        template.setValueSerializer(jsonSerializer);
        template.setHashValueSerializer(jsonSerializer);

        template.afterPropertiesSet();
        return template;
    }
}
```

> **踩坑提醒**：用 `Jackson2JsonRedisSerializer<Book>` 这种**指定类型**的，新版本会报错"could not deserialize JSON"。**用 `Object.class` 通用类型**，或用 `GenericJackson2JsonRedisSerializer`（带 `@class` 类型信息，更通用）。

### 6.2 5 种数据类型的 API 速查

```java
@Autowired
private StringRedisTemplate stringRedisTemplate;

// String
stringRedisTemplate.opsForValue().set("k", "v", 60, TimeUnit.SECONDS);
stringRedisTemplate.opsForValue().get("k");
stringRedisTemplate.opsForValue().increment("counter");   // 自增

// Hash
stringRedisTemplate.opsForHash().put("user:1", "name", "张三");
stringRedisTemplate.opsForHash().get("user:1", "name");
Map<Object, Object> map = stringRedisTemplate.opsForHash().entries("user:1");

// List
stringRedisTemplate.opsForList().leftPush("news", "新闻1");
stringRedisTemplate.opsForList().range("news", 0, 9);
stringRedisTemplate.opsForList().size("news");

// Set
stringRedisTemplate.opsForSet().add("tags", "java", "redis");
stringRedisTemplate.opsForSet().members("tags");
stringRedisTemplate.opsForSet().isMember("tags", "java");

// SortedSet
stringRedisTemplate.opsForZSet().add("rank", "book:1", 100);
Set<String> top10 = stringRedisTemplate.opsForZSet().reverseRange("rank", 0, 9);
```

### 6.3 完整例子：用户信息缓存

`pom.xml`：

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-data-redis</artifactId>
</dependency>
```

`application.yml`：

```yaml
spring:
  redis:
    host: localhost
    port: 6379
    password:                # ← 没设密码就空着
    database: 0              # ← 0~15 共 16 个逻辑库，默认 0
    timeout: 2000ms          # ← 命令超时时间
    lettuce:
      pool:
        max-active: 8        # ← 最大连接数
        max-idle: 8
        min-idle: 0
```

**实体类**：

```java
@Data
@RedisHash("user")            // ← 关键：对应 Redis 中的 "user" 前缀
public class User {

    @Id                       // ← 主键，对应 Redis 中的 "user:{id}"
    private String id;        //   必须用 String（@Id 注解要求）
    private String name;
    private String hobby;     // List<String> 自动转 Redis List
    private String subject;   // String[] 自动转 Redis Set
    private Map<String, String> role;  // Map 自动转 Redis Hash
}
```

**Repository**：

```java
public interface UserRepository extends CrudRepository<User, String> {
    // 单表 CRUD 框架已提供，复杂查询自己加
}
```

**测试**：

```java
@SpringBootTest
class RedisTests {

    @Autowired
    private UserRepository userRepository;

    @Autowired
    private StringRedisTemplate stringRedisTemplate;

    // 1. 用 Repository 存整个对象
    @Test
    void saveTest() {
        User user = new User();
        user.setId("1");
        user.setName("zhangsan");
        user.setHobby("[\"travel\", \"swim\"]");     // List 类型
        user.setSubject("[\"Chinese\", \"English\"]"); // Set 类型
        Map<String, String> role = new HashMap<>();
        role.put("admin", "wanguo");
        role.put("user", "zhaoliu");
        user.setRole(role);
        userRepository.save(user);   // 自动生成 key: user:1
    }

    // 2. String 类型
    @Test
    void stringTest() {
        stringRedisTemplate.opsForValue().set("name", "lisi");
        String name = stringRedisTemplate.opsForValue().get("name");
        System.out.println("name = " + name);
    }

    // 3. List 类型
    @Test
    void listTest() {
        stringRedisTemplate.opsForList().leftPush("hobby", "travel");
        stringRedisTemplate.opsForList().leftPush("hobby", "swim");
        List<String> hobby = stringRedisTemplate.opsForList().range("hobby", 0, -1);
        System.out.println("hobby = " + hobby);
    }

    // 4. Set 类型
    @Test
    void setTest() {
        stringRedisTemplate.opsForSet().add("subject", "Chinese", "English");
        Set<String> subject = stringRedisTemplate.opsForSet().members("subject");
        System.out.println("subject = " + subject);
    }

    // 5. Hash 类型
    @Test
    void hashTest() {
        stringRedisTemplate.opsForHash().put("role", "admin", "wanguo");
        stringRedisTemplate.opsForHash().put("role", "user", "zhaoliu");
        Map<Object, Object> role = stringRedisTemplate.opsForHash().entries("role");
        System.out.println("role = " + role);
    }
}
```

**@RedisHash 生成的 key 结构**（教材里那张图 5-24 我看了半天才看懂）：

当你 `userRepository.save(user)` 时，Redis 里会生成**3 类 key**：

```
user                    ← Hash，主入口，存对象元信息
user:1                  ← String，存实际数据
user:name:zhangsan      ← Set，存所有 name=zhangsan 的 User.id
                          （二级索引，教材图 5-24 讲的就是这个）
user:1:idx              ← Set，存 user:1 下的所有 secondary key
                          （辅助索引，教材图 5-25）
```

> 老实说：教材把这部分讲得很绕。我的建议是——**普通 CRUD 用 `RedisTemplate` + JSON 序列化就够了**，`@RedisHash` 适合需要"按二级字段查询"的场景（比如"查所有 name=zhangsan 的用户"），但用得不多。

## 7. 缓存三大问题（教材没讲但面试必问）

**当你用 Redis 做缓存时，会遇到 3 个经典问题**——

### 7.1 缓存穿透（Cache Penetration）

**问题**：查询一个**数据库里没有的数据**，比如 `id = -1`。缓存里没有 → 查数据库 → 数据库也没有 → 返回 null。**每次请求都打到数据库，缓存形同虚设**。

**场景**：攻击者故意查不存在的 id。

**解法**：

```java
// 1. 缓存空值（最简单）
Book book = bookRepository.findById(id).orElse(null);
if (book == null) {
    // 把 null 也缓存，5 分钟过期
    redisTemplate.opsForValue().set("book:" + id, "", 5, TimeUnit.MINUTES);
    return null;
}

// 2. 布隆过滤器（高级，先用 bit 数组判断 key 存不存在）
//    适合"数据全是有效 ID"的场景
```

### 7.2 缓存雪崩（Cache Avalanche）

**问题**：缓存里**大量 key 同一时间过期**，导致所有请求都打到数据库。

**场景**：你设的过期时间都是 5 分钟，恰好 5 分钟后所有 key 同时失效，10 万请求直接砸到数据库。

**解法**：

```java
// 1. 过期时间加随机值（错峰过期）
int ttl = 300 + new Random().nextInt(60);  // 5 分钟 ± 1 分钟
redisTemplate.opsForValue().set("book:" + id, book, ttl, TimeUnit.SECONDS);

// 2. 永不过期 + 后台异步刷新（适合热点数据）
redisTemplate.opsForValue().set("hot:book:1", book);  // 不设过期
// 后台任务每 5 分钟查数据库，刷新一次
```

### 7.3 缓存击穿（Cache Breakdown）

**问题**：一个**热点 key 突然过期**，恰好大量请求都在查这个 key。**所有请求都打到数据库**。

**场景**：某个爆款商品缓存过期了 1 秒，刚好赶上秒杀，10 万请求都打过来。

**解法**：

```java
// 1. 分布式锁（只让一个请求查数据库，其他等）
public Book getBookWithLock(int id) {
    String key = "book:" + id;
    Book cached = (Book) redisTemplate.opsForValue().get(key);
    if (cached != null) return cached;

    // 拿不到缓存，去抢锁
    String lockKey = "lock:book:" + id;
    if (tryLock(lockKey)) {
        try {
            // 抢到锁的，查数据库
            Book book = bookRepository.findById(id).orElse(null);
            redisTemplate.opsForValue().set(key, book, 5, TimeUnit.MINUTES);
            return book;
        } finally {
            unlock(lockKey);
        }
    } else {
        // 没抢到锁的，等 100ms 再重试
        Thread.sleep(100);
        return getBookWithLock(id);
    }
}

// 2. 逻辑过期（永远不真过期，只在数据上加 expireAt 字段）
//    业务代码判断 expireAt < now 才去查数据库
```

**三个问题对比**：

| 问题 | 现象 | 解法 |
|---|---|---|
| 穿透 | 查不存在的数据 | 缓存空值 / 布隆过滤器 |
| 雪崩 | 大量 key 同时过期 | 过期时间加随机值 |
| 击穿 | 1 个热点 key 过期 | 分布式锁 / 逻辑过期 |

## 8. 实战踩坑

1. **Redis 里看不到中文**——`redis-cli` 默认 GBK 编码，中文显示 `\xe4\xb8\xad\xe6\x96\x87`。启动加 `--raw`：`redis-cli --raw`
2. **缓存和数据库不一致**——改了数据库忘改缓存。解法：**先更新数据库，再删除缓存**（不是更新缓存），下次读时再从数据库加载
3. **大 Value 拖慢 Redis**——单个 key 的 value 不要超过 1MB。列表太长要分页，存大 JSON 要拆字段
4. **Redis 雪崩和穿透傻傻分不清**——记住：**穿透是查不到，雪崩是同时过期，击穿是单点热点**
5. **Keys 命令不能用**——`KEYS *` 会阻塞 Redis 整个线程，**生产环境禁止用**。要查匹配的 key 用 `SCAN`（游标迭代）
6. **连接池没配**——默认 Lettuce 单连接，高并发下排队。要配 `spring.redis.lettuce.pool.max-active=8`
7. **StringRedisTemplate 和 RedisTemplate 混用**——两个序列化方式不同，**存进去的 key 看起来一样，实际前缀不同**（一个有 `\xac\xed\x00` 序列化前缀），`DEL` 一个找不到另一个

## 9. 什么时候用 Redis（决策树）

```
数据要高性能读？ ──No──→ 不用 Redis
   │ Yes
   ↓
数据经常变？ ──No──→ 用 CDN / 静态缓存
   │ Yes
   ↓
数据要持久化？ ──No──→ 用 Caffeine（JVM 本地缓存）
   │ Yes
   ↓
多实例共享？ ──No──→ 用 Caffeine
   │ Yes
   ↓
需要分布式锁 / 队列 / 排行榜？
   │ Yes                       │ No
   ↓                           ↓
用 Redis                    用 Redis
```

> **个人经验**：**能用 Caffeine 就不用 Redis**。JVM 进程内缓存（毫秒级）比 Redis（网络 IO）还快一倍。只有"多实例共享"或"需要 Redis 特有功能"才上 Redis。

---

到这 ch5 整个学完了。**三篇笔记的脉络**：
- **ch5.1 JPA**：对象思维，方法名约定，**适合业务系统**
- **ch5.2 MyBatis-Plus**：SQL 思维，Lambda 风格，**适合复杂查询和报表**
- **ch5.3 Redis**：性能优化，**所有数据访问层的"加速外挂"**

学完这章你应该能回答：
1. 为什么需要 ORM？JPA 和 MyBatis-Plus 怎么选？
2. 怎么用 Redis 缓存？5 种数据类型各适合什么场景？
3. 缓存三大问题怎么解决？

下章（ch6）应该是 Spring Boot 的安全（Spring Security）和异步（@Async / 消息队列），这个会再开新坑。
