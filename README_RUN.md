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

- 数据全生命周期：爬虫调度（启动/停止/定时任务配置/异常处理/重试）、手动触发全量/增量爬取、数据清洗（增删改查）、数据备份与恢复、数据审核（过滤虚假/违规职位）。

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
| 爬虫调度 | ❌ 无权限 | ✅ 启动/停止/配置/监控 |
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
- selenium 4.15.2
- weasyprint 59.0 (用于生成 PDF 报告)
- pdfminer.six 20231228 (用于解析 PDF 简历)
- python-docx 0.8.11 (用于解析 DOCX 简历)
- scikit-learn 1.5.0 (用于文本相似度计算)
- numpy 2.0.0
- psutil 5.9.6
- lxml 4.9.3

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

六、爬虫与调度
----
- 爬虫实现位于 [job/tools.py](job/tools.py#L1-L400)，基于 Selenium + chromedriver。请把 `chromedriver.exe` 放到 [job/](job/)
- 推荐在管理员后台或定时任务（如 Windows Task Scheduler / cron）中运行爬虫；仅管理员具有调度/触发权限。
- 命令行示例（直接触发）：
```powershell
python -c "from job.tools import lieSpider; lieSpider('java','北京','1')"
```

七、关键模块索引
----
- 项目入口： [manage.py](manage.py#L1-L40)
- 配置： [JobRecommend/settings.py](JobRecommend/settings.py#L1-L200)
- 推荐引擎： [job/job_recommend.py](job/job_recommend.py#L1-L200)
- 爬虫： [job/tools.py](job/tools.py#L1-L400)
- 视图与路由： [job/views.py](job/views.py#L1-L680)
- 简历解析： [job/utils/resume_parser.py](job/utils/resume_parser.py#L1-L146)
- 相似度匹配： [job/algorithms/similarity_match.py](job/algorithms/similarity_match.py#L1-L53)
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

