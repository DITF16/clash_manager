from flask import Flask, render_template, request, jsonify
import yaml
import json
import os
from config_manager import ConfigManager

app = Flask(__name__)
config_manager = ConfigManager()


@app.route("/")
def index():
    """首页"""
    config = config_manager.load_config()
    return render_template("index.html", config=config)


@app.route("/api/proxies")
def get_proxies():
    """获取所有代理节点"""
    config = config_manager.load_config()
    proxies = [p["name"] for p in config.get("proxies", [])]
    return jsonify({"proxies": proxies})


@app.route("/api/proxy-groups")
def get_proxy_groups():
    """获取所有代理组"""
    config = config_manager.load_config()
    groups = config.get("proxy-groups", [])
    return jsonify({"proxy-groups": groups})


@app.route("/api/rules")
def get_rules():
    """获取所有规则"""
    config = config_manager.load_config()
    rules = config.get("rules", [])
    return jsonify({"rules": rules})


@app.route("/api/proxy-groups/add", methods=["POST"])
def add_proxy_group():
    """添加代理组"""
    data = request.json
    result = config_manager.add_proxy_group(data)
    return jsonify(result)


@app.route("/api/proxy-groups/update", methods=["POST"])
def update_proxy_group():
    """更新代理组"""
    data = request.json
    result = config_manager.update_proxy_group(data)
    return jsonify(result)


@app.route("/api/proxy-groups/delete", methods=["POST"])
def delete_proxy_group():
    """删除代理组"""
    data = request.json
    result = config_manager.delete_proxy_group(data.get("name"))
    return jsonify(result)


@app.route("/api/rules/add", methods=["POST"])
def add_rule():
    """添加规则"""
    data = request.json
    result = config_manager.add_rule(data)
    return jsonify(result)


@app.route("/api/rules/update", methods=["POST"])
def update_rule():
    """更新规则"""
    data = request.json
    result = config_manager.update_rule(data)
    return jsonify(result)


@app.route("/api/rules/delete", methods=["POST"])
def delete_rule():
    """删除规则"""
    data = request.json
    result = config_manager.delete_rule(data.get("index"))
    return jsonify(result)


@app.route("/api/config/save", methods=["POST"])
def save_config():
    """保存配置"""
    result = config_manager.save_config()
    return jsonify(result)


@app.route("/api/config/refresh", methods=["POST"])
def refresh_config():
    """刷新订阅（合并自定义配置）"""
    data = request.json
    subscription_url = data.get("subscription_url")
    result = config_manager.refresh_subscription(subscription_url)
    return jsonify(result)


@app.route("/api/config/export", methods=["GET"])
def export_config():
    """导出最终配置"""
    config = config_manager.get_merged_config()
    return jsonify({"config": yaml.dump(config, allow_unicode=True)})


@app.route('/api/modifications/save', methods=['POST'])
def save_modification():
    """保存当前修改为修改文件"""
    data = request.json
    mod_name = data.get('name')
    mod_description = data.get('description', '')
    config_data = data.get('config', {})
    
    result = config_manager.save_modification(mod_name, mod_description, config_data)
    return jsonify(result)


@app.route('/api/modifications/list', methods=['GET'])
def get_modifications_list():
    """获取所有修改文件列表"""
    result = config_manager.get_modifications_list()
    return jsonify(result)


@app.route('/api/modifications/apply', methods=['POST'])
def apply_modification():
    """应用修改文件"""
    data = request.json
    filename = data.get('filename')
    result = config_manager.apply_modification(filename)
    return jsonify(result)


@app.route('/api/modifications/delete', methods=['POST'])
def delete_modification():
    """删除修改文件"""
    data = request.json
    filename = data.get('filename')
    result = config_manager.delete_modification(filename)
    return jsonify(result)


@app.route('/api/rules/move', methods=['POST'])
def move_rule():
    """移动规则位置"""
    data = request.json
    result = config_manager.move_rule(data.get('index'), data.get('direction'))
    return jsonify(result)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
