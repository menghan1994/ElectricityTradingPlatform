"""MEDIUM: 公共 IP 地址校验与提取工具，消除 API 层重复代码。"""

import ipaddress

from fastapi import Request


def validate_ip(value: str) -> str | None:
    """校验 IP 地址格式，合法返回原值，否则返回 None。"""
    try:
        ipaddress.ip_address(value)
        return value
    except ValueError:
        return None


def get_client_ip(request: Request) -> str | None:
    """从请求中提取客户端 IP 地址（支持反向代理头部）。

    注意：X-Forwarded-For 取第一个 IP。生产环境中应配合 Nginx 的
    set_real_ip_from 和 real_ip_header 指令，确保仅信任可信代理。
    """
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        candidate = forwarded_for.split(",")[0].strip()
        validated = validate_ip(candidate)
        if validated:
            return validated
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        validated = validate_ip(real_ip.strip())
        if validated:
            return validated
    if request.client:
        return validate_ip(request.client.host)
    return None
