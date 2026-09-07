---
title: Redis 作为缓存后端:一行配置切换缓存实现
description: 第 6 章学习笔记（下）。讲怎么把 ch5.3 的 RedisTemplate 直接用法,升级到 Spring Cache 抽象,以及这一行配置切换的威力。
pubDate: 2026-09-07
tags: [Spring Boot, Spring Cache, Redis, Java]
---

> **读这章前**:ch5.3 Redis 基础要会，ch6.1 的 5 个缓存注解要会。

这章解决一个**架构升级**问题：**怎么从"自己写缓存逻辑"升级到"用注解"**。

## 1. 先回顾：ch5.3 我们怎么用 Redis？

ch5.3 写的是**直接用 RedisTemplate**，每个方法自己写缓存逻辑：

```java
@Service
public class BookServiceImpl {

    @Autowired
    private RedisTemplate<String, Object> redisTemplate;

    @Autowired
    private BookRepository bookRepository;

    public Book findById(Integer id) {
        // 1. 查缓存
        String key = "book:" + id;
        Book cached = (Book) redisTemplate.opsForValue().get(key);
        if (cached != null) return cached;

        // 2. 查数据库
        Book book = bookRepository.findById(id).orElse(null);

        // 3. 写回缓存
        if (book != null) {
            redisTemplate.opsForValue().set(key, book, 5, TimeUnit.MINUTES);
        }
        return book;
    }

    public Book updateById(Integer id, String name) {
        // ... 又是自己写：查 + 改 + 删缓存 3 步
    }

    public void delById(Integer id) {
        // ... 又是自己写：删 DB + 删缓存 2 步
    }
}
```

**问题**：

- **每个方法都要写 3 步**：查缓存 → 查 DB → 写缓存（重复 3 行 × N 个方法 = N×3 行）
- **改方法签名要改 3 处**：RedisTemplate ops、key 拼接、set 调用
- **缓存逻辑跟业务逻辑混在一起** → 业务代码读起来费劲

**ch6.3 的升级**：用 **Spring Cache 抽象**——业务代码加一个注解，缓存逻辑**框架帮你织入**：

```java
@Service
@CacheConfig(cacheNames = "book")
public class BookServiceImpl {

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

**对比**：

| 维度 | ch5.3 RedisTemplate | ch6.3 Spring Cache |
|---|---|---|
| 缓存代码位置 | 业务方法**内部** | 业务方法**外面**（注解）|
| 缓存逻辑 | 手写 | 框架自动织入（AOP）|
| 切缓存实现 | 改业务代码 | 改 `application.yml` 一行 |
| 关注点 | 缓存细节 | 业务本身 |

## 2. Spring Cache 抽象的优势

**这是整个 ch6 章的精髓**——**业务代码只面向注解编程，不关心底层缓存是什么**。

切换缓存实现只要改 `application.yml`：

```yaml
spring:
  cache:
    type: simple      # ← Simple（ConcurrentHashMap）
    type: ehcache     # ← 换成 Ehcache
    type: redis       # ← 换成 Redis
    type: caffeine    # ← 换成 Caffeine
```

**业务代码一行不动**。**今天用 Ehcache，明天想换 Redis，改一行配置就行**。

> 现实中很多项目**第一版用 Ehcache 跑通了，后来流量大了换成 Redis，业务代码完全没动**——这就是抽象的力量。

## 3. 完整例子：Spring Cache + Redis 后端

### 3.1 加依赖

`pom.xml`（在 ch6.1 基础上**只加 Redis**，其他不变）：

```xml
<dependencies>
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-web</artifactId>
    </dependency>

    <!-- Spring Cache 抽象 -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-cache</artifactId>
    </dependency>

    <!-- Spring Data JPA -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-data-jpa</artifactId>
    </dependency>

    <dependency>
        <groupId>mysql</groupId>
        <artifactId>mysql-connector-java</artifactId>
    </dependency>

    <!-- Spring Data Redis（cache 后端用） -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-data-redis</artifactId>
    </dependency>
</dependencies>
```

### 3.2 `application.yml`

```yaml
spring:
  datasource:
    url: jdbc:mysql://localhost:3306/springbootdata?characterEncoding=utf8&useSSL=false&serverTimezone=Asia/Shanghai
    username: root
    password: root
    driver-class-name: com.mysql.cj.jdbc.Driver

  jpa:
    show-sql: true

  # ========== Spring Cache 配置 ==========
  cache:
    type: redis
    redis:
      # 缓存前缀（区分不同项目的 key）
      key-prefix: 'book:'
      # 是否用 key 前缀
      use-key-prefix: true
      # 是否缓存 null（默认 false，不缓存 null 防止缓存穿透）
      cache-null-values: false
      # 缓存过期时间（秒），不指定就永不过期
      time-to-live: 400000

  # ========== Redis 配置 ==========
  redis:
    host: localhost
    port: 6379
    database: 0
    timeout: 2000ms
    lettuce:
      pool:
        max-active: 8
        max-idle: 8
        min-idle: 0
```

**关键配置说明**：

- `cache.type: redis` — **告诉 Spring Cache 用 Redis 作为后端**
- `cache.redis.key-prefix: 'book:'` — 所有缓存 key 加 `book:` 前缀（不同项目不冲突）
- `cache.redis.cache-null-values: false` — **不缓存 null**（防止"缓存穿透"，ch5.3 讲过）
- `cache.redis.time-to-live: 400000` — 缓存 400000 秒过期（约 4.6 天）
- `redis.*` — Redis 连接信息

### 3.3 启动类

```java
@SpringBootApplication
@EnableCaching   // ← 开启缓存
public class Chapter06Application {
    public static void main(String[] args) {
        SpringApplication.run(Chapter06Application.class, args);
    }
}
```

### 3.4 业务代码（**跟 ch6.1 一字不差**）

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

> **零改动**！ch6.1 用 Simple 缓存的代码，切到 ch6.3 改完 `application.yml` 就直接用 Redis 了。

### 3.5 验证

启动后：

1. 访问 `http://localhost:8080/book/findById/5`
2. 打开 Redis 客户端（RESP.app 或 `redis-cli`）：

```bash
> KEYS *
1) "book::5"   ← 看到了！前缀是 book:，cacheNames 是空（@CacheConfig 里没指定 value），key 是 5
```

3. 第二次访问同样 id：
   - **控制台不打 SQL**（命中缓存）
   - **Redis 里的 key 不变**

4. 改数据：
   - 访问 `http://localhost:8080/book/editById/5/观堂别集`
   - Redis 里的 `book::5` 对应的 value 已经被更新（@CachePut 生效）

5. 删数据：
   - 访问 `http://localhost:8080/book/delById/5`
   - Redis 里的 `book::5` 已经被删除（@CacheEvict 生效）

## 4. 切缓存实现到底有多简单？

| 切换前 | 切换后 | 改动量 |
|---|---|---|
| `simple` (默认) | `ehcache` | 加 `ehcache` 依赖 + 写 `ehcache.xml` + 改 `application.yml` |
| `ehcache` | `redis` | 加 `redis` 依赖 + 改 `application.yml`（**业务代码 0 改动**）|
| `redis` | `caffeine` | 加 `caffeine` 依赖 + 改 `application.yml` |

**业务代码 / Controller / Service / Repository 全部不动**。这才是面向抽象编程的威力。

> **对比 MyBatis-Plus 切换数据库**（ch5.2 讲过）：换数据库要改方言、改 SQL 函数；Spring Cache 切换缓存**完全 0 改动业务代码**，因为抽象做得更彻底。

## 5. 缓存 key 的完整结构

启动后查看 Redis 里的 key：

```
book::5
│   │ │
│   │ └── 5 (@Cacheable 的 key = "#id")
│   └────── 空（@CacheConfig 里 cacheNames = "book" 没指定 value）
└────────── key-prefix（yml 配的 "book:"）
```

**完整 key 拼接**：

```
key-prefix + "::" + cacheNames + "::" + key
```

**几个细节**：

- `::` 是 Spring Cache 的固定分隔符（用于反序列化时定位 cacheNames）
- `key-prefix` 是可选的（生产环境强烈建议加，避免多项目 key 冲突）
- `cacheNames` 可以用 `value` / `cacheNames` 两者之一指定

## 6. ch5.3 vs ch6.3：什么时候用哪个？

| 维度 | ch5.3 RedisTemplate | ch6.3 Spring Cache + Redis |
|---|---|---|
| 编程模型 | 命令式（手动调 get/set）| 声明式（注解）|
| 适合场景 | **需要细粒度控制**（如复杂 key、特殊操作）| **标准 CRUD 缓存** |
| 切换缓存 | 改业务代码 | 改 yml |
| 学习曲线 | 中等（要学 5 种数据类型 API）| 低（5 个注解搞定）|
| 性能 | 完全可控 | 框架默认（可配）|
| 灵活性 | **高**（能实现任何 Redis 操作）| 低（只支持标准 CRUD 缓存）|

**实战选择**：

- **80% 业务**：用 ch6.3 Spring Cache（简洁）
- **20% 业务**：用 ch5.3 RedisTemplate（复杂场景，如分布式锁、限流、排行榜、消息队列）

**两者可以并存**——同一个项目里，简单查询用 `@Cacheable`，复杂操作用 `RedisTemplate`：

```java
@Service
public class BookServiceImpl {

    // 简单查询 → 注解
    @Cacheable(key = "#id")
    public Book findById(Integer id) {
        return bookRepository.findById(id).orElse(null);
    }

    // 复杂操作 → 直接用 RedisTemplate
    @Autowired
    private RedisTemplate<String, Object> redisTemplate;

    public Long getViewCount(Integer id) {
        // 自增计数（Spring Cache 不支持）
        return redisTemplate.opsForValue().increment("book:view:" + id);
    }
}
```

> **这是最常见的实战模式**：注解 + RedisTemplate **混用**，各取所长。

## 7. 实战踩坑

1. **`cache.type` 拼错** — 应该是 `redis` 不是 `Redis`（小写），错了不生效也不报错。**配置完看启动日志确认加载了哪个 CacheManager**
2. **`@EnableCaching` 忘加** — 跟 ch6.1 一样，注解静默失效
3. **`cache-null-values: true` 缓存 null 造成问题** — 攻击者故意查不存在的 id，把所有 null 都缓存了，**内存爆掉**。**默认 false 更安全**
4. **`time-to-live` 不设置 = 永不过期** — 数据更新后旧缓存永远在。**生产环境必设**
5. **Redis 没装 / 启动不起来** — 启动报 `RedisConnectionFactory` 创建失败。**先 `redis-cli ping` 测一下**
6. **多实例 key 冲突** — 多个项目共用一个 Redis，没设 `key-prefix` 互相覆盖。**每个项目单独设前缀**
7. **RedisTemplate 跟 Spring Cache 序列化方式不一致** — RedisTemplate 默认 JDK 序列化（乱码），Spring Cache 默认 JSON。**两个查出来的 key-value 不互通**

## 8. Spring Cache 整体收尾

学完 ch6 三篇，你应该掌握：

| 能力 | 用的章节 |
|---|---|
| 用 5 个注解写声明式缓存 | ch6.1 |
| 选 Simple / Ehcache / Caffeine 哪种本地缓存 | ch6.2 |
| 用 Redis 作为分布式缓存 | ch6.3 |
| 切缓存实现不改业务代码 | ch6 全章 |
| 跟 ch5.3 RedisTemplate 混用 | ch5.3 + ch6.3 |

**ch6 的核心思想**：

> **业务代码不关心缓存是什么，缓存技术只是配置项**。这是"控制反转 + 依赖抽象"在缓存场景的具体体现——跟你 ch1 学的 IoC 是同一种思想，只是应用到了缓存上。

**Spring 全家桶的设计哲学是一致的**：

| 抽象 | 切实现成本 |
|---|---|
| **Spring Cache** | 改 yml（1 行）|
| **Spring Data JPA** | 改方言（少量）|
| **Spring Data Redis** | 改连接配置 |
| **Spring MVC** | 改视图解析器 |
| **Spring Security** | 改认证方式 |

> **掌握"通过抽象解耦"这个思想，比学任何一个具体框架都重要**。

---

下章 (ch7) 应该是 Spring Boot 的安全（Spring Security）和异步（@Async / 消息队列），敬请期待。