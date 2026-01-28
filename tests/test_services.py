#!/usr/bin/env python3
"""Test database service connections"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from dotenv import load_dotenv
load_dotenv()


def test_redis():
    """Test Redis connection"""
    print("\n📡 Testing Redis...")
    try:
        import redis
        url = os.getenv("BOT_REDIS_URL", "redis://:@localhost:6379/1")
        r = redis.from_url(url)
        r.ping()
        print(f"   ✓ Redis connected: {url}")
        return True
    except Exception as e:
        print(f"   ✗ Redis failed: {e}")
        return False


def test_mysql():
    """Test MySQL connection"""
    print("\n📡 Testing MySQL...")
    try:
        import mysql.connector
        conn = mysql.connector.connect(
            host=os.getenv("MYSQL_HOST", "localhost"),
            port=int(os.getenv("MYSQL_PORT", 3306)),
            user=os.getenv("MYSQL_USER", "bot"),
            password=os.getenv("MYSQL_PASSWORD", "bot"),
            database=os.getenv("MYSQL_DATABASE", "bot"),
        )
        cursor = conn.cursor()
        cursor.execute("SELECT VERSION()")
        version = cursor.fetchone()
        print(f"   ✓ MySQL connected: {version[0]}")
        conn.close()
        return True
    except Exception as e:
        print(f"   ✗ MySQL failed: {e}")
        return False


def test_milvus():
    """Test Milvus connection"""
    print("\n📡 Testing Milvus...")
    try:
        from pymilvus import connections
        host = os.getenv("MILVUS_HOST", "localhost")
        port = os.getenv("MILVUS_PORT", "19530")
        connections.connect("default", host=host, port=port)
        print(f"   ✓ Milvus connected: {host}:{port}")
        connections.disconnect("default")
        return True
    except Exception as e:
        print(f"   ✗ Milvus failed: {e}")
        return False


if __name__ == "__main__":
    print("="*50)
    print("Testing Data Services")
    print("="*50)

    results = []
    results.append(("Redis", test_redis()))
    results.append(("MySQL", test_mysql()))
    results.append(("Milvus", test_milvus()))

    print("\n" + "="*50)
    print("Summary")
    print("="*50)

    all_ok = True
    for name, ok in results:
        status = "✓" if ok else "✗"
        print(f"  {status} {name}")
        if not ok:
            all_ok = False

    if all_ok:
        print("\n✅ All services connected!")
    else:
        print("\n⚠️  Some services failed. Check Docker containers.")
