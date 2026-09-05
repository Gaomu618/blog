---
title: Spring Boot Web：注册三大组件、自定义 MVC、文件上传、异常处理
description: 第 3 章学习笔记。怎么把 Servlet/Filter/Listener 装进 Spring 容器,怎么扩展 MVC,文件上传怎么写,异常怎么统一处理。
pubDate: 2026-09-05
tags: [Spring Boot, Java]
---

这一章讲 Spring Boot 怎么跟"传统 Java Web 那一套"打交道。传统 Java Web 有三大组件：**Servlet、Filter、Listener**，Spring Boot 默认不包含它们，需要手动注册。

## 1. Java Web 三大组件

| 组件 | 干啥 | 典型场景 |
|---|---|---|
| **Servlet** | 处理 HTTP 请求，返回响应 | 业务接口（现在一般用 `@Controller` 替代，但概念一样）|
| **Filter** | 拦截请求/响应，可以提前 reject | 登录校验、字符编码、跨域处理 |
| **Listener** | 监听 Web 生命周期事件 | 统计在线人数、应用启动时加载字典 |

Spring Boot 项目里，**Filter 和 Listener 用得相对多**（比如全局登录拦截），Servlet 几乎被 `@Controller` 替代了。

## 2. 注册三大组件的 3 种方式

### 方式 1：注解方式（最简单，推荐）

在 Servlet 上加 `@WebServlet` / `@WebFilter` / `@WebListener`，主类加 `@ServletComponentScan`：

```java
// 自定义 Filter:所有请求都要过这里
@WebFilter("/*")
public class LoggingFilter implements Filter {
    @Override
    public void doFilter(ServletRequest req, ServletResponse res, FilterChain chain)
            throws IOException, ServletException {
        long start = System.currentTimeMillis();
        HttpServletRequest httpReq = (HttpServletRequest) req;
        System.out.println("请求开始: " + httpReq.getRequestURI());
        chain.doFilter(req, res);   // 放行,继续执行后面的过滤器和 Controller
        long cost = System.currentTimeMillis() - start;
        System.out.println("请求结束: " + cost + "ms");
    }
}
```

主类加扫描：

```java
@ServletComponentScan   // 扫描 @WebServlet / @WebFilter / @WebListener
@SpringBootApplication
public class DemoApplication { }
```

这样 `LoggingFilter` 自动生效。**注意：Filter 默认会被 Spring 容器管理多次（因为它实现了 `jakarta.servlet.Filter`），用 `FilterRegistrationBean` 可以更精确控制**。

### 方式 2：`RegistrationBean`（更灵活）

能精确控制 URL 映射、初始化参数、顺序：

```java
@Configuration
public class FilterConfig {

    @Bean
    public FilterRegistrationBean<LoggingFilter> loggingFilter() {
        FilterRegistrationBean<LoggingFilter> reg = new FilterRegistrationBean<>();
        reg.setFilter(new LoggingFilter());
        reg.addUrlPatterns("/*");        // 拦截所有
        reg.setOrder(1);                 // 多个 Filter 时的执行顺序,数字小的先执行
        reg.setName("loggingFilter");
        return reg;
    }
}
```

**什么时候用方式 2**：需要给 Filter 配 URL patterns、初始化参数、或者要控制多个 Filter 的执行顺序时。

### 方式 3：直接 `@Bean`（最少见）

`Servlet` 还能这样注册（但很少用）：

```java
@Bean
public ServletRegistrationBean<MyServlet> myServlet() {
    return new ServletRegistrationBean<>(new MyServlet(), "/my-servlet");
}
```

实际项目几乎用不到，因为都写 `@Controller` 了。

## 3. Spring MVC 自动配了啥

Spring Boot 启动时偷偷帮你配了一堆 MVC 相关 Bean，**日常开发 90% 不需要动**：

- 内容协商视图解析器（根据请求头返回 HTML / JSON）
- 静态资源处理器（`/static/`、`/public/`、`/resources/`、`/META-INF/resources/` 下的文件能直接访问）
- 静态首页（`static/index.html` 自动作为 `/` 的响应）
- `Converter` / `Formatter`（类型转换，比如 String 转 Date）
- `HttpMessageConverter`（对象和 JSON 互转）

举例：放一个文件在 `src/main/resources/static/hello.txt`，启动后浏览器直接访问 `http://localhost:8080/hello.txt` 就能下载。

## 4. 自定义 Spring MVC

要改默认行为，写一个 `WebMvcConfigurer` 实现类：

```java
package com.example.demo.config;

import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.*;

@Configuration
public class MyMvcConfig implements WebMvcConfigurer {

    // 1. 静态资源映射
    @Override
    public void addResourceHandlers(ResourceHandlerRegistry registry) {
        registry.addResourceHandler("/my/**")
                .addResourceLocations("classpath:/my-static/");
        // 访问 /my/foo.jpg 会去找 src/main/resources/my-static/foo.jpg
    }

    // 2. 视图控制器(URL 直接跳页面,不用写 Controller)
    @Override
    public void addViewControllers(ViewControllerRegistry registry) {
        registry.addViewController("/").setViewName("index");
        // 访问 / 直接渲染 templates/index.html
    }

    // 3. 拦截器
    @Override
    public void addInterceptors(InterceptorRegistry registry) {
        registry.addInterceptor(new LoginInterceptor())
                .addPathPatterns("/**")           // 拦截所有
                .excludePathPatterns("/login", "/css/**", "/js/**");  // 放行白名单
    }
}
```

### 登录拦截器完整实现

拦截器跟 Filter 有点像，但**拦截器是 Spring MVC 自己的**，能拿到 HandlerMethod（知道是哪个 Controller 哪个方法），Filter 拿不到：

```java
package com.example.demo.interceptor;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.servlet.HandlerInterceptor;

public class LoginInterceptor implements HandlerInterceptor {

    @Override
    public boolean preHandle(HttpServletRequest req, HttpServletResponse res, Object handler) throws Exception {
        // Controller 方法执行前
        HttpSession session = req.getSession();
        Object user = session.getAttribute("user");
        if (user == null) {
            res.sendRedirect("/login");   // 没登录,踢去登录页
            return false;                  // 返回 false 表示拦截,不继续执行
        }
        return true;                       // 返回 true 表示放行
    }

    @Override
    public void postHandle(HttpServletRequest req, HttpServletResponse res, Object handler, org.springframework.web.servlet.ModelAndView mv) throws Exception {
        // Controller 方法执行后,视图渲染前(很少用)
    }

    @Override
    public void afterCompletion(HttpServletRequest req, HttpServletResponse res, Object handler, Exception ex) throws Exception {
        // 视图渲染完成后(常用于清理资源、记录日志)
    }
}
```

**Filter vs Interceptor 怎么选**：

| 维度 | Filter | Interceptor |
|---|---|---|
| 规范 | Servlet 规范,所有 Web 框架都有 | Spring MVC 独有 |
| 触发时机 | 在 DispatcherServlet 之前 | 在 DispatcherServlet 之后、Controller 之前 |
| 能不能拿到 HandlerMethod | 不能 | 能 |
| 适合 | 字符编码、CORS、全局压缩 | 登录校验、权限控制 |

## 5. 文件上传

### 配置文件大小限制

**application.yml**

```yaml
spring:
  servlet:
    multipart:
      max-file-size: 10MB         # 单个文件最大
      max-request-size: 50MB      # 整个请求最大(多文件时)
```

### Controller

```java
@PostMapping("/upload")
public String upload(@RequestParam("file") MultipartFile file) throws Exception {
    if (file.isEmpty()) {
        return "上传失败,文件为空";
    }
    // 保存到 D:/uploads/ 目录
    String filename = file.getOriginalFilename();
    File dest = new File("D:/uploads/" + filename);
    file.transferTo(dest);
    return "上传成功: " + filename;
}
```

### 前端 form

```html
<form action="/upload" method="post" enctype="multipart/form-data">
    <input type="file" name="file" />
    <button type="submit">上传</button>
</form>
```

`enctype="multipart/form-data"` 必须有，不然浏览器不发送文件。

### `MultipartFile` 常用方法

```java
file.getOriginalFilename();   // 原文件名
file.getSize();               // 文件大小(字节)
file.getContentType();        // MIME 类型
file.getBytes();              // 字节数组
file.transferTo(dest);        // 保存到目标文件
file.isEmpty();               // 是否为空
```

## 6. 异常处理

### Spring Boot 默认的

`ErrorMvcAutoConfiguration` 自动配了 `/error` 端点。Controller 抛了异常没人接，Spring Boot 会把请求转发到 `/error`，返回错误页或 JSON。

### 自定义全局异常处理（必学）

**一个类搞定所有 Controller 的异常**：

```java
package com.example.demo.exception;

import org.springframework.web.bind.annotation.ControllerAdvice;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.ResponseBody;

import java.util.HashMap;
import java.util.Map;

@ControllerAdvice   // 标记这是"全局增强 Controller"
public class GlobalExceptionHandler {

    // 捕获所有未处理的异常
    @ExceptionHandler(Exception.class)
    @ResponseBody
    public Map<String, Object> handleException(Exception e) {
        Map<String, Object> result = new HashMap<>();
        result.put("code", 500);
        result.put("msg", "服务器开小差: " + e.getMessage());
        return result;
    }

    // 单独捕获业务异常
    @ExceptionHandler(BusinessException.class)
    @ResponseBody
    public Map<String, Object> handleBusiness(BusinessException e) {
        Map<String, Object> result = new HashMap<>();
        result.put("code", e.getCode());
        result.put("msg", e.getMessage());
        return result;
    }
}
```

`BusinessException` 是你自己定义的业务异常类：

```java
package com.example.demo.exception;

public class BusinessException extends RuntimeException {
    private int code;

    public BusinessException(int code, String message) {
        super(message);
        this.code = code;
    }

    public int getCode() { return code; }
}
```

Controller 里需要"出错就停"时直接 `throw`：

```java
@GetMapping("/user/{id}")
public User getUser(@PathVariable int id) {
    User user = userService.findById(id);
    if (user == null) {
        throw new BusinessException(404, "用户不存在");
    }
    return user;
}
```

`@ControllerAdvice` + `@ExceptionHandler` 这套组合**所有 Spring Boot 项目都在用**，必须会。
