#!/bin/bash
# OKX量化交易运行脚本

# 激活虚拟环境
source venv/bin/activate

# 进入OKX示例目录
cd exchanges/okx

# 运行buy-order.py
python buy-order.py