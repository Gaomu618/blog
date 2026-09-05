---
title: Spring Boot 整合 Thymeleaf：模板引擎入门到图书管理案例
description: 第 4 章学习笔记。Spring Boot 支持的模板引擎、Thymeleaf 怎么用、表达式、5 个属性、图书管理 CRUD 完整例子。
pubDate: 2026-09-05
tags: [Spring Boot, Java]
---

第 3 章讲了 Controller 怎么写，但 Controller 返回的字符串最终怎么变成浏览器看到的 HTML 页面？这就是第 4 章要解决的事——**模板引擎**。

## 1. Spring Boot 支持哪些模板引擎

Spring Boot 官方支持下面这些（**Spring Boot 3.x 起 Velocity 已被移除**）：

| 引擎 | 特点 | 用得最多 |
|---|---|---|
| **Thymeleaf** | 自然模板、HTML 可直接打开 | ✅ 强烈推荐 |
| FreeMarker | 老牌、灵活、性能好 | 老项目 |
| Mustache | 逻辑无关、前后端可共享 | 多端复用 |
| Groovy | 基于 Groovy 语法 | 简单场景 |

JSP **不在列表里**——因为 JSP 需要 Servlet 容器编译，而 Spring Boot 默认打 JAR 用内嵌 Tomcat，JSP 打包麻烦（要改成 WAR）。新项目**直接选 Thymeleaf**。

## 2. Thymeleaf 是什么

Thymeleaf 是一个**服务端 Java 模板引擎**：你写 HTML 模板，Thymeleaf 把数据塞进去，输出最终的 HTML 字符串。

它跟 JSP、Freemarker 最大的区别在于**自然模板**（Natural Templates）——一个 .html 文件既是模板，**又能直接被浏览器打开看到静态效果**。

看个例子。下面这个文件叫 `hello.html`：

```html
<!DOCTYPE html>
<html xmlns:th="http://www.thymeleaf.org">
<head><title>Hello</title></head>
<body>
    <p th:text="${name}">这里会被替换</p>
    <p>这里没有 th:,浏览器直接显示原文</p>
</body>
</html>
```

**双击这个 .html 用浏览器打开**，看到的是：

```
这里会被替换
这里没有 th:,浏览器直接显示原文
```

**经过 Thymeleaf 渲染**（Controller 传了 `name="Tagaki"`），输出：

```
Tagaki
这里没有 th:,浏览器直接显示原文
```

这意味着**前端工程师可以拿 .html 当普通 HTML 改,不用启服务**——对前后端协作特别友好。

## 3. 第一个 Thymeleaf 页面

### 加依赖

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-thymeleaf</artifactId>
</dependency>
```

### 模板放哪

约定：**`src/main/resources/templates/`** 目录下，后缀 `.html`。

不要放 `static/` 目录——那个是给浏览器直接访问的静态资源，模板不会被 Thymeleaf 处理。

### Controller 返回

```java
@Controller
public class HelloController {
    @GetMapping("/hello")
    public String hello(Model model) {
        model.addAttribute("name", "Tagaki");
        return "hello";   // 渲染 templates/hello.html
    }
}
```

注意返回的是**字符串**（视图名），不是数据。`@RestController` 返回数据，`@Controller` 返回视图。

### 模板文件

`src/main/resources/templates/hello.html`：

```html
<!DOCTYPE html>
<html xmlns:th="http://www.thymeleaf.org">
<head><title>Hello</title></head>
<body>
    <h1 th:text="'Hello, ' + ${name} + '!'">Hello 占位</h1>
</body>
</html>
```

`xmlns:th="http://www.thymeleaf.org"` 这行必须有，告诉 IDE 这个文件用 Thymeleaf 语法（IDE 会给提示）。

## 4. 5 个最常用的属性

属性是 `th:` 开头，写在 HTML 标签上。**这 5 个覆盖 90% 场景**：

### `th:text` —— 替换标签文本

```html
<p th:text="${user.name}">默认文本</p>
```

注意 `<p>` 里的"默认文本"是给浏览器直看用的，运行时被替换。

### `th:utext` —— 不转义 HTML

```html
<div th:utext="${article.htmlContent}">HTML 内容</div>
```

`th:text` 会把 `<` 转成 `&lt;`（安全），`th:utext` 不转义（会执行 HTML，**慎用，防 XSS**）。

### `th:if` / `th:unless` —— 条件渲染

```html
<div th:if="${user.age >= 18}">成年</div>
<div th:unless="${user.age >= 18}">未成年</div>
```

`th:if="false"` 时整个标签不输出。

### `th:each` —— 循环

```html
<ul>
    <li th:each="user : ${users}" th:text="${user.name}">名字</li>
</ul>
```

`th:each="user : ${users}"` 类似 Java 的 `for (User user : users)`。

完整版（带状态变量）：

```html
<tr th:each="book, iter : ${books}">
    <td th:text="${iter.count}">序号</td>   <!-- 1, 2, 3... -->
    <td th:text="${book.name}">书名</td>
</tr>
```

`iter` 是状态变量，提供 `count`（从 1 开始）、`index`（从 0 开始）、`first`、`last`、`even`、`odd` 等。

### `th:href` / `th:src` —— 资源 URL

```html
<a th:href="@{/user/{id}(id=${user.id})}">查看</a>
<img th:src="@{/img/logo.png}" />
```

`@{...}` 自动加 contextPath，避免硬编码。

## 5. 5 种表达式

Thymeleaf 有 5 种表达式，记住这 5 个名字能应付所有场景：

| 语法 | 名称 | 作用 | 例 |
|---|---|---|---|
| `${...}` | 变量 | 读上下文变量 | `${user.name}` |
| `*{...}` | 选择 | 在 `th:object` 内简写 | `*{name}` |
| `@{...}` | URL | 生成应用内 URL | `@{/user/list}` |
| `#{...}` | 消息 | 国际化文案 | `#{user.welcome}` |
| `~{...}` | 片段 | 引用其他模板片段 | `~{header :: nav}` |

最常用 3 个：

**`${...}`：**

```html
<p th:text="${user.name}">Tagaki</p>
```

**`*{...}` 配合 `th:object`（表单绑定神器）：**

```html
<form th:action="@{/user/save}" th:object="${user}" method="post">
    <input th:field="*{name}" />    <!-- 等同于 name="name" th:value="${user.name}" -->
    <input th:field="*{age}" />
    <button type="submit">保存</button>
</form>
```

`th:field="*{name}"` 自动展开成 `name="name"` + `value="${user.name}"`，表单回显时不用手写。

**`@{...}`：**

```html
<a th:href="@{/user/list}">用户列表</a>
<a th:href="@{/user/{id}(id=${user.id})}">详情</a>   <!-- 带参数 -->
```

自动加 contextPath（如 `/myapp/user/list`），不会写死路径。

## 6. 图书管理案例（CRUD 完整例子）

第 4 章最后那个案例实战，把上面的知识串起来。

### 数据类

```java
public class Book {
    private int id;
    private String name;
    private String author;
    private double price;

    // getter / setter / 构造方法 省略
}
```

### Service（用静态数据模拟）

```java
@Service
public class BookService {
    private final List<Book> books = new ArrayList<>();

    public BookService() {
        books.add(new Book(1, "Java 入门", "凯 S. 霍斯特曼", 88.0));
        books.add(new Book(2, "Spring Boot 实战", "Craig Walls", 99.0));
        books.add(new Book(3, "深入理解 JVM", "周志明", 119.0));
    }

    public List<Book> findAll() { return books; }
    public Book findById(int id) {
        return books.stream().filter(b -> b.id == id).findFirst().orElse(null);
    }
    public void add(Book book) { books.add(book); }
    public void update(Book book) {
        Book exist = findById(book.getId());
        if (exist != null) {
            exist.setName(book.getName());
            exist.setAuthor(book.getAuthor());
            exist.setPrice(book.getPrice());
        }
    }
    public void delete(int id) { books.removeIf(b -> b.id == id); }
}
```

### Controller

```java
@Controller
@RequestMapping("/book")
public class BookController {
    @Autowired
    private BookService bookService;

    @GetMapping("/list")
    public String list(Model model) {
        model.addAttribute("books", bookService.findAll());
        return "book/list";   // 渲染 templates/book/list.html
    }

    @GetMapping("/add")
    public String toAdd(Model model) {
        model.addAttribute("book", new Book());
        return "book/add";
    }

    @PostMapping("/add")
    public String add(Book book) {
        bookService.add(book);
        return "redirect:/book/list";
    }

    @GetMapping("/edit/{id}")
    public String toEdit(@PathVariable int id, Model model) {
        Book book = bookService.findById(id);
        model.addAttribute("book", book);
        return "book/edit";
    }

    @PostMapping("/update")
    public String update(Book book) {
        bookService.update(book);
        return "redirect:/book/list";
    }

    @GetMapping("/delete/{id}")
    public String delete(@PathVariable int id) {
        bookService.delete(id);
        return "redirect:/book/list";
    }
}
```

### 模板：列表页 `templates/book/list.html`

```html
<!DOCTYPE html>
<html xmlns:th="http://www.thymeleaf.org">
<head><title>图书列表</title></head>
<body>
    <h1>图书列表</h1>
    <a th:href="@{/book/add}">新增图书</a>
    <table border="1">
        <tr>
            <th>序号</th><th>书名</th><th>作者</th><th>价格</th><th>操作</th>
        </tr>
        <tr th:each="book, iter : ${books}">
            <td th:text="${iter.count}">1</td>
            <td th:text="${book.name}">Java 入门</td>
            <td th:text="${book.author}">作者</td>
            <td th:text="${book.price}">88.0</td>
            <td>
                <a th:href="@{/book/edit/{id}(id=${book.id})}">编辑</a>
                <a th:href="@{/book/delete/{id}(id=${book.id})}"
                   onclick="return confirm('确定删除?')">删除</a>
            </td>
        </tr>
    </table>
</body>
</html>
```

### 模板：新增页 `templates/book/add.html`

```html
<!DOCTYPE html>
<html xmlns:th="http://www.thymeleaf.org">
<head><title>新增图书</title></head>
<body>
    <h1>新增图书</h1>
    <form th:action="@{/book/add}" th:object="${book}" method="post">
        书名:<input th:field="*{name}" /><br/>
        作者:<input th:field="*{author}" /><br/>
        价格:<input th:field="*{price}" /><br/>
        <button type="submit">保存</button>
    </form>
</body>
</html>
```

这个例子里 **`th:object="${book}"` + `th:field="*{name}"`** 是表单处理的核心套路。`th:field` 自动展开成 `name` 属性 + `value` 默认值，新增时为空，编辑时回显已有数据。

启动后访问 `http://localhost:8080/book/list`，能列表→新增→编辑→删除。
