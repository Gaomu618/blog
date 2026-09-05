---
title: Spring Boot 入门：从环境搭建到第一个 Web 接口
description: 第 1 章学习笔记。环境装什么、怎么建项目、跑起来、starter 是啥、启动时干了啥。
pubDate: 2026-09-05
tags: [Spring Boot, Java]
---

课本这一章列了 16 条目标，归成 4 块讲：**环境**、**项目**、**跑起来**、**部署**。

## 1. Spring 是什么，Spring Boot 又是什么

Spring 是一个 Java 框架，核心是 **IoC** 和 **AOP**：

- **IoC**（Inversion of Control，控制反转）：你不用 `new` 对象，由 Spring 容器创建并"注入"给你
- **AOP**（Aspect-Oriented Programming，面向切面）：把"日志、事务、权限"这种每个方法都要写的横切代码抽出去，不污染业务

Spring 用起来啰嗦，要写一堆 XML 配置。**Spring Boot 是 Spring 的"快捷版"**——加几行依赖、几个注解就跑起来。

最大的差别在于部署：Spring Boot 打成一个 JAR，`java -jar` 直接跑，因为**自带 Tomcat**。传统 Spring 项目要打成 WAR 丢到外部 Tomcat 里。

## 2. 环境装啥

Spring Boot 3.x 要求 **JDK 17 起**（这是硬性要求，低于 17 装不上）：

| 工具 | 用途 | 验证装好没 |
|---|---|---|
| JDK 17 | 跑 Java | `java -version` |
| Maven 3.6+ | 依赖管理 + 构建 | `mvn -version` |
| IntelliJ IDEA | 写代码 | 装好就行 |

IDEA 用**社区版（Community）**就够，别下成收费的 Ultimate。

## 3. 创建项目

新手用第一种：

**方式 1：Spring Initializr 网页**

打开 https://start.spring.io/，选：
- Project: Maven
- Language: Java
- Spring Boot: 3.x（最新稳定版）
- Group: `com.example`
- Artifact: `demo`
- Java: 17
- Dependencies: 加上 `Spring Web`

点 Generate 下载 zip，IDEA 打开。

**方式 2：IDEA 内置**

New Project → Spring Initializr，跟网页一样填。

### 最小目录长这样

```
demo/
├── pom.xml
└── src/
    ├── main/
    │   ├── java/com/example/demo/
    │   │   └── DemoApplication.java   ← 主程序入口
    │   └── resources/
    │       └── application.properties ← 全局配置
    └── test/
        └── java/com/example/demo/
            └── DemoApplicationTests.java
```

### 主程序就这么点

```java
package com.example.demo;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class DemoApplication {
    public static void main(String[] args) {
        SpringApplication.run(DemoApplication.class, args);
    }
}
```

`@SpringBootApplication` 这一个等于三个注解一起：`@Configuration` + `@EnableAutoConfiguration` + `@ComponentScan`。

### 第一个 Web 接口

在 `com.example.demo` 下新建 `HelloController.java`：

```java
package com.example.demo;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class HelloController {

    @GetMapping("/hello")
    public String hello() {
        return "Hello, Spring Boot!";
    }
}
```

跑起来后浏览器开 `http://localhost:8080/hello`，看到 `Hello, Spring Boot!` 就成了。

## 4. 启动、热部署、测试、部署

### 启动的三种姿势

| 姿势 | 操作 |
|---|---|
| IDEA | 点 `DemoApplication` 旁边的绿色三角 |
| Maven 命令行 | `mvn spring-boot:run` |
| 打包后 | `mvn package`，然后 `java -jar target/demo-0.0.1-SNAPSHOT.jar` |

### 热部署（改完代码自动重启）

省得来回手动停启：

1. `pom.xml` 加依赖：
   ```xml
   <dependency>
       <groupId>org.springframework.boot</groupId>
       <artifactId>spring-boot-devtools</artifactId>
   </dependency>
   ```
2. IDEA 勾上 `Settings → Build, Execution, Deployment → Compiler → Build project automatically`
3. 改代码保存即重启

### 单元测试

`src/test/java` 目录是测试代码，模板已经写好一个能跑的：

```java
package com.example.demo;

import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;

@SpringBootTest
class DemoApplicationTests {
    @Test
    void contextLoads() {
        // 这个方法故意空着
        // 只要 Spring 容器能正常启动,测试就通过
    }
}
```

### 部署：JAR vs WAR

| 格式 | 怎么打 | 怎么跑 | 适合 |
|---|---|---|---|
| **JAR**（推荐）| `mvn package` | `java -jar xxx.jar` | 99% 的场景 |
| **WAR** | 改 `pom.xml` 打包方式 | 丢到外部 Tomcat | 老的运维体系 |

JAR 部署一定要会，WAR 知道有这回事就行。

## 5. starter 是个啥

`starter` 是 Spring Boot 的"依赖打包"——加一个名字就把一整套技术都拉进来。

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-web</artifactId>
</dependency>
```

这一行只引了 `spring-boot-starter-web` 一个东西，但它**传递依赖**地把 Spring MVC、Tomcat、Jackson（JSON 解析）都拉进来了。你不用手写一堆 `<dependency>`。

最常见的几个：

| starter | 引入什么 |
|---|---|
| `spring-boot-starter-web` | Spring MVC + Tomcat + JSON |
| `spring-boot-starter-data-jpa` | JPA + Hibernate |
| `spring-boot-starter-test` | JUnit + Mockito |
| `spring-boot-starter-thymeleaf` | Thymeleaf（ch4 讲） |

## 6. 启动时到底干了啥

`SpringApplication.run(...)` 跑起来后大致按这个顺序：

```
1. 创建 SpringApplication 实例
2. 读取 application.properties / application.yml
3. 从 @SpringBootApplication 所在包开始向下扫
4. 自动装配:看 classpath 有哪些 starter,自动配置对应的 Bean
5. 启动内嵌 Tomcat
6. 监听 8080 端口,开始接请求
```

