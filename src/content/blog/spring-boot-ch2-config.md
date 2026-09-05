---
title: Spring Boot 配置:把硬编码抽出来,不同环境不同配置
description: 第 2 章学习笔记。例子驱动,从"配置硬编码在代码里"的问题出发,讲三种注入方式 + Profile 多环境。
pubDate: 2026-09-05
tags: [Spring Boot, Java]
---

> **读这章前**:ch1 的"Hello World"项目要能跑起来。

这章解决一个实际问题:**怎么把代码里写死的值抽到配置文件里**。

## 1. 先看一个"坏味道"代码

假设你写了个查用户的服务,数据库地址直接写在代码里:

```java
@Service
public class UserService {
    public List<User> findAll() {
        // ↓ 硬编码!换个环境(dev/test/prod)就得改代码重新打包
        String url = "jdbc:mysql://192.168.1.100:3306/prod_db";
        String username = "root";
        String password = "123456";
        // ...
    }
}
```

**问题**:
- 换个环境(开发 → 测试 → 生产)就得改代码
- 密码写在代码里,代码一开源全泄露
- 同一个项目 5 个数据库连接,代码里要改 5 个地方

**解决办法**:把这些值抽到配置文件里。

## 2. 配置文件长啥样

Spring Boot 默认读 `src/main/resources/application.properties` 或 `application.yml`,**两个文件二选一**(都叫 application 但后缀不同)。

### properties 写法(老风格,平铺 key=value)

`src/main/resources/application.properties`:

```properties
# 注释用 # 号
server.port=8080
spring.datasource.url=jdbc:mysql://localhost:3306/test
spring.datasource.username=root
spring.datasource.password=123456
```

**关键特点**:
- 每一行一个配置,`key=value` 格式
- 用 `.` 分层级
- **值都是字符串**(即使写 8080,其实也是字符串,要转成 int 得让 Spring 自动转)

### yml 写法(新风格,层级缩进)

`src/main/resources/application.yml`:

```yaml
server:
  port: 8080
spring:
  datasource:
    url: jdbc:mysql://localhost:3306/test
    username: root
    password: 123456
```

**关键特点**:
- 用**缩进**表示层级(2 空格,不能用 Tab)
- 一眼能看出哪个配置属于哪个"分类"
- **自动识别类型**:`port: 8080` 是 int,`url: '...'` 是字符串

**yml 三个优势**:
1. 层级结构清晰——一眼能看出 `datasource` 下面有哪些子配置
2. 能写列表:`tags: [Java, Spring, SQL]`
3. 自动识别类型——不用手写 `"` 包字符串

**踩坑提醒**:yml 缩进必须用**空格**,不能用 Tab,少一个空格就报错。文件用 UTF-8 无 BOM 保存。

## 3. 把配置值注入 Bean(三种方式)

现在配置文件有了,怎么让 Java 代码读它?**三种方式,各有适用场景**。

### 方式 1:`@Value` 绑单个值(简单粗暴)

**场景**:你只要读一个零散的值,比如端口号、用户名。

**配置文件**:
```yaml
app:
  name: 我的博客
  version: 1.0
```

**Java 代码**:
```java
@Component   // ← 让 Spring 容器管理这个类
public class AppInfo {

    @Value("${app.name}")        // ← 读 app.name 的值
    private String name;

    @Value("${app.version}")     // ← 读 app.version
    private String version;

    @Value("${server.port:9090}") // ← 读 server.port,读不到就用 9090(冒号后是默认值)
    private int port;
}
```

**关键行**:
- `@Value("${...}")` — `{}` 里写**配置 key**,Spring 启动时把对应值注入这个字段
- `:` 后跟默认值 — 配置不存在时不报错,用这个兜底

> **这段代码想干什么**:把 `application.yml` 里的 `app.name`、`app.version`、`server.port` 这三个值,自动注入到 Java 类的三个字段上。Spring 启动时帮你做"配置 → 字段"这一步。
>
> **跑起来看啥**:`AppInfo` 启动后,字段已经被赋值了,可以打印看看:
> ```
> AppInfo{name='我的博客', version='1.0', port=8080}
> ```

`@Value` 还支持 **SpEL 表达式**(用 `#{...}` 而不是 `${...}`):

```java
@Value("#{2 * 1024 * 1024}")   // 算术:2MB
private int maxFileSize;

@Value("${app.name}")           // 读配置
private String appName;
```

| 语法 | 作用 | 例子 |
|---|---|---|
| `${...}` | 读配置值 | `${server.port}` |
| `#{...}` | SpEL 表达式(算术/方法调用) | `#{2 * 1024}` |

### 方式 2:`Environment` 编程式获取(灵活但啰嗦)

**场景**:运行时才知道要读哪个 key,或者要遍历所有配置。

```java
@Component
public class AppInfoService {
    @Autowired
    private Environment env;   // ← Spring 注入环境对象,里面有所有配置

    public void printConfig() {
        String name = env.getProperty("app.name");
        String port = env.getProperty("server.port");
        // getProperty 支持默认值:env.getProperty("xxx", "默认")
    }
}
```

**关键行**:
- `Environment` 是 Spring 提供的"配置大管家",所有配置都能通过它读
- `getProperty(key)` 拿值,不存在返回 null
- `getProperty(key, defaultValue)` 不存在用默认值

> **这段代码想干什么**:拿到 Spring 的"配置访问入口",用代码读配置,适合"运行时才知道 key"的场景。
>
> 日常开发**优先用 `@Value` 或 `@ConfigurationProperties`**,只在特别需要时才用 Environment。

### 方式 3:`@ConfigurationProperties` 批量绑定(最推荐)

**场景**:一组相关字段(比如整个 `app.user` 子树),手动 `@Value` 写一堆太啰嗦。

**配置文件**:
```yaml
app:
  user:
    name: Tagaki
    age: 22
    hobbies:
      - 写代码
      - 看技术书
```

**Java 代码**(目录 `src/main/java/com/example/demo/config/UserProperties.java`):

```java
package com.example.demo.config;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

import java.util.List;

@Component   // ← 交给 Spring 容器
@ConfigurationProperties(prefix = "app.user")  // ← 绑 yml 里 app.user 下面所有字段
public class UserProperties {

    private String name;       // 自动绑 app.user.name
    private int age;           // 自动绑 app.user.age
    private List<String> hobbies;  // 自动绑 app.user.hobbies(列表)

    // 下面这些 getter/setter 必须有
    // (可以手动写,也可以用 Lombok 的 @Data 简化)

    public String getName() { return name; }
    public void setName(String name) { this.name = name; }

    public int getAge() { return age; }
    public void setAge(int age) { this.age = age; }

    public List<String> getHobbies() { return hobbies; }
    public void setHobbies(List<String> hobbies) { this.hobbies = hobbies; }
}
```

**使用**:

```java
@Service
public class UserService {
    @Autowired
    private UserProperties userProps;  // ← Spring 启动时已经帮我们填好

    public void print() {
        System.out.println(userProps.getName());    // 输出:Tagaki
        System.out.println(userProps.getHobbies()); // 输出:[写代码, 看技术书]
    }
}
```

**关键行**:
- `@ConfigurationProperties(prefix = "app.user")` — `prefix` 是 yml 里的前缀,下面所有子键自动绑到 Bean 字段
- 字段名跟 yml 里的子键**严格对应**:`name` 绑 `name`,`hobbies` 绑 `hobbies`
- **必须有 getter/setter**——Spring 通过 setter 注入值
- `List<String>` 自动绑 yml 的 `- xxx` 列表

> **这段代码想干什么**:把 yml 里 `app.user` 这一个子树,自动绑到一个 Java 类的字段上。比 `@Value` 一个一个绑省事多了。
>
> **跑起来看啥**:`UserProperties` 启动时就被填好了,可以直接打印:
> ```
> UserProperties{name='Tagaki', age=22, hobbies=[写代码, 看技术书]}
> ```

**踩坑提醒**:
- **字段必须有 setter**——Spring 通过 setter 注入,没有 setter 就注入不了
- 字段名要跟 yml 子键**完全一致**(区分大小写)
- 复杂结构(嵌套对象、列表)要写对应的 Java 类型

### 选哪个?三句话总结

| 场景 | 选这个 |
|---|---|
| 单个零散的值,一两个字段 | `@Value` |
| 一组相关配置,5+ 字段 | `@ConfigurationProperties` |
| 运行时才知道要读啥 key | `Environment` |

**实战经验**:数据库连接池、Redis、上传文件大小这些"一组配置"都用 `@ConfigurationProperties`,零散的小开关用 `@Value`。

## 4. 加数据校验(进阶,推荐学)

`@ConfigurationProperties` 配 `@Validated` 可以做启动时校验——配置错了直接启动失败,而不是运行到一半崩。

```java
@Component
@ConfigurationProperties(prefix = "app.user")
@Validated   // ← 开启 JSR-303 校验
public class UserProperties {

    @NotBlank   // ← 名字不能为空
    private String name;

    @Min(1)     // ← 年龄至少 1 岁
    @Max(150)   // ← 年龄最多 150
    private int age;

    // getter/setter ...
}
```

**关键行**:
- `@Validated` 标在类上,告诉 Spring "这个 Bean 要校验"
- `@NotBlank` `@Min` `@Max` 都是 **JSR-303 校验注解**(`jakarta.validation.constraints.*`)

> **这段代码想干什么**:启动时检查配置——名字为空直接报错,年龄写 999 也直接报错,不让项目带着错的配置跑起来。

`@Validated` 这个注解需要**额外加依赖**:

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-validation</artifactId>
</dependency>
```

## 5. 引入外部配置文件(高级)

默认只读 `application.properties`。想读别的文件:

```java
@Component
@PropertySource("classpath:my.properties")  // ← 读 src/main/resources/my.properties
public class MyBean {
    @Value("${my.custom.key}")
    private String key;
}
```

**关键行**:
- `classpath:` 前缀表示"从 classpath 找"——Spring Boot 项目里就是 `src/main/resources/` 目录
- 这个注解**只能读 .properties**,不能读 .yml(yml 用 `@ConfigurationProperties`)

**想引入老 Spring 的 XML 配置**?

```java
@SpringBootApplication
@ImportResource("classpath:beans.xml")  // ← 引入老 Spring 时代的 XML
public class DemoApplication { }
```

**踩坑提醒**:新项目**别用 XML**,用注解和 `@ConfigurationProperties`。

## 6. Profile 多环境配置(实战必学)

**问题**:同一份代码,在开发/测试/生产环境用不同配置(比如数据库地址、Redis 地址),怎么办?

**答**:用 Profile。

### 多文件方式(强烈推荐)

`src/main/resources/` 下放这些文件:

```
application.yml          ← 默认配置(所有环境共享)
application-dev.yml      ← 开发环境
application-test.yml     ← 测试环境
application-prod.yml     ← 生产环境
```

**`application.yml`(基础配置 + 激活哪个环境)**:

```yaml
spring:
  profiles:
    active: dev    # ← 默认激活 dev 环境

server:
  port: 8080
  appname: my-blog
```

**`application-dev.yml`**(开发环境):

```yaml
spring:
  datasource:
    url: jdbc:mysql://localhost:3306/dev_db
    username: dev_user
    password: dev123
```

**`application-prod.yml`**(生产环境):

```yaml
spring:
  datasource:
    url: jdbc:mysql://prod-mysql:3306/prod_db
    username: prod_user
    password: ${DB_PASSWORD}   # ← 密码从环境变量读,不写死在文件里
```

**激活不同环境有 3 种方法**:

```bash
# 1. application.yml 里改 spring.profiles.active
# 2. 命令行参数(部署时最常用)
java -jar app.jar --spring.profiles.active=prod

# 3. 环境变量
SPRING_PROFILES_ACTIVE=prod java -jar app.jar
```

> **这段配置想干什么**:同一份代码,根据激活的 profile 加载不同的配置文件。开发用本地数据库,生产用生产数据库,代码完全不用改。

**跑起来看啥**:
- 激活 dev → 用 dev_db,密码 dev123
- 激活 prod → 用 prod_db,密码从环境变量读

### `@Profile` 注解:不同环境用不同 Bean

**场景**:开发环境用"假支付服务",生产用"真支付服务"。

```java
public interface PayService {
    String pay(String orderId);
}

@Component
@Profile("dev")   // ← 只在 dev 环境注册这个 Bean
public class FakePayService implements PayService {
    @Override
    public String pay(String orderId) {
        return "假支付成功(开发环境)";
    }
}

@Component
@Profile("prod")  // ← 只在 prod 环境注册
public class RealPayService implements PayService {
    @Override
    public String pay(String orderId) {
        // 调真实支付接口
        return "真实支付成功";
    }
}
```

**关键行**:
- `@Profile("dev")` 标记的 Bean,只在 dev 环境被 Spring 注册
- 同一个接口在不同环境**自动用不同实现**,业务代码(`PayService payService`)不用动

> **这段代码想干什么**:同一份业务代码,在 dev 环境用假实现方便调试,在 prod 环境用真实现走真实逻辑——不用改任何业务代码。

## 7. 常见踩坑

**踩坑 1:yml 报错"while scanning a simple key"**
原因:缩进用了 Tab,或者少了空格。
解决:全改成 2 空格缩进。

**踩坑 2:`@ConfigurationProperties` 字段没绑上**
原因:getter/setter 没写,或者字段名跟 yml 不一致。
解决:确认 setter 方法名是标准的 `setXxx`。

**踩坑 3:`@Value` 取到 `${xxx}` 字符串字面值**
原因:配置 key 不存在,默认值也没设,就直接拿到了 `${xxx}` 字面。
解决:加默认值:`@Value("${xxx:默认值}")`。

## 8. 一句话总结这章

**学的是"把配置从代码里抽出来"**——properties/yml 写法,`@Value` / `Environment` / `@ConfigurationProperties` 三种注入方式,Profile 切环境。下章学"怎么拦截请求 + 异常处理"。

学完你应该能:
- [ ] 写一个 `application.yml` 配置文件
- [ ] 用 `@ConfigurationProperties` 批量绑配置
- [ ] 配置 dev/test/prod 三个环境的 Profile
- [ ] 解释 `@Value` vs `@ConfigurationProperties` 的区别
