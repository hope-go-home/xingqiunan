# URL 安全守卫：拦截 Agent 通过 URL 工具访问内网/云元数据等私有地址
# 防御目标：SSRF（Server-Side Request Forgery）

import ipaddress
import socket
import re
from urllib.parse import urlparse

# 允许的 URL 协议
_ALLOWED_SCHEMES = {"http", "https"}

# 私网/特殊地址范围（含 IPv4 映射的 IPv6）
_PRIVATE_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),      # 环回
    ipaddress.ip_network("10.0.0.0/8"),        # A 类私网
    ipaddress.ip_network("172.16.0.0/12"),     # B 类私网
    ipaddress.ip_network("192.168.0.0/16"),    # C 类私网
    ipaddress.ip_network("169.254.0.0/16"),    # 链路本地
    ipaddress.ip_network("0.0.0.0/8"),         # 当前网络
    ipaddress.ip_network("100.64.0.0/10"),     # 共享地址空间
    ipaddress.ip_network("198.18.0.0/15"),     # 基准测试
    ipaddress.ip_network("224.0.0.0/4"),       # 多播
    ipaddress.ip_network("::1/128"),           # IPv6 环回
    ipaddress.ip_network("fc00::/7"),          # IPv6 唯一本地
    ipaddress.ip_network("fe80::/10"),         # IPv6 链路本地
]

# 云元数据地址（阿里云/AWS/GCP/Azure 全部封死）
_METADATA_HOSTS = {
    "169.254.169.254",   # AWS/GCP/Azure/阿里云 metadata
    "100.100.100.200",   # 阿里云 metadata
    "metadata.google.internal",  # GCP metadata
}

# 私网域名（本机/内网常见域名）
_PRIVATE_DOMAINS = {
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "::1",
}


def validate_public_url(url: str) -> tuple[bool, str]:
    """校验 URL 是否指向公网地址。返回 (通过, 原因)"""
    if not url or not isinstance(url, str):
        return False, "URL 不能为空"

    # 1. 协议检查
    try:
        parsed = urlparse(url)
    except Exception:
        return False, "URL 格式无效"

    if parsed.scheme.lower() not in _ALLOWED_SCHEMES:
        return False, f"仅支持 http/https 协议，当前: {parsed.scheme or '无'}"

    hostname = parsed.hostname
    if not hostname:
        return False, "URL 缺少主机名"

    # 2. 私网域名拦截
    low_host = hostname.lower()
    if low_host in _PRIVATE_DOMAINS:
        return False, f"禁止访问私网地址: {hostname}"

    # 3. 云元数据地址拦截
    if low_host in _METADATA_HOSTS:
        return False, f"禁止访问云元数据地址: {hostname}"

    # 4. DNS 解析 → 检查 IP 是否在私网范围内
    try:
        addrinfos = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
        for family, _, _, _, sockaddr in addrinfos:
            ip = ipaddress.ip_address(sockaddr[0])
            # 先检查元数据
            if str(ip) in _METADATA_HOSTS:
                return False, f"禁止访问云元数据地址: {hostname} -> {ip}"
            # 检查私网范围
            for net in _PRIVATE_NETWORKS:
                if ip in net:
                    return False, f"禁止访问私网地址: {hostname} -> {ip}"
    except socket.gaierror:
        return False, f"DNS 解析失败: {hostname}"
    except Exception:
        return False, f"URL 校验异常: {hostname}"

    return True, "OK"
