---
title: Spring Cache 声明式缓存：5 个注解搞定增删改查缓存
description: 第 6 章学习笔记（上）。从"每次查都打数据库"的问题出发，讲 Spring Cache 抽象 + 5 个声明式缓存注解 + 完整 Spring Boot 整合例子。
pubDate: 2026-09-07
tags: [Spring Boot, Spring Cache, Java]
---

> **读这章前**:ch1 Spring Boot 项目要能跑，ch5.1 JPA 至少看过一遍（这章用 JPA 写例子）。

这章解决一个**写烂代码**的问题：**怎么用最少的代码给所有查询加缓存**。

## 1. 先看一个"重复查数据库"的场景

假设你有个"图书详情"接口，**每个用户访问都要查数据库**：

```java
@RestController
public class BookController {
    @Autowired
    private BookService bookService;

    @RequestMapping("/book/findById/{id}")
    public Book findById(@PathVariable Integer id) {
        return bookService.findById(id);
    }
}

@Service
public class BookServiceImpl implements BookService {
    @Autowired
    private BookRepository bookRepository;

    @Override
    public Book findById(Integer id) {
        // 每次都打数据库！热门书 1 万次访问 = 1 万次 SQL
        return bookRepository.findById(id).orElse(null);
    }
}
```

**问题**：

- 同一本书被 1000 人查 = 1000 次 SQL（其中 999 次结果完全一样）
- 数据库连接被占满 → 整个系统崩
- 缓存逻辑散在业务代码里（"if 缓存有则 return，没则查"）→ 业务代码变得又丑又乱

**传统写法**（每个方法都得写一遍缓存逻辑）：

```java
public Book findById(Integer id) {
    // 1. 查缓存
    Book cached = (Book) redisTemplate.opsForValue().get("book:" + id);
    if (cached != null) return cached;

    // 2. 查数据库
    Book book = bookRepository.findById(id).orElse(null);

    // 3. 写回缓存
    if (book != null) {
        redisTemplate.opsForValue().set("book:" + id, book, 5, TimeUnit.MINUTES);
    }
    return book;
}
```

每个方法都要写这 3 步。**10 个查询方法 = 30 行重复代码**。

**Spring Cache 的解决思路**：用**注解**把缓存逻辑从业务代码里抽出来，框架通过 AOP 自动织入：

```java
// 加一个注解就完事
@Cacheable(cacheNames = "book", key = "#id")
public Book findById(Integer id) {
    return bookRepository.findById(id).orElse(null);
}
```

> 第一次调用：执行方法，查数据库，把结果存到缓存
> 第二次调用：发现缓存里有，直接返回，**不再执行方法体**

## 2. Spring Cache 是什么

**Spring Cache** 是 Spring 框架提供的一套**缓存抽象**。它不直接提供缓存实现，而是定义了一组**接口**和**注解**，让你可以**切换不同的缓存技术**（Redis / Ehcache / Caffeine 等）而不改业务代码。

**核心接口**：

```
CacheManager（缓存管理器） ← 多个 Cache 实例的管理者
    ↓
Cache（缓存）             ← 实际存数据的容器
    ↓
Key-Value
```

**Spring Boot 默认按这个顺序查找缓存组件**（找到第一个就用）：

```
① Generic
② JCache（EhCache 3 / Hazelcast / Infinispan）
③ EhCache 2.x
④ Hazelcast
⑤ Infinispan
⑥ Couchbase
⑦ Redis
⑧ Caffeine
⑨ Simple ← 最后兜底，用 ConcurrentHashMap（只在本进程生效）
```

> **实战经验**：**90% 的项目只用到 `Simple` 和 `Redis` 两种**。本地开发用 `Simple`（不用装 Redis），生产用 `Redis`（多实例共享）。

**关键点**：**业务代码只面向 `CacheManager` 和注解编程**——换缓存技术只改 `application.yml` 一行配置，**业务代码完全不动**。

## 3. 5 个声明式缓存注解（重点！）

### 3.1 `@EnableCaching`：总开关

在**启动类**上加，开启整个项目的缓存支持：

```java
@SpringBootApplication
@EnableCaching   // ← 加这一行就开启了
public class Chapter06Application {
    public static void main(String[] args) {
        SpringApplication.run(Chapter06Application.class, args);
    }
}
```

> **不加这个注解，下面所有 `@Cacheable` 都不生效**（这是最常见的踩坑之一）

### 3.2 `@Cacheable`：查询时用（**最常用**）

**作用**：方法执行前**先查缓存**，有就返回；没有就执行方法，**把结果存到缓存**。

```java
@Cacheable(cacheNames = "book", key = "#id")
public Book findById(Integer id) {
    System.out.println("执行数据库查询");
    return bookRepository.findById(id).orElse(null);
}
```

**第一次调用**（缓存为空）：

```
进入方法 → 查数据库 → 拿到 Book{id=1, name="楚辞"} → 存到缓存 book::1 → 返回
```

**第二次调用**（缓存命中）：

```
不进入方法！直接返回缓存里的 Book{id=1, name="楚辞"}
```

**关键属性**：

| 属性 | 作用 | 示例 |
|---|---|---|
| `value` / `cacheNames` | 缓存名称（**必填**，二选一）| `cacheNames = "book"` |
| `key` | 缓存的 key（默认用方法参数）| `key = "#id"` / `key = "#name + '-' + #id"` |
| `condition` | 满足条件才缓存（SpEL）| `condition = "#id > 0"` |
| `unless` | 不缓存的条件（SpEL，**针对结果**判断）| `unless = "#result == null"` |
| `sync` | 同步模式（多线程同时查同一个 key 时只放一个请求过去查 DB）| `sync = true` |

**SpEL 常用变量**：

| 变量 | 含义 |
|---|---|
| `#参数名` | 方法参数（用参数名，如 `#id`）|
| `#p0` / `#a0` | 第 0 个参数（按位置）|
| `#root.methodName` | 当前方法名 |
| `#root.target` | 当前对象 |
| `#result` | 方法返回值（**只在 `unless` 里用**）|

**实战示例**：

```java
// 多 cache（任一命中即返回）
@Cacheable({"book", "hotBook"}, key = "#id")
public Book findById(Integer id) { ... }

// 条件缓存（id > 0 才缓存）
@Cacheable(cacheNames = "book", key = "#id", condition = "#id > 1")
public Book findById(Integer id) { ... }

// 结果不为 null 才缓存
@Cacheable(cacheNames = "book", key = "#id", unless = "#result == null")
public Book findById(Integer id) { ... }

// 多参数拼 key
@Cacheable(cacheNames = "book", key = "#author + '-' + #status")
public List<Book> findByAuthorAndStatus(String author, int status) { ... }
```

### 3.3 `@CachePut`：更新时用（保证缓存同步）

**作用**：**总是执行方法**，然后把**返回值**更新到缓存。**用在"写"操作**（新增 / 修改）上。

```java
@CachePut(cacheNames = "book", key = "#id")
public Book updateById(Integer id, String name) {
    Book book = findById(id);
    book.setName(name);
    return bookRepository.save(book);
}
```

**和 `@Cacheable` 的区别**：

| 注解 | 缓存命中时 | 缓存未命中时 |
|---|---|---|
| `@Cacheable` | **不执行方法**，直接返回缓存 | 执行方法，把结果存缓存 |
| `@CachePut` | **总是执行方法**，更新缓存 | 执行方法，把结果存缓存 |

> **关键点**：**`@Cacheable` + `@CachePut` 必须在同一个 key 上**，否则缓存不一致（写库后缓存还是旧的）

### 3.4 `@CacheEvict`：删除时用（清缓存）

**作用**：执行方法后（默认），**删除指定 key 的缓存**。

```java
@CacheEvict(cacheNames = "book", key = "#id")
public void delById(Integer id) {
    bookRepository.deleteById(id);
}
```

**关键属性**：

| 属性 | 作用 |
|---|---|
| `allEntries = true` | 清空**整个缓存空间**（慎用，所有 key 一起删）|
| `beforeInvocation = true` | **方法执行前**清缓存（默认是执行后清）|

**`allEntries` 用法**：

```java
@CacheEvict(cacheNames = "book", allEntries = true)
public void clearAll() {
    // 这个方法执行后，"book" 缓存下所有 key 都被清掉
    log.info("清空 book 缓存");
}
```

**`beforeInvocation` 用法**（避免"删了缓存但方法抛异常导致数据库没删"的不一致）：

```java
@CacheEvict(cacheNames = "book", key = "#id", beforeInvocation = true)
public void delById(Integer id) {
    bookRepository.deleteById(id);
    // 如果这里抛异常：
    //   beforeInvocation=true → 缓存已清，方法没执行 → 用户下次查会从 DB 重新加载
    //   beforeInvocation=false (默认) → 缓存没清，方法没执行 → 用户拿到旧数据
}
```

> **经验法则**：**数据库删除操作用 `beforeInvocation = true`**，更安全。

### 3.5 `@Caching`：组合多个注解

一个方法上要同时用多个缓存操作（比如**先查缓存 → 没命中查 DB → 删几个相关 key**），用 `@Caching` 嵌套：

```java
@Caching(
    cacheable = {
        @Cacheable(cacheNames = "primary", key = "#id")
    },
    evict = {
        @CacheEvict(cacheNames = "secondary", key = "#id"),
        @CacheEvict(cacheNames = "stats", key = "#id")
    }
)
public Book findBook(Integer id) {
    return bookRepository.findById(id).orElse(null);
}
```

### 3.6 `@CacheConfig`：类级别公共配置

如果一个类里**所有方法都用同一个 cacheNames**，可以提到类上：

```java
@Service
@CacheConfig(cacheNames = "book")   // ← 公共配置
public class BookServiceImpl implements BookService {

    @Cacheable(key = "#id")          // ← 不用再写 cacheNames
    public Book findById(Integer id) { ... }

    @CachePut(key = "#id")           // ← 不用再写 cacheNames
    public Book updateById(Integer id, String name) { ... }

    @CacheEvict(key = "#id")         // ← 不用再写 cacheNames
    public void delById(Integer id) { ... }
}
```

> **就近原则**：方法上自己的注解**覆盖类上的**。如果类上写了 `cacheNames="book"`，方法上又写 `cacheNames="hotBook"`，**以方法上的为准**。

## 4. 完整例子：图书缓存

### 4.1 准备

`pom.xml`（`chapter06` 项目）：

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
</dependencies>
```

`application.yml`：

```yaml
spring:
  datasource:
    url: jdbc:mysql://localhost:3306/springbootdata?useUnicode=true&characterEncoding=utf8&useSSL=false&serverTimezone=Asia/Shanghai
    username: root
    password: root
    driver-class-name: com.mysql.cj.jdbc.Driver

  jpa:
    show-sql: true
    properties:
      hibernate:
        format_sql: true

  cache:
    type: simple   # ← 默认用 ConcurrentHashMap（本地缓存）
                   #   生产改成 redis 就一行
```

### 4.2 实体类

```java
@Entity
@Table(name = "book")
public class Book {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Integer id;
    @Column(name = "name")
    private String name;
    private String author;
    private String press;
    private String status;
    // getter / setter 省略
}
```

### 4.3 Repository

```java
public interface BookRepository extends JpaRepository<Book, Integer> {
}
```

### 4.4 Service 接口和实现

`BookService`：

```java
public interface BookService {
    Book findById(Integer id);
    Book updateById(Integer id, String name);
    void delById(Integer id);
}
```

`BookServiceImpl`（**关键**——5 个注解都用上）：

```java
@Service
@CacheConfig(cacheNames = "book")   // ← 公共配置：所有方法都用 "book" 缓存
public class BookServiceImpl implements BookService {

    @Autowired
    private BookRepository bookRepository;

    // 查：先查缓存，没命中再查 DB
    @Cacheable(key = "#id")
    public Book findById(Integer id) {
        System.out.println("执行了 findById(id=" + id + ")");
        return bookRepository.findById(id).orElse(null);
    }

    // 改：执行方法后更新缓存
    @CachePut(key = "#id")
    public Book updateById(Integer id, String name) {
        Book book = this.findById(id);
        book.setName(name);
        return bookRepository.save(book);
    }

    // 删：执行方法前清缓存（更安全）
    @CacheEvict(key = "#id", beforeInvocation = true)
    public void delById(Integer id) {
        bookRepository.deleteById(id);
    }
}
```

### 4.5 Controller

```java
@RestController
@RequestMapping("/book")
public class BookController {

    @Autowired
    private BookService bookService;

    @RequestMapping("/findById/{id}")
    public Book findById(@PathVariable Integer id) {
        return bookService.findById(id);
    }

    @RequestMapping("/editById/{id}/{name}")
    public Book editById(@PathVariable Integer id, @PathVariable String name) {
        return bookService.updateById(id, name);
    }

    @RequestMapping("/delById/{id}")
    public void delById(@PathVariable Integer id) {
        bookService.delById(id);
    }
}
```

### 4.6 启动类

```java
@SpringBootApplication
@EnableCaching   // ← 不加这个注解，所有 @Cacheable 都不生效
public class Chapter06Application {
    public static void main(String[] args) {
        SpringApplication.run(Chapter06Application.class, args);
    }
}
```

### 4.7 验证缓存效果

启动后浏览器依次访问：

```
1. http://localhost:8080/book/findById/3
   → 控制台打印 "执行了 findById(id=3)"
   → 返回 {"id":3, "name":"西游记", ...}

2. http://localhost:8080/book/findById/3   ← 同样 id
   → 控制台不打印任何东西（直接命中缓存）
   → 返回一样的结果

3. http://localhost:8080/book/editById/3/西游释厄传
   → 控制台打印（执行了 updateById）
   → 缓存被更新成 {"id":3, "name":"西游释厄传", ...}

4. http://localhost:8080/book/findById/3
   → 不执行方法（命中缓存）
   → 直接返回更新后的数据
```

**关键点**：

- **第一次**和**第二次**查同样 id，**第二次控制台不打日志** = 缓存生效
- 修改后**立即**查新值 = `@CachePut` 把缓存也更新了
- 删除后**不会**查到旧值 = `@CacheEvict` 清了缓存

## 5. 5 个注解速查表

| 场景 | 注解 | 关键属性 | 是否执行方法 |
|---|---|---|---|
| 查（命中不执行）| `@Cacheable` | `cacheNames`, `key` | 看命中 |
| 改（总是执行 + 更新缓存）| `@CachePut` | `cacheNames`, `key` | **总是执行** |
| 删（清缓存）| `@CacheEvict` | `key`, `allEntries`, `beforeInvocation` | 总执行（看 `beforeInvocation`）|
| 复杂组合 | `@Caching` | 嵌套其他注解 | 看内部 |
| 公共配置 | `@CacheConfig`（类上）| `cacheNames`, `keyGenerator` | — |

## 6. `@Cacheable` 4 个常见问题

### Q1：`@Cacheable` 不生效？

**答**：99% 是**忘了加 `@EnableCaching`**。检查启动类。

### Q2：同一个类内部方法调用，`@Cacheable` 不生效？

```java
@Service
public class BookServiceImpl {
    @Cacheable(key = "#id")
    public Book findById(Integer id) { ... }

    public void other() {
        // ❌ 这种情况 findById 的 @Cacheable 不生效！
        //   因为 AOP 代理不会拦截"内部 this 调用"
        Book book = this.findById(1);
    }
}
```

**解法 3 选 1**：

```java
// 方案 1：注入自己（@Lazy 避免循环依赖）
@Autowired @Lazy
private BookServiceImpl self;

public void other() {
    Book book = self.findById(1);  // ✅ 走代理
}

// 方案 2：AopContext.currentProxy()
public void other() {
    Book book = ((BookServiceImpl) AopContext.currentProxy()).findById(1);
}

// 方案 3：拆成两个 Service（最干净）
```

### Q3：缓存和数据库不一致？

**典型场景**：更新数据库后忘了 `@CachePut` 或 `@CacheEvict`，导致用户读到旧数据。

**最佳实践**：
- 写操作（增/改）：用 `@CachePut` 更新缓存
- 删操作：用 `@CacheEvict` 清缓存（**`beforeInvocation = true` 更安全**）
- 极端情况（写操作绕过了 service）：用 **`@Transactional` + 监听 `@TransactionalEventListener`** 异步清缓存

### Q4：key 冲突（不同方法用了同一个 key）？

```java
@Cacheable(cacheNames = "book", key = "#id")
public Book findById(Integer id) { ... }     // key = 1

@Cacheable(cacheNames = "user", key = "#id")
public User findUser(Integer id) { ... }    // key = 1（不冲突，cacheNames 不同）
```

`cacheNames` 是命名空间，不同 `cacheNames` 的 key 互不干扰。**用同一个 cacheNames 但不同 key 也会冲突**——确保 key 设计合理（比如加前缀 `#root.methodName + '-' + #id`）。

## 7. 选哪个缓存？（决策树）

```
数据要跨实例共享？ ──No──→ Caffeine（本地缓存，最快）
   │ Yes
   ↓
要持久化（重启不丢）？ ──No──→ Redis（内存 + 持久化）
   │ Yes
   ↓
数据量小（< 1GB）？ ──Yes──→ Redis
   │ No
   ↓
考虑 Redis Cluster 或分库
```

| 场景 | 推荐 |
|---|---|
| 单实例本地缓存 | Caffeine（最快，无网络）|
| 多实例 + 中小规模 | Redis（最常用）|
| 多实例 + 大规模 + 强一致 | Redis Cluster / Hazelcast |
| 单实例 + 数据要重启不丢 | Ehcache（带磁盘持久化）|
| 只想"快速跑起来" | Simple（默认，ConcurrentHashMap）|

## 8. 实战踩坑

1. **忘了 `@EnableCaching`** — `@Cacheable` 静默失效（不报错，就是不缓存）。**每次写完跑一次接口看控制台**
2. **同 key 拼前缀** — `cacheNames="book"` 时 key 直接 `#id`，多方法同 id 会撞。**复杂场景用 `#root.methodName + '-' + #id`**
3. **`@Cacheable` 返回 `null` 也会被缓存** — 想缓存 null 显式用 `condition = "..."`，否则加 `unless = "#result == null"` 不缓存
4. **`sync = true` 才能解决缓存击穿** — 不开 sync，100 个请求同时查同一个 key，100 个都打 DB
5. **大对象别缓存** — 一本书 5KB 没事，一个用户对象 50 个字段（10KB）经常被查就 5GB/天了
6. **缓存粒度** — `@Cacheable` 加在 `findById`（精确）比加在 `findAll`（全表）好得多

---

下篇讲 **Ehcache 整合**（ch6.2-ehcache.md）——JVM 进程内缓存，**比 Redis 还快**（少一次网络 IO），适合数据量适中 + 单实例场景。