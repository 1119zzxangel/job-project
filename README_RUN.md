项目简介
=====
这是一个基于 Django 的职位信息可视化与推荐系统。为满足日常运营与使用安全，项目采用“求职者（普通用户）”与“管理员（超级用户）”的双角色设计。本文档说明角色定位、权限边界、运行与部署步骤、关键路径和运维建议，便于开发、部署与面试演示使用。

一、角色总览
----
- 求职者（普通用户） — 系统服务对象，目标：高效找工作。权限：仅操作/查看个人相关数据（简历、收藏、推荐结果、个人设置）。
- 管理员（超级用户） — 系统运营与维护者，目标：保障系统稳定与数据质量。权限：全系统最高权限（用户管理、爬虫调度、数据清洗、配置、审计等）。

二、求职者（普通用户）功能清单
----
- 职位数据服务：按城市/薪资/学历/行业/经验筛选、关键词搜索；查看市场可视化图表（薪资/学历/行业分布）；薪资排行TOP10。
- 求职流程支持：个性化职位推荐、求职意向维护（城市/岗位/期望薪资）、收藏与申请跟踪。
- 简历相关：上传/编辑/删除简历；自动解析简历并进行职位匹配，生成匹配报告（匹配度、匹配/缺失技能点）。
- 个人中心：修改个人信息、头像、修改密码（支持找回/重置）；仅展示系统监控摘要（只读，可选）。

三、管理员（超级用户）功能清单
----
- 系统运维与管理：用户管理（查看/重置密码/冻结/权限分配/删除）、实时系统监控（CPU/内存/任务队列）、系统配置（爬虫频率/推荐权重/数据更新时间）、操作日志和审计。

- 数据全生命周期：数据清洗（增删改查）、数据备份与恢复、数据审核（过滤虚假/违规职位）。

- 运营与策略：职位上下架与置顶、推荐算法参数调整与回滚、简历脱敏查看与统计分析、生成运营报表（用户增长/抓取量/匹配成功率）。

- 账号密码：admin;admin123；ttx_admin;ttx051119

  1. 启动开发服务器（若未运行）：

  1. 前端登录页：打开 `http://127.0.0.1:8000/`，使用账号 `ttx_admin` / 密码 `ttx051119` 登录。登录后左侧菜单应显示“后台管理”入口（并允许访问 `爬虫调度`）。
  2. Django 管理后台：打开 `http://127.0.0.1:8000/admin/`，使用相同账号登录以访问完整后台。

四、功能权限对照（简要）
----
| 功能模块 | 求职者（普通用户） | 管理员（超级用户） |
|---|---:|---:|
| 主页（数据可视化） | 查看个人/市场数据 | 查看全量市场数据+系统监控 |
| 模型管理 | ❌ 无权限 | ✅ 配置/切换/监控 |
| 数据管理 | 查看/检索个人可访问数据 | 全量增删改查/审核/备份 |
| 职位推荐 | 个人推荐 + 求职意向管理 | 全量推荐管理 + 算法配置 |
| 简历匹配 | 上传/匹配（个人） | 简历统计/脱敏查看/匹配分析 |
| 用户管理 | 修改个人信息/密码 | 全量用户管理/封禁/权限分配 |

五、快速启动（本地开发）
----

1. 建议使用 Python 虚拟环境并安装依赖：

Windows 示例：
```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

项目依赖库包括：
- Django 3.2.8
- django-simpleui 2024.8.28
- weasyprint 59.0 (用于生成 PDF 报告)
- pdfminer.six 20231228 (用于解析 PDF 简历)
- python-docx 0.8.11 (用于解析 DOCX 简历)
- scikit-learn 1.5.0 (用于文本相似度计算)
- numpy 2.0.0
- psutil 5.9.6
- openai>=1.0.0 (用于大模型调用)

2. 配置数据库与环境变量：
- 推荐将敏感配置放到环境变量或 `.env`，不要直接写入 `JobRecommend/settings.py`。可参考 `JobRecommend/settings.py` 的连接位置 [JobRecommend/settings.py](JobRecommend/settings.py#L1-L200)。

3. 迁移与创建管理员账户：
```powershell
python manage.py migrate
python manage.py createsuperuser
```
管理员账户用于登录 Django admin（默认路径 `/admin/`）。如需初始化测试管理员，可在本地临时创建账号，生产环境请用安全密码并限制访问。

如果你希望同时在站内（`UserList`）创建一条管理员记录以便使用站内账户访问管理功能（如 `spiders` 页面），可以运行仓库根目录下的脚本：
```powershell
python create_admin_user.py <admin_username> <admin_password> [email]
```
该脚本会：
- 在 Django auth 中创建或确认存在超级用户；
- 在 `user_list` 表中插入或更新对应记录，设置 `role='admin'`，使站内会话具备管理员权限（显示后台入口并允许爬虫调度）。

4. 运行开发服务器：
```powershell
python manage.py runserver
```
访问应用： http://127.0.0.1:8000/ ，后台管理： http://127.0.0.1:8000/admin/。

六、模型管理
----
- 模型管理功能位于 [job/views.py](job/views.py#L610-L650) 和 [job/models.py](job/models.py#L100-L120)，支持多种大模型的配置和管理。

- **模型配置**：
  - 支持添加、编辑、删除模型配置
  - 支持设置模型名称、类型、接入点ID和API地址
  - 支持激活/停用模型

- **依赖安装**：
  项目已包含 `openai>=1.0.0` 依赖，安装依赖时会自动安装：
  ```powershell
  pip install -r requirements.txt
  ```

- **环境变量配置**：
  需要在 `.env` 文件中配置 API_KEY：
  ```
  API_KEY=your-api-key-here
  ```

- **使用方法**：
  1. 登录管理员账号
  2. 进入模型管理页面：`http://127.0.0.1:8000/models/`
  3. 添加模型配置并激活
  4. 系统会自动使用激活的模型进行简历解析

- **注意事项**：
  - 确保 API_KEY 正确配置
  - 确保 API URL 和接入点ID正确
  - 每个模型类型只能有一个激活的模型

七、功能模块详细介绍
----

### 7.1 用户管理模块
**功能描述**：提供用户注册、登录、权限管理和个人信息维护功能，支持求职者和管理员两种角色。

**技术实现**：
- **后端框架**：Django 3.2.8 内置用户认证系统
- **数据库模型**：自定义 UserList 模型，包含用户ID、用户名、密码（哈希存储）、邮箱、电话、头像、角色等字段
- **权限控制**：基于角色的访问控制（RBAC），通过 `role` 字段区分普通用户和管理员
- **密码安全**：使用 Django 的密码哈希机制，支持密码重置功能（通过 reset_token）
- **会话管理**：基于 Django session 机制，支持登录状态保持和权限验证

**核心文件**：
- 模型定义：[job/models.py](job/models.py#L88-L129)
- 视图处理：[job/views.py](job/views.py#L1-L680)
- 管理界面：[job/admin.py](job/admin.py#L20-L27)

**主要功能**：
- 用户注册与登录验证
- 个人信息修改（用户名、邮箱、电话、头像）
- 密码修改与找回
- 角色权限管理（普通用户/管理员）
- 用户数据统计与查询

---

### 7.2 模型管理模块
**功能描述**：支持多种大模型的配置和管理，包括添加、编辑、删除和切换模型，为简历解析提供不同的大模型服务。

**技术实现**：
- **后端框架**：Django 3.2.8 ORM 系统
- **数据模型**：ModelConfig 模型，包含模型ID、名称、类型、接入点ID、API地址、激活状态等字段
- **前端界面**：基于 Layui 的可视化管理界面
- **大模型调用**：使用 OpenAI SDK 统一调用接口
- **权限控制**：基于角色的访问控制，仅管理员可访问

**核心文件**：
- 模型定义：[job/models.py](job/models.py#L100-L120)
- 视图处理：[job/views.py](job/views.py#L610-L650)
- 管理界面：[job/admin.py](job/admin.py#L80-L100)
- 前端模板：templates/modelManage.html

**主要功能**：
- 模型配置管理（添加、编辑、删除）
- 模型激活与停用
- 模型状态监控
- 支持多种大模型服务
- 实时模型切换

**模型配置字段**：
- 模型基本信息：model_id, model_name, model_type
- 连接信息：endpoint_id, api_url
- 状态信息：is_active, created_at

---

### 7.3 职位推荐模块
**功能描述**：基于协同过滤算法为用户提供个性化职位推荐，支持基于用户历史行为和求职意向的智能推荐。

**技术实现**：
- **推荐算法**：基于物品的协同过滤（Item-based Collaborative Filtering）
- **相似度计算**：余弦相似度（Cosine Similarity）
  - 公式：similarity = common / sqrt(job1_sum * job2_sum)
  - 其中 common 为两个职位的共同投递用户数
- **推荐策略**：
  - 分析用户历史投递记录，提取偏好关键词
  - 计算未投递职位与已投递职位的相似度
  - 按相似度排序推荐 Top-K 职位
  - 支持基于用户意向的推荐（当无历史数据时）
- **数据处理**：Django ORM 查询优化，使用 Subquery 和 Q 对象
- **随机性**：使用 random.sample 增加推荐多样性

**核心文件**：
- 推荐引擎：[job/job_recommend.py](job/job_recommend.py#L1-L109)
- 数据模型：[job/models.py](job/models.py#L29-L42)

**主要功能**：
- 基于用户投递历史的个性化推荐
- 基于用户求职意向的推荐
- 支持冷启动处理（新用户推荐）
- 推荐结果排序和过滤
- 推荐效果统计和分析

**算法流程**：
1. 获取用户历史投递记录
2. 提取用户偏好关键词（Top-3）
3. 查找未投递的候选职位
4. 计算候选职位与已投递职位的相似度
5. 按相似度排序，返回 Top-K 推荐结果

---

### 7.4 简历解析与匹配模块
**功能描述**：支持多种格式的简历文件解析，自动提取技能、学历、工作经验等信息，并与职位要求进行智能匹配。支持大模型解析和关键词解析两种方式。

**技术实现**：
- **文件解析**：
  - PDF 解析：pdfminer.six 20231228
  - DOCX 解析：python-docx 0.8.11
  - TXT 解析：Python 内置文件操作
- **大模型解析**：
  - 使用 OpenAI SDK 调用大模型服务
  - 支持多种大模型的配置和切换
  - 异步处理，避免超时问题
- **关键词解析**：
  - 基于预定义技能库的关键词匹配
  - 使用词边界匹配避免误识别
- **相似度计算**：
  - TF-IDF 向量化：scikit-learn 1.5.0 的 TfidfVectorizer
  - 余弦相似度：cosine_similarity
  - N-gram 特征：支持 1-gram 和 2-gram
- **报告生成**：weasyprint 59.0 生成 PDF 格式的匹配报告

**核心文件**：
- 简历解析：[job/utils/resume_parser.py](job/utils/resume_parser.py#L1-L146)
- 大模型解析：[job/views.py](job/views.py#L580-L720)
- 相似度匹配：[job/algorithms/similarity_match.py](job/algorithms/similarity_match.py#L1-L53)
- 视图处理：[job/views.py](job/views.py#L1-L680)

**主要功能**：
- 多格式简历文件解析（PDF/DOCX/TXT）
- 自动提取简历中的技能信息
- 识别学历等级（博士/硕士/本科/大专/高中）
- 估算工作经验年限
- 简历与职位的智能匹配
- 生成详细的匹配报告（包含匹配度、匹配技能、缺失技能）
- 支持批量简历处理
- 支持大模型解析和关键词解析两种方式
- 自动选择当前激活的模型进行解析

**匹配算法**：
1. 将简历文本和职位技能要求转换为 TF-IDF 向量
2. 计算简历与职位的余弦相似度
3. 识别简历中包含的职位要求技能
4. 标记缺失的技能点
5. 生成匹配分数和详细报告

**技能库示例**：
- 编程语言：Python, Java, C++, JavaScript, TypeScript, SQL
- Web 框架：Django, Flask, React, Angular, Vue, Spring
- 数据科学：TensorFlow, PyTorch, Pandas, NumPy, Scikit-learn
- DevOps：Docker, Kubernetes, Git, Linux
- 数据库：MySQL, PostgreSQL, MongoDB, Redis

---

### 7.5 数据可视化模块
**功能描述**：提供丰富的数据可视化图表，展示职位市场分析、薪资分布、学历要求等统计信息。

**技术实现**：
- **图表库**：ECharts（通过 layuiadmin 集成）
- **前端框架**：jQuery 3.6.0 + Layui 2.7.6
- **数据交互**：AJAX 异步数据加载
- **图表类型**：
  - 柱状图：薪资分布、学历分布
  - 饼图：行业分布、公司规模分布
  - 折线图：趋势分析
  - 地图：地域分布
- **响应式设计**：支持不同屏幕尺寸的自适应显示

**核心文件**：
- 前端模板：templates/index.html, templates/salary.html, templates/bar_page.html
- 静态资源：static/layuiadmin/ 目录
- 视图处理：[job/views.py](job/views.py#L1-L680)

**主要功能**：
- 职位市场概览（总职位数、平均薪资等）
- 薪资分布可视化
- 学历要求统计
- 工作经验分布
- 行业分类统计
- 地域分布热力图
- 薪资排行榜 TOP10
- 实时数据更新

---

### 7.6 系统管理模块
**功能描述**：为管理员提供完整的系统管理功能，包括用户管理、数据管理、系统监控和配置管理。

**技术实现**：
- **管理后台**：Django Admin + django-simpleui 2024.8.28
- **界面美化**：SimpleUI 提供现代化的管理界面
- **权限控制**：基于 Django 的权限系统，仅管理员可访问
- **数据操作**：CRUD 操作、批量操作、数据导入导出
- **系统监控**：psutil 5.9.6 获取系统资源使用情况
- **日志记录**：Django 内置日志系统

**核心文件**：
- 管理配置：[job/admin.py](job/admin.py#L1-L131)
- 系统设置：[JobRecommend/settings.py](JobRecommend/settings.py#L1-L200)
- 视图处理：[job/views.py](job/views.py#L1-L680)

**主要功能**：
- **用户管理**：
  - 用户列表查看和搜索
  - 用户信息编辑和删除
  - 密码重置
  - 角色权限分配
  - 用户状态管理（冻结/解冻）

- **数据管理**：
  - 职位数据的增删改查
  - 爬虫信息管理
  - 投递记录查看
  - 批量数据操作
  - 数据清理和维护

- **爬虫管理**：
  - 爬虫任务启动和停止
  - 爬虫状态监控
  - 爬虫历史记录查看
  - 爬虫配置管理
  - 异常处理和重试

- **系统监控**：
  - CPU 使用率监控
  - 内存使用情况
  - 任务队列状态
  - 系统日志查看
  - 性能指标统计

---

### 7.7 前端交互模块
**功能描述**：提供用户友好的前端界面，实现与后端的数据交互和用户体验优化。

**技术实现**：
- **前端框架**：jQuery 3.6.0 + Layui 2.7.6
- **UI 组件**：Layui 的表单、表格、弹窗、分页等组件
- **数据交互**：AJAX 异步请求，支持 JSON 数据格式
- **模板引擎**：Django Template Language
- **响应式设计**：支持移动端和桌面端适配
- **文件上传**：支持拖拽上传和点击上传

**核心文件**：
- 模板文件：templates/ 目录下的所有 HTML 文件
- 静态资源：static/layuiadmin/ 目录
- 样式文件：static/layuiadmin/style/ 目录

**主要功能**：
- 用户登录和注册界面
- 职位搜索和筛选界面
- 职位详情展示
- 简历上传和解析界面
- 匹配结果展示
- 个人中心管理
- 管理员后台界面
- 响应式布局和交互效果

---

八、关键模块索引
----
- 项目入口： [manage.py](manage.py#L1-L40)
- 配置： [JobRecommend/settings.py](JobRecommend/settings.py#L1-L200)
- 推荐引擎： [job/job_recommend.py](job/job_recommend.py#L1-L109)
- 爬虫： [job/tools.py](job/tools.py#L1-L400)
- 视图与路由： [job/views.py](job/views.py#L1-L680)
- 简历解析： [job/utils/resume_parser.py](job/utils/resume_parser.py#L1-L146)
- 相似度匹配： [job/algorithms/similarity_match.py](job/algorithms/similarity_match.py#L1-L53)
- 数据模型： [job/models.py](job/models.py#L1-L129)
- 管理配置： [job/admin.py](job/admin.py#L1-L131)
- 静态/模板： `templates/` 与 `static/` 目录

八、运维建议与安全
----
- 将数据库密码和密钥放入环境变量或 `.env`，并在生产环境中关闭 `DEBUG`、设置 `ALLOWED_HOSTS`。
- 为爬虫引入代理池、重试机制与速率限制以降低封禁风险。
- 对管理员操作启用详细日志审计，并考虑对关键操作（数据删除/任务重跑）做二次确认。

九、开发与扩展建议
----
- 后续可新增“企业HR”角色以支持企业发布与管理职位，构建求职者-企业-管理员三方闭环。
- 推荐模块可拆分成可配置微服务，通过配置中心调整权重与回滚策略。

十、联系与下一步
----
如果需要，我可以：
- 将 `JobRecommend/settings.py` 改为读取环境变量；
- 在仓库中添加演示数据导入脚本与更详细的 README（含截图与示例）；
- 或者帮助在本地执行 `migrate`、创建超级用户并启动服务以验证流程。

版权与免责声明
----
本项目仅作学习与演示使用，若用于生产请仔细审查爬虫合规性与数据来源合法性。

