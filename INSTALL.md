# 安装说明

## 快速安装

只需要一个命令即可完成安装：

```bash
python install.py
```

或者：

```bash
python3 install.py
```

## 安装步骤

安装脚本会自动完成以下操作：

1. ✅ 检查Python环境（需要Python 3.6+）
2. ✅ 创建虚拟环境（如果不存在）
3. ✅ 升级pip和setuptools
4. ✅ 安装项目（使用 `pip install -e .`）
5. ✅ 安装所有依赖（backtrader、ccxt等）
6. ✅ 验证安装是否成功

## 使用方法

安装完成后，运行策略：

```bash
# 激活虚拟环境
source venv/bin/activate

# 进入OKX策略目录
cd exchanges/okx

# 运行策略
python buy-order.py
```

或者使用运行脚本：

```bash
./run_okx.sh
```

## 注意事项

1. **API配置**：请确保 `exchanges/params.json` 中配置了正确的OKX API密钥和密码

2. **coincurve依赖**：如果遇到coincurve安装失败，这是可选依赖，不影响基本功能。如需安装：
   ```bash
   source venv/bin/activate
   pip install coincurve==20.0.0
   ```

3. **代理设置**：如果不需要代理，可以修改 `exchanges/okx/buy-order.py` 中的代理配置

## 系统要求

- Python 3.6 或更高版本
- Linux / macOS / Windows
- 网络连接（用于下载依赖）

## 故障排除

如果安装失败，请检查：

1. Python版本是否符合要求：`python3 --version`
2. 网络连接是否正常
3. 是否有足够的磁盘空间
4. 查看错误信息，根据提示解决问题

