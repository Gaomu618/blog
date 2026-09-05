---
title: Spring Boot Web:三大组件注册 + MVC 自定义 + 文件上传 + 异常处理
description: 第 3 章学习笔记。例子驱动,先做一个"过滤所有请求"的小例子,再展开讲三大组件、自定义 MVC、文件上传、异常处理。
pubDate: 2026-09-05
tags: [Spring Boot, Java]
---

> **读这章前**:ch1 + ch2 跑通,有 Java 基础。

这章要解决的 4 个 Web 开发常见问题:
1. 想拦截所有请求打日志 → **三大组件之 Filter**
2. 想在 Spring 启动时配置静态资源、拦截器 → **自定义 MVC**
3. 想实现文件上传 → **MultipartFile**
4. 某个 Controller 抛了异常,想统一处理 → **`@ControllerAdvice`**

下面用**例子驱动**,先动手做再讲原理。

## 1. 先做一个小例子:过滤所有请求打日志

**目标**:所有请求过来时,控制台打印"请求开始 + 路径 + 耗时"。

### 第 1 步:写一个 Filter

新建 `src/main/java/com/example/demo/web/LoggingFilter.java`:

```java
package com.example.demo.web;

import jakarta.servlet.*;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.stereotype.Component;

import java.io.IOException;

@Component   // ← 让 Spring 容器管理这个类
public class LoggingFilter implements Filter {

    @Override
    public void doFilter(ServletRequest req, ServletResponse res, FilterChain chain)
            throws IOException, ServletException {
        // ↓ 1. 请求进来:记个时间
        long start = System.currentTimeMillis();
        HttpServletRequest httpReq = (HttpServletRequest) req;

        // ↓ 2. 打印请求信息
        System.out.println("→ 请求开始: " + httpReq.getRequestURI());

        // ↓ 3. 放行,继续执行后面的过滤器和 Controller
        chain.doFilter(req, res);

        // ↓ 4. 请求结束:算耗时,打印
        long cost = System.currentTimeMillis() - start;
        System.out.println("← 请求结束: " + cost + "ms");
    }
}
```

**关键行**:
- `@Component` 告诉 Spring "这是个组件,启动时把它注册到容器"
- `implements Filter` 是 Java Web 的标准接口,实现它就是一个"过滤器"
- `chain.doFilter(req, res)` —— **过滤器最关键的一行**,不调用的话请求会卡在这里走不下去
- `doFilter` 之前的代码 = 请求前,之后的代码 = 请求后(利用这个特性打日志)

> **这段代码想干什么**:在所有 HTTP 请求进出时插一脚——进来时打开始日志,出去时算耗时。**不写这一行 `chain.doFilter()`,整个网站会卡死,所有请求都进不到 Controller**——这个错新手常犯。
>
> **跑起来看啥**:启动后访问任意接口(比如 `/hello`),控制台会打印:
> ```
> → 请求开始: /hello
> ← 请求结束: 2ms
> ```

### 第 2 步:让 Spring 扫到 `@Component`

确保你的 `DemoApplication` 类在**最外层包**(默认是 `com.example.demo`),这样 Spring 默认会扫它和它的所有子包:

```
com.example.demo/
├── DemoApplication.java       ← 主类(扫包的起点)
├── controller/
├── service/
└── web/
    └── LoggingFilter.java      ← @Component,会被自动注册
```

**踩坑提醒**:`LoggingFilter` 跟 `DemoApplication` 在**同一个包或其子包**才会被扫到。如果 `LoggingFilter` 在 `com.other.demo.web`,需要主类加 `@ComponentScan("com.other.demo")` 显式指定。

### 第 3 步:用 `FilterRegistrationBean` 更精细控制(可选,看需求)

**问题**:`@Component` 默认拦截所有 URL (`/*`),但你可能只想拦 `/api/*`。

**解法**:不用 `@Component`,改用 `FilterRegistrationBean`:

```java
package com.example.demo.config;

import com.example.demo.web.LoggingFilter;
import org.springframework.boot.web.servlet.FilterRegistrationBean;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration   // ← 标记这是个配置类
public class FilterConfig {

    @Bean   // ← 把这个方法返回的对象注册成 Spring Bean
    public FilterRegistrationBean<LoggingFilter> loggingFilter() {
        FilterRegistrationBean<LoggingFilter> reg = new FilterRegistrationBean<>();
        reg.setFilter(new LoggingFilter());        // 用哪个 Filter
        reg.addUrlPatterns("/api/*");              // 只拦 /api/ 开头的
        reg.setOrder(1);                           // 多个 Filter 时的顺序,数字小的先执行
        reg.setName("loggingFilter");
        return reg;
    }
}
```

**关键行**:
- `addUrlPatterns("/api/*")` —— 限定拦截路径,**只有访问 `/api/xxx` 才会触发日志**
- `setOrder(1)` —— 多个 Filter 时的执行顺序,数字小的先执行

> **这段代码想干什么**:用 Java 配置的方式注册 Filter,能精确控制拦截哪些 URL。`@Component` 方式是"全部拦",这种方式是"按需拦"。

## 2. 三大组件到底是个啥

刚才写的 Filter 属于"Java Web 三大组件"之一,完整列表:

| 组件 | 作用 | 实际场景 |
|---|---|---|
| **Servlet** | 处理 HTTP 请求 | 现在的 `@Controller` 就是它的高级版 |
| **Filter** | 拦截请求/响应 | 刚才演示的:日志、登录校验、字符编码 |
| **Listener** | 监听 Web 生命周期事件 | 统计在线人数、应用启动时加载字典 |

**Filter 注册的两种方式对比**:

| 方式 | 优点 | 缺点 |
|---|---|---|
| `@Component` 标在 Filter 类上 | 简单 | 默认拦所有 URL,改不了顺序 |
| `FilterRegistrationBean` | 能控制 URL 范围、顺序、初始化参数 | 代码多一点 |

**Servlet 怎么注册?**——基本用不到了,因为 `@Controller` 已经是更高层的封装。**Listener 也基本被 `@PostConstruct` 等注解替代了**。

所以三大组件里**重点学 Filter**,Servlet 和 Listener 知道有这回事就行。

## 3. 自定义 Spring MVC

**问题**:Spring Boot 默认帮你配了一堆 MVC 设置(静态资源、视图解析、消息转换),但你想改某一项怎么办?

**答**:写一个 `WebMvcConfigurer` 实现类。

### 例子 1:加一个静态资源目录

**场景**:你想让 `D:/uploaded-files/` 里的图片能通过 `http://localhost:8080/files/xxx.jpg` 访问。

新建 `src/main/java/com/example/demo/config/MyMvcConfig.java`:

```java
package com.example.demo.config;

import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.ResourceHandlerRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

@Configuration   // ← 标记这是个配置类
public class MyMvcConfig implements WebMvcConfigurer {

    // ↓ 添加自定义静态资源映射
    @Override
    public void addResourceHandlers(ResourceHandlerRegistry registry) {
        registry.addResourceHandler("/files/**")              // 浏览器访问 /files/xxx
                .addResourceLocations("file:D:/uploaded-files/");  // 实际去找 D:/uploaded-files/xxx
    }
}
```

**关键行**:
- `addResourceHandler("/files/**")` —— 浏览器访问这个 URL 模式
- `addResourceLocations("file:D:/uploaded-files/")` —— 实际去硬盘哪个目录找
- 三个 `/` 是**任意层级**:`/files/a/b/c.jpg` 都能匹配

> **这段代码想干什么**:告诉 Spring Boot,"`/files/xxx` 不去默认静态资源目录找,去我指定的 `D:/uploaded-files/` 找"。常用于让用户能访问上传的文件。
>
> **跑起来看啥**:`D:/uploaded-files/photo.jpg` 通过 `http://localhost:8080/files/photo.jpg` 访问到。

### 例子 2:拦截器——登录校验

**场景**:除了 `/login` 之外,所有请求都要登录才能访问。

**第 1 步:写拦截器**

新建 `src/main/java/com/example/demo/web/LoginInterceptor.java`:

```java
package com.example.demo.web;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.servlet.HandlerInterceptor;

public class LoginInterceptor implements HandlerInterceptor {

    // ↓ Controller 执行前调用
    @Override
    public boolean preHandle(HttpServletRequest req, HttpServletResponse res, Object handler) throws Exception {
        HttpSession session = req.getSession();
        Object user = session.getAttribute("user");

        if (user == null) {
            // 没登录,踢去登录页
            res.sendRedirect("/login");
            return false;   // ← 返回 false 表示"拦截",后面的 Controller 不执行
        }
        return true;        // ← 返回 true 表示"放行"
    }
}
```

**关键行**:
- `preHandle` 是"请求进来 → Controller 之前"调用,**最常用的回调**
- 返回 `true` = 放行,`false` = 拦截
- 在这里能拿到 `HttpServletRequest`,所以能查 session、读 cookie

**第 2 步:注册到 MVC 配置**

在 `MyMvcConfig` 里加:

```java
@Override
public void addInterceptors(InterceptorRegistry registry) {
    registry.addInterceptor(new LoginInterceptor())   // 用哪个拦截器
            .addPathPatterns("/**")                   // 拦截哪些路径(全部)
            .excludePathPatterns("/login", "/css/**", "/js/**");  // 放行哪些(白名单)
}
```

**关键行**:
- `addPathPatterns("/**")` —— 拦截所有
- `excludePathPatterns("/login", ...)` —— 放行登录页、静态资源
- 白名单里的路径**不会触发拦截器**

> **这段代码想干什么**:拦截所有未登录的请求,踢回登录页。**白名单**(登录、静态资源)不拦。

**踩坑提醒**:
- 静态资源(css/js/图片)**通常要放白名单**,不然用户访问任何页面都先被踢回登录页
- 拦截器拿不到 HandlerMethod 是哪个具体方法(不像 AOP 那样细)

### 例子 3:ViewController(URL 直接跳页面)

**场景**:访问 `/` 直接跳到 `home.html`,不用写 Controller。

在 `MyMvcConfig` 里加:

```java
@Override
public void addViewControllers(ViewControllerRegistry registry) {
    registry.addViewController("/").setViewName("home");   // 访问 / 渲染 home.html
    registry.addViewController("/about").setViewName("about");
}
```

> **这段代码想干什么**:给纯跳转的 URL 配个"快捷方式",不用每个都写一个空 Controller。`/` 配 `home` 模板这种简单跳转常用。

### `WebMvcConfigurer` 三个常用方法速查

| 方法 | 干啥 | 例子 |
|---|---|---|
| `addResourceHandlers` | 静态资源映射 | 自定义图片访问路径 |
| `addInterceptors` | 注册拦截器 | 登录校验、权限控制 |
| `addViewControllers` | 简单 URL 跳转 | 根路径跳首页 |

## 4. 文件上传

### 第 1 步:配置 application.yml

```yaml
spring:
  servlet:
    multipart:
      max-file-size: 10MB         # 单个文件最大
      max-request-size: 50MB      # 整个请求最大(多文件上传时)
```

**关键行**:
- `max-file-size` — 单个文件超过 10MB 直接报异常
- `max-request-size` — 整个请求体(所有文件加起来)超过 50MB 报错

> **这段配置想干什么**:限制上传文件大小,避免有人上传超大文件把服务器搞崩。

### 第 2 步:写 Controller

新建 `src/main/java/com/example/demo/web/UploadController.java`:

```java
package com.example.demo.web;

import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.io.File;
import java.io.IOException;

@RestController
public class UploadController {

    @PostMapping("/upload")                                          // ↓ 接收文件
    public String upload(@RequestParam("file") MultipartFile file) throws IOException {
        if (file.isEmpty()) return "失败:文件为空";

        // ↓ 取原文件名,拼出保存路径
        String filename = file.getOriginalFilename();
        File dest = new File("D:/uploads/" + filename);

        // ↓ 把上传的文件写到目标位置
        file.transferTo(dest);

        return "上传成功:" + filename + " (" + file.getSize() + " 字节)";
    }
}
```

**关键行**:
- `@RequestParam("file") MultipartFile file` —— 把表单里的 `file` 字段绑到 `MultipartFile` 对象
- `file.transferTo(dest)` —— 把上传的文件保存到目标 File
- `file.isEmpty()` —— 判断文件是否为空(防用户没选文件就提交)
- `getOriginalFilename()` —— 取客户端上传的原文件名(可能含中文)

> **这段代码想干什么**:接收前端上传的文件,保存到 `D:/uploads/` 目录。运行后用 Postman 或 form 表单测试。
>
> **跑起来看啥**:用 Postman 发个 POST 到 `/upload`,带文件,会返回"上传成功:xxx.jpg (12345 字节)"。

### 第 3 步:前端 form

```html
<form action="/upload" method="post" enctype="multipart/form-data">
    <input type="file" name="file" />
    <button type="submit">上传</button>
</form>
```

**关键**:
- `enctype="multipart/form-data"` **必须有**——告诉浏览器"我要发文件",不是普通表单
- `name="file"` 要跟后端 `@RequestParam("file")` 一致

### `MultipartFile` 常用方法

```java
file.getOriginalFilename();   // 原文件名,如 "photo.jpg"
file.getSize();               // 大小(字节)
file.getContentType();        // MIME 类型,如 "image/jpeg"
file.getBytes();              // 字节数组(小文件用,大文件会 OOM)
file.transferTo(dest);        // 保存到目标 File(推荐,流式,不占内存)
file.isEmpty();               // 是否为空
```

## 5. 异常处理(所有 Spring Boot 项目都用)

**问题**:Controller 里抛了异常,默认会返回一堆难看的错误页或 JSON。**实际项目要统一格式**。

### Spring Boot 默认行为

如果不处理,抛了异常会:
- 浏览器访问:返回一个难看的 Whitelabel Error Page
- 接口请求:返回一段 JSON 包含错误信息和时间戳

**这两种都不友好**——前端拿到还要自己再解析。

### 解决办法:全局异常处理

新建 `src/main/java/com/example/demo/exception/GlobalExceptionHandler.java`:

```java
package com.example.demo.exception;

import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.Map;

@ControllerAdvice   // ← 标记"这是全局增强 Controller"
public class GlobalExceptionHandler {

    // ↓ 拦截所有 Exception
    @ExceptionHandler(Exception.class)
    @ResponseBody
    public Map<String, Object> handleException(Exception e) {
        Map<String, Object> result = new HashMap<>();
        result.put("code", 500);
        result.put("msg", "服务器开小差:" + e.getMessage());
        return result;
    }
}
```

**关键行**:
- `@ControllerAdvice` 标在类上 —— "这是个全局异常处理器"
- `@ExceptionHandler(Exception.class)` 标在方法上 —— "匹配 Exception 类型的异常"
- `@ResponseBody` —— 异常处理结果当 JSON 返回(不加的话会去找视图)

> **这段代码想干什么**:把项目里**所有 Controller 抛的 Exception** 接住,转成统一格式 `{"code": 500, "msg": "..."}` 返回给前端。**前端拿到一致的格式**,不用每个 Controller 自己处理异常。

**专门处理业务异常**(推荐):

```java
// 自定义业务异常
public class BusinessException extends RuntimeException {
    private int code;
    public BusinessException(int code, String message) {
        super(message);
        this.code = code;
    }
    public int getCode() { return code; }
}

// 在 GlobalExceptionHandler 里加方法
@ExceptionHandler(BusinessException.class)
@ResponseBody
public Map<String, Object> handleBusiness(BusinessException e) {
    Map<String, Object> result = new HashMap<>();
    result.put("code", e.getCode());
    result.put("msg", e.getMessage());
    return result;
}
```

**Controller 里抛业务异常**:

```java
@GetMapping("/user/{id}")
public User getUser(@PathVariable int id) {
    User user = userService.findById(id);
    if (user == null) {
        throw new BusinessException(404, "用户不存在");  // ← 直接抛,不用 try-catch
    }
    return user;
}
```

**关键行**:
- `throw new BusinessException(404, "...")` —— 业务上"找不到"的异常,直接抛
- GlobalExceptionHandler 会接住,转成 `{"code": 404, "msg": "用户不存在"}` 返回
- **业务代码不用 try-catch**,只管"正常逻辑",异常统一交给全局处理器

## 6. Filter vs Interceptor 选哪个

经常被问,简单对比:

| 维度 | Filter | Interceptor |
|---|---|---|
| 来自哪个规范 | Servlet 规范(所有 Web 框架) | Spring MVC 独有 |
| 触发时机 | DispatcherServlet **之前** | DispatcherServlet **之后**、Controller **之前** |
| 拿不拿得到 HandlerMethod | 拿不到 | 能拿到(知道是哪个 Controller 哪个方法) |
| 适合 | 字符编码、CORS、全局压缩 | 登录校验、权限控制 |

**实战建议**:
- 跟 Spring MVC 没关系的(比如改请求/响应编码)→ Filter
- 跟业务权限相关的(比如"只有 admin 才能调 /admin/xxx")→ Interceptor

## 7. 常见踩坑

**踩坑 1:Filter 没生效**
原因:Filter 类不在主类同包或子包,没被 `@ComponentScan` 扫到。
解决:把 Filter 移到主类同包,或加 `@ComponentScan("你的包")`。

**踩坑 2:`@ControllerAdvice` 不生效**
原因:没被 Spring 扫到(类不在扫描路径),或者 `@ExceptionHandler` 的异常类型写错了。
解决:确认类在主类同包,异常类用 `Exception.class` 测试。

**踩坑 3:文件上传报"the field exceeds its maximum permitted size"**
原因:文件超过 `max-file-size` 配置。
解决:改大 `max-file-size`,或前端压缩文件。

**踩坑 4:拦截器拦截了静态资源,所有页面打不开**
原因:拦截器没加 `excludePathPatterns` 放行 css/js/图片。
解决:加白名单 `excludePathPatterns("/css/**", "/js/**", "/images/**", "/favicon.ico")`。

## 8. 一句话总结这章

**学的是"在 Web 请求的前后插各种逻辑"**——Filter 拦请求、Interceptor 验登录、WebMvcConfigurer 配路由、文件上传接文件、全局异常统一处理。**这套组合拳是所有 Spring Boot 项目的标配**。

学完你应该能:
- [ ] 写一个 Filter 打印所有请求日志
- [ ] 写一个 Interceptor 做登录校验
- [ ] 用 WebMvcConfigurer 配置静态资源映射
- [ ] 实现文件上传 Controller
- [ ] 用 @ControllerAdvice 全局处理异常
