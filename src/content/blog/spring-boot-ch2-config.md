---
title: Spring Boot 配置：properties/yaml 写法、@ConfigurationProperties 绑定、多环境 Profile
description: 第 2 章学习笔记。把代码里的"硬编码"抽出来,绑到 Bean 上,不同环境用不同配置。
pubDate: 2026-09-05
tags: [Spring Boot, Java]
---

这一章的核心问题：怎么把代码里写死的值（比如数据库地址、端口号）抽到配置文件里？怎么一组相关的配置自动绑到一个 Bean 上？dev/test/prod 三个环境怎么切换？

## 1. 两种配置文件

Spring Boot 默认读 `src/main/resources/application.properties` 或 `application.yml`——**两个都叫 application，**但后缀不同，二选一**。properties 老，yml 新（推荐）。

### properties 写法（key=value，平铺）

```properties
# 注释用 #
server.port=8080
spring.datasource.url=jdbc:mysql://localhost:3306/test
spring.datasource.username=root
spring.datasource.password=123456
```

### yml 写法（缩进表示层级）

```yaml
server:
  port: 8080
spring:
  datasource:
    url: jdbc:mysql://localhost:3306/test
    username: root
    password: 123456
```

yml 三个优势：层级清晰、能写列表、能自动识别类型（int / bool / list 不用加引号）。

yml 有个坑：**缩进必须用空格，不能用 Tab**。少一个空格就报错，写的时候小心。

## 2. 把配置值绑到 Bean

三种方式，**用得最多的是第三种**。

### 方式 1：`@Value` 绑单个值

```java
@Component
public class ServerConfig {
    @Value("${server.port}")
    private int port;

    @Value("${app.name:DefaultApp}")   // 冒号后是默认值
    private String appName;
}
```

`@Value` 还支持 SpEL 表达式：

```java
@Value("#{2 * 1024}")        // 算术:2048
private int maxSize;

@Value("${server.port}")      // 读配置
private String port;
```

`${...}` 是取配置值，`#{...}` 是 SpEL 计算。

### 方式 2：`Environment` 编程式获取

```java
@Component
public class MyService {
    @Autowired
    private Environment env;

    public void print() {
        String url = env.getProperty("spring.datasource.url");
        // ...
    }
}
```

适合"运行时才知道要拿哪个 key"的场景。日常用 `@Value` 或 `@ConfigurationProperties` 就够。

### 方式 3：`@ConfigurationProperties` 批量绑定（推荐）

`@Value` 一个一个绑很啰嗦，一组相关配置用 `@ConfigurationProperties` 一次性绑到一个 Bean：

**application.yml**

```yaml
myapp:
  user:
    name: Tagaki
    age: 22
    hobbies:
      - 写代码
      - 看技术书
```

**UserProperties.java**

```java
package com.example.demo.config;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

@Component
@ConfigurationProperties(prefix = "myapp.user")
public class UserProperties {
    private String name;
    private int age;
    private List<String> hobbies;

    // getter 和 setter 必须有(可以手动写,也可以用 Lombok @Data 简化)
    public String getName() { return name; }
    public void setName(String name) { this.name = name; }
    public int getAge() { return age; }
    public void setAge(int age) { this.age = age; }
    public List<String> getHobbies() { return hobbies; }
    public void setHobbies(List<String> hobbies) { this.hobbies = hobbies; }
}
```

**用的时候直接注入：**

```java
@Service
public class UserService {
    @Autowired
    private UserProperties userProps;

    public void print() {
        System.out.println(userProps.getName());   // 输出:Tagaki
        System.out.println(userProps.getHobbies()); // 输出:[写代码, 看技术书]
    }
}
```

**`prefix` 指定前缀**，下面所有子属性自动绑到 Bean 字段，名字严格匹配（yml 写 `name` 对应 Java 写 `name`）。这就是"批量绑定"。

### 加数据校验

在字段上加 JSR-303 注解（`@ConfigurationProperties` 配 `@Validated`）：

```java
@Component
@ConfigurationProperties(prefix = "myapp.user")
@Validated   // 开启校验
public class UserProperties {
    @NotBlank
    private String name;

    @Min(1)
    @Max(150)
    private int age;

    // getter/setter ...
}
```

启动时如果 `myapp.user.name` 是空，会直接启动失败报错。比运行时崩好。

## 3. `@Value` vs `@ConfigurationProperties` 怎么选

| 场景 | 选这个 |
|---|---|
| 单个零散的值（一个字段一个 key）| `@Value` |
| 一组相关字段（同一个前缀）| `@ConfigurationProperties` |
| 需要数据校验（`@NotBlank` 等）| `@ConfigurationProperties` + `@Validated` |
| 需要松散绑定（`userName` ↔ `user-name` ↔ `user_name`）| `@ConfigurationProperties` |

**实战**：日常配置（如数据库连接池、Redis、文件上传）都建议用 `@ConfigurationProperties`，零散的小开关用 `@Value`。

## 4. 引入外部配置文件

默认只读 `application.properties`。想读别的文件：

```java
@Component
@PropertySource("classpath:my.properties")   // 读 src/main/resources/my.properties
public class MyBean {
    @Value("${my.key}")
    private String key;
}
```

**一个坑**：`@PropertySource` **只能读 .properties 文件，不能读 .yml**。要读 yml 就用 `@ConfigurationProperties` + 把配置放 application.yml 里。

要引入老 Spring 时代的 XML 配置：

```java
@SpringBootApplication
@ImportResource("classpath:beans.xml")   // 引入老的 beans.xml
public class DemoApplication { }
```

## 5. Profile 多环境配置

同一份代码，dev / test / prod 用不同配置——这是**实战必学**。

### 方式 1：多文件（强烈推荐）

`src/main/resources/` 下放这几个文件：

```
application.yml          ← 默认配置(所有环境共享)
application-dev.yml      ← 开发环境
application-test.yml     ← 测试环境
application-prod.yml     ← 生产环境
```

**application.yml**（基础配置 + 激活哪个环境）

```yaml
spring:
  profiles:
    active: dev    # 默认激活 dev
server:
  port: 8080       # 共享配置
```

**application-dev.yml**

```yaml
spring:
  datasource:
    url: jdbc:mysql://localhost:3306/dev_db
    username: dev_user
    password: dev123
```

**application-prod.yml**

```yaml
spring:
  datasource:
    url: jdbc:mysql://prod-mysql:3306/prod_db
    username: prod_user
    password: ${DB_PASSWORD}    # 密码从环境变量读,不写死在文件里
```

激活 prod 环境有三种方法：

```bash
# 1. 配置文件里改 spring.profiles.active
# 2. 命令行参数
java -jar app.jar --spring.profiles.active=prod

# 3. 环境变量
export SPRING_PROFILES_ACTIVE=prod && java -jar app.jar
```

### 方式 2：`@Profile` 注解标记 Bean

某些 Bean 只在特定环境才需要：

```java
@Component
@Profile("dev")   // 只在 dev 环境注册
public class DevMailService implements MailService {
    // 开发环境的邮件服务,发到本地测试邮箱
}

@Component
@Profile("prod")
public class ProdMailService implements MailService {
    // 生产环境的邮件服务,接真实 SMTP
}
```

这样同一个 `MailService` 接口，在不同环境用不同实现，不需要改业务代码。
