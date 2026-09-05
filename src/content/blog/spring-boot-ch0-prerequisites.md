---
title: 读 Spring Boot 前你需要会什么
description: ch1-ch4 的前置知识清单。Java 基础、Maven、HTTP、IoC 概念。不熟的先去补。
pubDate: 2026-09-05
tags: [Spring Boot, Java, 前置]
---

> 这篇是 ch1-ch4 的"门票"。先来这打个勾,免得后面看不懂骂我。

说实话,Spring Boot 是个"集成"框架——它把一堆东西打包好给你用。所以读它之前,你**自己得会那些被它打包的东西**。如果底子不够,读 ch1 就像听相声不知道前情提要。

## 一、Java 基础(必须)

下面这些**必须熟练**,不然看 ch1 的代码会懵。

| 知识点 | 你至少要会什么 | 不熟怎么办 |
|---|---|---|
| 类、对象、构造方法 | 能写一个 `User` 类带字段+getter/setter | 看《Java 核心技术》卷 I |
| 接口、`implements` | 能写一个接口+实现类 | 同上 |
| 继承、`extends` | 知道子类能继承父类的方法和字段 | 同上 |
| **注解** | 知道 `@Override` `@Deprecated` 这种是干嘛的 | 看 Java 注解的官方教程 |
| 泛型 `List<T>` `Map<K,V>` | 用过 `ArrayList`、`HashMap` | 写几个增删改查的 demo |
| Lambda 表达式 | 知道 `(a, b) -> a + b` 是什么 | 实际写两个例子 |
| try-catch 异常处理 | 能捕获并处理 IOException | 写过文件读取的代码 |

**检查题**:给你 5 分钟,你能手写出下面这个类吗?

```java
public class Book {
    private int id;
    private String name;

    public Book(int id, String name) {
        this.id = id;
        this.name = name;
    }

    public int getId() { return id; }
    public String getName() { return name; }
}
```

写不出来 → 先去补 Java 基础。

## 二、Maven 必须会

ch1 里你会看到一堆 `pom.xml` 配置。**不需要精通**,但要能看懂和跑命令。

**至少要会 3 个命令**:

```bash
mvn compile     # 编译源代码
mvn package     # 打包(打成 JAR/WAR)
mvn spring-boot:run   # 跑 Spring Boot 项目(插件提供的)
```

**至少要认识这些 pom.xml 里的字段**:

```xml
<dependencies>      <!-- 所有依赖放这里 -->
  <dependency>      <!-- 一个依赖 -->
    <groupId>org.springframework.boot</groupId>   <!-- 组织/公司名 -->
    <artifactId>spring-boot-starter-web</artifactId>  <!-- 项目名 -->
    <version>3.x.x</version>      <!-- 版本(可省,Spring Boot 有默认管理) -->
  </dependency>
</dependencies>
```

就像快递单:groupId 是发件公司,artifactId 是物品名,version 是批次号。三个凑一起才能定位一个具体的依赖。

**检查题**:看到一段 `pom.xml`,你能说出"这个项目用了 Spring MVC"吗?

## 三、HTTP 基础

Web 开发绕不开 HTTP。ch3 大量涉及。

**必须会的 4 件事**:

1. **URL 是什么**:`http://localhost:8080/user/123` 各部分啥意思
2. **GET vs POST**:
   - GET:从服务器**读**数据(查)
   - POST:往服务器**写**数据(增/改)
3. **常见状态码**:
   - `200 OK` 成功
   - `404 Not Found` 找不到
   - `500 Internal Server Error` 服务器崩了
4. **请求/响应结构**:
   - 请求 = 请求行(URL+方法) + Header + Body
   - 响应 = 状态行(200) + Header + Body(HTML/JSON)

**检查题**:你在浏览器地址栏输入 `http://example.com/api/user?id=1`,这是什么方法?传了什么参数?

## 四、3 个必须懂的概念(常被问到)

### 概念 1:IoC(Inversion of Control,控制反转)

**没学 Spring 之前,你是这样写代码的**:

```java
// 自己 new 一个对象
UserService userService = new UserService();
userService.doSomething();
```

**用 Spring 之后**:

```java
// 不 new,直接拿(Spring 帮你 new 好了)
@Autowired
private UserService userService;
```

`@Autowired` 让 Spring 把对象"注入"给你。**控制权**从你手里**反转**到 Spring 容器。

### 概念 2:AOP(Aspect-Oriented Programming,面向切面)

**没用 AOP 之前,每个方法都要写日志**:

```java
public void saveUser(User user) {
    System.out.println("开始保存用户...");  // 每个方法都要写
    userDao.save(user);
    System.out.println("保存用户结束");     // 每个方法都要写
}
```

**用 AOP 之后,日志抽到"切面"里,业务方法干干净净**:

```java
@Log   // 标注一下要记日志
public void saveUser(User user) {
    userDao.save(user);   // 只关心业务
}
```

横切关注点(日志、事务、权限)从业务代码里**抽出来**,不污染业务。

### 概念 3:注解(Annotation)

注解是 `**@xxx**` 这种东西,贴在类/方法/字段上,给"程序读的元数据"。

```java
@Override                        // 告诉编译器:这是重写父类方法
public String toString() { ... }

@RestController                  // 告诉 Spring:这是个 REST 控制器
public class UserController { ... }

@GetMapping("/user/{id}")        // 告诉 Spring:这个方法处理 GET /user/{id}
public User getUser(@PathVariable int id) { ... }
```

注解本身**不写逻辑**,只是"标记"。具体怎么响应,Spring 框架看到这些标记后会处理。

## 五、强烈建议先会的 1 件事

**会用 IntelliJ IDEA 跑 Java 程序**。

- 创建一个新项目
- 写一个 `main` 方法
- 点绿色三角跑
- 看 console 输出

如果这几步你**不熟**,先去 IDEA 里玩 30 分钟,随便写点 Java 代码,熟悉了再回来看 ch1。

## ✅ 检查清单:开始 ch1 之前

把下面这几条**每个都打勾**了再继续:

- [ ] 能手写一个带 getter/setter 的 Java 类
- [ ] 知道 `@Override` 是干什么的
- [ ] 会跑 `mvn package` 命令
- [ ] 能说出 `pom.xml` 里的 `groupId / artifactId / version` 各自是啥
- [ ] 知道 GET 和 POST 的区别
- [ ] 知道 200 / 404 / 500 各代表什么
- [ ] 知道 IoC 是"对象由 Spring 创建不用自己 new"
- [ ] 会用 IDEA 创建一个项目并跑起来

**有 3 个以上没勾** → 先去补,别急。
**全部勾了** → 直接看 ch1,可以无障碍。
