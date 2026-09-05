---
title: Spring Boot 整合 Thymeleaf:从"在浏览器里直接看"到图书管理
description: 第 4 章学习笔记。例子驱动,先做一个"能直接在浏览器打开的 HTML 模板",再讲 Thymeleaf 怎么把数据塞进去。
pubDate: 2026-09-05
tags: [Spring Boot, Java]
---

> **读这章前**:ch1 项目能跑,会用 `@Controller` 返回字符串。

这章要解决的问题:**Controller 返回的字符串,怎么变成浏览器看到的 HTML?**

## 1. 先体验一下"自然模板"

传统 JSP 跟 Thymeleaf 最大的区别:**Thymeleaf 模板本质就是合法 HTML,浏览器能直接打开看静态效果**。

新建 `src/main/resources/templates/hello.html`:

```html
<!DOCTYPE html>
<html xmlns:th="http://www.thymeleaf.org">
<head><title>Hello</title></head>
<body>
    <h1 th:text="'Hello, ' + ${name} + '!'">Hello 占位</h1>
    <p>这行没有 th:, 浏览器直接显示原文</p>
</body>
</html>
```

**双击这个 .html 用浏览器打开**——看到:

```
Hello 占位
这行没有 th:, 浏览器直接显示原文
```

**`xmlns:th="http://www.thymeleaf.org"` 是什么**:声明这个文件用 Thymeleaf 语法(IDE 才会给 `th:*` 提示)。**必须加**,不加模板能跑但代码没补全。

**为什么 `<h1>` 里写"Hello 占位"而不是空着**:让前端打开静态 HTML 时能看到"这里会出现内容"的占位文字,设计稿沟通更友好。

## 2. 让模板跑起来

### 第 1 步:加依赖

`pom.xml`:

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-thymeleaf</artifactId>
</dependency>
```

**这段依赖想干什么**:Spring Boot 一看到 `thymeleaf` 字样,启动时就把 Thymeleaf 的 Bean 全部配好——你不用手写任何配置。

### 第 2 步:写 Controller

新建 `src/main/java/com/example/demo/web/HelloController.java`:

```java
package com.example.demo.web;

import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;

@Controller   // ← 跟 @RestController 不同,这个会去找模板
public class HelloController {

    @GetMapping("/hello")
    public String hello(Model model) {
        model.addAttribute("name", "Tagaki");   // ← 把 name=Tagaki 传给模板
        return "hello";                          // ← 返回模板名,渲染 templates/hello.html
    }
}
```

**关键行**:
- `@Controller` 而不是 `@RestController` —— `@RestController` 直接返回数据(给接口用),`@Controller` 返回视图名(给页面用)
- `Model model` —— Spring 给的"数据容器",`addAttribute("name", "Tagaki")` 等于在模板里有个变量叫 `name`,值是 `Tagaki`
- 返回 `"hello"` —— 不是返回字符串给前端,是告诉 Spring "去 `templates/hello.html` 找模板,用刚才传的数据渲染"

> **这段代码想干什么**:用户访问 `/hello` 时,Spring 找到 `hello.html`,把 `name=Tagaki` 传进去,渲染成最终 HTML 返回浏览器。

### 第 3 步:跑起来

启动后访问 `http://localhost:8080/hello`,看到:

```
Hello, Tagaki!
这行没有 th:, 浏览器直接显示原文
```

`${name}` 被替换成了 `Tagaki`。

## 3. Thymeleaf 的 5 个常用属性(每个配例子)

下面这 5 个属性覆盖 90% 场景,逐个演示。

### `th:text` —— 替换标签文本(最常用)

**需求**:显示用户名。

```html
<p th:text="${user.name}">默认文本</p>
```

`<p>` 里的"默认文本"是给"直接浏览器打开"时看的占位,运行时被替换成 `${user.name}` 的值。

**踩坑**:`th:text` 会把 HTML 字符转义。如果后端传的是 `<b>加粗</b>`,显示成字面量而不是加粗。要"原样输出 HTML"用 `th:utext`(注意 XSS 风险,别用在前端输入)。

### `th:each` —— 循环

**需求**:显示用户列表。

```html
<ul>
    <li th:each="user : ${users}" th:text="${user.name}">名字</li>
</ul>
```

`th:each="user : ${users}"` 类似 Java 的 `for (User user : users)`,**`user` 是循环变量,`${users}` 是后端传的 List**。

**带状态变量的版本**(知道"这是第几个"):

```html
<tr th:each="book, iter : ${books}">
    <td th:text="${iter.count}">1</td>      <!-- 1, 2, 3... (从 1 开始) -->
    <td th:text="${book.name}">书名</td>
</tr>
```

`iter` 是状态变量,提供:
- `iter.count` —— 序号(从 1 开始)
- `iter.index` —— 索引(从 0 开始)
- `iter.first` / `iter.last` —— 是不是第一个/最后一个
- `iter.even` / `iter.odd` —— 是不是偶数/奇数行

### `th:if` / `th:unless` —— 条件渲染

**需求**:18 岁以上显示"成年",否则显示"未成年"。

```html
<div th:if="${user.age >= 18}">成年</div>
<div th:unless="${user.age >= 18}">未成年</div>
```

`th:if` 跟 Java 的 if 一样,条件为 true 才渲染。`th:unless` 相反(相当于 `!th:if`)。

### `th:href` / `th:src` —— 资源 URL

**需求**:链接到用户详情页。

```html
<a th:href="@{/user/{id}(id=${user.id})}">查看</a>
```

`@{...}` 表达式帮你:
- 自动加 contextPath(项目如果部署在 `/myapp` 下,会变成 `/myapp/user/123`)
- 自动 URL 编码(中文、特殊字符)

**带参数**:`@{/path(key=value)}` 多个参数用逗号。

### `th:object` + `th:field` —— 表单对象绑定(进阶,推荐学)

**需求**:用户编辑表单,自动回显数据。

**Controller**:
```java
@GetMapping("/user/edit")
public String editForm(Model model) {
    model.addAttribute("user", new User("Tagaki", 22));
    return "user/edit";
}
```

**模板** `templates/user/edit.html`:
```html
<form th:action="@{/user/save}" th:object="${user}" method="post">
    名字:<input th:field="*{name}" />     <!-- 等同于 name="name" value="${user.name}" -->
    年龄:<input th:field="*{age}" />
    <button type="submit">保存</button>
</form>
```

**关键行**:
- `<form th:object="${user}">` —— 标记"这个表单绑 `user` 对象"
- `<input th:field="*{name}">` —— 简写形式,自动展开成 `name="name" value="${user.name}"`
- `*{...}` 叫"选择表达式",**只能在 `th:object` 内部用**,等价于 `${user.name}`

> **这段代码想干什么**:`th:field="*{name}"` 一行顶三行——自动生成 input 的 `name` 属性(给后端用)、`value` 属性(显示旧值)、`id` 属性(给 label 用)。表单处理必备。
>
> **跑起来看啥**:编辑页打开,输入框已经预填了"Tagaki"和"22",不用手写 value。

## 4. 5 种表达式速查

| 语法 | 名称 | 作用 | 例子 |
|---|---|---|---|
| `${...}` | 变量 | 读上下文变量 | `${user.name}` |
| `*{...}` | 选择 | 在 `th:object` 内简写 | `*{name}` |
| `@{...}` | URL | 生成应用内 URL | `@{/user/list}` |
| `#{...}` | 消息 | 国际化文案 | `#{user.welcome}` |
| `~{...}` | 片段 | 引用其他模板片段 | `~{header :: nav}` |

**最常用 3 个**:`${}`(取值)、`@{}`(URL)、`*{}`(表单绑定)。

## 5. 综合案例:图书管理 CRUD

前面学的零碎,这节串起来做一个完整的"图书列表 + 新增 + 编辑 + 删除"。

### 数据类

`src/main/java/com/example/demo/entity/Book.java`:

```java
package com.example.demo.entity;

public class Book {
    private int id;
    private String name;
    private String author;
    private double price;

    public Book() {}   // ← Thymeleaf 表单绑定需要无参构造

    public Book(int id, String name, String author, double price) {
        this.id = id;
        this.name = name;
        this.author = author;
        this.price = price;
    }

    // ↓ 下面这些 getter/setter 是 Thymeleaf 反射访问字段用的,必须
    public int getId() { return id; }
    public void setId(int id) { this.id = id; }
    public String getName() { return name; }
    public void setName(String name) { this.name = name; }
    public String getAuthor() { return author; }
    public void setAuthor(String author) { this.author = author; }
    public double getPrice() { return price; }
    public void setPrice(double price) { this.price = price; }
}
```

**关键行**:
- **无参构造必须有** —— Thymeleaf 的 `th:field` 通过反射调用 `new Book()` 拿到对象再注入值
- getter/setter 必须有 —— 模板要通过 getter 读值,setter 写值
- 字段用包装类型 `Integer` / `Double` 也行,但基本类型更省内存(注意未赋值时是默认值 0)

### Service(用静态数据模拟,没数据库)

`src/main/java/com/example/demo/service/BookService.java`:

```java
package com.example.demo.service;

import com.example.demo.entity.Book;
import org.springframework.stereotype.Service;

import java.util.*;
import java.util.concurrent.atomic.AtomicInteger;

@Service   // ← 注册成 Spring Bean
public class BookService {
    private final List<Book> books = new ArrayList<>();
    private final AtomicInteger idGenerator = new AtomicInteger(3);  // 已有 3 本,新加从 4 开始

    public BookService() {
        // 初始化 3 本示例书
        books.add(new Book(1, "Java 入门", "凯 S. 霍斯特曼", 88.0));
        books.add(new Book(2, "Spring Boot 实战", "Craig Walls", 99.0));
        books.add(new Book(3, "深入理解 JVM", "周志明", 119.0));
    }

    public List<Book> findAll() { return books; }

    public Book findById(int id) {
        return books.stream().filter(b -> b.id == id).findFirst().orElse(null);
    }

    public void add(Book book) {
        book.setId(idGenerator.getAndIncrement());  // 自动生成新 id
        books.add(book);
    }

    public void update(Book book) {
        Book exist = findById(book.getId());
        if (exist != null) {
            exist.setName(book.getName());
            exist.setAuthor(book.getAuthor());
            exist.setPrice(book.getPrice());
        }
    }

    public void delete(int id) {
        books.removeIf(b -> b.id == id);
    }
}
```

**关键行**:
- `@Service` 标记这是业务层,Spring 启动时把它注册成 Bean,Controller 可以 `@Autowired` 注入
- `AtomicInteger` —— 多线程安全的自增 id 生成器(`id++` 在多线程下会重复)
- `findById` 用 Stream API 找第一个匹配的,比写 for 循环清爽

### Controller(6 个方法,6 个 URL)

`src/main/java/com/example/demo/web/BookController.java`:

```java
package com.example.demo.web;

import com.example.demo.entity.Book;
import com.example.demo.service.BookService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.*;

@Controller
@RequestMapping("/book")   // ← 所有路径前缀
public class BookController {

    @Autowired
    private BookService bookService;

    // 1. 列表页
    @GetMapping("/list")
    public String list(Model model) {
        model.addAttribute("books", bookService.findAll());
        return "book/list";   // 渲染 templates/book/list.html
    }

    // 2. 跳到新增页
    @GetMapping("/add")
    public String toAdd(Model model) {
        model.addAttribute("book", new Book());   // 空对象,给表单绑
        return "book/add";
    }

    // 3. 提交新增
    @PostMapping("/add")
    public String add(Book book) {
        bookService.add(book);
        return "redirect:/book/list";   // ← 重定向,防止刷新重复提交
    }

    // 4. 跳到编辑页
    @GetMapping("/edit/{id}")
    public String toEdit(@PathVariable int id, Model model) {
        model.addAttribute("book", bookService.findById(id));
        return "book/edit";
    }

    // 5. 提交编辑
    @PostMapping("/update")
    public String update(Book book) {
        bookService.update(book);
        return "redirect:/book/list";
    }

    // 6. 删除
    @GetMapping("/delete/{id}")
    public String delete(@PathVariable int id) {
        bookService.delete(id);
        return "redirect:/book/list";
    }
}
```

**关键行**:
- `@RequestMapping("/book")` —— 类级别前缀,所有方法路径都加 `/book`
- `@Autowired BookService` —— Spring 自动注入,不用 `new`
- `@PathVariable int id` —— 从 URL 路径里取变量,`/edit/3` → `id=3`
- `return "redirect:/book/list"` —— **重定向,刷新页面不会重复提交**(重要!)
- 提交后跳列表页(`redirect:` 前缀),而不是返回视图

> **这段代码想干什么**:提供 6 个 URL,对应图书管理的增删改查。`/book/list` 看列表,`/book/add` 新增,`/book/edit/{id}` 编辑,`/book/delete/{id}` 删除。`redirect:` 是为了"提交后跳页面,防刷新重复提交"。

### 模板 1:列表页 `templates/book/list.html`

```html
<!DOCTYPE html>
<html xmlns:th="http://www.thymeleaf.org">
<head><title>图书列表</title></head>
<body>
    <h1>图书列表</h1>
    <a th:href="@{/book/add}">新增图书</a>   <!-- ← 用 @{} 生成 URL -->
    <table border="1" cellpadding="8">
        <tr>
            <th>序号</th><th>书名</th><th>作者</th><th>价格</th><th>操作</th>
        </tr>
        <!-- ↓ 循环显示所有书 -->
        <tr th:each="book, iter : ${books}">
            <td th:text="${iter.count}">1</td>
            <td th:text="${book.name}">书名</td>
            <td th:text="${book.author}">作者</td>
            <td th:text="${book.price}">价格</td>
            <td>
                <!-- ↓ 编辑链接,id 从 book 取 -->
                <a th:href="@{/book/edit/{id}(id=${book.id})}">编辑</a>
                <!-- ↓ 删除链接 + 二次确认 -->
                <a th:href="@{/book/delete/{id}(id=${book.id})}"
                   onclick="return confirm('确定删除《'+'[[${book.name}]]'+'》吗?')">删除</a>
            </td>
        </tr>
    </table>
</body>
</html>
```

**关键行**:
- `th:each="book, iter : ${books}"` —— 遍历后端传过来的 `books` 列表
- `@{/book/edit/{id}(id=${book.id})}` —— 路径里嵌入 `book.id`,类似 `/book/edit/1`
- `[[${book.name}}` —— **内联表达式**,在 JS 字符串里安全嵌入(自动转义防 XSS)

> **这段模板想干什么**:接收 Controller 传的 `books` 列表,渲染成 HTML 表格。每一行展示一本书,带"编辑"和"删除"链接。

### 模板 2:新增页 `templates/book/add.html`

```html
<!DOCTYPE html>
<html xmlns:th="http://www.thymeleaf.org">
<head><title>新增图书</title></head>
<body>
    <h1>新增图书</h1>
    <!-- ↓ th:object 标记绑 book,th:field 自动展开 input 属性 -->
    <form th:action="@{/book/add}" th:object="${book}" method="post">
        <p>书名:<input th:field="*{name}" /></p>
        <p>作者:<input th:field="*{author}" /></p>
        <p>价格:<input th:field="*{price}" /></p>
        <button type="submit">保存</button>
    </form>
</body>
</html>
```

> **这段模板想干什么**:展示一个空表单让用户填书名/作者/价格,提交后 POST 到 `/book/add`。`th:field="*{name}"` 自动展开成 `<input name="name" />`,省事。

### 模板 3:编辑页 `templates/book/edit.html`

跟新增页**几乎一样**,只是数据已经填好(`th:field` 会回显):

```html
<!DOCTYPE html>
<html xmlns:th="http://www.thymeleaf.org">
<head><title>编辑图书</title></head>
<body>
    <h1>编辑图书</h1>
    <form th:action="@{/book/update}" th:object="${book}" method="post">
        <!-- ↓ id 也要传,后端才知道改哪本 -->
        <input type="hidden" th:field="*{id}" />
        <p>书名:<input th:field="*{name}" /></p>
        <p>作者:<input th:field="*{author}" /></p>
        <p>价格:<input th:field="*{price}" /></p>
        <button type="submit">保存</button>
    </form>
</body>
</html>
```

**关键行**:
- `<input type="hidden" th:field="*{id}" />` —— **隐藏字段存 id**,提交时一起发给后端,后端才知道改哪本
- `th:field` 自动用 `book` 的值回显,比如 `name` 输入框里自动显示原来的书名

### 跑起来看效果

启动后访问 `http://localhost:8080/book/list`:

- 看到 3 本示例书
- 点"新增" → 填表 → 提交 → 跳回列表,新书出现
- 点"编辑" → 表单预填 → 改完提交 → 跳回列表,改动生效
- 点"删除" → 二次确认 → 删除 → 跳回列表,书没了

## 6. 常见踩坑

**踩坑 1:模板改了,刷新页面没变化**
原因:Thymeleaf 缓存了模板。
解决:开发时关缓存——`application.yml` 加:
```yaml
spring:
  thymeleaf:
    cache: false
```

**踩坑 2:`th:field` 报红或没回显**
原因:`th:object` 写错,或者 Book 类没有无参构造/getter/setter。
解决:确认 Bean 有无参构造 + 完整 getter/setter。

**踩坑 3:点删除按钮弹出"找不到页面"**
原因:Controller 用了 `@PostMapping` 处理删除,但 HTML `<a>` 是 GET 请求。
解决:用 `@GetMapping` 处理删除(简单项目),或前端用 form + POST 触发删除(更安全)。

**踩坑 4:中文乱码**
原因:Controller 接收的请求体编码不对。
解决:`application.yml` 加:
```yaml
spring:
  http:
    encoding:
      charset: UTF-8
      force: true
```

## 7. 一句话总结这章

**学的是"怎么把数据塞进 HTML"**——Thymeleaf 的 5 个属性、5 种表达式、3 个模板文件,加上 Controller 6 个 URL,凑成一个完整的 CRUD 案例。这套模板引擎 + 增删改查的模式,90% 的内部管理系统都长这样。

学完你应该能:
- [ ] 解释 Thymeleaf 跟 JSP 的最大区别
- [ ] 用 `th:each` 渲染列表
- [ ] 用 `th:if` 做条件渲染
- [ ] 用 `th:object` + `th:field` 写表单
- [ ] 独立做一个完整的"列表 + 新增 + 编辑 + 删除"四件套
