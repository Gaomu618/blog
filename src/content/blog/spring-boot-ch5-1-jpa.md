---
title: Spring Data JPA:用面向对象的方式操作数据库
description: 第 5 章学习笔记（上）。从"写 SQL 太烦"的问题出发，讲 Spring Data JPA 的 4 种查询方式 + 完整 Spring Boot 整合例子。
pubDate: 2026-09-06
tags: [Spring Boot, Spring Data JPA, Java]
---

> **读这章前**:ch1 的 Spring Boot 项目要能跑起来，ch0 的 Maven 要会装。

这章解决一个实际问题：**怎么用最少的 SQL 写完增删改查**。

## 1. 先看一个"写到手酸"的场景

假设你有个 `book` 表，传统的 `JdbcTemplate` 写法是：

```java
@Repository
public class BookDao {

    @Autowired
    private JdbcTemplate jdbc;

    public Book findById(int id) {
        // 写一行 SQL，绑 4 个参数，把 ResultSet 手动映射成对象
        String sql = "SELECT id, name, author, press, status FROM book WHERE id = ?";
        return jdbc.queryForObject(sql, new Object[]{id}, (rs, rowNum) -> {
            Book b = new Book();
            b.setId(rs.getInt("id"));
            b.setName(rs.getString("name"));
            b.setAuthor(rs.getString("author"));
            b.setPress(rs.getString("press"));
            b.setStatus(rs.getInt("status"));
            return b;
        });
    }
}
```

**问题**：

- 每个查询都要写 SQL + 手动映射字段 → 字段一多（10+ 个）就容易漏
- 改字段名要改 3 处：SQL、setter、构造器
- 写完 1 个查询发现跟之前那个几乎一样，复制粘贴又改改

**JPA 的解决思路**：**你写接口，框架自动生成实现**。上面那段代码会变成：

```java
public interface BookRepository extends JpaRepository<Book, Integer> {
    // 方法名 findById 是约定，框架自动生成实现
    // 不用写 SQL，不用映射字段
}
```

`BookRepository.findById(1)` 就能查出 id=1 的书。这章就是讲这套机制怎么用。

## 2. Spring Data 是个大家族

JPA 是 Spring Data 家族里的一个分支，先看家族全貌（图 5-1）：

```
            Spring Data
            /    |     |    \
Spring Data  Spring Data  Spring Data  Spring Data
   JPA        JDBC        MongoDB      Redis
   ↓            ↓            ↓           ↓
关系型 DB    关系型 DB     文档 DB      内存 DB
(MySQL等)   (更底层)      (MongoDB)    (Redis)
```

**4 个子模块对应 4 类数据库**，API 风格统一（都是写接口 → 框架实现），学一个会一类。

**共同父接口继承链**：

```
Repository<T, ID>              ← 标记接口，没有任何方法
   ↑
CrudRepository<T, ID>         ← 增删改查
   ↑
PagingAndSortingRepository<T, ID>  ← 分页 + 排序
   ↑
JpaRepository<T, ID>           ← JPA 专用，扩展了批量删除、刷新等
```

**关键点**：

- 你自定义的接口只要 `extends JpaRepository<Book, Integer>`，就**自动**有了 CRUD + 分页 + 排序方法，**不用写实现类**。
- 框架默认实现类叫 `SimpleJpaRepository`，所有魔法都在这里。

## 3. Spring Data JPA 是啥

JPA 全称 **Java Persistence API**，它本身是**一套规范**（不是实现），定义了"怎么把对象映射到数据库表"的标准。

**JPA 和 Hibernate 的关系**：

| 角色 | 是什么 |
|---|---|
| JPA | 规范，定义了 `@Entity` / `@Id` / `EntityManager` 这些 API 的形状 |
| Hibernate | JPA 的一种**实现**（最常用），把规范落地成真的能跑的代码 |
| Spring Data JPA | 在 Hibernate 之上又包了一层，让我们写更少的代码 |

> 比喻：JPA 像 USB 接口规范，Hibernate 像某个品牌的 U 盘，Spring Data JPA 像"插上自动识别文件"的高级读卡器。

## 4. Spring Data JPA 的 4 种查询方式

光继承 `JpaRepository` 就能拿到 20 多个现成方法，但实际项目里经常要写"按作者查 + 按状态过滤 + 按价格排序"这种**自定义**查询。Spring Data JPA 给 4 种方式，从简到繁：

### 方式 1：父接口自带方法（不用动脑）

继承 `JpaRepository<T, ID>` 后直接有的方法（图 5-5）：

```java
// 查
Optional<T> findById(ID id);                 // 按主键查单个
List<T> findAll();                           // 查全部
List<T> findAll(Sort sort);                  // 查全部（带排序）
List<T> findAll(Pageable pageable);          // 查全部（带分页）

// 改（save 既能新增又能修改，看主键有没有）
<T> T save(T entity);                        // 新增或修改
<T> List<T> saveAll(Iterable<T> entities);   // 批量

// 删
void deleteById(ID id);                      // 按主键删
void delete(T entity);                       // 删实体
void deleteAll();                            // 删表（慎用！）
long count();                                // 统计行数
boolean existsById(ID id);                   // 判断主键存在不存在
```

**适用场景**：单表、简单查询、不需要写条件。

### 方式 2：按方法名约定（推荐，写得最多）

**规则**：方法名以 `findBy` / `countBy` / `deleteBy` / `existsBy` 开头，后面跟**实体字段名 + 关键字**。

```java
public interface BookRepository extends JpaRepository<Book, Integer> {
    // 等价 SQL: WHERE author = ?
    List<Book> findByAuthor(String author);

    // 等价 SQL: WHERE author = ? AND status = ?
    List<Book> findByAuthorAndStatus(String author, int status);

    // 等价 SQL: WHERE price > ?
    List<Book> findByPriceGreaterThan(double price);

    // 等价 SQL: WHERE name LIKE 'xxx%'
    List<Book> findByNameStartingWith(String prefix);

    // 等价 SQL: ORDER BY price ASC
    List<Book> findByAuthorOrderByPriceAsc(String author);
}
```

**支持的关键字**（图 5-7，记住常用的几个就够）：

| 关键字 | 示例 | 等价 SQL |
|---|---|---|
| `And` | `findByNameAndAuthor` | `WHERE name = ? AND author = ?` |
| `Or` | `findByNameOrAuthor` | `WHERE name = ? OR author = ?` |
| `Is` / `Equals` | `findByNameIs` | `WHERE name = ?` |
| `Between` | `findByPriceBetween` | `WHERE price BETWEEN ? AND ?` |
| `LessThan` / `GreaterThan` | `findByPriceLessThan` | `WHERE price < ?` |
| `After` / `Before` | `findByCreateTimeAfter` | `WHERE create_time > ?` |
| `IsNull` / `IsNotNull` | `findByNameIsNull` | `WHERE name IS NULL` |
| `Like` / `NotLike` | `findByNameLike` | `WHERE name LIKE ?` |
| `In` / `NotIn` | `findByStatusIn` | `WHERE status IN (?, ?, ?)` |
| `StartingWith` | `findByNameStartingWith` | `WHERE name LIKE '?%'` |
| `EndingWith` | `findByNameEndingWith` | `WHERE name LIKE '%?'` |
| `Containing` | `findByNameContaining` | `WHERE name LIKE '%?%'` |
| `OrderBy` | `findByAuthorOrderByPriceDesc` | `... ORDER BY price DESC` |

> **踩坑提醒**：`OrderBy` 后面接字段名 + `Asc`/`Desc`，**关键字之间不能有空格**，但 `OrderBy` 整体跟前面的字段之间可以有空格。
> 错的：`findByAuthor OrderBy Price` ❌
> 对的：`findByAuthorOrderByPrice` ✅

**适用场景**：80% 的查询都能用这个搞定，是最常用的方式。

### 方式 3：JPQL（复杂查询）

**JPQL = Java Persistence Query Language**，长得像 SQL，但是操作的是**实体类名和实体字段名**（不是表名和列名）。

```java
public interface BookRepository extends JpaRepository<Book, Integer> {

    // JPQL 写法：操作 Book 这个实体，操作 name/author/status 这些字段
    @Query("SELECT b FROM Book b WHERE b.name LIKE %:name% AND b.status = :status")
    List<Book> findByCondition(@Param("name") String name,
                                @Param("status") int status);

    // 占位符写法（?1 是第 1 个参数，?2 是第 2 个）
    @Query("SELECT b FROM Book b WHERE b.author = ?1 ORDER BY b.price DESC")
    List<Book> findByAuthorSorted(String author);

    // 修改（要加 @Modifying + @Transactional）
    @Modifying
    @Transactional
    @Query("UPDATE Book b SET b.status = ?1 WHERE b.id = ?2")
    int updateStatusById(int status, int id);

    // 删除
    @Modifying
    @Transactional
    @Query("DELETE FROM Book b WHERE b.status = 0")
    int deleteUnavailable();
}
```

**JPQL vs SQL 关键区别**：

| 维度 | SQL | JPQL |
|---|---|---|
| 操作对象 | 表名 (`book`)、列名 (`name`) | 实体类名 (`Book`)、字段名 (`name`) |
| 大小写 | 关键字不敏感 | 实体和字段**严格区分大小写** |
| 返回 | 字段 | 实体对象或字段 |

**适用场景**：方法名太长得离谱（4 个以上关键字）、要写子查询、需要返回部分字段。

### 方式 4：原生 SQL（特殊情况）

有些查询 JPQL 写不出来（数据库特定函数、复杂联表），就退化到原生 SQL：

```java
public interface BookRepository extends JpaRepository<Book, Integer> {

    @Query(value = "SELECT * FROM book WHERE name LIKE CONCAT('%', ?1, '%') AND status = ?2",
           nativeQuery = true)   // ← 加这个就是原生 SQL
    List<Book> findByNameRaw(String name, int status);
}
```

**关键点**：加 `nativeQuery = true` 后，`value` 里就是真 SQL，**操作表名和列名**。

**适用场景**：跨数据库兼容性不重要、要用 MySQL 的 `GROUP_CONCAT` / `IF` / 窗口函数等方言。

**取舍**：能用 JPQL 就别用原生 SQL。原生 SQL 绑死了数据库方言，换数据库（MySQL → PostgreSQL）要重写。

## 5. 完整例子：Spring Boot 整合 Spring Data JPA

光看方法不顶用，下面把"图书管理"那个例子完整跑通。

### 5.1 创建项目

`pom.xml`（`chapter05` 项目，关键依赖）：

```xml
<parent>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-parent</artifactId>
    <version>2.7.6</version>
</parent>

<dependencies>
    <!-- Spring Web（启动 Web 容器） -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-web</artifactId>
    </dependency>

    <!-- Spring Data JPA（核心） -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-data-jpa</artifactId>
    </dependency>

    <!-- MySQL 驱动 -->
    <dependency>
        <groupId>mysql</groupId>
        <artifactId>mysql-connector-java</artifactId>
        <scope>runtime</scope>
    </dependency>

    <!-- 测试 -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-test</artifactId>
        <scope>test</scope>
    </dependency>
</dependencies>
```

> 这段代码想干什么：声明项目用 Spring Boot 2.7.6，并引入 4 个依赖。`spring-boot-starter-data-jpa` 会**自动**引入 Hibernate 和数据库连接池，不用单独配。

### 5.2 配置数据源和 JPA

`src/main/resources/application.yml`：

```yaml
spring:
  datasource:                            # ← 数据源（连哪个库）
    url: jdbc:mysql://localhost:3306/springbootdata?useUnicode=true&characterEncoding=utf8&useSSL=false&serverTimezone=Asia/Shanghai
    username: root
    password: root
    driver-class-name: com.mysql.cj.jdbc.Driver

  jpa:                                  # ← JPA 配置
    hibernate:
      ddl-auto: update                  # ← 启动时自动建表（生产环境千万别用 update，自己写 SQL）
    show-sql: true                      # ← 控制台打印 SQL（学习时打开方便看）
    properties:
      hibernate:
        format_sql: true                # ← SQL 格式化（多行好看）
```

**关键配置说明**：

- `ddl-auto: update` — 启动时对比实体类和表结构，缺啥字段自动加。**生产环境要改成 `none`**，否则别人改了数据库就乱了
- `show-sql: true` — 控制台打印所有执行的 SQL，学 JPA 必开，不然你不知道框架帮你跑了啥
- `format_sql: true` — 配合 `show-sql` 把多行 SQL 格式化输出

### 5.3 创建实体类

`com.silence.chapter05.entity.Book`：

```java
import javax.persistence.*;        // ← JPA 的注解都在 javax.persistence 包下

@Entity                              // ← 告诉 JPA：这是个实体类，要和数据库表映射
@Table(name = "book")                // ← 对应数据库的 book 表（不写就用类名小写）
public class Book {

    @Id                              // ← 主键
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    // ← 主键自增策略：IDENTITY 用数据库自增（MySQL 的 AUTO_INCREMENT）
    //   还有 SEQUENCE（Oracle）、TABLE（用一张表记录）、AUTO（让框架选）
    private int id;

    @Column(name = "name")           // ← 对应 book 表的 name 列（不写就用字段名）
    private String name;             //   图书名称

    private String author;            //   图书作者
    private String press;            //   图书出版社
    private String remark;           //   图书备注
    private String pic;              //   图书封面
    private String publishTime;      //   出版时间
    private String edition;          //   版次
    private String isbn;             //   ISBN 号
    private int status;              //   图书状态（0 = 不可借，1 = 可借）

    // 构造方法、getter、setter 省略（IDE 自动生成即可）
}
```

**关键行**：

- `@Entity` — 必加，否则 JPA 不认这个类
- `@Table(name = "book")` — 类名和表名不一致时**必须**加，一致可以省略
- `@Id` + `@GeneratedValue` — 主键 + 自增策略，**两个必须一起用**
- `@Column` — 字段名和列名不一致时**必须**加，一致可以省略

> 实际项目里通常用 Lombok 的 `@Data` 注解自动生成 getter/setter，省得字段一多就几百行重复代码。

### 5.4 自定义 Repository 接口

`com.silence.chapter05.dao.BookRepository`：

```java
import com.silence.chapter05.entity.Book;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.transaction.annotation.Transactional;
import java.util.List;

public interface BookRepository extends JpaRepository<Book, Integer> {
    //     ↑ 第 1 个泛型是实体类型，第 2 个是主键类型

    // 1. 方法名约定
    Book findByAuthorAndStatus(String author, int status);

    // 2. JPQL
    @Query("SELECT b FROM Book b WHERE b.name LIKE %:name% AND b.status = :status")
    List<Book> findByCondition(@Param("name") String name,
                                @Param("status") int status);

    // 3. 自定义删除
    @Modifying
    @Transactional
    @Query("DELETE FROM Book b WHERE b.id = :id")
    int deleteBookById(@Param("id") int id);
}
```

**关键点**：

- **只写接口，不写实现类**。Spring 启动时会自动生成代理对象
- 泛型 `<Book, Integer>` — 第 1 个是实体类，第 2 个是主键类型（必须是包装类型，不能用 `int`）
- `findByAuthorAndStatus` 这种方法名是**约定**，不是注解；拼错大小写都不行

### 5.5 初始化数据

`src/main/resources/book.sql`（项目启动时执行，建表 + 插数据）：

```sql
CREATE DATABASE IF NOT EXISTS springbootdata;
USE springbootdata;

DROP TABLE IF EXISTS book;
CREATE TABLE book (
    id          int(11) NOT NULL AUTO_INCREMENT,
    name        varchar(32),
    author      varchar(32),
    press       varchar(32),
    remark      varchar(32),
    pic         varchar(64),
    publish_time varchar(32),
    edition     varchar(16),
    isbn        varchar(32),
    status      int(1),
    PRIMARY KEY (id)
);

INSERT INTO book VALUES (1, '楚辞', '屈原', '中国文联出版社', '楚辞', '', '2009-11-1', '1', 'ISBN-1', 0);
INSERT INTO book VALUES (2, '纳兰词', '纳兰性德', '中国文联出版社', '纳兰词', '', '2009-11-1', '1', 'ISBN-2', 1);
INSERT INTO book VALUES (3, '西游记', '吴承恩', '中国文联出版社', '西游记', '', '2009-11-1', '1', 'ISBN-3', 2);
INSERT INTO book VALUES (4, '离骚', '屈原', '清华大学出版社', '离骚', '', '2009-11-1', '1', 'ISBN-4', 1);
```

> 用 `spring.sql.init.mode=always` 可以让 Spring Boot 启动时自动跑这个 SQL（需要另外配 `spring.sql.init.mode`）。

### 5.6 启动类

`com.silence.chapter05.Chapter05Application`：

```java
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class Chapter05Application {
    public static void main(String[] args) {
        SpringApplication.run(Chapter05Application.class, args);
    }
}
```

### 5.7 测试增删改查

`src/test/java/com/silence/chapter05/Chapter05ApplicationTests.java`：

```java
import com.silence.chapter05.dao.BookRepository;
import com.silence.chapter05.entity.Book;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import java.util.List;
import java.util.Optional;

@SpringBootTest   // ← 启动 Spring 容器，跑测试
class Chapter05ApplicationTests {

    @Autowired
    private BookRepository bookRepository;

    // 1. 查询所有
    @Test
    void booksInfo() {
        List<Book> books = bookRepository.findAll();
        for (Book book : books) {
            System.out.println(book);
        }
    }
    // 输出：4 条 book 记录（id 1~4）

    // 2. 新增
    @Test
    void saveBook() {
        Book book = new Book();
        book.setName("天问");
        book.setAuthor("屈原");
        book.setPress("清华大学出版社");
        book.setStatus(0);
        bookRepository.save(book);       // 主键为空 → 新增；主键有值 → 修改
    }
    // 输出：表里多了 id=5, name="天问" 的记录

    // 3. 修改（先查出来，改字段，再 save）
    @Test
    void editBook() {
        Optional<Book> optional = bookRepository.findById(1);
        if (optional.isPresent()) {
            Book book = optional.get();
            book.setName("天问（修订版）");
            bookRepository.save(book);   // 主键 = 1 已存在 → 修改
        }
    }
    // 输出：id=1 的 name 从"楚辞"变成"天问（修订版）"

    // 4. 条件查询（方法名约定）
    @Test
    void findBook() {
        Book book = bookRepository.findByAuthorAndStatus("屈原", 1);
        System.out.println(book);
    }
    // 输出：Book(id=4, name="离骚", author="屈原", ..., status=1)

    // 5. 删除
    @Test
    void delBook() {
        bookRepository.deleteBookById(2);  // 调用自定义的 JPQL 删除
    }
    // 输出：id=2 的"纳兰词"被删了
}
```

**关键行**：

- `bookRepository.save(book)` — **同一个方法，新增和修改都靠它**。框架看主键：有值就修改，没值就新增（前提是主键策略是 `IDENTITY`）
- `findById` 返回 `Optional<Book>`（JDK 8 引入），**避免空指针**。要拿值必须 `.get()`，但用之前最好 `.isPresent()` 判一下
- `bookRepository.findByAuthorAndStatus(...)` — **框架看到方法名就自动生成实现**，完全不用你写 SQL

## 6. 总结：什么时候用哪种方式

| 场景 | 推荐方式 | 例子 |
|---|---|---|
| 单表、简单查询 | 父接口自带方法 | `findById(1)` / `findAll()` |
| 单表、条件清晰（≤3 个条件） | 方法名约定 | `findByAuthorAndStatus(...)` |
| 单表、条件复杂 / 要分页 | JPQL | `@Query("...")` |
| 跨表 / 跨数据库方言 | 原生 SQL | `nativeQuery = true` |

> 经验法则：**能用方法名约定就别用 JPQL，能用 JPQL 就别用原生 SQL**。每升一级复杂度，可读性和跨数据库能力都下降一档。

## 7. 踩过的坑

1. **`@Column` 字段名拼错，SQL 不报错但数据查不到**。把 `name` 写成 `naem`，字段映射不上，查询永远返回 null。**写完实体类先跑一次 `findAll()` 验证下**
2. **`save()` 改字段不生效**。主键没设自增策略，或者你手动 `setId(0)`，框架以为你要新增。检查 `@GeneratedValue` 注解在不在
3. **`@Modifying` 注解忘了加**。JPQL 写 `UPDATE` / `DELETE` 必须加 `@Modifying`，否则启动报错 `Executing an update/delete query`
4. **忘记加 `@Transactional`**。`@Modifying` 的 `UPDATE/DELETE` 需要事务支持，建议直接加在方法上或 Repository 接口上
5. **`JpaRepository` 的泛型写错**。主键类型用了基本类型 `int`（要 `Integer`），启动时 `NoClassDefFoundError`

---

下篇讲 MyBatis-Plus（ch5.2-mybatis-plus.md），风格跟这篇类似，但 API 设计更"动态 SQL"一些，看个人喜好选。
