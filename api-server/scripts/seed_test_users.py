"""批量创建测试用户脚本 — 通过 API 登录管理员账号后创建不同角色的测试用户。

用法：
    python api-server/scripts/seed_test_users.py

默认连接 http://localhost:8000，可通过环境变量 API_BASE_URL 覆盖。
"""

import os
import sys

import httpx

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
ADMIN_USERNAME = os.getenv("SEED_ADMIN_USERNAME", "admin")
# 需要通过环境变量提供管理员密码
ADMIN_PASSWORD = os.getenv("SEED_ADMIN_PASSWORD", "")

# 测试用户列表：(username, display_name, phone, email, role)
TEST_USERS = [
    # 交易员
    ("lina", "李娜", "13800001001", "lina@example.com", "trader"),
    ("zhangwei", "张伟", "13800001002", "zhangwei@example.com", "trader"),
    ("wangfang", "王芳", "13800001003", "wangfang@example.com", "trader"),
    # 储能运维员
    ("liuyang", "刘洋", "13800002001", "liuyang@example.com", "storage_operator"),
    ("chenming", "陈明", "13800002002", "chenming@example.com", "storage_operator"),
    # 交易主管
    ("zhaojie", "赵杰", "13800003001", "zhaojie@example.com", "trading_manager"),
    # 高管只读
    ("sunli", "孙莉", "13800004001", "sunli@example.com", "executive_readonly"),
    # 额外管理员
    ("admin2", "备用管理员", "13800005001", "admin2@example.com", "admin"),
]


def main() -> None:
    if not ADMIN_PASSWORD:
        print("错误: 请设置环境变量 SEED_ADMIN_PASSWORD（管理员密码）")
        sys.exit(1)

    # 1. 登录管理员
    print(f"正在登录管理员账户 '{ADMIN_USERNAME}' ...")
    resp = httpx.post(
        f"{API_BASE_URL}/api/v1/auth/login",
        json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
        timeout=10,
    )
    if resp.status_code != 200:
        print(f"登录失败: {resp.status_code} {resp.text}")
        sys.exit(1)

    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("登录成功。\n")

    # 2. 批量创建用户
    created = []
    skipped = []
    failed = []

    for username, display_name, phone, email, role in TEST_USERS:
        resp = httpx.post(
            f"{API_BASE_URL}/api/v1/users",
            json={
                "username": username,
                "display_name": display_name,
                "phone": phone,
                "email": email,
                "role": role,
            },
            headers=headers,
            timeout=10,
        )

        if resp.status_code in (200, 201):
            data = resp.json()
            temp_pw = data["temp_password"]
            created.append((username, display_name, role, temp_pw))
            print(f"  ✅ {username} ({display_name}) [{role}] — 临时密码: {temp_pw}")
        elif resp.status_code == 409:
            skipped.append(username)
            print(f"  ⏭️  {username} 已存在，跳过")
        else:
            failed.append((username, resp.status_code, resp.text))
            print(f"  ❌ {username} 创建失败: {resp.status_code} {resp.text}")

    # 3. 汇总
    print(f"\n{'='*60}")
    print(f"创建完成: {len(created)} 个 | 跳过: {len(skipped)} 个 | 失败: {len(failed)} 个")

    if created:
        print(f"\n{'用户名':<12} {'姓名':<10} {'角色':<20} {'临时密码'}")
        print("-" * 60)
        for username, display_name, role, temp_pw in created:
            print(f"{username:<12} {display_name:<10} {role:<20} {temp_pw}")

    print("\n⚠️  请保存临时密码，首次登录后需修改！")


if __name__ == "__main__":
    main()
