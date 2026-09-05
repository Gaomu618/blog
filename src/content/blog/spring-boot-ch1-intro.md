---
title: Spring Boot 入门:从装环境到第一个接口跑起来
description: 第 1 章学习笔记。例子驱动,先跑通一个 Hello World,再回头讲为什么能跑。
pubDate: 2026-09-05
tags: [Spring Boot, Java]
---

> **读这章前**:请先完成 [ch0 前置知识](./posts/spring-boot-ch0-prerequisites/) 里的 8 项检查。

这章用**例子驱动**写——不先讲概念,先动手把一个项目跑起来,看到效果再回头讲为什么。

## 1. 先跑通一个 Hello World

**目标**:5 步内让浏览器访问 `http://localhost:8080/hello` 看到 `Hello, Spring Boot!`

### 第 1 步:装环境

Spring Boot 3.x 要求 **JDK 17**。装好这三个:

| 工具 | 装好后验证 |
|---|---|
| JDK 17 | `java -version` 输出 17.x |
| Maven 3.6+ | `mvn -version` 输出 3.6+ |
| IntelliJ IDEA 社区版 | 装好即可,装中文语言包也行 |

### 第 2 步:在网页上生成项目

打开 https://start.spring.io/ ,**按图填**:

```
Project:     Maven
Language:    Java
Spring Boot: 3.x (最新稳定版)
Group:       com.example
Artifact:    demo
Java:        17

Dependencies (点 Add Dependencies):
  + Spring Web
```

点 **Generate** 下载 `demo.zip`,解压,IDEA 打开。

> **这段操作想干什么**:Spring Initializr 是一个"项目生成器",你告诉它要啥(语言/版本/依赖),它帮你拼好 `pom.xml` 和主程序文件——不用从零写。

### 第 3 步:看自动生成的项目结构

IDEA 打开后,左侧文件树长这样:

```
demo/
├── pom.xml                ← 依赖清单(Maven 看这个知道要下啥)
├── src/
│   ├── main/
│   │   ├── java/com/example/demo/
│   │   │   └── DemoApplication.java   ← 主程序入口
│   │   └── resources/
│   │       └── application.properties ← 配置(现在为空)
│   └── test/
│       └── java/com/example/demo/
│           └── DemoApplicationTests.java
```

**`pom.xml` 现在有什么(节选)**:

```xml
<dependencies>
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-web</artifactId>
    </dependency>
    <!-- 还有 starter-test,这个后面讲测试用 -->
</dependencies>
```

**关键行**:
- `spring-boot-starter-web` — 一行依赖拉了一整套 Web 开发的东西(Spring MVC、Tomcat、JSON)

> **这段 XML 想干什么**:告诉 Maven "我这个项目要用 Spring Boot 的 Web 功能",Maven 会自动下载并管理所有相关 jar 包。

### 第 4 步:看主程序

`src/main/java/com/example/demo/DemoApplication.java`:

```java
package com.example.demo;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication   // ← 标记这是 Spring Boot 应用入口
public class DemoApplication {
    public static void main(String[] args) {
        // ↓ 启动 Spring 容器 + 内嵌 Tomcat + 监听 8080 端口
        SpringApplication.run(DemoApplication.class, args);
    }
}
```

**关键行**:
- `@SpringBootApplication` — 这一行等于三个注解:
  - `@Configuration` 标记"这是个配置类"
  - `@EnableAutoConfiguration` 启用自动装配(根据依赖自动配 Bean)
  - `@ComponentScan` 自动扫当前包及其子包下的 Spring 组件
- `SpringApplication.run(...)` — 真正干活的,启动整个 Spring 容器

> **这段代码想干什么**:`main` 是 Java 程序的标准入口,加了这行注解+调用,启动时 Spring 容器就会跑起来,Tomcat 也会跟着起。

### 第 5 步:写第一个接口

在 `com.example.demo` 包下新建 `HelloController.java`:

```java
package com.example.demo;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController   // ← 标记"这是个 REST 控制器"
public class HelloController {

    // ↓ 访问 GET /hello 时,执行这个方法
    @GetMapping("/hello")
    public String hello() {
        return "Hello, Spring Boot!";
    }
}
```

**关键行**:
- `@RestController` — 等于 `@Controller` + `@ResponseBody`,意思是"返回的数据直接当 HTTP 响应体,不要找视图模板"
- `@GetMapping("/hello")` — 标记"HTTP GET 方法,路径是 /hello",Spring 看到这个就把请求路由到这个方法

> **这段代码想干什么**:给前端一个能访问的接口。运行后,前端(或浏览器)访问 `/hello`,会得到字符串 `Hello, Spring Boot!`。

### 第 6 步:跑起来

IDEA 里:
- 找到 `DemoApplication.java` 文件
- 类名旁边的 **绿色三角 ▶** → 点它
- 或右键 → Run 'DemoApplication'

或者命令行:
```bash
mvn spring-boot:run
```

**跑起来你会看到**:

```
  .   ____          _            __ _ _
 /\\ / ___'_ __ _ _(_)_ __  __ _ \ \ \ \
( ( )\___ | '_ | '_| | '_ \/ _` | \ \ \ \
 \\/  ___)| |_)| | | | | || (_| |  ) ) ) )
  '  |____| .__|_| |_|_| |_\__, | / / / /
 =========|_|==============|___/=/_/_/_/

:: Spring Boot ::               (v3.x.x)

... 一堆启动日志 ...
... Tomcat started on port 8080 (http) ...
... Started DemoApplication in 2.34 seconds ...
```

**打开浏览器**,访问 `http://localhost:8080/hello` —— 看到 `Hello, Spring Boot!` 就成了。

> **运行后会看到**:
> - 控制台打印 Spring Boot 启动 banner
> - 几秒后看到 "Tomcat started on port 8080"
> - 浏览器里显示 "Hello, Spring Boot!"
> - 控制台还能看到 `DispatcherServlet` 等日志

## 2. 跑通了,现在讲为什么能跑

前面 6 步你只跟着做了,可能很多步骤"不知道为什么"。这一节回头讲。

### 为什么 `pom.xml` 加一行就能用 Web?

`spring-boot-starter-web` 是一个 **"启动器"(starter)**,它**传递依赖**地把一整套东西拉进来:

```
spring-boot-starter-web
  ├── Spring MVC          (处理 HTTP 请求的框架)
  ├── spring-boot-starter-tomcat  (内嵌 Tomcat)
  ├── spring-boot-starter-json    (JSON 处理)
  └── 等等十几个 jar 包
```

你只写一行 `<dependency>`,Maven 帮你**自动**把所有需要的 jar 都拉下来。这就是 starter 的威力。

### 为什么 `@RestController` 加 `@GetMapping` 就能用?

Spring Boot 启动时干了几件事(简化版):

```
1. 读 pom.xml,知道项目里有 spring-boot-starter-web
2. 启动"自动装配",根据这个 starter 把 Spring MVC、Tomcat 等 Bean 注册到容器
3. 启动内嵌 Tomcat,监听 8080 端口
4. 扫到 @RestController 标记的 HelloController
5. 看到 @GetMapping("/hello"),把"GET /hello"这个请求路由到 hello() 方法
6. hello() 返回的字符串,作为 HTTP 响应体返回给浏览器
```

**所以你写两行注解,Spring 帮你把"接请求 → 找方法 → 调方法 → 返回响应"全做了**。

### 为什么 main 方法里那行能启动整个 Spring?

```java
SpringApplication.run(DemoApplication.class, args);
```

这一行**做了 4 件事**:
1. 创建 `SpringApplication` 实例
2. 读取 `application.properties` 配置
3. 启动 Spring 容器(创建所有 Bean)
4. **启动内嵌 Tomcat**,开始监听端口

这就是 Spring Boot 跟传统 Spring 最大的区别——**自带 Tomcat,不用部署到外部**。

## 3. 几个常用动作

### 热部署:改代码不用手动重启

新手最讨厌的事情之一是"改一行代码 → 停项目 → 重启 → 等 5 秒",热部署让你**保存就自动重启**。

**步骤**:

1. `pom.xml` 加依赖:
   ```xml
   <dependency>
       <groupId>org.springframework.boot</groupId>
       <artifactId>spring-boot-devtools</artifactId>
   </dependency>
   ```

2. IDEA 设置(关键,容易漏):
   - `Settings → Build, Execution, Deployment → Compiler`
   - 勾上 **Build project automatically**

3. 改完代码 **Ctrl+S 保存**,项目自动重启,浏览器刷新就能看到新效果。

> **这段配置想干什么**:devtools 监听文件变化,触发"项目重启"——但只重启你的代码,不重启 Tomcat,所以**比手动重启快得多**。

### 单元测试:验证代码逻辑

`src/test/java/.../DemoApplicationTests.java` 模板已经写好一个能跑的测试:

```java
package com.example.demo;

import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;

@SpringBootTest   // ← 标记"这是个 Spring Boot 集成测试"
class DemoApplicationTests {
    @Test
    void contextLoads() {
        // 这个方法故意空着
        // 只要 Spring 容器能正常启动,测试就算通过
    }
}
```

**关键行**:
- `@SpringBootTest` — 启动一个完整的 Spring 容器跑测试
- `@Test` — JUnit 标记这是个测试方法

**怎么跑**:
- IDEA 里:点方法名旁边绿色三角
- 命令行:`mvn test`

> **这段代码想干什么**:`contextLoads()` 是 Spring Initializr 默认给的"烟雾测试",验证整个 Spring 容器能正常启动——如果连启动都启动不了,后面的业务测试都不用跑了。

## 4. 部署:把项目扔到服务器上

### 打包成 JAR(推荐,99% 用这个)

```bash
mvn package
```

跑完会生成 `target/demo-0.0.1-SNAPSHOT.jar`。

**运行这个 JAR**:

```bash
java -jar target/demo-0.0.1-SNAPSHOT.jar
```

**关键点**:`-jar` 不是普通的 jar,Spring Boot 用 spring-boot-maven-plugin 把所有依赖都打进去了——所以这个 jar 包含了一个完整的运行环境,加上**内置的 Tomcat**,直接 `java -jar` 就能跑,**不需要任何外部服务器**。

### 改端口(默认 8080)

`application.properties` 加一行:

```properties
server.port=9090
```

> **运行后会看到**:`Tomcat started on port 9090`

## 5. 常见踩坑

**踩坑 1:启动报"找不到主类"**
原因:不是用 `mvn spring-boot:run` 启动,而是直接 IDEA 点 `main` 方法旁边的绿色三角,这时 IDEA 用默认的 JRE,可能没装 JDK 17。
解决:确认 `File → Project Structure → SDKs` 是 JDK 17。

**踩坑 2:端口被占用**
报错:`Web server failed to start. Port 8080 was already in use.`
解决:改端口(`server.port=9090`),或者杀掉占用 8080 的进程。

**踩坑 3:`@Autowired` 标红但能跑**
原因:IDEA 没识别 Spring 的 Bean,不是真错。
解决:`File → Settings → Inspections → Spring Core → Code → Autowiring for bean class` 改成 Warning 而不是 Error。

## 6. 一句话总结这章

**你学的是"怎么用 Spring Boot 把一个 Java Web 项目跑起来"**——前面 6 步让你先看到效果,中间 2 节告诉你为什么,后面 3 节是常用操作。下一章学"怎么把配置从代码里抽出来"。

学完这章你应该能:
- [ ] 从零创建一个 Spring Boot 项目
- [ ] 写一个 `@RestController` 返回 JSON 或字符串
- [ ] 用 `mvn spring-boot:run` 启动项目
- [ ] 用 `java -jar` 跑打好的 jar
- [ ] 解释 `@SpringBootApplication` 等于哪三个注解
