---
title: MyBatis-Plus:用"约定大于配置"的方式写 MyBatis
description: 第 5 章学习笔记（中）。从 MyBatis 写 SQL 的痛点出发，讲 MyBatis-Plus 的通用 Mapper、通用 Service、条件构造器，加上 Lambda 风格、自动填充、软删除这些教材没讲的实战内容。
pubDate: 2026-09-06
tags: [Spring Boot, MyBatis-Plus, Java]
---

> **读这章前**:ch1 的 Spring Boot 项目要能跑起来，ch0 的 Maven 要会装。**学完 ch5.1 的 JPA 再来**——这样能横向对比两种 ORM 思路。

这章解决一个 MyBatis 老问题：**单表 CRUD 的 SQL 写得太多**。

## 1. 先看一个"写到手酸"的场景

传统 MyBatis 里，写一个 `book` 表的 DAO，你得：

```java
public interface BookMapper {
    int insert(Book book);
    int updateById(Book book);
    int deleteById(int id);
    Book selectById(int id);
    List<Book> selectList(@Param("ew") Wrapper<Book> queryWrapper);
    // ... 10 几个方法
}
```

```xml
<!-- BookMapper.xml -->
<mapper namespace="com.silence.dao.BookMapper">
    <insert id="insert">
        INSERT INTO book (name, author, press, status)
        VALUES (#{name}, #{author}, #{press}, #{status})
    </insert>
    <update id="updateById">
        UPDATE book SET name=#{name}, author=#{author}, press=#{press}, status=#{status}
        WHERE id=#{id}
    </update>
    <delete id="deleteById">
        DELETE FROM book WHERE id=#{id}
    </delete>
    <select id="selectById" resultType="Book">
        SELECT * FROM book WHERE id=#{id}
    </select>
</mapper>
```

**问题**：

- 增删改查的 SQL 都是模板——换个表名、字段名就完事，但每个表都得抄一遍
- XML 文件跟接口、字段脱钩——改字段名要改 3 处
- 动态条件（WHERE 拼接）写起来很啰嗦——`<if>` + `<where>` 一堆标签

**MyBatis-Plus 的解决思路**：**单表 CRUD 帮你写好，你只写"复杂查询"**。上面那段代码会变成：

```java
// 只写接口，不写 XML，不写实现
public interface BookMapper extends BaseMapper<Book> {
    // 单表 CRUD 框架已经写好
    // 复杂查询自己加方法
}
```

`bookMapper.selectById(1)` 就能查，`bookMapper.deleteById(1)` 就能删。这章就是讲这套机制。

## 2. MyBatis-Plus 是啥

**MyBatis-Plus（MP）** 是 MyBatis 的增强工具，在 MyBatis 基础上**只做增强不做改变**——你的 MyBatis 代码 100% 兼容，MP 只是"加了一层方便的方法"。

**MyBatis、MyBatis-Plus、Hibernate、JPA 四者关系**：

| 工具 | 思路 | 适合 |
|---|---|---|
| MyBatis | 你写 SQL，框架帮你映射 | 复杂 SQL、性能敏感 |
| MyBatis-Plus | 你写**条件**，框架生成 SQL | 简单 CRUD 居多，复杂 SQL 自己写 |
| Spring Data JPA | 你写**方法名**，框架生成 SQL | 单表、对象思维 |
| Hibernate | 你写对象操作，框架生成 SQL | 复杂对象关系 |

> 比喻：MyBatis 像"手写菜谱"、MP 像"半成品超市"（90% 菜都现成，要特色菜自己炒）、JPA 像"点菜下单"（告诉服务员想吃什么，厨房做）。

**MP 跟 JPA 的核心差异**：

- **JPA**：方法名约定要写对才能用，写错直接报"找不到属性"
- **MP**：用 `Wrapper`（条件构造器）拼条件，写错字段运行时才报错
- **JPA**：跨数据库能力强（换方言基本不改代码）
- **MP**：SQL 写在框架里，跨数据库要看具体 SQL 方言

> **经验法则**：单表 CRUD 多 + 偶尔复杂 SQL，选 MP；对象关系复杂 + 喜欢面向对象思维，选 JPA。两个都能用，**看团队习惯**。

## 3. 11 个核心特性

教材列了一堆特性，我用大白话翻译：

| # | 特性 | 大白话 |
|---|---|---|
| 1 | 无侵入 | 你原来的 MyBatis 代码不用改 |
| 2 | 损耗小 | 启动时动态注入 SQL，几乎不影响性能 |
| 3 | 强大的 CRUD 操作 | `BaseMapper` 内置 20+ 通用方法 |
| 4 | 支持 Lambda 形式调用 | 用 `Book::getName` 代替 `"name"`，**字段名重构安全** |
| 5 | 支持主键自动生成 | 内置 4 种策略（数据库自增 / UUID / 雪花算法 / 自定义） |
| 6 | 支持 ActiveRecord 模式 | 实体类直接 `book.insert()`，**不用注入 Mapper** |
| 7 | 支持自定义全局通用操作 | 一次配置，全局生效 |
| 8 | 内置代码生成器 | 一键生成 Entity / Mapper / Service / Controller |
| 9 | 内置分页插件 | 一行代码分页，**基于物理分页**（不是内存分页） |
| 10 | 内置性能分析插件 | 慢 SQL 一眼看到 |
| 11 | 内置全局拦截插件 | 统一处理 SQL（脱敏、租户隔离等） |

下面挑**最常用的 5 个**展开讲。

## 4. 通用 Mapper：单表 CRUD 不写 SQL

`BaseMapper<T>` 内置方法（图 5-5 的扩充版）：

```java
public interface BookMapper extends BaseMapper<Book> {
    // ↑ 不用加 @Mapper 注解（配了 MapperScan 就不用加）
}

// 用的时候直接注入
@Autowired
private BookMapper bookMapper;
```

**新增 / 修改（同一个方法，靠主键判断）**：

```java
// 新增（主键为空 → 框架自动生成）
Book book = new Book();
book.setName("楚辞");
book.setAuthor("屈原");
bookMapper.insert(book);    // 返回 int 影响行数

// 修改（主键有值 → UPDATE）
book.setId(1);
bookMapper.updateById(book);  // 返回 int 影响行数
```

**删除**：

```java
// 按 ID 删
int rows = bookMapper.deleteById(1);

// 按条件删
int rows = bookMapper.delete(
    new QueryWrapper<Book>().eq("author", "屈原")
);
// 删了所有 author='屈原' 的书

// 批量删
int rows = bookMapper.deleteBatchIds(Arrays.asList(1, 2, 3));
```

**查询**：

```java
// 按 ID 查
Book book = bookMapper.selectById(1);

// 查全部
List<Book> list = bookMapper.selectList(null);

// 按条件查
List<Book> list = bookMapper.selectList(
    new QueryWrapper<Book>().eq("status", 1)
);

// 查数量
Long count = bookMapper.selectCount(
    new QueryWrapper<Book>().like("name", "诗")
);

// 分页（要配分页插件）
Page<Book> page = bookMapper.selectPage(
    new Page<>(1, 10),  // 第 1 页，每页 10 条
    new QueryWrapper<Book>().eq("status", 1)
);
page.getRecords();    // 当前页数据
page.getTotal();      // 总记录数
page.getPages();      // 总页数
```

**关键点**：

- `BaseMapper` 已经覆盖了 90% 的单表 CRUD
- **不写 SQL、不写 XML、不写实现类**——这是 MP 最大的省事点
- 自定义复杂查询（多表 JOIN、复杂 WHERE）还是要在 XML 里写 SQL

## 5. 通用 Service：业务层封装

`Service` 和 `Mapper` 的区别：`Mapper` 是数据访问层（一个表一个 Mapper），`Service` 是业务层（一个业务一个 Service，可能调多个 Mapper）。MP 也提供了通用 Service 帮你省事：

```java
public interface BookService extends IService<Book> {
    // 自定义业务方法
}

@Service
public class BookServiceImpl extends ServiceImpl<BookMapper, Book>
    implements BookService {
    // ServiceImpl<M, T> 已经注入了 M (Mapper)
    // 直接用 this.bookMapper 或继承的 list() / getOne() 等方法
    // 也可以 this.save(book) / this.updateById(book) / this.removeById(1)
}
```

**IService 内置方法**（图 5-12 的核心）：

| 分类 | 方法 | 作用 |
|---|---|---|
| 新增 | `save(entity)` | 插入一条 |
| | `saveBatch(list)` | 批量插入（默认 1000 条/批） |
| | `saveOrUpdate(entity)` | 智能判断新增/修改 |
| 修改 | `updateById(entity)` | 按主键修改 |
| | `update(wrapper)` | 按条件修改 |
| | `updateBatchById(list)` | 批量按主键修改 |
| 删除 | `removeById(id)` | 按主键删 |
| | `removeByIds(idList)` | 批量按主键删 |
| | `remove(wrapper)` | 按条件删 |
| 查询 | `getById(id)` | 按主键查 |
| | `list()` | 查全部 |
| | `list(wrapper)` | 按条件查 |
| | `page(page, wrapper)` | 分页查 |
| | `count()` | 总数 |
| | `getOne(wrapper)` | 查一条（多条会报错） |
| | `getOpt(wrapper)` | 查一条（返回 `Optional`） |

**关键点**：

- `ServiceImpl` **已经注入了对应的 Mapper**，你不用再 `@Autowired` 一次
- `getOne` 在多条结果时**会抛异常**（避免你误用），`getOpt` 返回 `Optional<Book>` 让你自己处理
- `updateBatchById` 是**真批量**（拼接成一条 SQL `UPDATE ... WHERE id IN (?, ?, ?)`），不是循环调用

## 6. 条件构造器：写动态 SQL 的"流式 API"

**这是 MP 的核心**——`Wrapper` 让你**用 Java 代码拼 SQL 条件**，不用写 XML 也不用写字符串。

### 6.1 经典风格（教材用的）

```java
QueryWrapper<Book> wrapper = new QueryWrapper<Book>();
wrapper.eq("status", 1)            // WHERE status = 1
      .like("name", "诗")          //   AND name LIKE '%诗%'
      .orderByDesc("id");          //   ORDER BY id DESC

List<Book> list = bookMapper.selectList(wrapper);
```

**常用方法**（图 5-13 速查）：

| 方法 | 等价 SQL |
|---|---|
| `eq("name", "楚辞")` | `name = '楚辞'` |
| `ne("status", 0)` | `status != 0` |
| `gt("price", 50)` | `price > 50` |
| `ge("price", 50)` | `price >= 50` |
| `lt("price", 100)` | `price < 100` |
| `le("price", 100)` | `price <= 100` |
| `between("price", 50, 100)` | `price BETWEEN 50 AND 100` |
| `like("name", "诗")` | `name LIKE '%诗%'` |
| `likeLeft("name", "诗")` | `name LIKE '%诗'` |
| `likeRight("name", "诗")` | `name LIKE '诗%'` |
| `in("status", 1, 2, 3)` | `status IN (1, 2, 3)` |
| `isNull("name")` | `name IS NULL` |
| `isNotNull("name")` | `name IS NOT NULL` |
| `orderByDesc("id")` | `ORDER BY id DESC` |
| `groupBy("author")` | `GROUP BY author` |
| `having("SUM(price) > {0}", 100)` | `HAVING SUM(price) > 100` |
| `last("LIMIT 1")` | 拼接 SQL 末尾（慎用，跨数据库可能炸） |

**链式调用**（AND / OR）：

```java
wrapper.eq("status", 1)
       .and(w -> w.like("name", "诗").or().like("author", "诗"))
       .orderByDesc("id");
// WHERE status = 1 AND (name LIKE '%诗%' OR author LIKE '%诗%') ORDER BY id DESC
```

### 6.2 Lambda 风格（教材没讲，但**强烈推荐**）

经典风格的问题：**字段名是字符串 `"name"`，重命名时编译器不会报错**。`@Autowired` 时复制粘贴漏改一处，运行时报"找不到字段"。

**Lambda 风格**用方法引用代替字符串，**重命名时编译器直接报错**：

```java
// 经典风格（字段名写死字符串，重命名不会报错）
new QueryWrapper<Book>().eq("name", "楚辞")

// Lambda 风格（方法引用，重命名编译失败）
new LambdaQueryWrapper<Book>().eq(Book::getName, "楚辞")
//                              ↑ 用方法引用代替字符串
```

**Lambda 风格常用方法**：

```java
// 查
List<Book> list = bookMapper.selectList(
    new LambdaQueryWrapper<Book>()
        .eq(Book::getStatus, 1)
        .like(Book::getName, "诗")
        .orderByDesc(Book::getId)
);

// 改
bookMapper.update(
    new Book() {{ setStatus(0); }},
    new LambdaUpdateWrapper<Book>().eq(Book::getAuthor, "屈原")
);

// 删
bookMapper.delete(
    new LambdaQueryWrapper<Book>().eq(Book::getStatus, 0)
);
```

> **真实项目经验**：**永远优先用 Lambda 风格**。一年后回头改字段名，经典风格的 bug 排查能花一整天，Lambda 风格编译器 1 秒告诉你错在哪。

### 6.3 复杂场景

**只查部分字段**（性能优化——别 `SELECT *`）：

```java
// 方式 1：select 指定字段
wrapper.select("id", "name", "author");
List<Book> list = bookMapper.selectList(wrapper);

// 方式 2：返回 Map（不映射实体）
List<Map<String, Object>> maps = bookMapper.selectMaps(wrapper);
```

**子查询**：

```java
wrapper.inSql("author", "SELECT name FROM author WHERE country = '中国'");
// WHERE author IN (SELECT name FROM author WHERE country = '中国')
```

**动态条件**（避免空条件拼成 `WHERE 1=1`）：

```java
String name = req.getName();  // 可能为 null
Integer status = req.getStatus();

LambdaQueryWrapper<Book> wrapper = new LambdaQueryWrapper<>();
wrapper.like(StringUtils.isNotBlank(name), Book::getName, name)
       .eq(status != null, Book::getStatus, status);
// ↑ 第 1 个参数为 false 时，框架自动跳过这个条件
```

## 7. 注解：让实体更"懂"表

教材里的实体类只用了 `@TableName`，实际项目**至少要会这 4 个注解**：

```java
import com.baomidou.mybatisplus.annotation.*;

@Data
@TableName("book")           // ← 对应 book 表（类名与表名不一致必加）
public class Book {

    @TableId(type = IdType.AUTO)   // ← 主键策略
    // AUTO      数据库自增（MySQL 常用）
    // ASSIGN_ID 雪花算法（19 位 Long，分布式友好，**默认**）
    // ASSIGN_UUID UUID 字符串
    // INPUT     手动 setId
    private Long id;

    @TableField("name")       // ← 字段名与列名不一致必加
    private String name;

    @TableField(select = false)  // ← 不参与查询（密码字段用）
    private String password;

    @TableField(fill = FieldFill.INSERT)   // ← 插入时自动填充
    private LocalDateTime createTime;

    @TableField(fill = FieldFill.INSERT_UPDATE)  // ← 插入+更新时自动填充
    private LocalDateTime updateTime;

    @TableLogic               // ← 软删除：查询时自动 WHERE deleted=0
    @TableField(select = false)  //   删除时自动 UPDATE ... SET deleted=1
    private Integer deleted;
}
```

**自动填充怎么配**（写一个 MetaObjectHandler）：

```java
@Component
public class MyMetaObjectHandler implements MetaObjectHandler {

    @Override
    public void insertFill(MetaObject metaObject) {
        this.strictInsertFill(metaObject, "createTime", LocalDateTime.class, LocalDateTime.now());
        this.strictInsertFill(metaObject, "updateTime", LocalDateTime.class, LocalDateTime.now());
    }

    @Override
    public void updateFill(MetaObject metaObject) {
        this.strictUpdateFill(metaObject, "updateTime", LocalDateTime.class, LocalDateTime.now());
    }
}
```

**软删除的好处**：

- 业务上"删除"但数据库里数据还在——能恢复、能审计
- 比物理删除安全（删错了找不回来）
- 配了 `@TableLogic` 之后，`selectList(null)` 自动只查 `deleted=0` 的，`removeById(1)` 自动变成 `UPDATE book SET deleted=1 WHERE id=1`，**业务代码完全不用改**

## 8. ActiveRecord 模式（教材没讲，看团队习惯）

`BaseMapper` 风格叫 **Repository 模式**（数据访问层）；`@TableName` + 继承 `Model<Book>` 叫 **ActiveRecord 模式**（实体自己管自己）。

```java
@TableName("book")
@Data
public class Book extends Model<Book> {  // ← 继承 Model
    @TableId(type = IdType.AUTO)
    private Long id;
    private String name;
    private String author;
    // ...
}

// 用的时候——直接 book.insert()，不用注入 mapper
Book book = new Book();
book.setName("楚辞");
book.insert();     // ← 实体直接调方法，框架处理数据库
```

**两种风格对比**：

| 维度 | Repository（推荐） | ActiveRecord |
|---|---|---|
| 实体职责 | 纯数据 | 数据 + 持久化 |
| 测试 | 容易（mock mapper） | 难（要 mock 数据库） |
| 适用 | 大多数项目 | 小项目、CRUD 单页面 |
| 团队接受度 | 高（Spring 思想） | 争议（像 Rails） |

> **个人建议**：**新项目用 Repository 模式**。ActiveRecord 写起来爽，但实体类跟数据库耦合，测试和重构成本高。

## 9. 完整例子：Spring Boot 整合 MyBatis-Plus

### 9.1 pom.xml

```xml
<parent>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-parent</artifactId>
    <version>2.7.6</version>
</parent>

<dependencies>
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-web</artifactId>
    </dependency>

    <!-- MyBatis-Plus starter（注意：不要同时引 mybatis-spring-boot-starter，会冲突） -->
    <dependency>
        <groupId>com.baomidou</groupId>
        <artifactId>mybatis-plus-boot-starter</artifactId>
        <version>3.5.3.1</version>
    </dependency>

    <dependency>
        <groupId>mysql</groupId>
        <artifactId>mysql-connector-java</artifactId>
        <scope>runtime</scope>
    </dependency>

    <dependency>
        <groupId>org.projectlombok</groupId>
        <artifactId>lombok</artifactId>
        <optional>true</optional>
    </dependency>
</dependencies>
```

> **踩坑提醒**：**不能同时引 `mybatis-spring-boot-starter` 和 `mybatis-plus-boot-starter`**，会冲突。如果项目里已经有 `mybatis-spring-boot-starter`，要把它去掉。

### 9.2 application.yml

```yaml
spring:
  datasource:
    url: jdbc:mysql://localhost:3306/springbootdata?useUnicode=true&characterEncoding=utf8&useSSL=false&serverTimezone=Asia/Shanghai
    username: root
    password: root
    driver-class-name: com.mysql.cj.jdbc.Driver

mybatis-plus:
  configuration:
    map-underscore-to-camel-case: true   # ← 数据库下划线字段自动转 Java 驼峰
    log-impl: org.apache.ibatis.logging.stdout.StdOutImpl  # ← 控制台打印 SQL
  global-config:
    db-config:
      logic-delete-field: deleted   # ← 全局软删除字段
      logic-delete-value: 1         # ← 软删除值
      logic-not-delete-value: 0     # ← 未删除值
      id-type: ASSIGN_ID            # ← 全局主键策略（雪花算法）
```

### 9.3 实体类

`com.silence.chapter05.entity.EBook`：

```java
@Data
@TableName("book")      // ← 对应 book 表
public class EBook {

    @TableId(type = IdType.AUTO)
    private Integer id;

    private String name;        // 图书名称
    private String author;      // 图书作者
    private String press;       // 出版社
    private String remark;      // 备注
    private String pic;         // 封面
    private String publishTime; // 出版时间
    private String edition;     // 版次
    private String isbn;        // ISBN
    private Integer status;     // 状态

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;

    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updateTime;

    @TableLogic
    @TableField(select = false)
    private Integer deleted;
}
```

### 9.4 Mapper 接口

`com.silence.chapter05.dao.BookMapper`：

```java
import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.silence.chapter05.entity.EBook;
import org.apache.ibatis.annotations.Mapper;

@Mapper    // ← 配了 MapperScan 就不用加
public interface BookMapper extends BaseMapper<EBook> {
    // 这里什么都不用写，单表 CRUD 框架已经提供
    // 多表查询 / 复杂 SQL 自己加方法 + XML
}
```

### 9.5 Service 接口和实现

`com.silence.chapter05.service.IBookService`：

```java
import com.baomidou.mybatisplus.extension.service.IService;
import com.silence.chapter05.entity.EBook;

public interface IBookService extends IService<EBook> {
    // 通用 Service 已经提供 list() / getById() / save() / updateById() / removeById()
    // 自定义业务方法加在这里
}
```

`com.silence.chapter05.service.impl.BookServiceImpl`：

```java
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.silence.chapter05.dao.BookMapper;
import com.silence.chapter05.entity.EBook;
import com.silence.chapter05.service.IBookService;
import org.springframework.stereotype.Service;

@Service
public class BookServiceImpl extends ServiceImpl<BookMapper, EBook>
    implements IBookService {
    //                              ↑ M 写 Mapper, T 写实体
    // 继承的 baseMapper 字段可以直接用
    // this.save(book) / this.list() / this.page(page, wrapper) 都行
}
```

### 9.6 启动类加 @MapperScan

`com.silence.chapter05.Chapter05Application`：

```java
import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
@MapperScan("com.silence.chapter05.dao")
// ↑ 扫描 Mapper 接口，不用每个接口都加 @Mapper
public class Chapter05Application {
    public static void main(String[] args) {
        SpringApplication.run(Chapter05Application.class, args);
    }
}
```

### 9.7 测试增删改查

```java
@SpringBootTest
class Chapter05ApplicationMPTests {

    @Autowired
    private IBookService bookService;

    @Autowired
    private BookMapper bookMapper;

    // 1. 新增
    @Test
    void saveEBook() {
        EBook book = new EBook();
        book.setName("人间词话");
        book.setAuthor("王国维");
        book.setPress("四川文艺出版社");
        book.setStatus(1);
        bookService.save(book);
    }
    // 输出：4 条原有 + 1 条新加（id=5）

    // 2. 条件查询（Lambda 风格）
    @Test
    void findEBook() {
        List<EBook> list = bookService.list(
            new LambdaQueryWrapper<EBook>()
                .eq(EBook::getStatus, 1)
                .like(EBook::getName, "词")
        );
        list.forEach(System.out::println);
    }
    // 输出：name 含"词"且 status=1 的书

    // 3. 修改
    @Test
    void editEBook() {
        EBook book = bookService.getById(4);
        book.setName("楚辞（修订版）");
        book.setPress("中华书局");
        bookService.updateById(book);
    }
    // 输出：id=4 的 name 和 press 改了

    // 4. 软删除
    @Test
    void delEBook() {
        bookService.removeById(2);
        // ↑ 实际执行: UPDATE book SET deleted=1 WHERE id=2 AND deleted=0
        // 数据还在表里，只是 deleted=1 了
    }

    // 5. 分页
    @Test
    void pageEBook() {
        Page<EBook> page = bookService.page(
            new Page<>(1, 10),
            new LambdaQueryWrapper<EBook>().orderByDesc(EBook::getId)
        );
        System.out.println("总条数: " + page.getTotal());
        System.out.println("总页数: " + page.getPages());
        page.getRecords().forEach(System.out::println);
    }
}
```

## 10. JPA vs MyBatis-Plus 选型对比

| 维度 | JPA | MyBatis-Plus |
|---|---|---|
| 单表 CRUD | 极简（方法名约定） | 极简（BaseMapper） |
| 复杂查询 | JPQL / 原生 SQL | XML / `@Select` 注解 / Wrapper |
| 字段名写错 | 编译报错（**安全**） | 运行时 SQL 错（**不安全**，除非用 Lambda） |
| 对象思维 | 强（领域驱动友好） | 弱（半 SQL 半对象） |
| SQL 可控性 | 弱（Hibernate 生成的 SQL 难调） | **强**（能写 XML 调优） |
| 跨数据库 | **强**（换方言基本不改） | 中（注意方言） |
| 团队上手 | 中等 | **快**（懂 SQL 就能上手） |
| 性能调优 | 难（生成的 SQL 不一定最优） | **易**（自己写 SQL） |
| 复杂报表 | 难（多表 JOIN + 分组不友好） | **友好** |

> **经验法则**：
> - **业务系统**（CRUD 多，复杂 SQL 少）→ JPA 写起来更爽
> - **数据系统**（复杂报表、统计查询多）→ MyBatis-Plus 更合适
> - **很多公司**两者都混用——主业务用 JPA，报表模块用 MyBatis-Plus

## 11. 实战踩坑

1. **同时引了 `mybatis-spring-boot-starter` 和 `mybatis-plus-boot-starter`** → 启动报 `BeanDefinitionStoreException`。**去掉 `mybatis-spring-boot-starter`**，只用 MP 的 starter
2. **`@TableField(select = false)` 后 `selectList` 查不到该字段**——这是设计如此，密码字段就不该返回。**但** `selectById` 仍然能查到，逻辑有点反直觉，注意测试
3. **分页不生效**——`Page` 对象没用对。要先注入 `PaginationInnerInterceptor` 配到 `MybatisPlusInterceptor`：
   ```java
   @Configuration
   public class MybatisPlusConfig {
       @Bean
       public MybatisPlusInterceptor mybatisPlusInterceptor() {
           MybatisPlusInterceptor interceptor = new MybatisPlusInterceptor();
           interceptor.addInnerInterceptor(new PaginationInnerInterceptor(DbType.MYSQL));
           return interceptor;
       }
   }
   ```
4. **软删除忘了配全局**——单独实体的 `@TableLogic` 注解要写对字段名；`application.yml` 的 `logic-delete-field` 跟实体字段名一致
5. **`Wrapper` 的字段名拼错不报错**——这是经典风格最大的坑。**用 Lambda 风格**解决
6. **批量插入超过 1000 条报 `PacketTooBigException`**——MySQL 默认 `max_allowed_packet=4M`。要么分批，要么改 MySQL 配置：`SET GLOBAL max_allowed_packet=64M;`
7. **雪花算法主键溢出**——`ASSIGN_ID` 生成的 19 位 Long 远超 `int` 范围。**主键必须用 `Long`，不能用 `Integer`**

---

下篇讲 Redis（ch5.3-redis.md），从"为什么需要缓存"讲起，5 种数据类型 + Spring Data Redis + 一个完整的"图书访问量"小项目。
